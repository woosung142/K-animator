import os
import logging
import base64

from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi.security import APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password) # 평문 비밀번호와 해시된 비밀번호 비교 (로그인)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password) # 비밀번호 해시화 (회원가입)

SECRET_KEY = None

try:
    key_vault_name = os.getenv("KEY_VAULT_NAME")
    secret_name = os.getenv("JWT_SECRET_NAME")

    if not key_vault_name or not secret_name:
        raise ValueError("KEY_VAULT_NAME 및 JWT_SECRET_NAME 환경 변수가 설정되지 않았음.")

    kv_uri = f"https://{key_vault_name}.vault.azure.net"

    credential = DefaultAzureCredential() # Azure AD 인증

    client = SecretClient(vault_url=kv_uri, credential=credential)
    retrieved_secret = client.get_secret(secret_name)

    SECRET_KEY = retrieved_secret.value
    SECRET_KEY = base64.b64decode(SECRET_KEY)
    logger.info("Azure Key Vault 에서 JWT를 성공적으로 검색함.")

except Exception as e:     #로컬용
    logger.warning(f"Azure Key Vault에서 JWT검색하는 동안 오류 발생: {e}. 로컬 환경 변수를 사용")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15 # 15분
REFRESH_TOKEN_EXPIRE_DAYS = 7   # 7일

# Access Token, Refresh Token 생성
def create_access_token(data: dict):

    to_encode = data.copy()
    to_encode.update({
        "type": "access",
        "iss": "k-animator-auth-service",
        "aud": "k-animator-api"        
        })

    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):

    to_encode = data.copy()
    to_encode.update({
        "type": "refresh",
        "iss": "k-animator-auth-service",
        "aud": "k-animator-api"        
        })

    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
