from celery import Celery
from io import BytesIO
from PIL import Image
import requests
from azure.storage.blob import BlobServiceClient
import uuid
import os
import subprocess
from dotenv import load_dotenv
from openai import AzureOpenAI

# .env 로딩
load_dotenv()

# Azure OpenAI 설정
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_VERSION = "2024-05-01-preview"  # 필요 시 버전 고정

client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version="2024-05-01-preview"
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

# Celery 설정
celery_app = Celery(
    'worker',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0'
)

@celery_app.task(name="generate_image", bind=True)
def generate_image(self, prompt: str) -> dict:
    try:
        task_id = self.request.id

        # Azure OpenAI에 이미지 생성 요청
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            n=1
        )
        image_url = response.data[0].url

        # 이미지 다운로드
        image_data = requests.get(image_url).content
        img = Image.open(BytesIO(image_data))

        # PNG 저장 및 업로드
        png_buffer = BytesIO()
        img.save(png_buffer, format="PNG")
        png_buffer.seek(0)
        filename_png = f"{task_id}.png"
        container_client.upload_blob(name=filename_png, data=png_buffer, overwrite=True)
        png_url = f"https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net/{AZURE_CONTAINER_NAME}/{filename_png}"

        # PSD 저장 (ImageMagick 이용)
        temp_png_path = f"/tmp/{task_id}.png"
        temp_psd_path = f"/tmp/{task_id}.psd"
        img.save(temp_png_path, format="PNG")
        subprocess.run(["convert", temp_png_path, temp_psd_path], check=True)

        # PSD 업로드
        with open(temp_psd_path, "rb") as f:
            container_client.upload_blob(name=f"{task_id}.psd", data=f, overwrite=True)
        psd_url = f"https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net/{AZURE_CONTAINER_NAME}/{task_id}.psd"

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
