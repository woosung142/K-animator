from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie, Request
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional
from sqlalchemy.orm import Session
import redis
from jose import jwt, JWTError

from shared.db import database
from shared.db import crud as shared_crud
from auth.db import crud as auth_crud
from auth.schemas import schemas
from auth.schemas.schemas import UserUpdatepassword
from auth.core import security
from shared.dependencies import get_user_id_from_gateway
from auth.db.redis_re import get_redis_refresh

auth_router = APIRouter(
    tags=["인증 (공개)"]
)

# 공개 API 엔드포인트: 회원가입
@auth_router.post("/signup", 
                  response_model=schemas.User, 
                  status_code=status.HTTP_201_CREATED,
                  summary="사용자 생성 (회원가입)",
                  description="새로운 사용자를 생성합니다. `ID`와 `email`은 고유해야 합니다.")
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = shared_crud.get_user(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="사용자 이름이 이미 존재합니다.")
    
    db_email = shared_crud.get_email(db, email=user.email)
    if db_email:
        raise HTTPException(status_code=400, detail="이메일이 이미 존재합니다.")

    return auth_crud.create_user(db=db, user=user) 

# API 엔드포인트: Access Token 발급
@auth_router.post("/login",
                  response_model=schemas.Token,
                  summary="로그인 (Access/Refresh 토큰 발급)",
                  description="사용자 이름과 비밀번호로 로그인하여 JWT 토큰을 발급받습니다.")
def login_for_access_token(
    response: Response,
    request: Request,
    user_login: schemas.UserLogin,
    db: Session = Depends(database.get_db),
    redis_refresh: redis.Redis = Depends(get_redis_refresh)
):
    user = auth_crud.authenticate_user(db, username=user_login.username, password=user_login.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="잘못된 사용자 이름 또는 비밀번호입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = {"sub": user.id}
    access_token = security.create_access_token(data=token_data)
    refresh_token = security.create_refresh_token(data=token_data)

    redis_refresh.set(
        user.id,
        refresh_token,
        ex=int(security.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
    )
    

    is_secure_env = request.url.scheme == 'https'
    cookie_samesite = "none" if is_secure_env else "lax"
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=int(security.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60),
        samesite=cookie_samesite,
        secure=is_secure_env
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@auth_router.post("/refresh",
                  response_model=schemas.Token,
                  summary="Access Token 재발급",
                  description="HttpOnly 쿠키에 담긴 유효한 Refresh Token을 사용하여 새로운 Access Token과 Refresh Token을 발급받습니다.")
def refresh_access_token(
    response: Response,
    request: Request,
    refresh_token: Optional[str] = Cookie(None),
    db: Session = Depends(database.get_db),
    redis_refresh: redis.Redis = Depends(get_redis_refresh)
):
    # --- [상세 디버깅 로그 추가] ---
    print("\n--- [DEBUG] Access Token 재발급 시도 ---")
    
    if not refresh_token:
        print("--- [DEBUG][실패] 1. 쿠키에서 Refresh Token을 찾을 수 없습니다.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="리프레시 토큰 쿠키 없음")
    print(f"--- [DEBUG][성공] 1. 쿠키에서 Refresh Token 발견: ...{refresh_token[-10:]}")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="유효하지 않은 리프레시 토큰입니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(refresh_token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            print("--- [DEBUG][실패] 2. 토큰 payload에 'sub' (user_id)가 없습니다.")
            raise credentials_exception
        print(f"--- [DEBUG][성공] 2. 토큰 디코딩 성공, user_id: {user_id}")
    except JWTError as e:
        print(f"--- [DEBUG][실패] 2. JWT 디코딩 오류 발생: {e}")
        raise credentials_exception

    user = shared_crud.get_id(db, user_id=user_id)
    if not user:
        print(f"--- [DEBUG][실패] 3. DB에서 user_id '{user_id}'를 찾을 수 없습니다.")
        raise credentials_exception
    print(f"--- [DEBUG][성공] 3. DB에서 사용자 조회 성공: {user.username}")
    
    stored_refresh_token = redis_refresh.get(user_id)
    if not stored_refresh_token:
        print(f"--- [DEBUG][실패] 4. Redis에서 user_id '{user_id}'에 대한 토큰을 찾을 수 없습니다.")
        raise credentials_exception
    print(f"--- [DEBUG][성공] 4. Redis에서 토큰 조회 성공: ...{stored_refresh_token[-10:]}")
    
    if stored_refresh_token != refresh_token:
        print("--- [DEBUG][실패] 5. 쿠키의 토큰과 Redis의 토큰이 일치하지 않습니다.")
        print(f"    - 쿠키 토큰: ...{refresh_token[-10:]}")
        print(f"    - Redis 토큰: ...{stored_refresh_token[-10:]}")
        raise credentials_exception
    print("--- [DEBUG][성공] 5. 쿠키 토큰과 Redis 토큰 일치 확인.")

    new_token_data = {"sub": user.id}
    new_access_token = security.create_access_token(data=new_token_data)
    new_refresh_token = security.create_refresh_token(data=new_token_data)

    redis_refresh.set(
        user.id,
        new_refresh_token,
        ex=int(security.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
    )
    

    is_secure_env = request.url.scheme == 'https'
    cookie_samesite = "none" if is_secure_env else "lax"

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        max_age=int(security.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60),
        samesite=cookie_samesite,
        secure=is_secure_env
    )

    return {"access_token": new_access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}

users_router = APIRouter(
    tags=["사용자 (인증필요)"]
)

@users_router.post("/logout",
                   status_code=status.HTTP_200_OK,
                   summary="로그아웃",
                   description="현재 사용자를 로그아웃 처리하고 Redis 및 쿠키에서 Refresh Token을 삭제합니다.")
def logout(
    response: Response,
    user_id: str = Depends(get_user_id_from_gateway),
    redis_refresh: redis.Redis = Depends(get_redis_refresh)
):
    redis_refresh.delete(user_id)
    response.delete_cookie(key="refresh_token")
    return {"message": "성공적으로 로그아웃되었습니다."}

# 보호 API 엔드포인트
@users_router.get("/me",
                  response_model=schemas.User,
                  summary="내 정보 보기",
                  description="현재 로그인된 사용자의 프로필 정보를 조회합니다.")
def read_users_me(user_id: str = Depends(get_user_id_from_gateway), db: Session = Depends(database.get_db)):
    user = shared_crud.get_id(db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# 회원 정보 수정 (이름)
@users_router.patch("/me",
                    response_model=schemas.User,
                    summary="내 정보 수정 (이름)",
                    description="현재 로그인된 사용자의 전체 이름(`full_name`)을 수정합니다.")
def update_user_me(
    user_update: schemas.UserUpdate,
    user_id: str = Depends(get_user_id_from_gateway),
    db: Session = Depends(database.get_db)
):
    user = shared_crud.get_id(db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return auth_crud.update_user(db=db, user=user, user_update=user_update)

# 로그인 후 비밀번호 변경
@users_router.patch("/me/password",
                    status_code=status.HTTP_200_OK,
                    summary="비밀번호 변경",
                    description="현재 비밀번호를 확인한 후, 새로운 비밀번호로 변경합니다.")
def change_password(
    passwords: schemas.UserUpdatepassword,
    db: Session = Depends(database.get_db),
    user_id: str = Depends(get_user_id_from_gateway)
):
    user = shared_crud.get_id(db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if not security.verify_password(passwords.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 일치하지 않습니다."
        )
    
    auth_crud.update_password(db=db, user=user, new_password=passwords.new_password)
    return {"message": "비밀번호가 성공적으로 변경되었습니다."}

@users_router.delete("/me",
                     status_code=status.HTTP_204_NO_CONTENT,
                     summary="회원 탈퇴",
                     description="현재 로그인된 사용자의 계정을 삭제하고 모든 세션 정보를 제거합니다.")
def delete_user_me(
    response: Response,
    user_id: str = Depends(get_user_id_from_gateway),
    db: Session = Depends(database.get_db),
    redis_refresh: redis.Redis = Depends(get_redis_refresh)
):
    user = shared_crud.get_id(db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    redis_refresh.delete(user_id)
    response.delete_cookie(key="refresh_token")
    auth_crud.delete_user(db=db, user=user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

