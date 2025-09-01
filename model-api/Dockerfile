# Python 기반 이미지 사용.
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 종속성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# FastAPI 서버 실행 (생성된 이미지는 API용)
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]