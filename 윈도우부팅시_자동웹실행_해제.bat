@echo off
chcp 65001 > nul
setlocal

echo ========================================================
echo   🎵 윈도우 부팅 시 Suno Studio 웹 자동실행 해제
echo ========================================================
echo.

set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_DIR%\SunoStudio_WebAutoStart.lnk"

if exist "%SHORTCUT_PATH%" (
    del "%SHORTCUT_PATH%"
    echo [완료] 윈도우 시작 프로그램에서 자동실행이 해제되었습니다.
) else (
    echo [안내] 이미 등록되어 있지 않거나 해제된 상태입니다.
)

echo.
pause
