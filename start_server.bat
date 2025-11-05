@echo off
cd /d "%~dp0"
set PYTHONPATH=%cd%
echo Starting FastAPI server...
echo Server will be available at http://127.0.0.1:8000
echo Press Ctrl+C to stop the server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
pause
