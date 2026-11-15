@echo off
chcp 65001 > nul
title Suno Studio Master
cd /d "%~dp0"

echo ========================================================
echo   Suno AI Mastering Studio
echo ========================================================
echo.
echo Starting the studio engine server...
echo The app chooses the first available port (8000, then 8001, then 8080)
echo and opens your browser automatically.
echo.
echo (Keep this window open while using the studio)
echo.

python app.py
pause
