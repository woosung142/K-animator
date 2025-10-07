from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from ..db import crud, database, models
from ..core import security

oauth2_scheme = APIKeyHeader(name="Authorization", auto_error=False)

def decode_token(token: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="자격증을 확인할 수 없습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token or not token.startswith("Bearer "):
        raise credentials_exception
    token = token.split(" ")[1]
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        return payload
    except JWTError:
        raise credentials_exception
    
# 토큰 검증
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db)
)-> models.User:

    payload = decode_token(token)
    user_id: str = payload.get("sub")

    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
        detail="자격 증명을 확인할 수 없습니다.")

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
        detail="엔드포인트에 대한 토큰 유형이 올바르지않습니다.")

    user = crud.get_id(db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
        detail="사용자를 찾을 수 없습니다.")
    return user

