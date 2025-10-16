from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles 
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from starlette.requests import Request
from starlette.responses import Response
from PIL import Image
import io
import os
import requests
from pathlib import Path
import uuid
from datetime import datetime, timedelta
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session

from shared.db import crud, database, models    # 공유폴더
from shared.dependencies import get_user_id_from_gateway # 공유폴더
from shared import blob_storage

router = APIRouter(
    tags=["유틸리티 API"]
)
# Azure Speech 토큰 발급 API
SPEECH_KEY = os.getenv("SPEECH_KEY")
SPEECH_REGION = os.getenv("SPEECH_REGION")

# 업로드 최대 허용 용량
MAX_MB = 10
MAX_SIZE = MAX_MB * 1024 * 1024

# 업로드 크기 제한 해제 미들웨어 정의
class LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_upload_size: int):
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_upload_size:
            return Response(
                content=f"파일 크기가 너무 큽니다. 최대 {self.max_upload_size // (1024 * 1024)}MB까지 허용됩니다.",
                status_code=413
            )
        return await call_next(request)

# 이미지 업로드 및 리사이징 API
@router.post("/upload-image")
async def upload_image(
    image_file: UploadFile = File(...),
    user_id: str = Depends(get_user_id_from_gateway) # 게이트웨이에서 사용자 ID 추출
):
    unique_id = uuid.uuid4().hex
    file_extension = Path(image_file.filename).suffix
    blob_name = f"user_{user_id}/uploads/{unique_id}.png"  # 통일된 확장자 사용

    try:
        print(f"[요청 수신] 파일명: {image_file.filename}")
        contents = await image_file.read()
        print(f"[파일 크기] {len(contents)} bytes")

        # 파일 크기 체크
        if len(contents) > MAX_SIZE:
            print(f"[오류] 파일 크기 초과: {len(contents)} bytes > {MAX_SIZE} bytes")
            raise HTTPException(status_code=413, detail=f"이미지 크기는 최대 {MAX_MB}MB까지 허용됩니다.")

        # PIL 이미지 열기 및 리사이즈 (최대 1024px)
        image = Image.open(io.BytesIO(contents))
        image = image.convert("RGB")
        image.thumbnail((1024, 1024))
        print("[처리] 이미지 변환 및 썸네일 생성 완료")

        # PNG로 저장 (압축)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        print("[처리] PNG 변환 완료, 업로드 준비")

        # Blob 업로드
        blob_storage.upload_blob(blob_name=blob_name, data=buffer.getvalue())

        # 버퍼 초기화 (리소스 해제 목적)
        buffer.close()
        print(f"[업로드 완료] Blob 이름: {blob_name}")

        blob_url = blob_storage.generate_sas_url(blob_name=blob_name, expiry_minutes=10)

        print(f"[SAS URL] {blob_url}")
        return {"image_url": blob_url}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[예외 발생] {e}")
        raise HTTPException(status_code=500, detail=f"Blob 업로드 실패: {e}")

@router.get("/get-speech-token")
async def get_speech_token(
    user_id: str = Depends(get_user_id_from_gateway)
):
    print("[요청 수신] /get-speech-token 호출")

    if not SPEECH_KEY or not SPEECH_REGION:
        print("[오류] 환경 변수 누락: SPEECH_KEY 또는 SPEECH_REGION이 설정되지 않음")
        raise HTTPException(status_code=500, detail="Azure Speech Service 환경 변수가 설정되지 않았습니다.")

    fetch_token_url = f'https://{SPEECH_REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken'
    headers = {
        'Ocp-Apim-Subscription-Key': SPEECH_KEY,
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    print(f"[전송 준비] 요청 URL: {fetch_token_url}")
    try:
        response = requests.post(fetch_token_url, headers=headers)
        response.raise_for_status()
        print("[응답 수신] 토큰 발급 성공")
        return JSONResponse({'token': response.text, 'region': SPEECH_REGION})
    except requests.exceptions.RequestException as e:
        print(f"[예외 발생] 토큰 발급 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/my-images", summary="내 이미지 목록 조회")
def read_images(
    user_id: str = Depends(get_user_id_from_gateway),
    db: Session = Depends(database.get_db)
):
    images_from_db = crud.get_images_by_user(db=db, user_id=user_id)
    
    response_images = []
    for image in images_from_db:
        # 각 이미지의 파일 경로를 사용하여 실시간으로 SAS URL을 생성합니다.
        png_sas_url = blob_storage.generate_sas_url(blob_name=image.png_url, expiry_minutes=5)
        psd_sas_url = blob_storage.generate_sas_url(blob_name=image.psd_url, expiry_minutes=5)

        # 3. 동적으로 생성된 SAS URL을 담아 응답 목록에 추가합니다.
        response_images.append({
            "id": image.id,
            "png_url": png_sas_url,
            "psd_url": psd_sas_url,
            "created_at": image.created_at
        })
        
    return response_images