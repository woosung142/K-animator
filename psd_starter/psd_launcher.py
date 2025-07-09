import traceback
import logging
from flask import Flask, request, jsonify
import subprocess
import os
import requests
import threading
import sys

# 트레이용
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw

# 로그 파일로 모든 stdout, stderr 리디렉션
try:
    sys_stdout = open("stdout.log", "w")
    sys_stderr = open("stderr.log", "w")
    sys.stdout = sys_stdout
    sys.stderr = sys_stderr
except Exception:
    pass

app = Flask(__name__)

@app.route('/download-and-open-psd', methods=['POST'])
def download_and_open_psd():
    data = request.json
    url = data.get('url')
    filename = data.get('filename')

    if not url or not filename:
        return jsonify({'status': 'fail', 'reason': 'URL 또는 파일명 누락'}), 400

    try:
        save_dir = os.path.expanduser("~/Downloads")
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)

        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        subprocess.Popen(['start', '', save_path], shell=True)
        return jsonify({'status': 'success'}), 200

    except Exception as e:
        return jsonify({'status': 'fail', 'reason': str(e)}), 500

def run_flask():
    try:
        app.run(host='localhost', port=5001)
    except Exception:
        with open("fatal_error.log", "w") as f:
            traceback.print_exc(file=f)

def create_icon():
    # 기본 아이콘 이미지 (검은 원)
    image = Image.new('RGB', (64, 64), color=(0, 0, 0))
    d = ImageDraw.Draw(image)
    d.ellipse((16, 16, 48, 48), fill=(255, 255, 255))

    # 종료 함수
    def on_exit(icon, item):
        icon.stop()
        os._exit(0)

    menu = Menu(MenuItem('종료', on_exit))
    icon = Icon("PSD 실행기", image, "PSD 자동 실행기", menu)
    icon.run()

if __name__ == '__main__':
    # Flask 서버를 백그라운드에서 실행
    threading.Thread(target=run_flask, daemon=True).start()

    # 트레이 아이콘 실행 (메인 스레드)
    create_icon()
