from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from shared.db import crud, database, models
from core import security

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
    
