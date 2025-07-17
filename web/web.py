from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from PIL import Image
import io
import os
import requests
from pathlib import Path
import uuid
from datetime import datetime, timedelta

app = FastAPI()

# Blob Storage 환경변수
AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_STORAGE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
AZURE_CONTAINER_NAME = "user-uploads"

# 업로드 최대 허용 용량
MAX_MB = 10
MAX_SIZE = MAX_MB * 1024 * 1024

# Blob 클라이언트 초기화
blob_service_client = BlobServiceClient(
    account_url=f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
    credential=AZURE_STORAGE_ACCOUNT_KEY
)

@app.get("/")
async def root():
    return FileResponse("index.html")

# 이미지 업로드 및 리사이징 API
@app.post("/upload-image")
async def upload_image(image_file: UploadFile = File(...)):
    unique_id = uuid.uuid4().hex
    file_extension = Path(image_file.filename).suffix
    blob_name = f"{unique_id}.png"  # 통일된 확장자 사용

    try:
        contents = await image_file.read()
        
        # 파일 크기 체크
        if len(contents) > MAX_SIZE:
            raise HTTPException(status_code=413, detail=f"이미지 크기는 최대 {MAX_MB}MB까지 허용됩니다.")

        # PIL 이미지 열기 및 리사이즈 (최대 1024px)
        image = Image.open(io.BytesIO(contents))
        image = image.convert("RGB")
        image.thumbnail((1024, 1024))

        # PNG로 저장 (압축)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)

        # Blob 업로드
        blob_client = blob_service_client.get_blob_client(
            container=AZURE_CONTAINER_NAME,
            blob=blob_name
        )
        blob_client.upload_blob(buffer.getvalue(), overwrite=True)

        # 버퍼 초기화 (리소스 해제 목적)
        buffer.close()

        # SAS URL 생성
        sas_token = generate_blob_sas(
            account_name=AZURE_STORAGE_ACCOUNT_NAME,
            container_name=AZURE_CONTAINER_NAME,
            blob_name=blob_name,
            account_key=AZURE_STORAGE_ACCOUNT_KEY,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(minutes=10)
        )
        blob_url = f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{AZURE_CONTAINER_NAME}/{blob_name}?{sas_token}"

        return {"image_url": blob_url}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Blob 업로드 실패: {e}")

# Azure Speech 토큰 발급 API
SPEECH_KEY = os.getenv("SPEECH_KEY")
SPEECH_REGION = os.getenv("SPEECH_REGION")

@app.get("/get-speech-token")
async def get_speech_token():
    if not SPEECH_KEY or not SPEECH_REGION:
        raise HTTPException(status_code=500, detail="Azure Speech Service 환경 변수가 설정되지 않았습니다.")

    fetch_token_url = f'https://{SPEECH_REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken'
    headers = {
        'Ocp-Apim-Subscription-Key': SPEECH_KEY,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    try:
        response = requests.post(fetch_token_url, headers=headers)
        response.raise_for_status()
        return JSONResponse({'token': response.text, 'region': SPEECH_REGION})
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))
