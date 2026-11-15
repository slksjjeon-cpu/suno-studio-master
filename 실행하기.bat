@echo off
title Antigravity Music Studio
cd /d "%~dp0"

echo ========================================================
echo   Antigravity Music Studio - 오프라인 뮤직 스튜디오
echo   접속 주소: http://localhost:8000
echo ========================================================

netstat -ano -p tcp | findstr 127.0.0.1:8000 | findstr LISTENING >nul
if %ERRORLEVEL% equ 0 (
    echo [알림] 스튜디오 서버가 이미 실행 중입니다!
    echo [알림] 브라우저 창 http://localhost:8000 을 바로 엽니다.
    start "" "http://localhost:8000"
    echo [알림] 아무 키나 누르면 이 창을 닫습니다.
    pause
    exit /b 0
)

start "" cmd /c "ping 127.0.0.1 -n 3 >nul & start http://localhost:8000"

echo [알림] 스튜디오 서버를 시작합니다...
if exist "C:\Python314\python.exe" (
    "C:\Python314\python.exe" app.py
) else (
    python app.py
)

echo [알림] 스튜디오가 종료되었습니다.
pause
