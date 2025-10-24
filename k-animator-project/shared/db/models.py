import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

#고유식별값 생성
def generate_uuid():
    return str(uuid.uuid4())

#users 테이블 모델 정의
class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=generate_uuid)

    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String, index=True)
    hashed_password = Column(String)

    images = relationship("Image", back_populates="owner", cascade="all, delete-orphan")

#사용자가 생성한 이미지 저장할 테이블 모델 정의
class Image(Base):
    __tablename__ = "images"

    id = Column(String, primary_key=True, default=generate_uuid)
    task_id = Column(String, unique=True, index=True)
    png_url = Column(String)
    psd_url = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())    # 생성시간
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)   # user 테이블과 연결

    owner = relationship("User", back_populates="images")
