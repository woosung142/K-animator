FROM python:3.10-slim

# 이미지 변환용 ImageMagick만 설치 (PSD 변환에 필요)
RUN apt-get update && \
    apt-get install -y imagemagick && \
    rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# requirements.txt 복사 및 설치
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사
COPY . .

# Celery 워커 실행
CMD ["celery", "-A", "worker", "worker", "--loglevel=info"]
