@echo off
cd /d "%~dp0"
python helpers\one_click_editor.py --mode turbo %*
pause
