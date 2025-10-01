from sqlalchemy.orm import Session
from . import models
from ..schemas import schemas
from ..core import security

# username으로 사용자 조회
def get_user(db: Session, username: str):
    return db.query(models.User).filter(
    models.User.username == username).first()
def get_email(db: Session, email: str):
    return db.query(models.User).filter(
    models.User.email == email).first()

# 신규 사용자 생성
def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = security.get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# 회원 정보 수정 (이름)
def update_user(db: Session, user: models.User, user_update: schemas.UserUpdate):
    update_data = user_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(user, key, value)
        
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# 비번 수정 
def update_password(db: Session, user: models.User, new_password: str):
    hashed_password = security.get_password_hash(new_password)
    user.hashed_password = hashed_password
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# 회원 탈퇴
def delete_user(db: Session, user: models.User):
    db.delete(user)
    db.commit()
    return

def authenticate_user(db: Session, username: str, password: str):
    """
    사용자 이름과 비밀번호로 사용자를 인증합니다.
    성공 시 사용자 객체를, 실패 시 None을 반환합니다.
    """
    user = get_user(db, username)
    if not user:
        return None
    if not security.vetify_password(password, user.hashed_password):
        return None
    return user