# 1. Python 공식 이미지 (경량 버전)를 베이스 이미지로 사용합니다.
#    alpine 버전은 이미지가 작아 배포에 유리합니다.
FROM python:3.9-slim-buster

# 2. 컨테이너 내부의 작업 디렉토리를 설정합니다.
#    모든 명령어는 이 디렉토리 내에서 실행됩니다.
WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 3000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "3000"]
