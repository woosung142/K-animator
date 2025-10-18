# webtoon_two_layers.py
# -*- coding: utf-8 -*-
r"""
생성물(5개):
- palette_flat.png        : 팔레트(K-means) + 가이드 필터로 만든 '색 면' 베이스(RGB).
- sketch_hard.png         : 연속 알파 스케치(하드). 0~255 그레이(값 클수록 선 강함).
- sketch_hard_rgba.png    : RGBA, A 채널에 선 강도(연속 알파).
- color_white_lines.png   : 선택 마스크(soft/hard) 주변만 흰색으로 덮어 선 약화.
- merged_preview.png      : color_only에서 A_soft 비율만큼 선이 사라진 미리보기.

주의: 본 축약본은 trans_* 파라미터를 파싱만 하며 사용하지 않습니다.
"""

import os
import argparse
import numpy as np
import cv2
from PIL import Image

# ---------- utils ----------
def ensure_dir(p): os.makedirs(p, exist_ok=True)

def srgb_to_linear(u8):
    x = u8.astype(np.float32) / 255.0
    a = 0.055
    return np.where(x <= 0.04045, x/12.92, ((x + a)/(1 + a))**2.4)

# ---------- color base ----------
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

# ---------- sketch ----------
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

# ---------- main decomposition ----------
def webtoon_decompose(img_rgb, K=12, gf_r=16, gf_eps=2e-3, gf_passes=2,
                      alpha_gain=1.15, hard_gain=1.35, hard_bias=0.0, hard_gamma=0.85):
    bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

    pal  = palette_quantize(bgr, K=K)
    flat = guided_color_flatten(pal, r=gf_r, eps=gf_eps, passes=gf_passes)  # BGR

    A0 = soft_line_alpha(bgr)  # 0..1

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

# ---------- whiten lines ----------
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

# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser()

    # 1) 여기 기본 경로를 넣어두면, 인자 없이 실행해도 동작
    ap.add_argument(
        "--input",
        type=str,
        required=False,
        default=r"C:\Users\sojeong\k_animator\data\input\ex1 (52).png",
        help="입력 이미지 경로(미지정 시 기본값 사용)"
    )
    ap.add_argument(
        "--output_dir",
        type=str,
        required=False,
        default=r"C:\Users\sojeong\k_animator\data\webtoon_layers",
        help="출력 폴더(미지정 시 기본값 사용)"
    )

    # 색 면
    ap.add_argument("--palette_k", type=int, default=12)
    ap.add_argument("--gf_radius", type=int, default=16)
    ap.add_argument("--gf_eps", type=float, default=2e-3)
    ap.add_argument("--gf_passes", type=int, default=2)

    # 스케치
    ap.add_argument("--alpha_gain", type=float, default=1.15)
    ap.add_argument("--hard_gain", type=float, default=1.35)
    ap.add_argument("--hard_bias", type=float, default=0.0)
    ap.add_argument("--hard_gamma", type=float, default=0.85)

    # 화이트 덮기용 마스크·강도
    ap.add_argument("--mask_source", type=str, default="soft", choices=["soft","hard"])
    ap.add_argument("--white_strength", type=float, default=0.65)
    ap.add_argument("--white_expand", type=int, default=1)
    ap.add_argument("--white_feather", type=int, default=1)

    # 미리보기
    ap.add_argument("--sketch_overlay", type=float, default=0.6)

    # ▼▼▼ 요청하신 trans_* 파라미터: 현재는 '파싱만' 하며 미사용(축약본 유지 목적) ▼▼▼
    ap.add_argument("--trans_weight", type=float, default=0.6)
    ap.add_argument("--trans_gamma", type=float, default=1.8)
    ap.add_argument("--trans_expand", type=int,   default=0)
    ap.add_argument("--trans_recolor", type=float, default=0.95)
    ap.add_argument("--trans_desat", type=float,   default=0.8)
    ap.add_argument("--trans_luma", type=float,    default=0.8)
    ap.add_argument("--trans_alpha_boost", type=float, default=0.22)
    ap.add_argument("--trans_feather", type=int,   default=1)
    # ▲▲▲ 여기까지 추가만 해 둠. 투명화 산출물 복구 시 그대로 사용 가능. ▲▲▲

    args = ap.parse_args()
    ensure_dir(args.output_dir)

    rgb = np.array(Image.open(args.input).convert("RGB"))
    A_soft, A_hard, color_only_u8, flat_bgr = webtoon_decompose(
        rgb,
        K=args.palette_k, gf_r=args.gf_radius, gf_eps=args.gf_eps, gf_passes=args.gf_passes,
        alpha_gain=args.alpha_gain,
        hard_gain=args.hard_gain, hard_bias=args.hard_bias, hard_gamma=args.hard_gamma
    )

    H, W = A_soft.shape

    # 1) palette_flat.png
    Image.fromarray(cv2.cvtColor(flat_bgr, cv2.COLOR_BGR2RGB)).save(
        os.path.join(args.output_dir, "palette_flat.png")
    )

    # 2) sketch_hard.png
    sketch_hard_u8 = np.clip(A_hard*255.0, 0, 255).astype(np.uint8)
    Image.fromarray(sketch_hard_u8).save(os.path.join(args.output_dir, "sketch_hard.png"))

    # 3) sketch_hard_rgba.png  (RGB=0, A=선 강도)
    sketch_hard_rgba = np.dstack([
        np.zeros((H,W), np.uint8),
        np.zeros((H,W), np.uint8),
        np.zeros((H,W), np.uint8),
        sketch_hard_u8
    ])
    Image.fromarray(sketch_hard_rgba, mode="RGBA").save(
        os.path.join(args.output_dir, "sketch_hard_rgba.png")
    )

    # 마스크 선택
    line_mask = A_soft if args.mask_source == "soft" else A_hard

    # 4) color_white_lines.png  (선 주변만 흰색으로 약화)
    color_white = whiten_lines(
        img_rgb=color_only_u8,
        line_mask_01=line_mask,
        strength=args.white_strength,
        expand_px=args.white_expand,
        feather_px=args.white_feather
    )
    Image.fromarray(color_white).save(os.path.join(args.output_dir, "color_white_lines.png"))

    # 5) merged_preview.png  (color_only에서 A_soft*k 만큼 선 제거 미리보기)
    prev = color_only_u8.astype(np.float32)/255.0
    S = np.clip(args.sketch_overlay, 0.0, 1.0) * (A_soft[...,None])
    prev = np.clip((1.0 - S) * prev, 0.0, 1.0)
    Image.fromarray(np.clip(prev*255.0, 0, 255).astype(np.uint8)).save(
        os.path.join(args.output_dir, "merged_preview.png")
    )

    print("[OK] saved to:", os.path.abspath(args.output_dir))
    print("[mask used for white/preview]:", "A_soft" if args.mask_source=="soft" else "A_hard")

if __name__ == "__main__":
    main()
