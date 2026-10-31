@echo off
echo [*] Starting ALFRED AI Backend API on http://127.0.0.1:8000 ...
cd /d "%~dp0\.."
set PYTHONPATH=.
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
