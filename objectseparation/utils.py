import os, cv2, numpy as np

def ensure_dir(p: str): os.makedirs(p, exist_ok=True)

def save_mask_png(mask: np.ndarray, path: str):
    cv2.imwrite(path, (mask.astype(np.uint8) * 255))

def overlay_masks(rgb: np.ndarray, per_masks, bal_masks, txt_masks):
    out = rgb.copy()
    def blend(ms, color):
        for m in ms:
            out[m>0] = (out[m>0]*0.55 + np.array(color)*0.45).astype(np.uint8)
    blend(per_masks, (255,0,0))     # person
    blend(bal_masks, (0,255,255))   # balloon
    blend(txt_masks, (0,0,255))     # text
    return out
