import os
import numpy as np
import cv2
from PIL import Image
from controlnet_aux import PidiNetDetector, LineartAnimeDetector, HEDdetector
from transformers import pipeline
from celery import Celery
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Celery configuration
# The user mentioned redis, so I'll use that as the broker.
# I'll assume the redis service is named 'redis'.
BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

app = Celery(
    "sam2worker",
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
SAM2_MODEL_PATH = "/media/kanimator-sd-models/sam2-model"
# Let's assume a shared volume for data I/O
SHARED_DATA_PATH = os.environ.get("SHARED_DATA_PATH", "/app/data") # This will be mounted

# ========= Hyperparameters from sam2_enhanced_pipeline.py =========
TARGET_SIZE = 1024
CLAHE_CLIP_LIMIT = 2.5
CLAHE_TILE_SIZE = 8
GAMMA = 1.0
EDGE_THRESHOLD = 0.5
RING_DARKEN = 0.85
BOX_PADDING = 8
MIN_BOX_AREA = 1000

# Helper functions from sam2_enhanced_pipeline.py (with slight modifications for worker context)
def imread_unicode(p):
    data = np.fromfile(p, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        logger.error(f"Failed to read image from {p}")
    return img

def resize_long_edge(img, target_size):
    h, w = img.shape[:2]
    if max(h, w) <= target_size:
        return img
    if h > w:
        new_h = target_size
        new_w = int(w * target_size / h)
    else:
        new_w = target_size
        new_h = int(h * target_size / w)
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

def bilateral_denoise(img):
    return cv2.bilateralFilter(img, 9, 75, 75)

def clahe_enhance(img, clip_limit=2.5, tile_size=8):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

def gamma_correction(img, gamma=1.0):
    if gamma == 1.0: return img
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype("uint8")
    return cv2.LUT(img, table)

def generate_edge_hints(img, method="pidinet", threshold=0.5):
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    try:
        if method == "pidinet":
            detector = PidiNetDetector.from_pretrained("lllyasviel/Annotators")
        elif method == "lineart":
            detector = LineartAnimeDetector.from_pretrained("lllyasviel/Annotators")
        elif method == "hed":
            detector = HEDdetector.from_pretrained("lllyasviel/Annotators")
        else:
            raise ValueError(f"Unknown edge method: {method}")
        edge_map = detector(img_pil, safe=True, detect_resolution=1024, image_resolution=1024)
        edge_array = np.array(edge_map)
        if len(edge_array.shape) == 3:
            edge_gray = cv2.cvtColor(edge_array, cv2.COLOR_BGR2GRAY)
        else:
            edge_gray = edge_array
        h, w = img.shape[:2]
        edge_resized = cv2.resize(edge_gray, (w, h))
        _, edge_binary = cv2.threshold(edge_resized, int(255 * threshold), 255, cv2.THRESH_BINARY)
        return edge_binary
    except Exception as e:
        logger.error(f"Edge detection failed: {e}")
        return None

def create_outer_ring_hint(img, edge_binary, darken_factor=0.85):
    if edge_binary is None: return img
    enhanced = img.copy().astype(np.float32)
    kernel = np.ones((3, 3), np.uint8)
    edge_dilated = cv2.dilate(edge_binary, kernel, iterations=1)
    outer_ring = cv2.subtract(edge_dilated, edge_binary)
    ring_mask = outer_ring > 0
    enhanced[ring_mask] *= darken_factor
    return np.clip(enhanced, 0, 255).astype(np.uint8)

def generate_box_prompts(edge_binary, min_area=1000, padding=8):
    if edge_binary is None: return []
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(edge_binary, connectivity=8)
    boxes = []
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < min_area: continue
        x, y, w, h = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP], stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
        x, y = max(0, x - padding), max(0, y - padding)
        w, h = min(edge_binary.shape[1] - x, w + 2 * padding), min(edge_binary.shape[0] - y, h + 2 * padding)
        boxes.append((x, y, x + w, y + h))
    return boxes

def enhanced_preprocessing(img, edge_method="pidinet"):
    resized = resize_long_edge(img, TARGET_SIZE)
    denoised = bilateral_denoise(resized)
    clahe_img = clahe_enhance(denoised, CLAHE_CLIP_LIMIT, CLAHE_TILE_SIZE)
    gamma_img = gamma_correction(clahe_img, GAMMA)
    edge_binary = generate_edge_hints(gamma_img, edge_method, EDGE_THRESHOLD)
    if edge_binary is not None:
        enhanced = create_outer_ring_hint(gamma_img, edge_binary, RING_DARKEN)
    else:
        enhanced = gamma_img
    boxes = generate_box_prompts(edge_binary, MIN_BOX_AREA, BOX_PADDING)
    return enhanced, edge_binary, boxes

@app.task(name="sam2.segment")
def segment_image(image_path: str):
    """
    Celery task to perform object segmentation using SAM2.
    Takes an image path, performs preprocessing and segmentation,
    and returns paths to the results for the next task.
    """
    logger.info(f"Starting segmentation for image: {image_path}")

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Input image not found at: {image_path}")

    # Create a unique output directory for this task
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    task_out_dir = os.path.join(SHARED_DATA_PATH, base_name)
    os.makedirs(task_out_dir, exist_ok=True)

    img = imread_unicode(image_path)
    if img is None:
        raise ValueError("Could not read image.")

    # --- Preprocessing ---
    logger.info("Performing enhanced preprocessing...")
    enhanced_img, edge_binary, boxes = enhanced_preprocessing(img, edge_method="pidinet")
    
    enhanced_path = os.path.join(task_out_dir, f"{base_name}_enhanced.png")
    cv2.imwrite(enhanced_path, enhanced_img)
    logger.info(f"Saved enhanced image to: {enhanced_path}")

    # --- SAM2 Execution ---
    logger.info("Loading SAM2 model...")
    try:
        # The user specified a local path, so we use it.
        mask_gen = pipeline("mask-generation", model=SAM2_MODEL_PATH, device=0)
    except Exception as e:
        logger.error(f"Failed to load SAM2 model from {SAM2_MODEL_PATH}. Error: {e}")
        # Fallback to huggingface hub if local fails, as in original script
        try:
            logger.warning("Falling back to loading SAM2 model from Hugging Face Hub.")
            mask_gen = pipeline("mask-generation", model="facebook/sam2.1-hiera-base-plus", device=0)
        except Exception as e_hf:
            raise RuntimeError(f"Failed to load SAM2 model from both local path and Hugging Face Hub. Errors: Local='{e}', HF='{e_hf}'")

    logger.info("Running SAM2 mask generation...")
    img_pil = Image.fromarray(cv2.cvtColor(enhanced_img, cv2.COLOR_BGR2RGB))
    
    if boxes:
        logger.info(f"Using {len(boxes)} generated box prompts.")
        box_coords = [[box[0], box[1], box[2], box[3]] for box in boxes]
        output = mask_gen(img_pil, boxes=box_coords)
    else:
        logger.info("No boxes generated, using automatic mask generation.")
        output = mask_gen(img_pil)

    # --- Save results ---
    masks_path = os.path.join(task_out_dir, f"{base_name}_masks.npz")
    # The output from pipeline is a list of dicts. We need to save the masks.
    # Let's check the format. It's usually {'masks': [mask], 'scores': [score], ...}
    # The original script does np.savez_compressed(masks_path, **out)
    # Let's assume `output` is a dict that can be saved this way.
    if isinstance(output, list): # The pipeline can return a list of dicts
        # We need to extract masks from the list.
        all_masks = [item['mask'] for item in output]
        np.savez_compressed(masks_path, masks=all_masks)
    else: # Or a single dict
        np.savez_compressed(masks_path, **output)

    logger.info(f"Saved SAM2 masks to: {masks_path}")

    # The user's goal is to remove an object. The `select_enhanced_masks.py` script
    # implies a user selection step. For a fully async pipeline, we need a strategy.
    # Let's assume for now we want to inpaint ALL detected objects.
    # The next worker will need the original image and a single combined mask.
    
    # Let's load the masks back and create a single binary mask.
    # This simplifies the job for the inpainting worker.
    
    all_masks = []
    with np.load(masks_path, allow_pickle=True) as data:
        if 'masks' in data:
            all_masks = data['masks']
        else: # Fallback for older format
            # This part is tricky without knowing the exact output format.
            # Let's assume 'masks' key exists.
            pass

    original_size = imread_unicode(image_path).shape[1::-1] # (w, h)
    final_mask_path = os.path.join(task_out_dir, f"{base_name}_combined_mask.png")

    if not all_masks: # Simplified check for empty list
        logger.warning("SAM2 did not return any masks. Creating an empty mask.")
        final_mask_img = Image.new('L', original_size, 0)
    else:
        # Combine all masks into one.
        # Assuming masks are PIL Images or numpy arrays
        first_mask = all_masks[0]
        if isinstance(first_mask, Image.Image):
            final_mask_np = np.array(first_mask)
        else:
            final_mask_np = first_mask

        for i in range(1, len(all_masks)):
            if isinstance(all_masks[i], Image.Image):
                mask_np = np.array(all_masks[i])
            else:
                mask_np = all_masks[i]
            final_mask_np = np.logical_or(final_mask_np, mask_np)
        
        final_mask_img = Image.fromarray(final_mask_np.astype(np.uint8) * 255, "L")
        
        # Resize mask to original image size
        final_mask_img = final_mask_img.resize(original_size, Image.NEAREST)

    final_mask_img.save(final_mask_path)
    logger.info(f"Saved final mask for inpainting to: {final_mask_path}")

    return {
        "original_image_path": image_path,
        "combined_mask_path": final_mask_path,
        "output_dir": task_out_dir
    }