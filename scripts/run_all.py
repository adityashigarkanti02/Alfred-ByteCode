"""
ALFRED AI - Unified Multi-Service Launch Script.

Runs the complete system locally:
1. Local Companion PC Filesystem Service on http://127.0.0.1:8001
2. ALFRED AI Core Backend API on http://127.0.0.1:8000
3. Next.js Cybersecurity Frontend on http://127.0.0.1:3000

Handles graceful termination upon Ctrl+C.
"""

import os
import sys
import time
import subprocess
import signal

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    print("=" * 70)
    print("   ALFRED AI — Prompt-Injection-Resistant Autonomous Agent")
    print("=" * 70)
    print(f"[*] Root Directory: {ROOT_DIR}")

    processes = []

    try:
        # 1. Start Local Companion Service
        print("\n[+] Starting Local Companion PC Filesystem Service (Port 8001)...")
        companion_env = os.environ.copy()
        companion_env["PYTHONPATH"] = os.path.join(ROOT_DIR, "local-companion")
        companion_env["COMPANION_PORT"] = "8001"
        p_companion = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001"],
            cwd=os.path.join(ROOT_DIR, "local-companion"),
            env=companion_env
        )
        processes.append(("Local Companion", p_companion))
        time.sleep(1)

        # 2. Start ALFRED Core Backend
        print("[+] Starting ALFRED Core Backend API (Port 8000)...")
        backend_env = os.environ.copy()
        backend_env["PYTHONPATH"] = ROOT_DIR
        p_backend = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=ROOT_DIR,
            env=backend_env
        )
        processes.append(("Backend API", p_backend))
        time.sleep(1)

        # 3. Start Next.js Frontend
        print("[+] Starting Next.js Web Dashboard (Port 3000)...")
        p_frontend = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=os.path.join(ROOT_DIR, "frontend"),
            shell=True
        )
        processes.append(("Frontend Dashboard", p_frontend))

        print("\n" + "=" * 70)
        print("   ALL ALFRED AI SERVICES RUNNING")
        print("   - Dashboard:        http://localhost:3000")
        print("   - Backend API:      http://127.0.0.1:8000/docs")
        print("   - Local Companion:  http://127.0.0.1:8001/docs")
        print("   Press Ctrl+C to shut down all services safely.")
        print("=" * 70 + "\n")

        # Keep alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[!] Shutting down ALFRED AI services...")
        for name, proc in processes:
            print(f"[*] Stopping {name}...")
            try:
                proc.terminate()
            except Exception:
                pass
        print("[✓] All services stopped safely.")


if __name__ == "__main__":
    main()
