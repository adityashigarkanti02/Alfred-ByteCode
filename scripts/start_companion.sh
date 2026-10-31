#!/usr/bin/env bash
echo "[*] Starting ALFRED AI Local Companion Service on http://127.0.0.1:8001 ..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../local-companion"
export PYTHONPATH=.
export COMPANION_PORT=8001
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
