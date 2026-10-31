#!/usr/bin/env bash
echo "[*] Starting ALFRED AI Backend API on http://127.0.0.1:8000 ..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
export PYTHONPATH=.
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
