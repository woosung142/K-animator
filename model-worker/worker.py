from celery import Celery
import base64
from io import BytesIO
from PIL import Image
import torch
from diffusers import StableDiffusionPipeline

# 디바이스 설정 (GPU 우선)
device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if device == "cuda" else torch.float32

# 경량화된 최신 모델 (diffusers 호환)
pipe = StableDiffusionPipeline.from_pretrained(
    "nota-ai/bk-sdm-tiny",
    torch_dtype=dtype
).to(device)

pipe.enable_attention_slicing()  # 메모리 최적화 옵션

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
        # 생성: num_inference_steps를 20~30으로 설정하면 품질/속도 균형
        img = pipe(prompt, num_inference_steps=25, guidance_scale=7.5).images[0]

        # base64 인코딩
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
