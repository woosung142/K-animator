from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os
import requests
from pathlib import Path

load_dotenv()

app = FastAPI()
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")
BASE_DIR = Path(__file__).resolve().parent

# --- [추가] uploads 폴더를 정적 파일 경로로 마운트 ---
# 이렇게 해야 /uploads/filename.png 같은 URL로 이미지에 접근 가능
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# --- [추가] 이미지 업로드 API 엔드포인트 ---
@app.post("/upload-image")
async def upload_image(image_file: UploadFile = File(...)):
    # 고유한 파일 이름 생성 (파일 이름 충돌 방지)
    unique_id = uuid.uuid4().hex
    file_extension = Path(image_file.filename).suffix
    unique_filename = f"{unique_id}{file_extension}"
    
    file_path = Path("uploads") / unique_filename

    try:
        # 파일을 서버의 uploads 폴더에 저장
        with open(file_path, "wb") as buffer:
            buffer.write(await image_file.read())
        
        # 클라이언트가 접근할 수 있는 이미지 URL 반환
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
    return FileResponse(BASE_DIR / "templates" / "index.html")

# Azure 인증 토큰 발급 API
@app.get("/api/get-speech-token")
async def get_speech_token():
    """Azure Speech Service용 인증 토큰을 발급합니다."""
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

@app.post("/send-message")
async def send_message(request: Request):
    data = await request.json()
    messages = data.get("messages")
    session_id = data.get("sessionId")

    if not messages or not session_id:
        raise HTTPException(status_code=400, detail="메시지 또는 세션 ID가 없습니다.")

    try:
        full_url = f"{N8N_WEBHOOK_URL}?sessionId={session_id}"
        n8n_response = requests.post(full_url, json={"chatInput": messages}, timeout=15)
        n8n_response.raise_for_status()

        resp_json = n8n_response.json()
        print("[n8n 응답]", resp_json)  # 디버깅용 출력

        text = resp_json.get("output", "[빈 응답]")
        return JSONResponse(content={"text": text})

    except requests.exceptions.RequestException as e:
        print("n8n 통신 오류:", e)
        raise HTTPException(status_code=500, detail="챗봇 서버와 통신할 수 없습니다.")

# --- [수정된 부분] ---
if __name__ == "__main__":
    import uvicorn
    
    # HTTPS 적용을 위해 SSL 옵션 추가
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=443,  # HTTPS 기본 포트
        reload=True,
        ssl_keyfile="/etc/letsencrypt/live/prtest.shop/privkey.pem",
        ssl_certfile="/etc/letsencrypt/live/prtest.shop/fullchain.pem"
    )