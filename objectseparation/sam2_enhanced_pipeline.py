import os, sys, numpy as np, cv2
from PIL import Image
from controlnet_aux import PidiNetDetector, LineartAnimeDetector, HEDdetector
import argparse

# ========= 경로/모델 =========
IMAGE_PATH = r"data/input/test2.png"
OUT_DIR    = r"out_enhanced"
SAM2_MODEL = "facebook/sam2.1-hiera-base-plus"

# ========= 하이퍼파라미터 =========
TARGET_SIZE = 1024          # 긴 변 기준 리사이즈
CLAHE_CLIP_LIMIT = 2.5      # CLAHE 클립 제한
CLAHE_TILE_SIZE = 8         # CLAHE 타일 크기
GAMMA = 1.0                 # 감마 보정
EDGE_THRESHOLD = 0.5        # 엣지 임계값
RING_DARKEN = 0.85          # 외곽 링 어둡게 하기
BOX_PADDING = 8             # 박스 패딩
MIN_BOX_AREA = 1000         # 최소 박스 면적

os.makedirs(OUT_DIR, exist_ok=True)

def imread_unicode(p):
    img = cv2.imread(p)
    if img is not None: return img
    data = np.fromfile(p, dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)

def resize_long_edge(img, target_size):
    """긴 변을 기준으로 리사이즈"""
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
    """라인 보존하며 노이즈 제거"""
    return cv2.bilateralFilter(img, 9, 75, 75)

def clahe_enhance(img, clip_limit=2.5, tile_size=8):
    """CLAHE로 로컬 대비 강화"""
    # LAB 색공간으로 변환
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # L 채널에만 CLAHE 적용
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
    l = clahe.apply(l)
    
    # 다시 BGR로 변환
    lab = cv2.merge([l, a, b])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

def gamma_correction(img, gamma=1.0):
    """감마 보정"""
    if gamma == 1.0:
        return img
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype("uint8")
    return cv2.LUT(img, table)

def generate_edge_hints(img, method="pidinet", threshold=0.5):
    """엣지 기반 힌트 생성"""
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    
    try:
        if method == "pidinet":
            detector = PidiNetDetector.from_pretrained("lllyasviel/Annotators")
            edge_map = detector(img_pil, safe=True, detect_resolution=1024, image_resolution=1024)
        elif method == "lineart":
            detector = LineartAnimeDetector.from_pretrained("lllyasviel/Annotators")
            edge_map = detector(img_pil, detect_resolution=1024, image_resolution=1024, coarse=False)
        elif method == "hed":
            detector = HEDdetector.from_pretrained("lllyasviel/Annotators")
            edge_map = detector(img_pil, detect_resolution=1024, image_resolution=1024, apply_smoothing=True)
        else:
            raise ValueError(f"Unknown edge method: {method}")
        
        # PIL Image를 numpy로 변환
        if isinstance(edge_map, Image.Image):
            edge_array = np.array(edge_map)
        else:
            edge_array = edge_map
        
        # 그레이스케일로 변환
        if len(edge_array.shape) == 3:
            edge_gray = cv2.cvtColor(edge_array, cv2.COLOR_RGB2GRAY)
        else:
            edge_gray = edge_array
        
        # 원본 크기로 리사이즈
        h, w = img.shape[:2]
        edge_resized = cv2.resize(edge_gray, (w, h))
        
        # 이진화
        _, edge_binary = cv2.threshold(edge_resized, int(255 * threshold), 255, cv2.THRESH_BINARY)
        
        return edge_binary
        
    except Exception as e:
        print(f"엣지 디텍션 실패: {e}")
        return None

def create_outer_ring_hint(img, edge_binary, darken_factor=0.85):
    """외곽 링을 어둡게 하여 경계 신호 강화"""
    if edge_binary is None:
        return img
    
    enhanced = img.copy().astype(np.float32)
    
    # 1px 팽창
    kernel = np.ones((3, 3), np.uint8)
    edge_dilated = cv2.dilate(edge_binary, kernel, iterations=1)
    
    # 외곽 링만 추출 (팽창된 것 - 원본)
    outer_ring = cv2.subtract(edge_dilated, edge_binary)
    
    # 외곽 링 영역을 어둡게
    ring_mask = outer_ring > 0
    enhanced[ring_mask] *= darken_factor
    
    return np.clip(enhanced, 0, 255).astype(np.uint8)

def generate_box_prompts(edge_binary, min_area=1000, padding=8):
    """엣지 맵에서 박스 프롬프트 자동 생성"""
    if edge_binary is None:
        return []
    
    # 연결 성분 분석
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(edge_binary, connectivity=8)
    
    boxes = []
    for i in range(1, num_labels):  # 0은 배경
        area = stats[i, cv2.CC_STAT_AREA]
        if area < min_area:
            continue
        
        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]
        
        # 패딩 추가
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(edge_binary.shape[1] - x, w + 2 * padding)
        h = min(edge_binary.shape[0] - y, h + 2 * padding)
        
        boxes.append((x, y, x + w, y + h))
    
    return boxes

def l0_smoothing(img, lambda_val=0.01):
    """L0 스무딩으로 색 덩어리 강화 (간단한 구현)"""
    # 간단한 가우시안 블러 + 언샤프 마스킹
    blurred = cv2.GaussianBlur(img, (5, 5), 0)
    mask = cv2.absdiff(img, blurred)
    mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(mask, 30, 255, cv2.THRESH_BINARY)
    
    # 마스크 영역만 블러 적용
    result = img.copy()
    mask_3d = np.stack([mask] * 3, axis=2)
    result = np.where(mask_3d > 0, blurred, img)
    
    return result

def enhanced_preprocessing(img, edge_method="pidinet", use_l0=False):
    """전체 전처리 파이프라인"""
    print("=== 1단계: 해상도 조정 ===")
    resized = resize_long_edge(img, TARGET_SIZE)
    print(f"리사이즈: {img.shape} → {resized.shape}")
    
    print("=== 2단계: 노이즈 제거 ===")
    denoised = bilateral_denoise(resized)
    
    print("=== 3단계: 로컬 대비 강화 (CLAHE) ===")
    clahe_img = clahe_enhance(denoised, CLAHE_CLIP_LIMIT, CLAHE_TILE_SIZE)
    
    print("=== 4단계: 감마 보정 ===")
    gamma_img = gamma_correction(clahe_img, GAMMA)
    
    print("=== 5단계: 엣지 힌트 생성 ===")
    edge_binary = generate_edge_hints(gamma_img, edge_method, EDGE_THRESHOLD)
    
    print("=== 6단계: 외곽 링 강화 ===")
    if edge_binary is not None:
        enhanced = create_outer_ring_hint(gamma_img, edge_binary, RING_DARKEN)
    else:
        enhanced = gamma_img
    
    print("=== 7단계: 색 덩어리 강화 (L0) ===")
    if use_l0:
        enhanced = l0_smoothing(enhanced)
    
    print("=== 8단계: 박스 프롬프트 생성 ===")
    boxes = generate_box_prompts(edge_binary, MIN_BOX_AREA, BOX_PADDING)
    print(f"생성된 박스: {len(boxes)}개")
    
    return enhanced, edge_binary, boxes

def visualize_boxes(img, boxes, save_path):
    """박스 시각화"""
    vis = img.copy()
    for i, (x1, y1, x2, y2) in enumerate(boxes):
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(vis, str(i+1), (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.imwrite(save_path, vis)
    return vis

def main():
    parser = argparse.ArgumentParser(description='Enhanced SAM2 Pipeline')
    parser.add_argument('--input', default=IMAGE_PATH, help='Input image path')
    parser.add_argument('--edge', choices=['pidinet', 'lineart', 'hed'], default='pidinet', help='Edge detection method')
    parser.add_argument('--prep', choices=['none', 'clahe', 'l0'], default='clahe', help='Preprocessing level')
    parser.add_argument('--size', type=int, default=1024, help='Target size for long edge')
    args = parser.parse_args()
    
    # 전역 변수 업데이트
    global TARGET_SIZE
    TARGET_SIZE = args.size
    input_image = args.input
    
    print(f"입력 이미지: {input_image}")
    print(f"엣지 방법: {args.edge}")
    print(f"전처리: {args.prep}")
    print(f"타겟 크기: {TARGET_SIZE}")
    
    # 이미지 로드
    img = imread_unicode(input_image)
    if img is None:
        print(f"이미지 로드 실패: {input_image}")
        return
    
    base = os.path.splitext(os.path.basename(input_image))[0]
    
    # 전처리 실행
    use_l0 = (args.prep == 'l0')
    enhanced, edge_binary, boxes = enhanced_preprocessing(img, args.edge, use_l0)
    
    # 결과 저장
    print("\n=== 결과 저장 ===")
    
    # 전처리된 이미지
    enhanced_path = os.path.join(OUT_DIR, f"{base}_enhanced_{args.edge}_{args.prep}.png")
    cv2.imwrite(enhanced_path, enhanced)
    print(f"전처리된 이미지: {enhanced_path}")
    
    # 엣지 맵
    if edge_binary is not None:
        edge_path = os.path.join(OUT_DIR, f"{base}_edge_{args.edge}.png")
        cv2.imwrite(edge_path, edge_binary)
        print(f"엣지 맵: {edge_path}")
    
    # 박스 시각화
    if boxes:
        box_path = os.path.join(OUT_DIR, f"{base}_boxes_{args.edge}.png")
        visualize_boxes(enhanced, boxes, box_path)
        print(f"박스 시각화: {box_path}")
        
        # 박스 정보 저장
        box_info_path = os.path.join(OUT_DIR, f"{base}_boxes_{args.edge}.txt")
        with open(box_info_path, 'w') as f:
            for i, (x1, y1, x2, y2) in enumerate(boxes):
                f.write(f"Box {i+1}: ({x1}, {y1}) -> ({x2}, {y2})\n")
        print(f"박스 정보: {box_info_path}")
    
    print(f"\n=== 다음 단계 ===")
    print("1. 전처리된 이미지를 SAM2에 입력")
    print("2. 생성된 박스를 SAM2 box prompt로 사용")
    print("3. 필요시 박스 크기 조정 후 재시도")
    
    # 간단한 SAM2 실행 (선택사항)
    try:
        from transformers import pipeline
        print("\n=== SAM2 실행 (선택사항) ===")
        
        # SAM2 모델 로드
        mask_gen = pipeline("mask-generation", model=SAM2_MODEL, device=0)
        
        # 전처리된 이미지로 SAM2 실행
        img_pil = Image.fromarray(cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB))
        
        if boxes:
            # 박스 프롬프트 사용
            print(f"박스 프롬프트 {len(boxes)}개로 SAM2 실행...")
            # 박스 좌표를 SAM2 형식으로 변환
            box_coords = [[box[0], box[1], box[2], box[3]] for box in boxes]
            out = mask_gen(img_pil, boxes=box_coords)
        else:
            # 자동 제안
            print("자동 제안으로 SAM2 실행...")
            out = mask_gen(img_pil)
        
        # 결과 저장
        masks_path = os.path.join(OUT_DIR, f"{base}_masks_{args.edge}_{args.prep}.npz")
        np.savez_compressed(masks_path, **out)
        print(f"SAM2 결과: {masks_path}")
        
    except Exception as e:
        print(f"SAM2 실행 실패: {e}")
        print("수동으로 SAM2를 실행하세요.")

if __name__ == "__main__":
    main()
