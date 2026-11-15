import os
import sys
import time
import re
import subprocess
import socket
import threading

DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
SHORTCUT_FILE = os.path.join(DESKTOP, "SunoStudio_웹접속.url")
INFO_FILE = os.path.join(DESKTOP, "SunoStudio_웹주소.txt")
CLOUDFLARED_PATH = r"C:\Program Files (x86)\cloudflared\cloudflared.exe"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def is_port_open(port=8000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex(('127.0.0.1', port)) == 0

def update_desktop_shortcuts(url):
    try:
        with open(SHORTCUT_FILE, "w", encoding="utf-8") as f:
            f.write(f"[InternetShortcut]\nURL={url}\nIconIndex=0\n")
        
        info_text = f"""==================================================
🎵 Suno Studio Master 실시간 웹 접속 안내
==================================================

[외부 접속용 HTTPS 웹 주소]
👉 {url}

[안내 사항]
1. 스마트폰 / 태블릿 / 외부 PC 어디서든 위 주소로 접속하시면
   집 컴퓨터의 스튜디오를 그대로 사용하실 수 있습니다.
2. PC에서 바로 열려면 바탕화면의 [SunoStudio_웹접속.url] 파일을 더블클릭하세요.
3. 새로운 버전 업데이트나 기능 수정이 이루어지면
   별도 재배포 없이 이 웹 주소에 100% 실시간 자동 반영됩니다!
==================================================
(업데이트 시각: {time.strftime('%Y-%m-%d %H:%M:%S')})
"""
        with open(INFO_FILE, "w", encoding="utf-8") as f:
            f.write(info_text)
        print(f"\n[OK] ==================================================")
        print(f"[OK] 🚀 실시간 웹 주소 활성화 완료!")
        print(f"[OK] 주소: {url}")
        print(f"[OK] 바탕화면에 바로가기 및 안내 파일이 생성되었습니다.")
        print(f"[OK] ==================================================\n")
    except Exception as e:
        print(f"[WARN] Failed to write shortcuts: {e}")

def run_service():
    # 1. Start app.py if port 8000 is not already running
    app_proc = None
    if not is_port_open(8000):
        print("[1/2] Suno Studio 로컬 엔진 시작 중...")
        env = os.environ.copy()
        env["STUDIO_NO_BROWSER"] = "1"
        app_proc = subprocess.Popen(
            [sys.executable, "app.py"],
            cwd=BASE_DIR,
            env=env
        )
        # Wait until port 8000 is responding
        for _ in range(30):
            if is_port_open(8000):
                print("[OK] Suno Studio 로컬 엔진 가동 완료 (http://127.0.0.1:8000)")
                break
            time.sleep(0.5)
    else:
        print("[OK] Suno Studio 로컬 엔진이 이미 실행 중입니다 (포트 8000).")

    # 2. Start cloudflared tunnel
    if not os.path.exists(CLOUDFLARED_PATH):
        print(f"[ERROR] cloudflared.exe 를 찾을 수 없습니다: {CLOUDFLARED_PATH}")
        return

    print("[2/2] Cloudflare 보안 웹 터널 가동 중...")
    cf_proc = subprocess.Popen(
        [CLOUDFLARED_PATH, "tunnel", "--url", "http://127.0.0.1:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace"
    )

    url_found = False
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    for line in cf_proc.stdout:
        print(line, end="")
        if not url_found:
            match = url_pattern.search(line)
            if match:
                assigned_url = match.group(0)
                update_desktop_shortcuts(assigned_url)
                url_found = True

    cf_proc.wait()
    if app_proc:
        app_proc.terminate()

if __name__ == "__main__":
    run_service()
