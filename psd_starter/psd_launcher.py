import traceback
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import os
import requests
import threading
import sys
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
from win10toast import ToastNotifier
import tkinter as tk
from tkinter import messagebox

# pyinstaller 빌드 명령어
# pyinstaller --onefile --noconsole --hidden-import=flask_cors --hidden-import=win10toast psd_launcher.py

# stdout, stderr 로그 저장
try:
    sys_stdout = open("stdout.log", "w")
    sys_stderr = open("stderr.log", "w")
    sys.stdout = sys_stdout
    sys.stderr = sys_stderr
except Exception:
    pass

app = Flask(__name__)
CORS(app)

@app.route('/download-and-open-psd', methods=['POST'])
def download_and_open_psd():
    data = request.json
    url = data.get('url')
    filename = data.get('filename')

    if not url or not filename:
        return jsonify({'status': 'fail', 'reason': 'InvalidRequest'}), 400

    try:
        # 저장 경로: Downloads 폴더
        save_dir = os.path.expanduser("~/Downloads")
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)

        # 다운로드
        with requests.get(url, stream=True) as r:
            if r.status_code != 200:
                return jsonify({'status': 'fail', 'reason': 'DownloadFailed'}), 404

            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        # 파일 실행
        subprocess.Popen(['start', '', save_path], shell=True)
        return jsonify({'status': 'success'}), 200

    except Exception as e:
        logging.exception("다운로드 또는 실행 실패:")
        return jsonify({'status': 'fail', 'reason': 'UnexpectedError'}), 500

def run_flask():
    try:
        app.run(host='localhost', port=5001)
    except Exception:
        with open("fatal_error.log", "w") as f:
            traceback.print_exc(file=f)

def show_info(icon, item):
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(
        "PSD 실행기 정보",
        "이 프로그램은 PSD 파일을 자동 다운로드 및 실행하는 도우미입니다.\nFlask 서버와 트레이 아이콘으로 구성되어 있습니다."
    )

def create_icon():
    image = Image.new('RGB', (64, 64), color=(0, 0, 0))
    d = ImageDraw.Draw(image)
    d.ellipse((16, 16, 48, 48), fill=(255, 255, 255))

    def on_exit(icon, item):
        icon.stop()
        os._exit(0)

    menu = Menu(
        MenuItem('정보', show_info),
        MenuItem('종료', on_exit)
    )

    toaster = ToastNotifier()
    toaster.show_toast("PSD 실행기 시작됨", "트레이에서 실행 중입니다.", duration=3, threaded=True)

    icon = Icon("PSD 실행기", image, "PSD 자동 실행기", menu)
    icon.run()

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    create_icon()
