# ALFRED AI — Installation & Setup Guide

This guide details running ALFRED AI locally or using Docker Compose.

---

## Prerequisites
- **Python**: 3.10+ (tested on Python 3.11, 3.12, 3.14)
- **Node.js**: v18+ (tested on Node v20 & v24)
- **Git**

---

## 1. Quick Start (Local Development)

### Step 1: Install Python Dependencies
```bash
# In repository root
pip install -r backend/requirements.txt
pip install -r local-companion/requirements.txt
```

### Step 2: Install Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

### Step 3: Run All Services with One Command
```bash
python scripts/run_all.py
```

This single command starts:
1. **Local Companion Service**: `http://127.0.0.1:8001`
2. **ALFRED Core Backend API**: `http://127.0.0.1:8000`
3. **Next.js Cybersecurity Dashboard**: `http://localhost:3000`

---

## 2. Docker Compose Deployment

To run with PostgreSQL and containerized services:
```bash
cd infrastructure
docker-compose up --build
```

Access the application at:
- Web Dashboard: `http://localhost:3000`
- Backend API Docs: `http://localhost:8000/docs`
- Companion API Docs: `http://localhost:8001/docs`

---

## 3. Environment Variables Configuration

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

| Variable | Default Value | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./alfred.db` | SQLAlchemy connection URL (SQLite or PostgreSQL) |
| `ALFRED_CAPABILITY_SECRET` | Auto-generated | Master HMAC key for signing execution tokens |
| `ALFRED_COMPANION_SECRET` | Pre-shared token | Shared secret for companion authentication |
| `COMPANION_PORT` | `8001` | Local companion service port |
| `ALFRED_SANDBOX_DIR` | `./workspace_sandbox` | Authorized local workspace path |
| `OPENAI_API_KEY` | *(Optional)* | OpenAI key (fallback to deterministic planner if omitted) |
| `GEMINI_API_KEY` | *(Optional)* | Google Gemini key |

---

## 4. Google Gmail OAuth 2.0 Configuration (Optional)

By default, ALFRED AI operates in **Sandbox Mode** with realistic benign and adversarial email samples. To connect your real Gmail account:
1. Go to Google Cloud Console (`https://console.cloud.google.com/`).
2. Create an OAuth 2.0 Client ID (Web Application).
3. Set Authorized Redirect URI: `http://localhost:8000/api/v1/integrations/gmail/callback`.
4. Download `credentials.json` and set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`.
