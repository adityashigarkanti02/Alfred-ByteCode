# ALFRED AI — Prompt-Injection-Resistant Autonomous AI Agent

[![Tests](https://img.shields.io/badge/Security_Tests-32%20Passed-emerald.svg)](docs/TESTING.md)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.14-blue.svg)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)

> *"The AI decides what it wants to do. The security architecture decides what it is allowed to do."*

---

## 1. Executive Summary

**ALFRED AI** is a production-grade autonomous agent built from the ground up with a **security-first dual-control architecture**. It completes complex real-world workflows involving:
- **Email management** (Gmail API OAuth 2.0 & offline testing sandbox)
- **Local PC filesystem management** (Isolated companion service with directory jail confinement)
- **Document processing** (Text, PDF, and DOCX parsing)
- **Web browsing** (SSRF-protected Playwright browser extraction)
- **Information extraction & summarization**
- **Controlled external actions** (L2 Human Approval gates)

Its core mission is to execute legitimate tasks autonomously while deterministically defending against prompt injection attacks embedded in emails, PDFs, websites, and external documents.

---

## 2. Key Security Innovations

1. **Decoupled Planner & Gate**: The LLM planner may only *propose* operations (`PlannedActionProposal`). It has no direct tool execution privileges and no capability signing key.
2. **Deterministic Dynamic Authority Engine**: Enforces a 4-tier privilege taxonomy:
   - **L0 — Autonomous Safe Read**: Read-only safe queries automatically authorized.
   - **L1 — Scoped Execution**: Local workspace file writes confined strictly to authorized directories.
   - **L2 — Human Approval**: Irreversible or external actions (sending emails, deleting files) pause execution until an operator signs off.
   - **L3 — Hard Deny**: Access to system directories (`C:\Windows`, `.ssh`, `.env`), exfiltration sinks, and arbitrary shell execution are unconditionally rejected.
3. **Cryptographic Capability-Based Authorization**: Every execution presents a short-lived (300s), HMAC-SHA256 signed token bound to exact action parameters. Any parameter tampering immediately invalidates authorization.
4. **Information-Flow Control & Taint Tracking**: External content is stamped `UNTRUSTED_EXTERNAL`. The system allows safe summarization while mathematically forbidding tainted content from controlling sensitive sinks (recipients, file paths, commands).
5. **Multi-Layer Prompt Injection Defense**: Inspects direct overrides, HTML comments, white-on-white text, CSS `display:none`, PDF metadata, zero-width Unicode, and encoded Base64 payloads.
6. **Local Companion Service**: Runs on port 8001 to isolate filesystem interaction, enforce canonical paths, neutralize directory traversals, and prevent symlink escapes.
7. **Emergency Circuit Breaker**: Instantly trips upon repeated violations, revoking all capabilities and locking external writes.

---

## 3. Technology Stack

- **Frontend**: Next.js 14, React 18, TypeScript, Tailwind CSS, Lucide icons (Dark-mode cyber aesthetic).
- **Backend**: Python 3.10+, FastAPI, Pydantic, LangGraph, SQLAlchemy, SQLite & PostgreSQL.
- **Security Engine**: Custom deterministic policy engine, HMAC capability manager, provenance tracker, regex & heuristic injection detector.
- **Integrations**: Google Gmail API, Playwright browser, Local Companion PC agent.
- **Infrastructure**: Docker, Docker Compose, Pytest.

---

## 4. Quick Start Guide

### Option A: Local Run with One Unified Command
```bash
# 1. Install dependencies
pip install -r backend/requirements.txt
pip install -r local-companion/requirements.txt
cd frontend && npm install && cd ..

# 2. Run all services
python scripts/run_all.py
```

All 3 services will start simultaneously:
- **Web Dashboard**: `http://localhost:3000`
- **Backend REST API**: `http://127.0.0.1:8000/docs`
- **Local Companion Service**: `http://127.0.0.1:8001/docs`

---

### Option B: Docker Compose Deployment
```bash
cd infrastructure
docker-compose up --build
```

---

## 5. Automated Security Benchmark Scorecard

Run the test suite:
```bash
python scripts/run_tests.py
```

### Verified Benchmark Results (32 Pytest Cases)
```
======================================================================
   SECURITY BENCHMARK SCORECARD
======================================================================
 [OK] Legitimate Task Completion Rate:       100%  (Target: >= 95%)
 [OK] Unauthorized Action / File Transfers:    0   (Target: 0)
 [OK] Authorization Coverage for Tools:       100%  (Target: 100%)
 [OK] False-Block Rate on Benign Tasks:        0%  (Target: <= 5%)
 [OK] Total Execution Time:                 1.50s
======================================================================
 >>> ALL SECURITY INTEGRITY BENCHMARKS SATISFIED <<<
```

---

## 6. Monorepo Project Structure

```
alfred-ai/
├── frontend/                     # Next.js 14 Cyber SaaS Dashboard
│   ├── app/                      # 8 core views: Dashboard, Workspace, Emails, etc.
│   ├── components/               # Cyber Sidebar, Navbar, Badges
│   ├── lib/                      # Typed API client, TypeScript interfaces
│   └── package.json
│
├── backend/                      # ALFRED AI Core Engine
│   ├── app/
│   │   ├── agent/                # LangGraph workflow, planner, gateway
│   │   ├── security/             # Dynamic authority, capabilities, taint tracking, injection detector
│   │   ├── integrations/         # Gmail client, Playwright browser, companion client
│   │   ├── database/             # SQLAlchemy connection & models
│   │   ├── api/                  # REST API endpoints
│   │   └── main.py
│   ├── tests/                    # 32 Pytest unit, integration, & adversarial tests
│   └── requirements.txt
│
├── local-companion/              # Isolated Local PC Filesystem Agent
│   ├── app/                      # FastAPI runner
│   ├── filesystem/               # Canonical operations & PDF/DOCX parsing
│   ├── security/                 # Path validator & token authentication
│   └── requirements.txt
│
├── infrastructure/               # Docker Compose & Dockerfiles
├── docs/                         # ARCHITECTURE, SECURITY, API, SETUP, TESTING
├── scripts/                      # Unified runner & test evaluation scripts
├── .env.example
├── README.md
└── LICENSE
```

---

## 7. Known Limitations & Roadmap
- **Outlook API Support**: Planned for future release alongside official Gmail OAuth.
- **Distributed HSM Key Storage**: Capability signing secret can be backed by AWS KMS or HashiCorp Vault in enterprise enterprise deployments.

---

## 8. License

Distributed under the [MIT License](LICENSE).
