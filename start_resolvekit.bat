@echo off
setlocal
cd /d "%~dp0"

echo === ResolveKit (DaVinci Resolve assistant) ===
echo.

if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    py -3 -m venv venv || python -m venv venv
)

call venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install -q -r requirements.txt

echo.
echo WebSocket backend starting on ws://127.0.0.1:8765
echo Open the ResolveKit panel inside DaVinci Resolve to connect.
echo.
python server.py

echo.
echo ResolveKit server stopped.
pause
