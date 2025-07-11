# 베이스 이미지
FROM python:3.10-slim

# 작업 디렉토리 생성
WORKDIR /app

# 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 코드 전체 복사
COPY . .

# uploads 폴더 미리 만들어두기 (없으면 에러 날 수 있음)
RUN mkdir -p uploads

# FastAPI 앱 실행
CMD ["uvicorn", "web:app", "--host", "0.0.0.0", "--port", "80"]
