from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional
from sqlalchemy.orm import Session
import redis
from jose import jwt, JWTError

from ..db import crud, database, models
from ..schemas import schemas
from ..schemas.schemas import UserUpdatepassword
from ..core import security
from ..core.dependency import get_current_user
from ..db.redis_re import get_redis_refresh

router = APIRouter(
    prefix="/auth",
    tags=["회원인증 API"]
)

# 공개 API 엔드포인트: 회원가입
@router.post("/signup", 
response_model=schemas.User, 
status_code=status.HTTP_201_CREATED,
summary="사용자 생성 (회원가입)",
description="새로운 사용자를 생성합니다. `username`과 `email`은 고유해야 합니다.")

def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    # 중복된 username 검사
    db_user = crud.get_user(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="사용자 이름이 이미 존재합니다.")
    
    # 중복된 email 검사
    db_email = crud.get_email(db, email=user.email)
    if db_email:
        raise HTTPException(status_code=400, detail="이메일이 이미 존재합니다.")

    return crud.create_user(db=db, user=user) 

# API 엔드포인트: Access Token 발급
@router.post("/token",
response_model=schemas.Token,
summary="로그인 (Access/Refresh 토큰 발급)",
description="사용자 이름과 비밀번호로 로그인하여 JWT 토큰을 발급받습니다.")

def login_for_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db),
    redis_refresh: redis.Redis = Depends(get_redis_refresh)
):
    user = crud.authenticate_user(db, username=form_data.username, password=form_data.password)

    # security.py의 vetify_password 함수 사용해서 비밀번호 검증
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="잘못된 사용자 이름 또는 비밀번호입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 액세스 토큰 및 리프레시 토큰 생성
    token_data = {"sub": user.username}
    access_token = security.create_access_token(data=token_data)
    refresh_token = security.create_refresh_token(data=token_data)

    # 리프레시 토큰을 Redis에 저장
    redis_refresh.set(
        user.username,
        refresh_token,
        ex=int(security.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
    )
    # 리프레시 토큰을 HttpOnly 쿠키로 설정
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly = True,
        max_age = int(security.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
    )
    return {"access_token": access_token,"refresh_token" : refresh_token, "token_type": "bearer"}

@router.post("/logout",
status_code=status.HTTP_200_OK,
summary="로그아웃",
description="현재 사용자를 로그아웃 처리하고 Redis 및 쿠키에서 Refresh Token을 삭제합니다.")

def logout(
    response: Response,
    current_user: schemas.User = Depends(get_current_user),
    redis_refresh: redis.Redis = Depends(get_redis_refresh)
):

    redis_refresh.delete(current_user.username)
    response.delete_cookie(key="refresh_token")
    return {"message": "성공적으로 로그아웃되었습니다."}

@router.post("/refresh",
response_model=schemas.Token,
summary="Access Token 재발급",
description="HttpOnly 쿠키에 담긴 유효한 Refresh Token을 사용하여 새로운 Access Token과 Refresh Token을 발급받습니다.")

def refresh_access_token(
    response: Response,
    refresh_token: Optional[str] = Cookie(None), # 쿠키에서 리프레시 토큰 가져오기
    db: Session = Depends(database.get_db),
    redis_refresh: redis.Redis = Depends(get_redis_refresh)
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="리프레시 토큰이 존재하지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="유효하지 않은 리프레시 토큰입니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 1. 전달받은 리프레시 토큰 디코딩
        payload = jwt.decode(
            refresh_token, security.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # 2. 토큰의 username으로 DB와 Redis 조회
    user = crud.get_user(db, username=username)
    stored_refresh_token = redis_refresh.get(username)

    if not user or not stored_refresh_token:
        raise credentials_exception
    
    # 3. Redis에서 가져온 토큰을 디코딩하여 비교
    if stored_refresh_token != refresh_token:
        raise credentials_exception

    # 4. 검증 완료 후, 새로운 토큰들 생성 (Refresh Token Rotation)
    new_token_data = {"sub": user.username}
    new_access_token = security.create_access_token(data=new_token_data)
    new_refresh_token = security.create_refresh_token(data=new_token_data)

    # 5. Redis와 쿠키에 새로운 리프레시 토큰 저장
    redis_refresh.set(
        user.username,
        new_refresh_token,
        ex=int(security.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
    )
    
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        max_age=int(security.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
    )

    return {"access_token": new_access_token,"refresh_token": new_refresh_token,  "token_type": "bearer"}


# 보호 API 엔드포인트
@router.get("/users/me",
response_model=schemas.User,
summary="내 정보 보기",
description="현재 로그인된 사용자의 프로필 정보를 조회합니다. Access Token의 유효성을 검증하는 용도로도 사용됩니다.")

def read_users_me(current_user: schemas.User = Depends(get_current_user)):
    return current_user

# 회원 정보 수정 (이름)
@router.patch("/users/me",
response_model=schemas.User,
summary="내 정보 수정 (이름)",
description="현재 로그인된 사용자의 전체 이름(`full_name`)을 수정합니다.")

def update_user_me(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    return crud.update_user(db=db, user=current_user, user_update=user_update)

# 로그인 후 비밀번호 변경
@router.patch("/users/me/password",
status_code=status.HTTP_200_OK,
summary="비밀번호 변경",
description="현재 비밀번호를 확인한 후, 새로운 비밀번호로 변경합니다.")

def change_password(
    passwords: schemas.UserUpdatepassword,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    if not security.vetify_password(passwords.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 일치하지 않습니다."
        )
    
    crud.update_password(db=db, user=current_user, new_password=passwords.new_password)
    return {"message": "비밀번호가 성공적으로 변경되었습니다."}

@router.delete("/users/me",
status_code=status.HTTP_204_NO_CONTENT,
summary="회원 탈퇴",
description="현재 로그인된 사용자의 계정을 삭제하고 모든 세션 정보를 제거합니다.")

def delete_user_me(
    response: Response,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
    redis_refresh: redis.Redis = Depends(get_redis_refresh)
):
    redis_refresh.delete(current_user.username)
    response.delete_cookie(key="refresh_token")
    crud.delete_user(db=db, user=current_user)
    return
