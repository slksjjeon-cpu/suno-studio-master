@echo off
chcp 65001 > nul
setlocal

echo ========================================================
echo   🎵 윈도우 부팅 시 Suno Studio 웹 자동실행 등록
echo ========================================================
echo.

set "TARGET_DIR=%~dp0"
set "VBS_FILE=%TARGET_DIR%SunoStudio_웹_조용히실행.vbs"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_DIR%\SunoStudio_WebAutoStart.lnk"

powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\"%VBS_FILE%\"'; $s.WorkingDirectory = '%TARGET_DIR%'; $s.Save()"

if exist "%SHORTCUT_PATH%" (
    echo [성공] 윈도우 시작 프로그램에 성공적으로 등록되었습니다!
    echo 이제 컴퓨터를 켜면 백그라운드에서 자동으로 웹 스튜디오가 실행됩니다.
    echo 바탕화면의 [SunoStudio_웹주소.txt]를 통해 언제든 주소를 확인하실 수 있습니다.
) else (
    echo [실패] 등록 중 오류가 발생했습니다.
)

echo.
pause
