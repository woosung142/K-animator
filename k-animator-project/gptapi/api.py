from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
from celery import Celery
from celery.result import AsyncResult
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

class LayerSeparationRequest(BaseModel):
    image_url: str

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")  #배포 전 수정
celery_app = Celery("worker", broker=CELERY_BROKER_URL)
celery_app.conf.result_backend = CELERY_BROKER_URL

@router.post("/separate-layers")
async def separate_layers_task_endpoint(
    request: LayerSeparationRequest
    ):
    if not request.image_url or not request.image_url.strip():
        raise HTTPException(status_code=400, detail="Image URL cannot be empty.")

    logger.info(f"[REQUEST] POST /api/gpt/separate-layers")
    logger.info(f"[DATA] image_url: {request.image_url}")

    task = celery_app.send_task(
        "separate_layers_task",
        args=[request.image_url]
    )
    logging.info(f"[TASK] Celery task 'separate_layers_task' 전송 완료 - task_id: {task.id}")
    return {"task_id": task.id}

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

@router.get("/result/{task_id}")
async def get_result(task_id: str):
    logger.info(f"[REQUEST] GET /api/result/{task_id}")
    result = AsyncResult(task_id, app=celery_app)

    logger.info(f"[INFO] Task ID: {task_id}, Status: {result.state}")

    if result.state == 'PENDING':
        return {"status": "PENDING"}
    
    elif result.state == 'SUCCESS':
        logger.info(f"[SUCCESS] 결과 수신 완료: {result.result}")
        return result.result
    
    elif result.state == 'FAILURE':
        logger.error(f"[ERROR] Celery 태스크 실패: {result.info}")
        raise HTTPException(status_code=500, detail=f"Task failed: {result.info}")
        
    else:
        return {"status": result.state}