@echo off
title Antigravity Music Studio
cd /d "%~dp0"

echo ========================================================
echo   Antigravity Music Studio
echo ========================================================
echo.
echo Starting the studio engine server...
echo The app chooses the first available port (8000, 8001, 8080)
echo and opens your browser automatically.
echo.

python app.py

echo [INFO] Server stopped.
pause
