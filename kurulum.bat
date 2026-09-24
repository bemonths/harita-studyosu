@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python bulunamadi. https://www.python.org adresinden Python 3.12 kurun, sonra bu dosyayi tekrar calistirin.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  py -3.12 -m venv .venv || py -3 -m venv .venv
)
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Paket kurulumu basarisiz oldu. Internet baglantinizi kontrol edin.
  pause
  exit /b 1
)
set PYTHONUTF8=1
.venv\Scripts\python -c "from engine import assets; assets.ensure()"
if errorlevel 1 (
  pause
  exit /b 1
)
echo.
echo Kurulum tamam. Baslatmak icin baslat.bat dosyasina cift tiklayin.
pause
