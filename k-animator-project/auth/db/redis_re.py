import os
import logging
import redis
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

redis_refresh = None

try:
    logger.info("Redis 연결을 위해 key vault에서 시크릿 조회 시작")
    # Azure Key Vault에서 Redis 비밀번호 및 호스트 이름 검색
    key_vault_name = os.getenv("KEY_VAULT_NAME")
    redis_password_secret_name = os.getenv("REDIS_PASSWORD_SECRET_NAME")
    redis_host_secret_name = os.getenv("REDIS_HOST_SECRET_NAME")

    if not all([key_vault_name, redis_password_secret_name, redis_host_secret_name]):
        raise ValueError("KEY_VAULT_NAME, REDIS_PASSWORD_SECRET_NAME, REDIS_HOST_SECRET_NAME 환경 변수가 설정되지 않았음.")

    kv_uri = f"https://{key_vault_name}.vault.azure.net"

    # workload identity를 사용하여 Azure Key Vault에 인증
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=kv_uri, credential=credential)

    # Key Vault에서 Redis 접속 정보 가져오기
    logger.info(f"'{redis_host_secret_name}' 시크릿 조회 중")
    redis_host = client.get_secret(redis_host_secret_name).value

    logger.info(f"'{redis_password_secret_name}' 시크릿 조회 중")
    redis_password = client.get_secret(redis_password_secret_name).value

    # Redis 연결 설정
    redis_refresh = redis.StrictRedis(
        host=redis_host,
        port=6380,
        password=redis_password,
        ssl=True,
        ssl_cert_reqs=None,
        decode_responses=True,
        socket_connect_timeout=5,
    )
    # Redis 연결 테스트
    redis_refresh.ping()
    logger.info("Redis 연결 성공 및 Azure Key Vault에서 Redis 접속 정보 검색 완료")

except Exception as e:
    logger.error(f"Azure Key Vault 연동 또는 Redis 연결 중 오류 발생: {e}")

def get_redis_refresh():
    if redis_refresh is None:
        raise Exception("Redis 연결이 설정되지 않았습니다. 서버 로그를 확인.")
    return redis_refresh