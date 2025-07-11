from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
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

# Blob 클라이언트 초기화
blob_service_client = BlobServiceClient(
    account_url=f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
    credential=AZURE_STORAGE_ACCOUNT_KEY
)

# 정적 파일 서빙 디렉토리 마운트
# app.mount("/static", StaticFiles(directory=BASE_DIR / "templates"), name="static")

# 메인 페이지
@app.get("/")
async def root():
    return FileResponse("index.html")

# 이미지 업로드 API
@app.post("/upload-image")
async def upload_image(image_file: UploadFile = File(...)):
    unique_id = uuid.uuid4().hex
    file_extension = Path(image_file.filename).suffix
    blob_name = f"{unique_id}{file_extension}"

    try:
        blob_client = blob_service_client.get_blob_client(container=AZURE_CONTAINER_NAME, blob=blob_name)
        await blob_client.upload_blob(image_file.file, overwrite=True)

        # SAS URL 생성 (유효기간 10분)
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Blob 업로드 실패: {e}")

# Azure 인증 토큰 발급 API
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

# 메시지 전송 API (에코 형식)
@app.post("/send-message")
async def send_message(request: Request):
    data = await request.json()
    messages = data.get("messages")
    session_id = data.get("sessionId")

    if not messages or not session_id:
        raise HTTPException(status_code=400, detail="메시지 또는 세션 ID가 없습니다.")

    print("[사용자 입력]", messages)
    return JSONResponse(content={"text": f"'{messages}' 메시지를 잘 받았습니다."})
