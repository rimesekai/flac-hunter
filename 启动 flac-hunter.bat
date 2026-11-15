@echo off
rem flac-hunter GUI launcher (crash log: tasks\gui.log)
cd /d "%~dp0"
if not exist tasks mkdir tasks
start "flac-hunter GUI" /min cmd /c "python gui.py > tasks\gui.log 2>&1"
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:8756
