import os, numpy as np, cv2
from PIL import Image
import argparse
import subprocess
import sys

# ========= 경로 설정 =========
OUT_DIR = r"out_enhanced"
EDGE_DIR = r"edge_results"

def imread_unicode(p):
    img = cv2.imread(p)
    if img is not None: return img
    data = np.fromfile(p, dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)

def load_enhanced_images(base_name):
    """강화된 이미지들 로드"""
    enhanced_images = {}
    methods = ['original', 'pidinet', 'lineart', 'hed']
    
    for method in methods:
        if method == 'original':
            # 원본 이미지는 기본 경로에서 로드
            original_path = f"data/input/{base_name}.png"
            if os.path.exists(original_path):
                enhanced_images[method] = imread_unicode(original_path)
        else:
            # enhanced 이미지들 로드
            enhanced_path = os.path.join(OUT_DIR, f"{base_name}_enhanced_{method}_clahe.png")
            if os.path.exists(enhanced_path):
                enhanced_images[method] = cv2.imread(enhanced_path)
    
    return enhanced_images

def load_sam2_masks(base_name, method="pidinet"):
    """SAM2 마스크 로드"""
    masks_path = os.path.join(OUT_DIR, f"{base_name}_masks_{method}_clahe.npz")
    if os.path.exists(masks_path):
        data = np.load(masks_path, allow_pickle=True)
        return list(data["masks"])
    return None

def composite_overlay(background_img, masks, selected, method_name="Original"):
    """선택된 건 진하게, 후보는 연하게"""
    vis = background_img.copy()
    H, W = background_img.shape[:2]
    
    color_sel = (0,255,255)  # 노란색
    color_all = (200,200,200)  # 회색
    
    # 전체 후보 윤곽(연하게)
    for m in masks:
        cnts,_ = cv2.findContours((m>0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(vis, cnts, -1, color_all, 1)
    
    # 선택 마스크 채우기(진하게)
    if selected:
        merged = np.zeros((H,W), np.uint8)
        for i in selected:
            merged |= (masks[i]>0).astype(np.uint8)
        col = np.full_like(background_img, color_sel, dtype=np.uint8)
        vis = cv2.addWeighted(vis, 1.0, (col * merged[...,None]).astype(np.uint8), 0.35, 0)
    
    # 방법 이름과 마스크 개수 표시
    info_text = f"{method_name.upper()} - Masks: {len(masks)} | Selected: {len(selected)}"
    cv2.putText(vis, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    
    return vis

def inpaint_remove(bgr, masks, selected, method="telea", radius=3):
    if not selected: return bgr.copy(), np.zeros(bgr.shape[:2], np.uint8)
    H,W = bgr.shape[:2]
    merged = np.zeros((H,W), np.uint8)
    for i in selected:
        merged |= (masks[i]>0).astype(np.uint8)
    m8 = merged*255
    if method=="telea":
        out = cv2.inpaint(bgr, m8, radius, cv2.INPAINT_TELEA)
    else:
        out = cv2.inpaint(bgr, m8, radius, cv2.INPAINT_NS)
    return out, merged

def run_sd_inpainting(base_name, selected_masks, prompt="background, seamless, natural", device="cuda"):
    """SD 인페인팅 실행"""
    try:
        # 원본 이미지 경로
        original_path = f"data/input/{base_name}.png"
        if not os.path.exists(original_path):
            print(f"❌ 원본 이미지를 찾을 수 없습니다: {original_path}")
            return False
        
        # 선택된 마스크를 하나로 합치기
        if not selected_masks:
            print("❌ 선택된 마스크가 없습니다.")
            return False
        
        # 마스크 파일 경로
        masks_path = os.path.join(OUT_DIR, f"{base_name}_masks_pidinet_clahe.npz")
        if not os.path.exists(masks_path):
            print(f"❌ 마스크 파일을 찾을 수 없습니다: {masks_path}")
            return False
        
        # SD 인페인팅 실행
        cmd = [
            sys.executable, "sd_inpainting.py",
            "--input", original_path,
            "--mask", masks_path,
            "--output", os.path.join(OUT_DIR, f"{base_name}_sd_inpainted.png"),
            "--prompt", prompt,
            "--device", device
        ]
        
        print("SD 인페인팅 실행 중...")
        print(f"명령: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("SD 인페인팅 완료!")
            print(f"결과: {os.path.join(OUT_DIR, f'{base_name}_sd_inpainted.png')}")
            return True
        else:
            print(f"SD 인페인팅 실패: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"SD 인페인팅 오류: {e}")
        return False

def run_sam2_with_boxes(base_name, method="pidinet"):
    """박스 프롬프트로 SAM2 실행"""
    try:
        from transformers import pipeline
        
        # 강화된 이미지 로드
        enhanced_path = os.path.join(OUT_DIR, f"{base_name}_enhanced_{method}_clahe.png")
        if not os.path.exists(enhanced_path):
            print(f"강화된 이미지를 찾을 수 없습니다: {enhanced_path}")
            return None
        
        enhanced_img = cv2.imread(enhanced_path)
        img_pil = Image.fromarray(cv2.cvtColor(enhanced_img, cv2.COLOR_BGR2RGB))
        
        # 박스 정보 로드
        box_path = os.path.join(OUT_DIR, f"{base_name}_boxes_{method}.txt")
        boxes = []
        if os.path.exists(box_path):
            with open(box_path, 'r') as f:
                for line in f:
                    if 'Box' in line and '->' in line:
                        # "Box 1: (x1, y1) -> (x2, y2)" 파싱
                        coords = line.split('->')[0].split('(')[1].split(')')[0]
                        x1, y1 = map(int, coords.split(', '))
                        coords2 = line.split('->')[1].strip().split(')')[0]
                        x2, y2 = map(int, coords2.split(', '))
                        boxes.append([x1, y1, x2, y2])
        
        print(f"로드된 박스: {len(boxes)}개")
        
        # SAM2 모델 로드
        mask_gen = pipeline("mask-generation", model="facebook/sam2.1-hiera-base-plus", device=0)
        
        if boxes:
            # 박스 프롬프트 사용
            print(f"박스 프롬프트 {len(boxes)}개로 SAM2 실행...")
            out = mask_gen(img_pil, boxes=boxes)
        else:
            # 자동 제안
            print("자동 제안으로 SAM2 실행...")
            out = mask_gen(img_pil)
        
        # 마스크 추출
        masks = []
        if 'masks' in out:
            for mask in out['masks']:
                if isinstance(mask, Image.Image):
                    mask_array = np.array(mask)
                else:
                    mask_array = mask
                
                if len(mask_array.shape) == 3:
                    mask_array = cv2.cvtColor(mask_array, cv2.COLOR_RGB2GRAY)
                
                mask_binary = (mask_array > 128).astype(np.uint8)
                masks.append(mask_binary)
        
        print(f"SAM2 결과: {len(masks)}개 마스크")
        
        # 마스크 저장
        masks_path = os.path.join(OUT_DIR, f"{base_name}_masks_{method}_clahe.npz")
        np.savez_compressed(masks_path, masks=np.array(masks, dtype=object))
        print(f"마스크 저장: {masks_path}")
        
        return masks
        
    except Exception as e:
        print(f"SAM2 실행 실패: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Enhanced SAM2 Mouse Selection')
    parser.add_argument('--input', default='test2', help='Input image name (without extension)')
    parser.add_argument('--method', choices=['pidinet', 'lineart', 'hed'], default='pidinet', help='Edge detection method')
    parser.add_argument('--sd_prompt', default='background, seamless, natural, clean', help='SD inpainting prompt')
    parser.add_argument('--device', choices=['cuda', 'cpu'], default='cuda', help='Device for SD inpainting')
    args = parser.parse_args()
    
    base_name = args.input
    method = args.method
    
    print(f"=== Enhanced SAM2 Mouse Selection ===")
    print(f"이미지: {base_name}")
    print(f"방법: {method}")
    
    # 1. SAM2 마스크 생성 (없으면 실행)
    masks = load_sam2_masks(base_name, method)
    if masks is None:
        print("\nSAM2 마스크가 없습니다. 생성 중...")
        masks = run_sam2_with_boxes(base_name, method)
        if masks is None:
            print("SAM2 마스크 생성 실패!")
            return
    
    print(f"로드된 마스크: {len(masks)}개")
    
    # 2. 강화된 이미지들 로드
    enhanced_images = load_enhanced_images(base_name)
    if not enhanced_images:
        print("강화된 이미지를 찾을 수 없습니다!")
        return
    
    # 사용 가능한 방법들
    available_methods = list(enhanced_images.keys())
    current_method_idx = 0
    current_method = available_methods[current_method_idx]
    
    selected = set()
    win = "Enhanced SAM2 Select (Left: toggle, N/P: next/prev, S: save, D: SD inpainting, R: reset, Q: quit)"
    
    # GUI 창 생성 시도
    try:
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)
        gui_available = True
    except cv2.error as e:
        print(f"GUI 창 생성 실패: {e}")
        print("마우스 선택 기능을 사용할 수 없습니다.")
        gui_available = False

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            # 해당 픽셀을 포함하는 마스크 후보들을 찾고, 가장 작은 면적(=더 타이트) 우선
            hits = []
            for idx, m in enumerate(masks):
                if y>=m.shape[0] or x>=m.shape[1]: continue
                if m[y,x] > 0:
                    hits.append((np.count_nonzero(m), idx))
            if hits:
                hits.sort()  # 면적 작은 순
                _, idx = hits[0]
                if idx in selected: selected.remove(idx)
                else: selected.add(idx)

    if not gui_available:
        print("GUI를 사용할 수 없어서 자동으로 모든 마스크를 선택합니다.")
        selected = set(range(len(masks)))
        print(f"선택된 마스크: {len(selected)}개")
        
        # 자동으로 결과 저장
        original_img = enhanced_images.get('original', list(enhanced_images.values())[0])
        out, merged = inpaint_remove(original_img, masks, selected, method="telea", radius=3)
        os.makedirs(OUT_DIR, exist_ok=True)
        cv2.imwrite(os.path.join(OUT_DIR, f"{base_name}_remove_mask.png"), merged*255)
        cv2.imwrite(os.path.join(OUT_DIR, f"{base_name}_removed.png"), out)
        print("[AUTO-SAVED]", os.path.join(OUT_DIR, f"{base_name}_removed.png"))
        return

    cv2.setMouseCallback(win, on_mouse)

    print(f"사용 가능한 방법들: {', '.join(available_methods)}")
    print(f"현재 방법: {current_method}")
    print("키보드 단축키:")
    print("  N: 다음 방법, P: 이전 방법")
    print("  왼쪽 클릭: 마스크 선택/해제")
    print("  S: 바이너리 마스크 저장")
    print("  R: 리셋, Q: 종료")

    while True:
        current_img = enhanced_images[current_method]
        vis = composite_overlay(current_img, masks, selected, current_method)
        cv2.imshow(win, vis)
        
        key = cv2.waitKey(20) & 0xFF
        if key in (ord('q'), 27):  # q or ESC
            break
        elif key == ord('r'):
            selected.clear()
            print("선택 초기화")
        elif key == ord('n'):  # 다음 방법
            current_method_idx = (current_method_idx + 1) % len(available_methods)
            current_method = available_methods[current_method_idx]
            print(f"다음 방법: {current_method}")
        elif key == ord('p'):  # 이전 방법
            current_method_idx = (current_method_idx - 1) % len(available_methods)
            current_method = available_methods[current_method_idx]
            print(f"이전 방법: {current_method}")
        elif key == ord('s'):  # 바이너리 마스크 저장
            if selected:
                # 선택된 마스크들을 합쳐서 바이너리 마스크 생성
                merged_mask = np.zeros_like(masks[0], dtype=np.uint8)
                for idx in selected:
                    merged_mask |= (masks[idx] > 0).astype(np.uint8)
                
                os.makedirs(OUT_DIR, exist_ok=True)
                mask_path = os.path.join(OUT_DIR, f"{base_name}_binary_mask.png")
                cv2.imwrite(mask_path, merged_mask * 255)
                print(f"[SAVED] 바이너리 마스크: {mask_path}")
                print(f"선택된 마스크: {len(selected)}개")
            else:
                print("먼저 마스크를 선택하세요!")

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
