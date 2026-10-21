@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
echo === V10.2 SETUP - CHI CAN CHAY 1 LAN ===
where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")
%PY% --version >nul 2>nul || (echo [LOI] Can Python 3.10+ va Add Python to PATH. & pause & exit /b 1)
%PY% -m pip install -e .
if errorlevel 1 (echo [LOI] Cai thu vien Python that bai. & pause & exit /b 1)
where ffmpeg >nul 2>nul
if errorlevel 1 (
 echo [CAN LAM THEM] Chua co FFmpeg. Neu co winget, mo Terminal va chay:
 echo winget install Gyan.FFmpeg
 echo Sau do dong/mo lai cua so va chay SETUP_ONCE.bat lan nua.
 pause
 exit /b 1
)
echo SETUP XONG. Tu gio keo video vao EDIT_VIDEO.bat hoac cho video vao INPUT.
pause
