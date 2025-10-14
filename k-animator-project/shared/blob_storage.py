# shared/blob_storage.py

import os
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
import logging

# 1. 모든 환경 변수를 이 파일에서 중앙 관리합니다.
AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_STORAGE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME") # 기본 컨테이너 이름

# 2. Blob Service 클라이언트를 한 번만 초기화하여 재사용합니다.
blob_service_client = None
if AZURE_STORAGE_ACCOUNT_NAME and AZURE_STORAGE_ACCOUNT_KEY:
    connection_string = f"DefaultEndpointsProtocol=https;AccountName={AZURE_STORAGE_ACCOUNT_NAME};AccountKey={AZURE_STORAGE_ACCOUNT_KEY};EndpointSuffix=core.windows.net"
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
else:
    logging.warning("Azure Storage credentials not found. Blob storage functions will not work.")

# 3. SAS URL 생성 함수를 여기에 정의합니다. (이제 모든 서비스가 이 함수를 사용)
def generate_sas_url(blob_name: str, container_name: str = AZURE_CONTAINER_NAME, expiry_minutes: int = 10) -> str:
    """지정된 Blob에 대한 읽기 전용 SAS URL을 생성합니다."""
    if not blob_service_client:
        return ""
        
    sas_token = generate_blob_sas(
        account_name=AZURE_STORAGE_ACCOUNT_NAME,
        container_name=container_name,
        blob_name=blob_name,
        account_key=AZURE_STORAGE_ACCOUNT_KEY,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(minutes=expiry_minutes)
    )
    return f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"

# 4. Blob에 데이터를 업로드하는 공용 함수를 만듭니다.
def upload_blob(blob_name: str, data: bytes, container_name: str = AZURE_CONTAINER_NAME, overwrite: bool = True):
    """주어진 데이터를 Blob에 업로드합니다."""
    if not blob_service_client:
        raise ConnectionError("Blob service client is not initialized.")
    
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    blob_client.upload_blob(data, overwrite=overwrite)
    logging.info(f"Blob uploaded successfully: {container_name}/{blob_name}")

# 5. Blob 데이터를 다운로드하는 공용 함수를 만듭니다. (model-worker에서 사용)
def get_blob_bytes(blob_name: str, container_name: str) -> bytes:
    """Blob에서 데이터를 바이트 형태로 다운로드합니다."""
    if not blob_service_client:
        raise ConnectionError("Blob service client is not initialized.")
    
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    stream = blob_client.download_blob()
    return stream.readall()

def get_blob_base64_image(blob_dir, file_name):
    try:
        blob_path = f"{blob_dir}/{file_name}.png"
        blob_client = container_client.get_blob_client(blob=blob_path)

        stream = blob_client.download_blob()
        img_bytes = stream.readall()

        image = Image.open(BytesIO(img_bytes))
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        logging.info(f"[ERROR] Blob 이미지 로딩 실패 - {file_name}: {e}")
        return None