from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from utils.web import router as utils_api_router

app = FastAPI(title="Utility Service")

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

origins = [
    "https://dev.prtest.shop",  # 실제 프론트엔드 배포 도메인
    "https://www.prtest.shop",
    "http://localhost:8080"      # 로컬 개발 환경 주소
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
#Front Door 및 APIM 헬스체크용 API
@app.get("/health", include_in_schema=False)
def health_check():
    return {"status": "ok"}

app.include_router(utils_api_router, prefix="/api/utils")

@app.get("/")
def read_root():
    return {"message": "Utility service is running"}