from sqlalchemy.orm import Session
from . import models

# username으로 사용자 조회
def get_user(db: Session, username: str):
    return db.query(models.User).filter(
    models.User.username == username).first()
def get_email(db: Session, email: str):
    return db.query(models.User).filter(
    models.User.email == email).first()

def get_id(db: Session, user_id: str):
    return db.query(models.User).filter(
    models.User.id == user_id).first()


def get_images_by_user(db: Session, user_id: str):
    return db.query(models.Image).filter(
    models.Image.user_id == user_id).order_by(models.Image.created_at.desc()).all()
