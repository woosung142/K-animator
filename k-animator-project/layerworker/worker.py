from dotenv import load_dotenv
from celery import Celery
from celery.signals import after_setup_logger
import logging
import os
import tempfile
import requests
import subprocess
from pathlib import Path

import numpy as np
import cv2
from PIL import Image
from psd_tools.api.layers import ImageLayer
from psd_tools.api.psd_image import PSDImage

# shared.blob_storage 모듈을 임포트합니다.
# 이 모듈은 Dockerfile에 의해 /app/shared/ 경로에 복사되어 있어야 합니다.
from shared import blob_storage

# --- 환경변수 로딩 ---
load_dotenv()

# Celery 설정
# broker와 backend URL은 환경변수 또는 docker-compose에서 설정하는 것이 좋습니다.
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

celery_app = Celery('layerworker', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

# --- 로거 설정 ---
@after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    formatter = logging.Formatter('[%(asctime)s: %(levelname)s/%(processName)s] %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# --- edit.py의 이미지 처리 함수들을 여기에 통합 ---

def srgb_to_linear(u8):
    x = u8.astype(np.float32) / 255.0
    a = 0.055
    return np.where(x <= 0.04045, x/12.92, ((x + a)/(1 + a))**2.4)

def palette_quantize(bgr, K=12, attempts=1):
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).reshape(-1,3).astype(np.float32)
    criteria=(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5)
    _,labels,centers=cv2.kmeans(lab, K, None, criteria, attempts, cv2.KMEANS_PP_CENTERS)
    qlab = centers[labels.flatten()].reshape(bgr.shape).astype(np.uint8)
    q = cv2.cvtColor(qlab, cv2.COLOR_LAB2BGR)
    q = cv2.medianBlur(q, 3)
    return q

def guided_color_flatten(bgr, r=16, eps=2e-3, passes=2):
    I = bgr.astype(np.float32)/255.0
    out = I.copy()
    k = (2*r+1, 2*r+1)
    for _ in range(passes):
        mean_I = cv2.blur(I, k); mean_out = cv2.blur(out, k)
        mean_Iout = cv2.blur(I*out, k)
        cov = mean_Iout - mean_I*mean_out
        mean_II = cv2.blur(I*I, k); varI = mean_II - mean_I*mean_I
        a = cov / (varI + eps); b = mean_out - a*mean_I
        mean_a = cv2.blur(a, k); mean_b = cv2.blur(b, k)
        out = mean_a * I + mean_b
    return np.clip(out*255.0, 0, 255).astype(np.uint8)

def soft_line_alpha(I_bgr):
    Y = cv2.cvtColor(I_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)/255.0
    bh = cv2.morphologyEx((1.0 - Y), cv2.MORPH_BLACKHAT,
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3)))
    A0 = np.clip(bh*2.0, 0.0, 1.0)
    A0 = cv2.GaussianBlur(A0, (0,0), 0.6)
    return A0

def make_sketch_hard_from_soft(A_soft, gain=1.35, bias=0.0, gamma=0.85):
    a = np.power(np.clip(A_soft, 0, 1).astype(np.float32), gamma) * gain + float(bias)
    return np.clip(a, 0.0, 1.0)

def webtoon_decompose(img_rgb, K=12, gf_r=16, gf_eps=2e-3, gf_passes=2,
                      alpha_gain=1.15, hard_gain=1.35, hard_bias=0.0, hard_gamma=0.85):
    bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    pal  = palette_quantize(bgr, K=K)
    flat = guided_color_flatten(pal, r=gf_r, eps=gf_eps, passes=gf_passes)
    A0 = soft_line_alpha(bgr)
    I_lin = srgb_to_linear(cv2.cvtColor(bgr,  cv2.COLOR_BGR2RGB))
    C_lin = srgb_to_linear(cv2.cvtColor(flat, cv2.COLOR_BGR2RGB))
    A_mul = 1.0 - (I_lin + 1e-4) / (C_lin + 1e-4)
    A_mul = np.clip(A_mul, 0.0, 1.0)
    A1 = np.mean(A_mul, axis=2)
    A_soft = np.clip(0.5*A0 + 0.5*A1, 0.0, 1.0)
    A_soft = cv2.GaussianBlur(A_soft, (0,0), 0.5)
    A_soft = np.clip(A_soft * float(alpha_gain), 0.0, 1.0)
    A_hard = make_sketch_hard_from_soft(A_soft, gain=hard_gain, bias=hard_bias, gamma=hard_gamma)
    C_rgb = cv2.cvtColor(flat, cv2.COLOR_BGR2RGB).astype(np.float32)/255.0
    I_rgb = img_rgb.astype(np.float32)/255.0
    color_only = (1.0 - A_soft[...,None])*I_rgb + A_soft[...,None]*C_rgb
    color_only_u8 = np.clip(color_only*255.0, 0, 255).astype(np.uint8)
    return A_soft, A_hard, color_only_u8, flat

def whiten_lines(img_rgb, line_mask_01, strength=0.65, expand_px=1, feather_px=1):
    A = np.clip(line_mask_01.astype(np.float32), 0.0, 1.0)
    if expand_px > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*expand_px+1, 2*expand_px+1))
        A = cv2.dilate((A*255).astype(np.uint8), k, 1).astype(np.float32)/255.0
    if feather_px > 0:
        ksz = (2*feather_px+1) | 1
        A = cv2.GaussianBlur(A, (ksz, ksz), 0.0)
    img = img_rgb.astype(np.float32) / 255.0
    W = np.clip(A * float(strength), 0.0, 1.0)[..., None]
    out = (1.0 - W) * img + W * 1.0
    return np.clip(out*255.0, 0, 255).astype(np.uint8)

# --- Celery Task 구현 ---

@celery_app.task(name="separate_layers_task", bind=True)
def separate_layers_task(self, image_url: str) -> dict:
    task_id = self.request.id
    logging.info(f"[TASK] separate_layers_task 시작 - task_id: {task_id}")
    logging.info(f"[INPUT] image_url: {image_url[:100]}...")

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # 1. 이미지 다운로드
            logging.info(f"[STEP 1] 이미지 다운로드 시작")
            response = requests.get(image_url, stream=True)
            response.raise_for_status()
            
            input_image = Image.open(response.raw).convert("RGB")
            rgb_array = np.array(input_image)
            logging.info(f"[STEP 1] 이미지 다운로드 및 RGB 변환 완료. Shape: {rgb_array.shape}")

            # 2. 레이어 분리 로직 실행
            logging.info(f"[STEP 2] 레이어 분리 시작")
            A_soft, A_hard, color_only_u8, _ = webtoon_decompose(rgb_array)
            
            H, W, _ = rgb_array.shape
            
            # 3. 주요 레이어를 Pillow 이미지 객체로 준비
            logging.info(f"[STEP 3] 주요 레이어 Pillow 이미지로 변환 시작")
            
            color_layer_pil = Image.fromarray(whiten_lines(img_rgb=color_only_u8, line_mask_01=A_soft))
            
            sketch_hard_u8 = np.clip(A_hard*255.0, 0, 255).astype(np.uint8)
            sketch_layer_rgba_pil = Image.fromarray(np.dstack([
                np.zeros((H,W), np.uint8),
                np.zeros((H,W), np.uint8),
                np.zeros((H,W), np.uint8),
                sketch_hard_u8
            ]), mode="RGBA")
            logging.info(f"[STEP 3] 레이어 변환 완료")

            # 4. psd-tools로 PSD 생성
            logging.info(f"[STEP 4] PSD 생성 시작")
            output_psd_path = os.path.join(temp_dir, f"{task_id}.psd")
            
            # psd-tools를 사용하여 레이어 생성
            color_image_layer = ImageLayer.from_pil(color_layer_pil, name='color')
            sketch_image_layer = ImageLayer.from_pil(sketch_layer_rgba_pil, name='sketch')
            
            # PSD 이미지 구성 (아래쪽 레이어부터 순서대로)
            psd = PSDImage([color_image_layer, sketch_image_layer])
            with open(output_psd_path, 'wb') as f:
                psd.save(f)
            logging.info(f"[STEP 4] PSD 생성 완료: {output_psd_path}")

            # 5. PSD 파일 Blob Storage에 업로드
            logging.info(f"[STEP 5] PSD 파일 Blob Storage 업로드 시작")
            psd_blob_name = f"public/generated/psd_layers/{task_id}.psd"
            
            with open(output_psd_path, "rb") as f:
                blob_storage.upload_blob(blob_name=psd_blob_name, data=f.read(), overwrite=True)
            logging.info(f"[STEP 5] Blob 업로드 완료: {psd_blob_name}")

            # 6. SAS URL 생성
            logging.info(f"[STEP 6] SAS URL 생성 시작")
            psd_sas_url = blob_storage.generate_sas_url(blob_name=psd_blob_name, expiry_minutes=60)
            logging.info(f"[STEP 6] SAS URL 생성 완료")

            logging.info(f"[SUCCESS] 작업 완료 - task_id: {task_id}")
            return {"status": "SUCCESS", "psd_layer_url": psd_sas_url}

        except Exception as e:
            logging.error(f"[ERROR] 레이어 분리 실패 (task_id: {task_id}): {e}", exc_info=True)
            raise e
""