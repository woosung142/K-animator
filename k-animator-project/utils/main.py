from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
# utils 서비스의 라우터를 import 합니다.
from utils.web import router as utils_api_router

app = FastAPI(title="Utility Service")

# [핵심] APIM과 같은 리버스 프록시 뒤에서 실행될 때,
# 'X-Forwarded-Proto' (https) 헤더를 신뢰하도록 설정합니다.
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# --- CORS 설정 ---
# 프론트엔드의 도메인을 허용하여 브라우저에서 API를 호출할 수 있게 합니다.
origins = [
    "https://dev.prtest.shop",  # 실제 프론트엔드 배포 도메인
    "http://localhost:8080",      # 로컬 개발 환경 주소
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --------------------

# [핵심] Ingress에 설정된 경로와 일치하도록 prefix를 설정합니다.
app.include_router(utils_api_router, prefix="/api/utils")

@app.get("/")
def read_root():
    return {"message": "Utility service is running"}