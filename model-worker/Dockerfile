FROM python:3.10-slim

# 시스템 패키지 설치 (Pillow 관련, 타임존 설정 등)
RUN apt-get update && \
    apt-get install -y git libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# 작업 디렉토리
WORKDIR /app

# CPU용 PyTorch + diffusers 등 사전 설치 (huggingface_hub 버전 주의)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir \
        torch==2.2.2+cpu \
        torchvision==0.17.2+cpu \
        --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir \
        transformers \
        huggingface_hub==0.16.4 \
        diffusers \
        safetensors

# 나머지 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 모델 캐시 사전 다운로드
RUN python -c "from diffusers import StableDiffusionPipeline; StableDiffusionPipeline.from_pretrained('cagliostrolab/tiny-stable-diffusion-v1-0')"

# 코드 복사
COPY . .

# Celery 워커 실행
CMD ["celery", "-A", "worker", "worker", "--loglevel=info"]
