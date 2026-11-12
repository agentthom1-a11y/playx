@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul || (echo Python launcher not found. Install Python 3.11+ and add it to PATH. & exit /b 1)
if not exist ".venv\Scripts\python.exe" (
  py -3.11 -m venv .venv || (echo Unable to create Python environment. & exit /b 1)
)
if not exist ".venv\Scripts\playx.exe" (
  .venv\Scripts\python.exe -m pip install --disable-pip-version-check -e ".[full]" || exit /b 1
)
.venv\Scripts\python.exe playx_launcher.py
