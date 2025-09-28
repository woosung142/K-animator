from fastapi import FastAPI
from .api import endpoints
from .db import database, models

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="K-animator Auth API",
    description="K-animator 인증 및 인가를 위한 API 서비스",
    version="1.0.0",
)

app.include_router(endpoints.router, prefix="/api", tags=["Authentication"])

@app.get("/", tags=["Root"])
def read_root():
    return{"status": "OK", "message": "K-animator Auth API 서비스가 실행 중입니다."}


