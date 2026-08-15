@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo 第一次使用，正在准备，请稍等...
  python -m venv .venv
  call .venv\Scripts\activate.bat
  python -m pip install -e ".[desktop]"
) else (
  call .venv\Scripts\activate.bat
)

python -m chartkit desktop
if errorlevel 1 python -m chartkit serve
