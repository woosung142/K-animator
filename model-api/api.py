from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from celery import Celery
from fastapi.middleware.cors import CORSMiddleware
import os
import logging

app = FastAPI()

# CORS 허용.
origins = ["https://dev.prtest.shop", "https://www.prtest.shop"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Celery 설정
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
celery_app = Celery("model-api", broker=CELERY_BROKER_URL)
celery_app.conf.result_backend = CELERY_BROKER_URL

# 요청 스키마
class PromptRequest(BaseModel):
    category: str
    layer: str
    tag: str
    caption_input: str | None = None
    image_url: str | None = None

class FinalPromptRequest(BaseModel):
    dalle_prompt: str  

# 프롬프트 생성 요청
@app.post("/api/generate-prompt")
async def generate_prompt_endpoint(request: PromptRequest):
    logging.info(f"[REQUEST] POST /api/generate-image")
    logging.info(f"[DATA] category: {request.category}")
    logging.info(f"[DATA] layer: {request.layer}")
    logging.info(f"[DATA] tag: {request.tag}")
    logging.info(f"[DATA] caption_input: {request.caption_input}")
    logging.info(f"[DATA] image_url: {request.image_url}")

    task = celery_app.send_task(
        "generate_image",
        args=[
            request.category,   
            request.layer,
            request.tag,    #키워드
            request.caption_input,  #장면 설명
            request.image_url
        ]
    )
    logging.info(f"[TASK] Celery task 전송 완료 - task_id: {task.id}")
    return {"task_id": task.id}

# 최종 이미지 생성 요청
@app.post("/api/generate-image-from-prompt")
async def generate_image_from_prompt(request: FinalPromptRequest):
    logging.info("[REQUEST] POST /api/generate-image-from-prompt")
    task = celery_app.send_task(
        "generate_final_image",
        args=[request.dalle_prompt]
    )
    logging.info(f"[TASK] celery 'generate_final_image' task 전송 완료 - task_id: {task.id}")
    return {"task_id": task.id}

# 결과 조회 (prompt 또는 image 결과 모두 포함)
@app.get("/api/result/{task_id}")
async def get_result(task_id: str):
    logging.info(f"[REQUEST] GET /api/result/{task_id}")
    result = celery_app.AsyncResult(task_id)
    logging.info(f"[INFO] 현재 상태: {result.state}")

    if result.state == "PENDING":
        return {"status": "PENDING"}

    elif result.state == "SUCCESS":
        logging.info(f"[SUCCESS] 결과 수신 완료: {result.result}")
        result_data = result.result or {}

        response = {"status": "SUCCESS"}

        if "prompt" in result_data:
            response["prompt"] = result_data["prompt"]
        if "png_url" in result_data:
            response["png_url"] = result_data["png_url"]
        if "psd_url" in result_data:
            response["psd_url"] = result_data["psd_url"]

        return response

    elif result.state == "FAILURE":
        logging.info(f"[ERROR] Celery 태스크 실패: {result.result}")
        raise HTTPException(status_code=500, detail="Task failed")

    else:
        logging.info(f"[INFO] 기타 상태: {result.state}")
        return {"status": result.state}
