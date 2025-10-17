from dotenv import load_dotenv
from celery import Celery
from celery.signals import after_setup_logger
from io import BytesIO
from PIL import Image
import requests
import os
import subprocess
from openai import AzureOpenAI
import logging
import base64

from shared import blob_storage

# --- 환경변수 로딩 ---
load_dotenv()
#  gpt-image-1
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://gbsa0-mcsqr6kr-swedencentral.cognitiveservices.azure.com/")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-image-1")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview") # gpt-image-1

# Azure Blob Storage 환경변수
AZURE_ACCOUNT_NAME = os.getenv("AZURE_ACCOUNT_NAME")
AZURE_ACCOUNT_KEY = os.getenv("AZURE_ACCOUNT_KEY")
AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME")

celery_app = Celery('worker', broker='redis://redis:6379/0', backend='redis://redis:6379/0')

# --- 로거 설정 ---
@after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    formatter = logging.Formatter('[%(asctime)s: %(levelname)s/%(processName)s] %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# --- Azure OpenAI 클라이언트 초기화 ---
client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version=AZURE_OPENAI_API_VERSION
)

@celery_app.task(name="gpt_image", bind=True)
def generate_image(self, text_prompt: str, image_url: str | None = None) -> dict:
    task_id = self.request.id
    logging.info(f"[TASK] gpt_image 시작 - task_id: {task_id}")
    logging.info(f"[INPUT] text_prompt: {text_prompt}")

    try:
        final_prompt = f"A Korean-style webtoon background scene of: {text_prompt}"
        logging.info(f"[STEP 1] 최종 생성 프롬프트: {final_prompt}")

        # --- FIX: openai 라이브러리를 사용하여 API 호출 ---
        response = client.images.generate(
            model=AZURE_OPENAI_DEPLOYMENT,
            prompt=final_prompt,
            n=1,
            size="1024x1024",
            quality="hd"
        )
        
        b64_image = response.data[0].b64_json
        logging.info(f"[STEP 2] 이미지 생성 완료 : {b64_image[:30]}...")

        # --- 이하 로직은 동일 ---
        image_data = base64.b64decode(b64_image)
        pil_image = Image.open(BytesIO(image_data))

        filename_png = f"public/generated/png/{task_id}.png"
        filename_psd = f"public/generated/psd/{task_id}.psd"

        png_buffer = BytesIO()
        pil_image.save(png_buffer, format="PNG")
        png_buffer.seek(0)
        blob_storage.upload_blob(name=filename_png, data=png_buffer, overwrite=True)
        logging.info(f"[STEP 5] PNG Blob 저장 완료: {filename_png}")
        png_buffer.close()

        temp_png_path = f"/tmp/{task_id}.png"
        temp_psd_path = f"/tmp/{task_id}.psd"
        pil_image.save(temp_png_path, format="PNG")
        
        subprocess.run(["convert", temp_png_path, temp_psd_path], check=True)
        
        with open(temp_psd_path, "rb") as f:
            blob_storage.upload_blob(name=filename_psd, data=f, overwrite=True)
        logging.info(f"[STEP 6] PSD Blob 저장 완료: {filename_psd}")

        os.remove(temp_png_path)
        os.remove(temp_psd_path)

        png_url = blob_storage.generate_sas_url(AZURE_ACCOUNT_NAME, AZURE_ACCOUNT_KEY, AZURE_CONTAINER_NAME, filename_png)
        psd_url = blob_storage.generate_sas_url(AZURE_ACCOUNT_NAME, AZURE_ACCOUNT_KEY, AZURE_CONTAINER_NAME, filename_psd)

        logging.info(f"[SUCCESS] 작업 완료 - task_id: {task_id}")
        return {"status": "SUCCESS", "png_url": png_url, "psd_url": psd_url}

    except Exception as e:
        logging.error(f"[ERROR] 전체 프로세스 실패 (task_id: {task_id}): {e}", exc_info=True)
        raise e

