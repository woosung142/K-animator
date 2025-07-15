from celery import Celery
from io import BytesIO
from PIL import Image
import requests
import os
import subprocess
import psycopg2
import base64
import torch
from datetime import datetime, timedelta
from transformers import AutoProcessor, AutoModel
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

# 환경변수 로딩
load_dotenv()
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_VERSION = "2024-05-01-preview"
PG_HOST = os.getenv("PG_HOST")
PG_PORT = os.getenv("PG_PORT")
PG_DBNAME = os.getenv("PG_DBNAME")
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")
AZURE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
AZURE_CONTAINER_NAME = "rag-images"
AZURE_CONNECTION_STRING = f"DefaultEndpointsProtocol=https;AccountName={AZURE_ACCOUNT_NAME};AccountKey={AZURE_ACCOUNT_KEY};EndpointSuffix=core.windows.net"

# KoCLIP 모델 로딩
processor = AutoProcessor.from_pretrained("koclip/koclip-base-pt")
model = AutoModel.from_pretrained("koclip/koclip-base-pt").eval().to("cuda" if torch.cuda.is_available() else "cpu")
device = next(model.parameters()).device

# 클라이언트 초기화
client = AzureOpenAI(api_key=AZURE_OPENAI_KEY, azure_endpoint=AZURE_OPENAI_ENDPOINT, api_version=AZURE_OPENAI_VERSION)
blob_service = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
container_client = blob_service.get_container_client(AZURE_CONTAINER_NAME)

# Celery 설정
celery_app = Celery('worker', broker='redis://redis:6379/0', backend='redis://redis:6379/0')

# 유틸 함수
def embed_text_koclip(text):
    inputs = processor(text=[text], return_tensors="pt", truncation=True, padding=True).to(device)
    with torch.no_grad():
        embedding = model.get_text_features(**inputs)
    return embedding[0].cpu().numpy().tolist()

def get_blob_base64_image(blob_dir, file_name):
    try:
        blob_path = f"{blob_dir}/{file_name}.png"
        blob_client = container_client.get_blob_client(blob=blob_path)
        stream = blob_client.download_blob()
        img_bytes = stream.readall()
        image = Image.open(BytesIO(img_bytes))
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"[ERROR] Blob 이미지 로딩 실패 - {file_name}: {e}")
        return None

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

# 메인 태스크
@celery_app.task(name="generate_image", bind=True)
def generate_image(self, category: str, layer: str, tag: str, caption_input: str | None = None, image_url: str | None = None) -> dict:
    try:
        task_id = self.request.id

        # 1. KoCLIP 임베딩, 빈값일때 기본값으로 설정
        text_to_embed = caption_input if caption_input else f"{tag}가 포함된 한국풍의 장면을 그려줘"
        embedding_vector = embed_text_koclip(text_to_embed)
        vector_str = "[" + ",".join([str(x) for x in embedding_vector]) + "]"

        # 2. DB 유사 이미지 검색
        conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DBNAME, user=PG_USER, password=PG_PASSWORD)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT file_name FROM korea_image_data
            WHERE category = %s AND layer = %s AND tag ILIKE %s
            ORDER BY vec_caption <-> %s::vector
            LIMIT 3;
            """,
            (category, layer, f"%{tag}%", vector_str)
        )
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        if not results:
            return {"status": "FAILURE", "error": "No similar images found in DB"}

        # 3. Blob에서 base64 이미지 로딩
        images_content = []
        for row in results:
            file_name = row[0]
            image_b64 = get_blob_base64_image("img", file_name)
            if image_b64:
                images_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_b64}"
                    }
                })

        if not images_content:
            return {"status": "FAILURE", "error": "No matching image files found in Blob Storage"}

        # 4. GPT-4o 프롬프트 생성
        messages = [{
            "role": "user",
            "content": [{"type": "text", "text": "다음 여러 이미지를 바탕으로, 한국적인 분위기를 살린 그림처럼 묘사된 장면을 DALL·E 3에 전달할 수 있도록 영어로 프롬프트를 작성해줘. 너무 세밀하게 표현하지 말고 간단한 웹툰 그림으로 그릴 수 있게 요청해줘"}] + images_content
        }]
        response = client.chat.completions.create(model="gpt-4o", messages=messages, max_tokens=800, temperature=0.7)
        dalle_prompt = response.choices[0].message.content.strip()

        # 5. DALL·E 3 이미지 생성
        dalle_response = client.images.generate(model="dall-e-3", prompt=dalle_prompt, size="1024x1024", n=1)
        image_url = dalle_response.data[0].url
        dalle_image_data = requests.get(image_url).content
        dalle_img = Image.open(BytesIO(dalle_image_data))

        # 6. Blob 저장: png/ 하위에 저장
        png_buffer = BytesIO()
        dalle_img.save(png_buffer, format="PNG")
        png_buffer.seek(0)
        filename_png = f"png/{task_id}.png"
        container_client.upload_blob(name=filename_png, data=png_buffer, overwrite=True)
        png_url = generate_sas_url(AZURE_ACCOUNT_NAME, AZURE_ACCOUNT_KEY, AZURE_CONTAINER_NAME, filename_png)

        # 7. PSD 변환 후 psd/ 하위에 저장
        temp_png_path = f"/tmp/{task_id}.png"
        temp_psd_path = f"/tmp/{task_id}.psd"
        dalle_img.save(temp_png_path, format="PNG")
        subprocess.run(["convert", temp_png_path, temp_psd_path], check=True)
        with open(temp_psd_path, "rb") as f:
            container_client.upload_blob(name=f"psd/{task_id}.psd", data=f, overwrite=True)
        psd_url = generate_sas_url(AZURE_ACCOUNT_NAME, AZURE_ACCOUNT_KEY, AZURE_CONTAINER_NAME, f"psd/{task_id}.psd")

        os.remove(temp_png_path)
        os.remove(temp_psd_path)

        return {"status": "SUCCESS", "png_url": png_url, "psd_url": psd_url}

    except Exception as e:
        return {"status": "FAILURE", "error": str(e)}