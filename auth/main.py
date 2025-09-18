from datetime import timedelta
from fastapi import Depends, HTTPException, status, FastAPI
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt

from . import schemas, security

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 임시 사용자 데이터베이스
fake_users_db = {
    "testuser": {
        "username": "testuser",
        "full_name": "Test User",
        "email": "test@example.com",
        "hashed_password": security.get_password_hash("testpassword"),
    }
}
# DB에서 사용자 정보 가져오기
def get_user(db: dict, username: str):
    if username in db:
        user_dict = db[username]
        return schemas.UserInDB(**user_dict)
    return None
# 공개 API 엔드포인트: 회원가입
@app.post("/users/", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate):
    db_user = get_user(fake_users_db, user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="사용자 이름이 이미 존재합니다.")
    
    # security.py의 get_password_hash 함수 사용해서 비밀번호 해싱
    hashed_password = security.get_password_hash(user.password)
    user_in_db = schemas.UserInDB(**user.dict(), hashed_password=hashed_password)

    # 임시 DB에 저장
    fake_users_db[user.username] = user_in_db.dict()
    return user_in_db

# API 엔드포인트: Access Token 발급
@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user  = get_user(fake_users_db, form_data.username)

    # security.py의 vetify_password 함수 사용해서 비밀번호 검증
    if not user or not security.vetify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="잘못된 사용자 이름 또는 비밀번호입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 액세스 토큰 및 리프레시 토큰 생성
    token_data = {"sub": user.username}
    access_token = security.create_access_token(data=token_data)
    refresh_token = security.create_refresh_token(data=token_data)

    return {"access_token": access_token, 
            "refresh_token": refresh_token, 
            "token_type": "bearer"
    }

def decode_token(token: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="자격증을 확인할 수 없습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        return payload
    except JWTError:
        raise credentials_exception
    
# 토큰 검증
async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    username: str = payload.get("sub")
    user = get_user(fake_users_db, username)

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
        detail="엔드포인트에 대한 토큰 유형이 올바르지않습니다.")
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
        detail="자격 증명을 확인할 수 없습니다.")
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
        detail="사용자를 찾을 수 없습니다.")
    return user

async def get_current_user_from_refresh_token(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    username: str = payload.get("sub")
    user = get_user(fake_users_db, username)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
        detail="Not a refresh token")
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
        detail="자격 증명을 확인할 수 없습니다.")
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
        detail="사용자를 찾을 수 없습니다.")
    return user
@app.post("/refresh", response_model=schemas.Token)
async def refresh_access_token(current_user: schemas.User = Depends(get_current_user_from_refresh_token)):

    # 액세스 토큰 및 리프레시 토큰 생성
    token_data = {"sub": user.username}
    access_token = security.create_access_token(data=token_data)
    refresh_token = security.create_refresh_token(data=token_data)

    return {"access_token": access_token, 
            "refresh_token": refresh_token, 
            "token_type": "bearer"
    }

# 보호 API 엔드포인트
@app.get("/users/me/", response_model=schemas.User)
async def read_users_me(current_user: schemas.User = Depends(get_current_user)):
    return current_user