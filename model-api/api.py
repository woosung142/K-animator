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
    caption_input: str | None = None
    category: str
    layer: str
    tag: str
    image_url: str | None = None  # 현재 미사용, 확장 대비 포함

@app.post("/api/generate-image")
async def generate_image(request: PromptRequest):
    task = celery_app.send_task(
        "generate_image",
        args=[
            request.caption_input,
            request.category,
            request.layer,
            request.tag,
            request.image_url 
        ]
    )
    return {"task_id": task.id}

@app.get("/api/result/{task_id}")
async def get_result(task_id: str):
    result = celery_app.AsyncResult(task_id)
    if result.state == "PENDING":
        return {"status": "PENDING"}
    elif result.state == "SUCCESS":
        return {
            "status": "SUCCESS",
            "png_url": result.result.get("png_url"),
            "psd_url": result.result.get("psd_url")
        }
    elif result.state == "FAILURE":
        raise HTTPException(status_code=500, detail="Task failed")
    else:
        return {"status": result.state}
