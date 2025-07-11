from celery import Celery
from io import BytesIO
from PIL import Image
import requests
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
import uuid
import os
import subprocess
from dotenv import load_dotenv
from openai import AzureOpenAI
from datetime import datetime, timedelta

# .env 로딩
load_dotenv()

# Azure OpenAI 설정
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_VERSION = "2024-05-01-preview"

client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version=AZURE_OPENAI_VERSION
)

# Azure Blob 설정
AZURE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME", "images")

AZURE_CONNECTION_STRING = (
    f"DefaultEndpointsProtocol=https;"
    f"AccountName={AZURE_ACCOUNT_NAME};"
    f"AccountKey={AZURE_ACCOUNT_KEY};"
    f"EndpointSuffix=core.windows.net"
)

blob_service = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
container_client = blob_service.get_container_client(AZURE_CONTAINER_NAME)

# SAS URL 생성 함수
def generate_sas_url(account_name, account_key, container_name, blob_name, expiry_minutes=10):
    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(minutes=expiry_minutes)
    )
    return f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"

# Celery 설정
celery_app = Celery(
    'worker',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0'
)

@celery_app.task(name="generate_image", bind=True)
def generate_image(self, prompt: str, image_url: str | None = None) -> dict:
    try:
        task_id = self.request.id

        # DALL·E API 요청 (현재는 image_url 사용 불가이므로 프롬프트만 전달)
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            n=1
        )
        dalle_image_url = response.data[0].url

        # DALL·E 생성 이미지 다운로드
        dalle_image_data = requests.get(dalle_image_url).content
        dalle_img = Image.open(BytesIO(dalle_image_data))

        # PNG 저장 → Azure 업로드
        png_buffer = BytesIO()
        dalle_img.save(png_buffer, format="PNG")
        png_buffer.seek(0)
        filename_png = f"{task_id}.png"
        container_client.upload_blob(name=filename_png, data=png_buffer, overwrite=True)

        # SAS URL로 PNG 접근 주소 생성
        png_url = generate_sas_url(AZURE_ACCOUNT_NAME, AZURE_ACCOUNT_KEY, AZURE_CONTAINER_NAME, filename_png)

        # PSD 저장 (ImageMagick 이용)
        temp_png_path = f"/tmp/{task_id}.png"
        temp_psd_path = f"/tmp/{task_id}.psd"
        dalle_img.save(temp_png_path, format="PNG")
        subprocess.run(["convert", temp_png_path, temp_psd_path], check=True)

        # PSD 업로드
        with open(temp_psd_path, "rb") as f:
            container_client.upload_blob(name=f"{task_id}.psd", data=f, overwrite=True)

        # SAS URL로 PSD 접근 주소 생성
        psd_url = generate_sas_url(AZURE_ACCOUNT_NAME, AZURE_ACCOUNT_KEY, AZURE_CONTAINER_NAME, f"{task_id}.psd")

        # 임시파일 삭제
        os.remove(temp_png_path)
        os.remove(temp_psd_path)

        return {
            "status": "SUCCESS",
            "png_url": png_url,
            "psd_url": psd_url
        }

    except Exception as e:
        return {
            "status": "FAILURE",
            "error": str(e)
        }
