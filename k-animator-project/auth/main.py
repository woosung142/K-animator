from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth.api.endpoints import auth_router, users_router # 'auth' 패키지 경로에서 import
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
app = FastAPI(title="Auth Service")


app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

origins = [
    "https://dev.prtest.shop", # 실제 배포된 프론트엔드 주소
    "https://www.prtest.shop",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # 허용할 출처 목록
    allow_credentials=True,      # [중요] 쿠키를 허용합니다.
    allow_methods=["*"],         # 모든 HTTP 메소드를 허용합니다.
    allow_headers=["*"],         # 모든 HTTP 헤더를 허용합니다.
)


app.include_router(auth_router, prefix="/api/auth") # 공개용 API
app.include_router(users_router, prefix="/api/users") # 보호용 API
@app.get("/")
def read_root():
    return {"message": "Auth service is running"}