from celery import Celery
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
        print(f"[ERROR] Blob 이미지 로딩 실패 - {file_name}: {e}")
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
    "콘티": (
        "A very rough wireframe-style layout using only light pencil lines. "
        "There should be no shading, coloring, or filled areas — just loose hand-drawn outlines that indicate object placement and basic shapes. "
        "The sketch must look incomplete and minimal, focusing solely on structure, like a storyboard or planning draft."
    ),
    "스케치": (
        "A clean black-and-white pencil sketch with clearly defined outlines and simple grayscale shading. "
        "All major forms are visible, and contours are refined. "
        "No color is applied — depth and structure are shown using only brightness and line weight."
    ),
    "채색 기본": (
    "A partially colored illustration using flat tones in selected areas. "
    "Large portions of the image must remain uncolored, left white or in sketch form, to intentionally show incomplete coloring. "
    "The color palette should be minimal, with no shading or lighting — this is a color blocking phase to suggest intended tones."
    ),
    "채색 명암": (
    "A fully colored illustration where all areas are filled with flat, solid colors only. "
    "There should be no lighting, no shadows, no highlights, and no gradients. "
    "The image must remain completely flat in tone — it should look like a coloring book filled in, with no sense of light or depth."
    ),
    "배경": (
        "A fully rendered and polished scene with complete coloring, shading, lighting, texture, and atmosphere. "
        "All elements — foreground and background — are realistically detailed, showing depth, material qualities, and a unified environment. "
        "This should look like a finalized background image ready for use in production."
    )
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
        print(f"[ERROR] Wikipedia 이미지 검색 실패: {e}")
    return None


@celery_app.task(name="generate_image", bind=True)
def generate_image(self, category: str, layer: str, tag: str, caption_input: str | None = None, image_url: str | None = None) -> dict:
    try:
        task_id = self.request.id
        print(f"[TASK] generate_image 시작 - task_id: {task_id}")
        print(f"[INPUT] category: {category}, layer: {layer}, tag: {tag}, caption_input: {caption_input}, image_url: {image_url}")
        
        # 1. KoCLIP 임베딩
        text_to_embed = caption_input if caption_input else f"{tag}가 포함된 한국 웹툰 이미지를 그려주세요."
        print(f"[STEP 1] 임베딩 대상 텍스트: {text_to_embed}")
        embedding_vector = embed_text_koclip(text_to_embed)
        vector_str = "[" + ",".join([str(x) for x in embedding_vector]) + "]"
        print(f"[STEP 1] 생성된 임베딩 벡터 길이: {len(embedding_vector)}")

        images_content = []

        # 2. 사용자 업로드 이미지 (최우선, 1장)
        if image_url:
            print(f"[STEP 2] 사용자 업로드 이미지 추가: {image_url}")
            images_content.append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })

        # 3. DB 유사 이미지 최대 1장 추가
        if len(images_content) < 2:
            conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DBNAME, user=PG_USER, password=PG_PASSWORD)
            cursor = conn.cursor()
            keywords = [f"%{word.strip()}%" for word in tag.split()]
            print(f"[STEP 3] 태그 키워드 변환: {keywords}")

            sql = """
                SELECT file_name FROM korea_image_data
                WHERE category = %s AND layer = %s
                  AND tag ILIKE ANY (%s)
                ORDER BY vec_caption <-> %s::vector
                LIMIT 1;
            """
            cursor.execute(sql, (category, layer, keywords, vector_str))
            results = cursor.fetchall()
            print(f"[STEP 3] DB 검색 결과 file_name 리스트: {results}")
            cursor.close()
            conn.close()

            for row in results:
                file_name = row[0]
                print(f"[STEP 3] Blob에서 이미지 로딩 시도: {file_name}")
                image_b64 = get_blob_base64_image("img", file_name)
                if image_b64:
                    print(f"[STEP 3] base64 변환 성공: {file_name}")
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
                print(f"[STEP 4] Wikipedia 이미지 추가: {wiki_image_url}")
                images_content.append({
                    "type": "image_url",
                    "image_url": {"url": wiki_image_url}
                })
            else:
                print(f"[STEP 4] Wikipedia 이미지 없음")

        # 5. 이미지가 없어도 텍스트만으로 생성 가능
        if not images_content:
            print(f"[STEP 5] 이미지 없이 텍스트만으로 프롬프트 생성됨")

        # 6. GPT 프롬프트 생성
        prompt_text = (
            "Analyze the provided images and generate a background illustration that can be used in a DALL·E 3 prompt.\n"
            "- The illustration should depict a Korean-style background in webtoon style.\n"
            "- Do not include any human figures.\n"
            "- Objects should be simplified and intuitively represented.\n"
            "- Composition and placement should be suitable for a background scene.\n"
            "- The prompt must be formatted in fluent and optimized English for DALL·E 3.\n\n"
            "Additional instructions for the image prompt:\n"
            "- The purpose of the image is to serve as a Korean-style background in webtoon format where a person may be added later.\n"
            "- The main food item from the input keyword should be placed at the center of the table.\n"
            "- Other side dishes should be arranged next to it in a natural and balanced way.\n"
            "- Do NOT include raw ingredients or uncooked food components.\n"
            "- Do NOT include cooking tools, utensils, or preparation scenes.\n"
            "- Even without specific instructions, the background should always depict a traditional Korean dining table as the default.\n"
            "- The scene must exclude people and focus solely on the background setting.\n\n"
            f"Style step: '{layer}'\n"
            f"Style guide for this step:\n{layer_descriptions.get(layer, '')}\n\n"
            f"Original description from the user: \"{caption_input}\""
        )

        print(f"[STEP 6] 생성된 프롬프트:\n{prompt_text}")

        messages = [{
            "role": "user",
            "content": [{"type": "text", "text": prompt_text}] + images_content
        }]
        response = client.chat.completions.create(model="gpt-4o", messages=messages, max_tokens=800, temperature=0.7)
        dalle_prompt = response.choices[0].message.content.strip()
        print(f"[STEP 6] GPT 생성 결과:\n{dalle_prompt}")

        return {"status": "SUCCESS", "prompt": dalle_prompt}

    except Exception as e:
        print(f"[ERROR] 프롬프트 생성 실패: {e}")
        return {"status": "FAILURE", "error": str(e)}


@celery_app.task(name="generate_final_image", bind=True)
def generate_final_image(self, dalle_prompt: str) -> dict:
    try:
        task_id = self.request.id
        print(f"[TASK] generate_final_image 시작 - task_id: {task_id}")
        print(f"[INPUT] DALL·E 프롬프트: {dalle_prompt}")

        # 8. DALL·E 3 이미지 생성
        dalle_response = client.images.generate(model="dall-e-3", prompt=dalle_prompt, size="1024x1024", n=1)
        image_url = dalle_response.data[0].url
        print(f"[STEP 8] DALL·E 이미지 URL: {image_url}")
        dalle_image_data = requests.get(image_url).content
        dalle_img = Image.open(BytesIO(dalle_image_data))

        # 9. Blob 저장: png/ 하위에 저장
        png_buffer = BytesIO()
        dalle_img.save(png_buffer, format="PNG")
        png_buffer.seek(0)
        filename_png = f"png/{task_id}.png"
        container_client.upload_blob(name=filename_png, data=png_buffer, overwrite=True)
        png_url = generate_sas_url(AZURE_ACCOUNT_NAME, AZURE_ACCOUNT_KEY, AZURE_CONTAINER_NAME, filename_png)
        print(f"[STEP 9] PNG Blob 저장 완료: {png_url}")
        png_buffer.close()

        # 10. PSD 변환 후 psd/ 하위에 저장
        temp_png_path = f"/tmp/{task_id}.png"
        temp_psd_path = f"/tmp/{task_id}.psd"
        dalle_img.save(temp_png_path, format="PNG")
        subprocess.run(["convert", temp_png_path, temp_psd_path], check=True)
        with open(temp_psd_path, "rb") as f:
            container_client.upload_blob(name=f"psd/{task_id}.psd", data=f, overwrite=True)
        psd_url = generate_sas_url(AZURE_ACCOUNT_NAME, AZURE_ACCOUNT_KEY, AZURE_CONTAINER_NAME, f"psd/{task_id}.psd")
        print(f"[STEP 10] PSD 업로드 완료: {psd_url}")

        # 임시 파일 삭제
        os.remove(temp_png_path)
        os.remove(temp_psd_path)

        return {"status": "SUCCESS", "png_url": png_url, "psd_url": psd_url}

    except Exception as e:
        print(f"[ERROR] 전체 프로세스 실패: {e}")
        return {"status": "FAILURE", "error": str(e)}