@echo off
chcp 65001 > nul
title Suno Studio Master (Web Server Mode)
cd /d "%~dp0"

echo ========================================================
echo   🎵 Suno Studio Master 실시간 웹 서버 실행기
echo ========================================================
echo.
echo 스튜디오 엔진과 외부 웹 접속 보안 터널을 시작합니다...
echo (이 창을 닫으면 외부 웹 접속이 종료됩니다.)
echo.

python web_launcher.py
pause
