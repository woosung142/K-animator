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

# 정적 파일(index.html, CSS, JS 등)을 서빙할 디렉토리 마운트
# /static 경로로 접근하면 templates 폴더의 파일들을 서빙합니다.
app.mount("/static", StaticFiles(directory=BASE_DIR / "templates"), name="static")

# Jinja2Templates를 사용하는 경우 (더 복잡한 HTML 템플릿에 유용)
# templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/")
async def root():
    # StaticFiles를 사용하면 직접 파일 경로를 지정하지 않고,
    # /static/index.html 경로로 리다이렉트하거나,
    # Jinja2Templates를 사용하여 렌더링할 수 있습니다.
    # 여기서는 /static/index.html로 리다이렉트하는 예시를 들겠습니다.
    # 또는 그냥 /static/index.html을 직접 브라우저에서 접근하게 할 수도 있습니다.
    
    # 만약 Jinja2Templates를 사용한다면:
    # return templates.TemplateResponse("index.html", {"request": request})

    # 간단하게 index.html을 직접 반환하려면 FileResponse를 계속 사용할 수 있지만,
    # 경로를 templates 폴더 안으로 변경해야 합니다.
    return FileResponse(BASE_DIR / "templates" / "index.html")


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

