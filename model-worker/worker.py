from celery import Celery
import base64
from io import BytesIO
from PIL import Image
import torch
from diffusers import StableDiffusionPipeline

# 디바이스 설정 (GPU 우선)
device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if device == "cuda" else torch.float32

# Stable Diffusion 모델 로드 (Tiny 모델 사용)
pipe = StableDiffusionPipeline.from_pretrained(
    "cagliostrolab/tiny-stable-diffusion-v1-0",
    torch_dtype=dtype
).to(device)

# Celery 설정
celery_app = Celery(
    'worker',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0'
)

# 이미지 생성 태스크
@celery_app.task(name="generate_image")
def generate_image(prompt: str) -> dict:
    try:
        # 이미지 생성
        img = pipe(prompt, num_inference_steps=25).images[0]

        # base64로 인코딩
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        encoded_img = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return {
            "status": "SUCCESS",
            "image_base64": f"data:image/png;base64,{encoded_img}"
        }

    except Exception as e:
        return {
            "status": "FAILURE",
            "error": str(e)
        }
