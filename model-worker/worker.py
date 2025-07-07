from celery import Celery
from io import BytesIO
from PIL import Image
import torch
from diffusers import StableDiffusionPipeline
from azure.storage.blob import BlobServiceClient
import uuid
import os
from dotenv import load_dotenv

# .env 로딩
load_dotenv()

# Azure Blob 설정 (환경변수에서 조립)
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

# 디바이스 설정
device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if device == "cuda" else torch.float32

# 모델 로딩
pipe = StableDiffusionPipeline.from_pretrained(
    "nota-ai/bk-sdm-tiny",
    torch_dtype=dtype
).to(device)
pipe.enable_attention_slicing()

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
        img = pipe(prompt, num_inference_steps=25, guidance_scale=7.5).images[0]

        # PNG 저장
        png_buffer = BytesIO()
        img.save(png_buffer, format="PNG")
        png_buffer.seek(0)
        filename_png = f"{task_id}.png"
        container_client.upload_blob(name=filename_png, data=png_buffer, overwrite=True)
        png_url = f"https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net/{AZURE_CONTAINER_NAME}/{filename_png}"

        # PSD 저장
        psd_buffer = BytesIO()
        img.save(psd_buffer, format="PSD")  # Pillow 10.1+ 필요
        psd_buffer.seek(0)
        filename_psd = f"{task_id}.psd"
        container_client.upload_blob(name=filename_psd, data=psd_buffer, overwrite=True)
        psd_url = f"https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net/{AZURE_CONTAINER_NAME}/{filename_psd}"

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
