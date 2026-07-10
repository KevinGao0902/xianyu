@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Run Python 3.11 setup first.
  pause
  exit /b 1
)

echo Starting Xianyu manager at http://127.0.0.1:8090
".venv\Scripts\python.exe" Start.py
