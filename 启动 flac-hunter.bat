@echo off
rem flac-hunter 本地 GUI 启动器：双击运行，自动开浏览器（127.0.0.1:8756）
cd /d "%~dp0"
start "flac-hunter GUI" /min python gui.py
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:8756
