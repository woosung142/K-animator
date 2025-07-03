FROM python:3.10-slim

# 시스템 패키지 설치 (Pillow 관련, 타임존 설정 등)
RUN apt-get update && \
    apt-get install -y git libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# 작업 디렉토리
WORKDIR /app

# 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# 모델 캐시 사전 다운로드 (선택, 없으면 런타임 최초 실행 시 다운로드됨)
RUN python -c "from diffusers import StableDiffusionPipeline; StableDiffusionPipeline.from_pretrained('cagliostrolab/tiny-stable-diffusion-v1-0')"

# 코드 복사
COPY . .

# Celery 워커 실행
CMD ["celery", "-A", "worker", "worker", "--loglevel=info"]
