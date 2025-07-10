import traceback
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import os
import requests
import threading
import webbrowser
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
from win10toast import ToastNotifier
import tkinter as tk
from tkinter import messagebox
import sys
import msvcrt

# pyinstaller 빌드 명령어
# pyinstaller --onefile --noconsole --hidden-import=flask_cors --hidden-import=win10toast psd_launcher.py


# 중복 실행 방지용 락 파일 경로
LOCKFILE = os.path.expanduser("~\\psd_launcher.lock")

# Flask 앱은 가장 먼저 정의되어야 함 (다른 함수에서 참조하기 때문)
app = Flask(__name__)
CORS(app)

# 중복 실행 방지를 위한 락 파일 생성 및 잠금 시도
def prevent_multiple_instances():
    global lockfile
    try:
        lockfile = open(LOCKFILE, 'w')
        msvcrt.locking(lockfile.fileno(), msvcrt.LK_NBLCK, 1)
    except IOError:
        sys.exit("이미 실행 중입니다.")

# PSD 다운로드 및 실행 요청을 처리하는 Flask 엔드포인트
@app.route('/download-and-open-psd', methods=['POST'])
def download_and_open_psd():
    data = request.json
    url = data.get('url')
    filename = data.get('filename')

    if not url or not filename:
        return jsonify({'status': 'fail', 'reason': 'InvalidRequest'}), 400

    try:
        save_dir = os.path.expanduser("~/Downloads")
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)

        with requests.get(url, stream=True) as r:
            if r.status_code != 200:
                return jsonify({'status': 'fail', 'reason': 'DownloadFailed'}), 404

            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        subprocess.Popen(['start', '', save_path], shell=True)
        return jsonify({'status': 'success'}), 200

    except Exception as e:
        logging.exception("다운로드 또는 실행 실패:")
        return jsonify({'status': 'fail', 'reason': 'UnexpectedError'}), 500

# Flask 서버를 백그라운드에서 실행
def run_flask():
    try:
        app.run(host='localhost', port=5001)
    except Exception:
        traceback.print_exc()

# 트레이 메뉴에서 '정보' 선택 시 설명창 출력
def show_info(icon, item):
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(
        "PSD 실행기 정보",
        "이 프로그램은 PSD 파일을 자동 다운로드 및 실행하는 도우미입니다.\nFlask 서버와 트레이 아이콘으로 구성되어 있습니다."
    )

# 트레이 메뉴에서 '웹사이트 열기' 클릭 시 브라우저 실행
def open_website(icon, item):
    webbrowser.open("https://n8n.koreacentral.cloudapp.azure.com")

# 트레이 아이콘 생성 및 메뉴 구성
def create_icon():
    # 흰색 원이 있는 단순한 아이콘 이미지 생성
    image = Image.new('RGB', (64, 64), color=(0, 0, 0))
    d = ImageDraw.Draw(image)
    d.ellipse((16, 16, 48, 48), fill=(255, 255, 255))

    # 트레이 메뉴에서 '종료' 선택 시 앱 종료
    def on_exit(icon, item):
        icon.stop()
        os._exit(0)

    # 트레이 메뉴 항목 정의
    menu = Menu(
        MenuItem('웹사이트 열기', open_website),
        MenuItem('정보', show_info),
        MenuItem('종료', on_exit)
    )

    # 시작 알림 토스트 출력
    toaster = ToastNotifier()
    toaster.show_toast("PSD 실행기 시작됨", "트레이에서 실행 중입니다.", duration=3, threaded=True)

    # 트레이 아이콘 실행
    icon = Icon("PSD 실행기", image, "PSD 자동 실행기", menu)
    icon.run()

# 실행 시작점: 중복 방지 → Flask 서버 실행 → 트레이 아이콘 실행
if __name__ == '__main__':
    prevent_multiple_instances()
    threading.Thread(target=run_flask, daemon=True).start()
    create_icon()
