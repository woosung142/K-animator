# Python 3.10 슬림 베이스 이미지.
FROM python:3.10-slim AS base

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

FROM base AS builder

# 작업 디렉토리 설정
WORKDIR /app

RUN pip install --upgrade pip

# requirements.txt 복사 및 패키지 설치
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

FROM base AS final

WORKDIR /app

# Builder 단계에서 설치한 파이썬 패키지들을 그대로 복사
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 애플리케이션 코드 복사
COPY . .

# Celery 워커 실행 명령
CMD ["celery", "-A", "worker", "worker", "--loglevel=info"]