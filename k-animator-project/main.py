from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# src 폴더를 기준으로 각 기능별 라우터를 import 합니다.
from auth.api import endpoints as auth_endpoints
from model_api import api as model_endpoints
from backend import web as utils_endpoints
from backend.web import LimitUploadSizeMiddleware, MAX_SIZE
from auth.db import models, database

# --- 태그 메타데이터 정의 ---
tags_metadata = [
    {"name": "회원인증 API", "description": "회원가입, 로그인, 토큰 관리 등"},
    {"name": "이미지 생성 API", "description": "Celery를 이용한 비동기 이미지 생성"},
    {"name": "유틸리티 API", "description": "이미지 업로드, 외부 서비스 토큰 발급 등"},
]

models.Base.metadata.create_all(bind=database.engine)

# --- FastAPI 앱 생성 ---
app = FastAPI(
    title="K-Animator API",
    openapi_tags=tags_metadata
)

# --- 미들웨어 설정 ---
# (CORS, 파일 크기 제한 등)
origins = ["https://dev.prtest.shop", "https://www.prtest.shop"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 2. 파일 크기 제한 미들웨어
app.add_middleware(LimitUploadSizeMiddleware, max_upload_size=MAX_SIZE)

# --- 모든 라우터 연결 ---
app.include_router(auth_endpoints.router, prefix="/api")
app.include_router(model_endpoints.router, prefix="/api")
app.include_router(utils_endpoints.router, prefix="/api")