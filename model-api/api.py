from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from celery import Celery
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

# CORS 허용 (개발 중에는 전체 허용, 배포시 제한 권장)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Celery 설정
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
celery_app = Celery("model-api", broker=CELERY_BROKER_URL)
celery_app.conf.result_backend = CELERY_BROKER_URL

# 입력값 스키마
class PromptRequest(BaseModel):
    category: str
    layer: str
    tag: str
    caption_input: str | None = None
    image_url: str | None = None

class FinalPromptRequest(BaseModel):
    dalle_prompt: str  

@app.post("/api/generate-prompt")
async def generate_prompt_endpoint(request: PromptRequest):
    data = await request.json()
    print("[실제 전달받은 요청 JSON]", data)
    print(f"[REQUEST] POST /api/generate-image")
    print(f"[DATA] category: {request.category}")
    print(f"[DATA] layer: {request.layer}")
    print(f"[DATA] tag: {request.tag}")
    print(f"[DATA] caption_input: {request.caption_input}")
    print(f"[DATA] image_url: {request.image_url}")

    task = celery_app.send_task(
        "generate_image",
        args=[
            request.category,       
            request.layer,
            request.tag,
            request.caption_input,
            request.image_url
        ]
    )
    print(f"[TASK] Celery task 전송 완료 - task_id: {task.id}")
    return {"task_id": task.id}

@app.post("/api/generate-image-from-prompt")
async def generate_image_from_prompt(request: FinalPromptRequest):
    print("[REQUEST] POST /api/generate-image-from-prompt")
    task = celery_app.send_task(
        "generate_final_image",
        args=[request.dalle_prompt]
    )
    print(f"[TASK]celery 'generate_final_image' task 전송 완료 - task_id: {task.id}")
    return {"task_id": task.id}

@app.get("/api/result/{task_id}")
async def get_result(task_id: str):
    print(f"[REQUEST] GET /api/result/{task_id}")
    result = celery_app.AsyncResult(task_id)
    print(f"[INFO] 현재 상태: {result.state}")

    if result.state == "PENDING":
        return {"status": "PENDING"}
    elif result.state == "SUCCESS":
        print(f"[SUCCESS] 결과 수신 완료: {result.result}")
        return {
            "status": "SUCCESS",
            "png_url": result.result.get("png_url"),
            "psd_url": result.result.get("psd_url")
        }
    elif result.state == "FAILURE":
        print(f"[ERROR] Celery 태스크 실패: {result.result}")
        raise HTTPException(status_code=500, detail="Task failed")
    else:
        print(f"[INFO] 기타 상태: {result.state}")
        return {"status": result.state}