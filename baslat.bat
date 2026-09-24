@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Once kurulum.bat dosyasini calistirin.
  pause
  exit /b 1
)
set PYTHONUTF8=1
.venv\Scripts\python run_ui.py
pause
