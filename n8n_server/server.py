from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles # StaticFiles 임포트
from fastapi.templating import Jinja2Templates # Jinja2Templates 임포트 (선택 사항)
from dotenv import load_dotenv
import os
import requests
from pathlib import Path

load_dotenv()

app = FastAPI()
PORT = int(os.getenv("PORT", 3000))
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")
BASE_DIR = Path(__file__).resolve().parent

# Azure Speech Service 환경 변수
SPEECH_KEY = os.getenv("SPEECH_KEY")
SPEECH_REGION = os.getenv("SPEECH_REGION")

# 정적 파일(index.html, CSS, JS 등)을 서빙할 디렉토리 마운트
# /static 경로로 접근하면 templates 폴더의 파일들을 서빙합니다.
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

    except requests.RequestException as e:
        print("n8n 통신 오류:", e)
        raise HTTPException(status_code=500, detail="챗봇 서버와 통신할 수 없습니다.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)

