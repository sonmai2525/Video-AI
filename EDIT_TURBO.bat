@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (set "PY=py -3") else (set "PY=python")
where ffmpeg >nul 2>nul || (echo [ERROR] Install FFmpeg first. & pause & exit /b 1)
where ffprobe >nul 2>nul || (echo [ERROR] Install FFprobe first. & pause & exit /b 1)
if "%~1"=="" (
  %PY% helpers\one_click_editor.py --mode turbo
) else (
  %PY% helpers\one_click_editor.py --mode turbo %*
)
set "RC=%errorlevel%"
echo.
if not "%RC%"=="0" echo [ERROR] Editor failed with code %RC%.
pause
exit /b %RC%
