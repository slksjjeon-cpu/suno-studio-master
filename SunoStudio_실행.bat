@echo off
chcp 65001 > nul
title Suno Studio Master
cd /d "%~dp0"

echo ========================================================
echo   🎵 Suno AI 워터마크 제거 & 프로 마스터링 스튜디오
echo ========================================================
echo.
echo [1/2] 브라우저(http://127.0.0.1:8000)를 엽니다...
start "" "http://127.0.0.1:8000"

echo [2/2] 스튜디오 로컬 엔진을 가동합니다...
echo (이 창을 닫으면 스튜디오가 종료됩니다.)
echo.
python app.py
pause
