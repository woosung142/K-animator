from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from celery import Celery
import os
import logging

router = APIRouter(
    tags=["GPT API"]
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImagePromptRequest(BaseModel):
    text_prompt: str
    image_url: str | None = None

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")  #배포 전 수정
celery_app = Celery("worker", broker=CELERY_BROKER_URL)
celery_app.conf.result_backend = CELERY_BROKER_URL

@router.post("/generate-image")
async def generate_image_task(
    request: ImagePromptRequest
):
    if not request.text_prompt or not request.text_prompt.strip():
        raise HTTPException(status_code=400, detail="Text prompt cannot be empty.")

    logging.info(f"[REQUEST] POST /api/generate-image")
    logging.info(f"[DATA] prompt: {request.text_prompt}")
    logging.info(f"[DATA] image_url: {request.image_url}")

    task = celery_app.send_task(    #redis에 적재
        "gpt_image",
        args=[
            request.text_prompt,    
            request.image_url
        ]
    )
    logging.info(f"[TASK] Celery task 전송 완료 - task_id: {task.id}")
    return {"task_id": task.id}