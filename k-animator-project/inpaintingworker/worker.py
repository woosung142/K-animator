import os
import torch
import numpy as np
from PIL import Image, ImageOps
import cv2
from diffusers import StableDiffusionInpaintPipeline
from celery import Celery
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Celery configuration
BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

app = Celery(
    "inpaintingworker",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["worker"]
)
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Model and Path settings from user request
SD_INPAINT_MODEL_PATH = "/media/kanimator-sd-models/stable-diffusion-inpainting"

# Helper functions from sd_inpainting.py
def _to_multiple(size, m=8):
    w, h = size
    w2 = max(m, (w // m) * m)
    h2 = max(m, (h // m) * m)
    return (w2, h2)

def load_image(path, force_multiple=None):
    img = Image.open(path).convert("RGB")
    if force_multiple:
        tgt = _to_multiple(img.size, force_multiple)
        if img.size != tgt:
            img = img.resize(tgt, Image.LANCZOS)
    return img

def load_mask_L(path):
    return Image.open(path).convert("L")

def preprocess_mask(mask_L, size=None, invert=False, dilate=0, close=0, feather=0):
    if invert:
        mask_L = ImageOps.invert(mask_L)
    if size is not None and mask_L.size != size:
        mask_L = mask_L.resize(size, Image.NEAREST)
    m = np.array(mask_L, dtype=np.uint8)
    m = (m > 127).astype(np.uint8) * 255
    if dilate > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate*2+1, dilate*2+1))
        m = cv2.dilate(m, k, iterations=1)
    if close > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close*2+1, close*2+1))
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k, iterations=1)
    if feather > 0:
        m = cv2.GaussianBlur(m, (feather*2+1, feather*2+1), 0)
    return Image.fromarray(m, mode="L")

def pick_dtype_device(device_arg="auto"):
    device = "cuda" if torch.cuda.is_available() and device_arg == "auto" else device_arg
    dtype = torch.float16 if (device == "cuda") else torch.float32
    return device, dtype

def infer_use_safetensors(model_dir):
    if not os.path.isdir(model_dir): return False
    return any(f.endswith(".safetensors") for f in os.listdir(os.path.join(model_dir, "unet")))


@app.task(name="inpainting.inpaint")
def inpaint_image(segmentation_result: dict, prompt: str = "clean empty background, seamless, natural", negative_prompt: str = "person, people, human, face, hands, feet, text, watermark, artifacts, blurry, low quality"):
    """
    Celery task to perform inpainting on an image using a mask.
    """
    original_image_path = segmentation_result.get("original_image_path")
    mask_path = segmentation_result.get("combined_mask_path")
    output_dir = segmentation_result.get("output_dir")

    logger.info(f"Starting inpainting for image: {original_image_path} with mask: {mask_path}")

    if not all([original_image_path, mask_path, output_dir]):
        raise ValueError("Missing required paths in segmentation_result.")
    if not os.path.isfile(original_image_path):
        raise FileNotFoundError(f"Input image not found: {original_image_path}")
    if not os.path.isfile(mask_path):
        raise FileNotFoundError(f"Mask file not found: {mask_path}")

    base_name = os.path.splitext(os.path.basename(original_image_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}_inpainted.png")

    device, dtype = pick_dtype_device()
    use_st = infer_use_safetensors(SD_INPAINT_MODEL_PATH)

    logger.info(f"Device: {device}/{dtype}, Safetensors: {use_st}")

    # Load inputs
    image = load_image(original_image_path, force_multiple=8)
    maskL = load_mask_L(mask_path)
    
    # Preprocess mask (dilate to be safe)
    mask = preprocess_mask(maskL, size=image.size, dilate=32, close=8, feather=4)

    logger.info("Loading Stable Diffusion Inpainting pipeline...")
    try:
        pipe = StableDiffusionInpaintPipeline.from_pretrained(
            SD_INPAINT_MODEL_PATH,
            torch_dtype=dtype,
            use_safetensors=use_st,
            safety_checker=None,
        ).to(device)
    except Exception as e:
        raise RuntimeError(f"Failed to load inpainting model from {SD_INPAINT_MODEL_PATH}. Error: {e}")

    gen = torch.Generator(device=device).manual_seed(0)

    logger.info("Running inpainting inference...")
    result = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,
        image=image,
        mask_image=mask,
        guidance_scale=7.5,
        num_inference_steps=30,
        strength=0.98,
        generator=gen,
    ).images[0]

    result.save(output_path)
    logger.info(f"Successfully saved inpainted image to: {output_path}")

    return {"inpainted_image_path": output_path}