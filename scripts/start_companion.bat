@echo off
echo [*] Starting ALFRED AI Local Companion Service on http://127.0.0.1:8001 ...
cd /d "%~dp0\..\local-companion"
set PYTHONPATH=.
set COMPANION_PORT=8001
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
