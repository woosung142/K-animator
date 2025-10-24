# app_sd/sd_inpainting.py
import os
import argparse
import torch
import numpy as np
from PIL import Image, ImageOps
import cv2
from diffusers import StableDiffusionInpaintPipeline

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

def binarize(img_L):
    arr = np.array(img_L)
    arr = (arr > 127).astype(np.uint8) * 255
    return Image.fromarray(arr, mode="L")

def preprocess_mask(mask_L, size=None, invert=False, dilate=0, close=0, feather=0):
    """흰=채우기. size 맞추고(NEAREST), invert/팽창/클로징/페더 적용."""
    if invert:
        mask_L = ImageOps.invert(mask_L)
    if size is not None and mask_L.size != size:
        mask_L = mask_L.resize(size, Image.NEAREST)

    m = np.array(mask_L, dtype=np.uint8)

    # binary 안전화
    m = (m > 127).astype(np.uint8) * 255

    # morphological ops (pixels)
    if dilate and dilate > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate*2+1, dilate*2+1))
        m = cv2.dilate(m, k, iterations=1)

    if close and close > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close*2+1, close*2+1))
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k, iterations=1)

    # feather는 inpaint 입력 마스크에는 과도하게 주지 않는 게 안전.
    # 대신 후처리 블렌딩에 쓰는 편이 안정적이라 여기선 약하게만(옵션).
    if feather and feather > 0:
        m = cv2.GaussianBlur(m, (feather*2+1, feather*2+1), 0)
        # 여전히 0~255 범위 유지

    return Image.fromarray(m, mode="L")

def pick_dtype_device(device_arg):
    if device_arg == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = device_arg
    dtype = torch.float16 if (device == "cuda") else torch.float32
    return device, dtype

def infer_use_safetensors(model_dir):
    for _, _, files in os.walk(model_dir):
        if any(f.endswith(".safetensors") for f in files):
            return True
    return False

def main():
    ap = argparse.ArgumentParser(description="SD 1.5 Inpainting (with mask grow)")
    ap.add_argument("--model", "--model_dir", dest="model_dir", required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--mask", required=True)
    ap.add_argument("--output", default=None)
    ap.add_argument("--prompt", default="clean empty bench, background only, seamless, natural")
    ap.add_argument("--negative", default="person, people, human, face, hands, feet, text, speech bubble, watermark, artifacts, blurry")
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--guidance", type=float, default=7.5)
    ap.add_argument("--strength", type=float, default=0.98)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="auto", choices=["auto","cpu","cuda"])
    ap.add_argument("--force-multiple", type=int, default=8)

    # ★ 마스크 전처리 옵션
    ap.add_argument("--invert-mask", action="store_true", help="필요 시 흑/백 반전")
    ap.add_argument("--dilate", type=int, default=32, help="마스크 팽창 픽셀(가장자리 넉넉)")
    ap.add_argument("--close",  type=int, default=8,  help="구멍 메움(클로징) 픽셀")
    ap.add_argument("--feather",type=int, default=4,  help="가벼운 페더링(가우시안) 픽셀")

    # 결과 블렌딩(선택)
    ap.add_argument("--blend", type=float, default=1.0, help="마스크 영역 결과와 원본 블렌드(0~1)")

    args = ap.parse_args()

    if not os.path.isdir(args.model_dir):
        raise FileNotFoundError(f"모델 폴더 없음: {args.model_dir}")
    if not os.path.isfile(args.input):
        raise FileNotFoundError(f"입력 이미지 없음: {args.input}")
    if not os.path.isfile(args.mask):
        raise FileNotFoundError(f"마스크 없음: {args.mask}")

    # output 경로 기본값
    if args.output is None:
        base = os.path.splitext(os.path.basename(args.input))[0]
        out_dir = os.path.join(os.path.dirname(os.path.dirname(args.model_dir)), "out_enhanced")
        os.makedirs(out_dir, exist_ok=True)
        args.output = os.path.join(out_dir, f"{base}_sd_inpainted.png")
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

    device, dtype = pick_dtype_device(args.device)
    use_st = infer_use_safetensors(args.model_dir)

    # 입력/마스크 로드
    fm = args.force_multiple if args.force_multiple and args.force_multiple > 0 else None
    image = load_image(args.input, force_multiple=fm)
    maskL = load_mask_L(args.mask)
    mask  = preprocess_mask(
        maskL, size=image.size,
        invert=args.invert_mask,
        dilate=args.dilate, close=args.close, feather=args.feather
    )

    print("[INFO] model    :", os.path.abspath(args.model_dir))
    print("[INFO] input    :", os.path.abspath(args.input), image.size)
    print("[INFO] mask in  :", os.path.abspath(args.mask), "(invert)" if args.invert_mask else "")
    print("[INFO] mask out :", mask.size, f"(dilate={args.dilate}, close={args.close}, feather={args.feather})")
    print("[INFO] output   :", os.path.abspath(args.output))
    print("[INFO] device   :", device, "/", dtype, "| safetensors:", use_st)

    # 파이프라인
    pipe = StableDiffusionInpaintPipeline.from_pretrained(
        args.model_dir,
        torch_dtype=dtype,
        use_safetensors=use_st,
        safety_checker=None,
    ).to(device)

    gen = torch.Generator(device=device).manual_seed(args.seed)

    result = pipe(
        prompt=args.prompt,
        negative_prompt=(args.negative or None),
        image=image,
        mask_image=mask,
        guidance_scale=args.guidance,
        num_inference_steps=args.steps,
        strength=args.strength,
        generator=gen,
    )
    out = result.images[0]

    # (선택) 블렌딩
    if args.blend < 1.0:
        ori = np.array(image).astype(np.float32)
        res = np.array(out).astype(np.float32)
        m   = (np.array(mask).astype(np.float32) / 255.0)[..., None]
        a   = args.blend
        comp = ori*(1-m) + (ori*(1-a) + res*a)*m
        out = Image.fromarray(np.clip(comp,0,255).astype(np.uint8))

    out.save(args.output)
    print(f"[OK] saved: {os.path.abspath(args.output)}")

if __name__ == "__main__":
    main()
