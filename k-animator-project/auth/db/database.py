from dotenv import load_dotenv
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
load_dotenv()
SQLALCHEMY_DATABASE_URL = None # DB 연결 문자열 초기화
try:
    logger.info("DB 연결을 위해 key vault에서 시크릿 조회 시작")
    # Azure Key Vault에서 DB 비밀번호 및 호스트 이름 검색
    key_vault_name = os.getenv("KEY_VAULT_NAME")
    db_password_secret_name = os.getenv("DB_PASSWORD_SECRET_NAME")
    db_host_secret_name = os.getenv("DB_HOST_SECRET_NAME")

    if not all([key_vault_name, db_password_secret_name, db_host_secret_name]):
        raise ValueError("KEY_VAULT_NAME, DB_PASSWORD_SECRET_NAME, DB_HOST_SECRET_NAME 환경 변수가 설정되지 않았음.")

    kv_uri = f"https://{key_vault_name}.vault.azure.net"

    # workload identity를 사용하여 Azure Key Vault에 인증
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=kv_uri, credential=credential)

    # Key Vault에서 DB 접속 정보 가져오기
    logger.info(f"'{db_host_secret_name}' 시크릿 조회 중")
    db_host = client.get_secret(db_host_secret_name).value

    logger.info(f"'{db_password_secret_name}' 시크릿 조회 중")
    db_password = client.get_secret(db_password_secret_name).value

    db_user ="psqladmin"
    db_name = "authdb"

    # SQLAlchemy 연결 문자열 생성 -> DB를 찾아가기 위해 필요한 정보 담아 문자열로 생성
    SQLALCHEMY_DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}/{db_name}"
    logger.info("DB 연결 문자열 생성 완료")
    logger.info("Azure Key Vault에서 DB 접속 정보 검색 완료")

except Exception as e:
    logger.error(f"Azure Key Vault 연동 또는 DB 연결 문자열 생성 중 오류 발생: {e}")
    
# DB 엔진 및 세션 생성
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    if SQLALCHEMY_DATABASE_URL is None:
        raise Exception("데이터베이스 URL이 설정되지 않았습니다. 서버 로그를 확인.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

