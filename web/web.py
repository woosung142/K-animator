from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import requests
from pathlib import Path
import uuid


app = FastAPI()
BASE_DIR = Path(__file__).resolve().parent

# uploads 폴더를 정적 파일 경로로 마운트
app.mount("/uploads", StaticFiles(directory=BASE_DIR / "uploads"), name="uploads")

# 이미지 업로드 API
@app.post("/upload-image")
async def upload_image(image_file: UploadFile = File(...)):
    unique_id = uuid.uuid4().hex
    file_extension = Path(image_file.filename).suffix
    unique_filename = f"{unique_id}{file_extension}"
    file_path = Path("uploads") / unique_filename

    try:
        with open(file_path, "wb") as buffer:
            buffer.write(await image_file.read())
        return {"image_url": f"/uploads/{unique_filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 저장 실패: {e}")

# Azure Speech Service 환경 변수
SPEECH_KEY = os.getenv("SPEECH_KEY")
SPEECH_REGION = os.getenv("SPEECH_REGION")

# 정적 파일 서빙 디렉토리 마운트
app.mount("/static", StaticFiles(directory=BASE_DIR / "templates"), name="static")

@app.get("/")
async def root():
    return FileResponse(BASE_DIR / "web" / "index.html")

# Azure 인증 토큰 발급 API
@app.get("/api/get-speech-token")
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
