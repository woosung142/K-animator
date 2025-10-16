from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
# modelapi의 라우터를 import 합니다.
from modelapi.api import router as modelapi_router

app = FastAPI(title="Model API Service")

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

origins = [
    "https://dev.prtest.shop", # 실제 배포된 프론트엔드 주소
    "http://localhost:8080",    # 로컬 개발 환경 주소
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --------------------

# [핵심] Terraform/Ingress에 설정된 경로와 일치하도록 prefix를 설정합니다.
app.include_router(model_pi_router, prefix="/api/model")

@app.get("/")
def read_root():
    return {"message": "Model API service is running"}
