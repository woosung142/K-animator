from celery import Celery
from celery.signals import after_setup_logger
from io import BytesIO
from PIL import Image
import requests
import os
import subprocess
import psycopg2
import base64
import torch
from datetime import datetime, timedelta
from transformers import AutoProcessor, AutoModel
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
import logging

# 환경변수 로딩
load_dotenv()
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_VERSION = "2024-05-01-preview"
PG_HOST = os.getenv("PG_HOST")
PG_PORT = os.getenv("PG_PORT")
PG_DBNAME = os.getenv("PG_DBNAME")
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")
AZURE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
AZURE_CONTAINER_NAME = "rag-images"
AZURE_CONNECTION_STRING = f"DefaultEndpointsProtocol=https;AccountName={AZURE_ACCOUNT_NAME};AccountKey={AZURE_ACCOUNT_KEY};EndpointSuffix=core.windows.net"

# KoCLIP 모델 로딩
processor = AutoProcessor.from_pretrained("koclip/koclip-base-pt")
model = AutoModel.from_pretrained("koclip/koclip-base-pt").eval().to("cuda" if torch.cuda.is_available() else "cpu")
device = next(model.parameters()).device

# 클라이언트 초기화
client = AzureOpenAI(api_key=AZURE_OPENAI_KEY, azure_endpoint=AZURE_OPENAI_ENDPOINT, api_version=AZURE_OPENAI_VERSION)
blob_service = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
container_client = blob_service.get_container_client(AZURE_CONTAINER_NAME)

# Celery 설정
celery_app = Celery('worker', broker='redis://redis:6379/0', backend='redis://redis:6379/0')

@after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    formatter = logging.Formatter('[%(asctime)s: %(levelname)s/%(processName)s] %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# 유틸 함수
def embed_text_koclip(text):
    inputs = processor(text=[text], return_tensors="pt", truncation=True, padding=True).to(device)
    with torch.no_grad():
        embedding = model.get_text_features(**inputs)
    return embedding[0].cpu().numpy().tolist()

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

def generate_sas_url(account_name, account_key, container_name, blob_name, expiry_minutes=10):
    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(minutes=expiry_minutes)
    )
    return f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"


layer_descriptions = {
    "콘티": "A rough, gray pencil storyboard-style sketch focusing on layout and composition. "
            "Forms are simplified with minimal detail and overlapping sketch lines are acceptable. "
            "No color or shading is applied — the emphasis is solely on spatial arrangement and rough structure.",
    "스케치": "A clean line drawing with clearly defined black outlines. "
              "All main elements are visible with refined contours and accurate proportions. "
              "No coloring or shading — just detailed, precise edges on a white background.",
    "채색 기본": "A flat-colored illustration where base colors are applied to each element. "
                 "No shadows, highlights, or gradients are used — the focus is on color separation and clarity. "
                 "Shapes should be filled with solid tones to indicate material or category.",
    "채색 명암": "A fully colored illustration with realistic shading, highlights, and lighting direction. "
                 "Depth, form, and texture are emphasized using shadows and color intensity. "
                 "Contrast between light and dark areas should reflect real-world perception.",
    "배경": "A complete and polished scene with a coherent background, ambient lighting, and environmental context. "
           "All elements should be fully rendered with consistent perspective and atmosphere. "
           "The composition feels complete, as if prepared for publication or final output."
}


def get_wikipedia_main_image(tag):
    try:
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&titles={tag}&prop=pageimages&format=json&pithumbsize=500"
        response = requests.get(search_url)
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            thumbnail = page.get("thumbnail", {})
            if "source" in thumbnail:
                return thumbnail["source"]
    except Exception as e:
        logging.info(f"[ERROR] Wikipedia 이미지 검색 실패: {e}")
    return None


@celery_app.task(name="generate_image", bind=True)
def generate_image(self, category: str, layer: str, tag: str, caption_input: str | None = None, image_url: str | None = None) -> dict:
    try:
        task_id = self.request.id
        logging.info(f"[TASK] generate_image 시작 - task_id: {task_id}")
        logging.info(f"[INPUT] category: {category}, layer: {layer}, tag: {tag}, caption_input: {caption_input}, image_url: {image_url}")
        
        # 1. KoCLIP 임베딩
        text_to_embed = caption_input if caption_input else f"{tag}가 포함된 한국 웹툰 이미지를 그려주세요."
        logging.info(f"[STEP 1] 임베딩 대상 텍스트: {text_to_embed}")
        embedding_vector = embed_text_koclip(text_to_embed)
        vector_str = "[" + ",".join([str(x) for x in embedding_vector]) + "]"
        logging.info(f"[STEP 1] 생성된 임베딩 벡터 길이: {len(embedding_vector)}")

        images_content = []

        # 2. 사용자 업로드 이미지 (최우선, 1장)
        if image_url:
            logging.info(f"[STEP 2] 사용자 업로드 이미지 추가: {image_url}")
            images_content.append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })

        # 3. DB 유사 이미지 최대 1장 추가
        if len(images_content) < 2:
            conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DBNAME, user=PG_USER, password=PG_PASSWORD)
            cursor = conn.cursor()
            keywords = [f"%{word.strip()}%" for word in tag.split()]
            logging.info(f"[STEP 3] 태그 키워드 변환: {keywords}")

            sql = """
                SELECT file_name FROM korea_image_data
                WHERE category = %s AND layer = %s
                  AND tag ILIKE ANY (%s)
                ORDER BY vec_caption <-> %s::vector
                LIMIT 1;
            """
            cursor.execute(sql, (category, layer, keywords, vector_str))
            results = cursor.fetchall()
            logging.info(f"[STEP 3] DB 검색 결과 file_name 리스트: {results}")
            cursor.close()
            conn.close()

            for row in results:
                file_name = row[0]
                logging.info(f"[STEP 3] Blob에서 이미지 로딩 시도: {file_name}")
                image_b64 = get_blob_base64_image("img", file_name)
                if image_b64:
                    logging.info(f"[STEP 3] base64 변환 성공: {file_name}")
                    images_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}"
                        }
                    })

        # 4. Wikipedia 이미지 1장 (없을 경우만)
        if len(images_content) < 2:
            wiki_image_url = get_wikipedia_main_image(tag)
            if wiki_image_url:
                logging.info(f"[STEP 4] Wikipedia 이미지 추가: {wiki_image_url}")
                images_content.append({
                    "type": "image_url",
                    "image_url": {"url": wiki_image_url}
                })
            else:
                logging.info(f"[STEP 4] Wikipedia 이미지 없음")

        # 5. 이미지가 없어도 텍스트만으로 생성 가능
        if not images_content:
            logging.info(f"[STEP 5] 이미지 없이 텍스트만으로 프롬프트 생성됨")

        # 6. gpt 프롬프트 생성
        prompt_text = (
            "Analyze the provided images and generate a Korean-style webtoon background scene suitable for a DALL·E 3 prompt.\n"
            "The scene should reflect a natural and culturally authentic Korean setting that fits the input concept.\n"
            "Include Korean cultural elements in a visually balanced and respectful manner.\n"
            "You may place small traditional items (such as furniture, ornaments, or patterns) around the main object.\n"
            "These cultural elements should appear in the background or as part of the environment, not as the main focus.\n"
            "Even without specific instructions, the scene should convey a Korean cultural atmosphere by default.\n"
            "Optional supporting objects may be placed near the main concept, but they must not compete for attention.\n"
            "You may adjust the level of detail depending on the artistic stage, from rough draft to polished background.\n"
            "If necessary, you may include human figures, but they should not be the central focus — never portray them as main characters.\n"
            "The prompt must be written in natural, fluent English optimized for DALL·E 3 input.\n\n"
            f"Style step: '{layer}'\n"
            f"Style guide for this step:\n{layer_descriptions.get(layer, '')}\n\n"
            f"Original description from the user: \"{caption_input}\""
)




        logging.info(f"[STEP 6] 생성된 프롬프트:\n{prompt_text}") 

        messages = [{
            "role": "user",
            "content": [{"type": "text", "text": prompt_text}] + images_content
        }]
        response = client.chat.completions.create(model="gpt-4o", messages=messages, max_tokens=800, temperature=0.7)
        dalle_prompt = response.choices[0].message.content.strip()
        logging.info(f"[STEP 6] GPT 생성 결과:\n{dalle_prompt}")

        return {"status": "SUCCESS", "prompt": dalle_prompt}

    except Exception as e:
        logging.info(f"[ERROR] 프롬프트 생성 실패: {e}")
        return {"status": "FAILURE", "error": str(e)}


@celery_app.task(name="generate_final_image", bind=True)
def generate_final_image(self, dalle_prompt: str) -> dict:
    try:
        task_id = self.request.id
        logging.info(f"[TASK] generate_final_image 시작 - task_id: {task_id}")
        logging.info(f"[INPUT] DALL·E 프롬프트: {dalle_prompt}")

        # 8. DALL·E 3 이미지 생성
        dalle_response = client.images.generate(model="dall-e-3", prompt=dalle_prompt, size="1024x1024", n=1)
        image_url = dalle_response.data[0].url
        logging.info(f"[STEP 8] DALL·E 이미지 URL: {image_url}")
        dalle_image_data = requests.get(image_url).content
        dalle_img = Image.open(BytesIO(dalle_image_data))

        # 9. Blob 저장: png/ 하위에 저장
        png_buffer = BytesIO()
        dalle_img.save(png_buffer, format="PNG")
        png_buffer.seek(0)
        filename_png = f"png/{task_id}.png"
        container_client.upload_blob(name=filename_png, data=png_buffer, overwrite=True)
        png_url = generate_sas_url(AZURE_ACCOUNT_NAME, AZURE_ACCOUNT_KEY, AZURE_CONTAINER_NAME, filename_png)
        logging.info(f"[STEP 9] PNG Blob 저장 완료: {png_url}")
        png_buffer.close()

        # 10. PSD 변환 후 psd/ 하위에 저장
        temp_png_path = f"/tmp/{task_id}.png"
        temp_psd_path = f"/tmp/{task_id}.psd"
        dalle_img.save(temp_png_path, format="PNG")
        subprocess.run(["convert", temp_png_path, temp_psd_path], check=True)
        with open(temp_psd_path, "rb") as f:
            container_client.upload_blob(name=f"psd/{task_id}.psd", data=f, overwrite=True)
        psd_url = generate_sas_url(AZURE_ACCOUNT_NAME, AZURE_ACCOUNT_KEY, AZURE_CONTAINER_NAME, f"psd/{task_id}.psd")
        logging.info(f"[STEP 10] PSD 업로드 완료: {psd_url}")

        # 임시 파일 삭제
        os.remove(temp_png_path)
        os.remove(temp_psd_path)

        return {"status": "SUCCESS", "png_url": png_url, "psd_url": psd_url}

    except Exception as e:
        logging.info(f"[ERROR] 전체 프로세스 실패: {e}")
        return {"status": "FAILURE", "error": str(e)}