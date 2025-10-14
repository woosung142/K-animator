from pydantic import BaseModel, EmailStr, validator
from typing import Optional
import re
##### 사용자 관련 스키마임 ##########
class UserBase(BaseModel):      # 공통 정보
    username: str
    email: EmailStr
    full_name: Optional[str] = None 

    @validator('username')
    def validate_usernmae(cls, value):
        if not value or ' ' in value:
            raise ValueError('사용자 ID는 비어있을 수 없고 공백을 포함할 수 없습니다.')
        if not re.match("^[a-zA-Z0-9_-]+$", value):
            raise ValueError('사용자 ID는 영문자, 숫자, 밑줄(_), 대시(-)만 포함할 수 있습니다.')
        return value

class UserCreate(UserBase):     # 회원가입 받을 정보
    password: str

    @validator('password')
    def validate_password(cls, value):
        if not value or len(value.strip()) == 0:
            raise ValueError('비밀번호는 비어있을 수 없습니다.')
        if len(value) < 8:
            raise ValueError('비밀번호는 최소 8자 이상이어야 합니다.')
        return value

class User(UserBase):           # 회원가입 응답
    pass

class UserInDB(UserBase):       # DB에 저장된 정보
    hashed_password: str

class UserUpdate(BaseModel):    # 정보 수정 (이름)
    full_name: Optional[str] = None

class UserUpdatepassword(BaseModel):    # 비번 수정
    current_password: str
    new_password: str

class UserLogin(BaseModel):    # 로그인 받을 정보
    username: str
    password: str


########## 토큰 관련 스끼익마 #########
class TokenData(BaseModel):
    username: Optional[str] = None

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str