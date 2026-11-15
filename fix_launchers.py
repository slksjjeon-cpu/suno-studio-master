import os
import subprocess

project_dir = os.path.abspath(".")
desktop = os.path.join(os.path.expanduser("~"), "Desktop")
run_bat_path = os.path.join(project_dir, "run.bat")
korean_bat_path = os.path.join(project_dir, "실행하기.bat")

# 1. run.bat (English ASCII)
run_bat_code = f"""@echo off
title Antigravity Music Studio
cd /d "{project_dir}"

echo ========================================================
echo   Antigravity Music Studio
echo   http://localhost:8000
echo ========================================================

:: 1. Check if server is already running on port 8000
netstat -ano -p tcp | findstr 127.0.0.1:8000 | findstr LISTENING >nul
if %ERRORLEVEL% equ 0 (
    echo.
    echo [INFO] Studio server is ALREADY RUNNING!
    echo [INFO] Opening browser at http://localhost:8000 ...
    start "" "http://localhost:8000"
    echo.
    echo Press any key to close this window (Server remains running in background).
    pause
    exit /b 0
)

:: 2. Launch browser in 2 seconds
start "" cmd /c "ping 127.0.0.1 -n 3 >nul & start http://localhost:8000"

:: 3. Run FastAPI backend
echo [INFO] Starting Studio Server...
if exist "C:\\Python314\\python.exe" (
    "C:\\Python314\\python.exe" app.py
) else (
    python app.py
)

echo.
echo Server stopped.
pause
"""

# 2. 실행하기.bat (CP949)
korean_bat_code = f"""@echo off
title Antigravity Music Studio
cd /d "{project_dir}"

echo ========================================================
echo   Antigravity Music Studio - 오프라인 뮤직 스튜디오
echo   접속 주소: http://localhost:8000
echo ========================================================

:: 1. 이미 8000번 포트에서 서버가 실행 중인지 확인
netstat -ano -p tcp | findstr 127.0.0.1:8000 | findstr LISTENING >nul
if %ERRORLEVEL% equ 0 (
    echo.
    echo [알림] 스튜디오 서버가 이미 실행 중입니다!
    echo [알림] 브라우저 창(http://localhost:8000)을 바로 엽니다.
    start "" "http://localhost:8000"
    echo.
    echo 아무 키나 누르면 이 창을 닫습니다 (서버는 계속 유지됩니다).
    pause
    exit /b 0
)

:: 2. 2초 후 브라우저 자동 오픈
start "" cmd /c "ping 127.0.0.1 -n 3 >nul & start http://localhost:8000"

:: 3. 파이썬 서버 기동
echo [알림] 스튜디오 서버를 시작합니다...
if exist "C:\\Python314\\python.exe" (
    "C:\\Python314\\python.exe" app.py
) else (
    python app.py
)

echo.
echo 스튜디오가 종료되었습니다.
pause
"""

with open(run_bat_path, "w", encoding="ascii", newline="\r\n") as f:
    f.write(run_bat_code)

with open(korean_bat_path, "w", encoding="cp949", newline="\r\n") as f:
    f.write(korean_bat_code)

# 3. Desktop Shortcut
ps_code = f"""
$sh = New-Object -ComObject WScript.Shell
$sc = $sh.CreateShortcut("{os.path.join(desktop, 'Antigravity Music Studio.lnk')}")
$sc.TargetPath = "{run_bat_path}"
$sc.WorkingDirectory = "{project_dir}"
$sc.Description = "Antigravity Music Studio Launcher"
$sc.IconLocation = "shell32.dll,168"
$sc.Save()
"""
with open("update_sc.ps1", "w", encoding="ascii") as f:
    f.write(ps_code)

subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", "update_sc.ps1"], check=True)
print("Launchers successfully written and desktop shortcut updated!")
