@echo off
setlocal
cd /d "%~dp0"

echo ===================================================
echo   Starting Pepeland Waypoints Server...
set IS_DEBUG=true
echo   [DEBUG MODE] Cracked clients enabled (IS_DEBUG=true)
echo ===================================================

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

pause
