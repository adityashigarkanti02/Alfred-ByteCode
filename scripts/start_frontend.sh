#!/usr/bin/env bash
echo "[*] Starting ALFRED AI Frontend Dashboard on http://localhost:3000 ..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../frontend"
npm run dev
