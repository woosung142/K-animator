# Python 3.10 슬림 베이스 이미지
FROM python:3.10-slim

# 필수 시스템 패키지 설치 (ImageMagick 포함)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    imagemagick \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev && \
    rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# requirements.txt 복사 및 패키지 설치
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# Celery 워커 실행 명령
CMD ["celery", "-A", "worker", "worker", "--loglevel=info"]