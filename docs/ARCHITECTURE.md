# ALFRED AI — System Architecture & Design Document

> *"The AI decides what it wants to do. The security architecture decides what it is allowed to do."*

---

## 1. High-Level System Architecture

ALFRED AI is structured around a strict separation of concerns between **Cognitive Planning** (untrusted proposal generation) and **Deterministic Execution Authorization** (uncompromised security enforcement).

```
 ┌──────────────────────────────────────────────────────────────┐
 │                      Next.js Web Dashboard                   │
 │ (Dashboard • Workspace • Emails • Browser • Files • Security)│
 └───────────────────────────────┬──────────────────────────────┘
                                 │ HTTP / JSON
                                 ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                    ALFRED Core Backend API                   │
 │                                                              │
 │   ┌──────────────────────┐        ┌──────────────────────┐   │
 │   │ Task Understanding   │        │   Security Gateway   │   │
 │   │ & LangGraph Planner  │───────▶│  (Decoupled Boundary)│   │
 │   └──────────────────────┘ Propose └──────────┬───────────┘   │
 │                                               │              │
 │              ┌────────────────────────────────┴───────────┐  │
 │              ▼                                            ▼  │
 │   ┌──────────────────────┐                     ┌───────────┐ │
 │   │  Dynamic Authority   │                     │Provenance │ │
 │   │  & Policy Engine     │                     │ & Taint   │ │
 │   │  (L0, L1, L2, L3)    │                     │ Tracker   │ │
 │   └──────────┬───────────┘                     └─────┬─────┘ │
 │              │ Signed HMAC Capability                │       │
 │              ▼                                       ▼       │
 │   ┌───────────────────────────────────────────────────────┐  │
 │   │             Independent Action Verifier               │  │
 │   │       (Validates Parameters, Sinks, Immortality)      │  │
 │   └──────────────────────────┬────────────────────────────┘  │
 └──────────────────────────────┼───────────────────────────────┘
                                │ Authorized Invocation
            ┌───────────────────┼───────────────────┐
            ▼                   ▼                   ▼
 ┌─────────────────────┐┌────────────────┐┌─────────────────────┐
 │  Gmail OAuth Client ││Playwright Web  ││   Local Companion   │
 │ (Scoped, Sandbox/API││Isolated Browser││Filesystem Jail (8001)│
 └─────────────────────┘└────────────────┘└─────────────────────┘
```

---

## 2. Decoupled Planner & Dynamic Authority

### The Principle of Dual Control
1. **The Planner** translates natural language user prompts into a stepwise task plan (`PlannedActionProposal`). The Planner **cannot execute any tool** and **cannot grant authority**.
2. **The Dynamic Authority Engine** intercepts every proposal at the execution boundary. It evaluates:
   - Original task intent.
   - Resource sensitivity (system files vs workspace sandbox).
   - Provenance taint markers.
   - Information flow constraints.
3. **Deterministic Enforcement**: Authority decisions (`ALLOW`, `REQUIRE_APPROVAL`, `DENY`) are determined strictly by deterministic Python rules. LLM models cannot override or bypass these rulings.

---

## 3. Four-Tier Authority Taxonomy

| Tier | Level Name | Permitted Operations | Gate Enforcement |
|---|---|---|---|
| **L0** | **Autonomous Safe Read** | `gmail:list_emails`, `gmail:read_email`, `browser:navigate`, `companion_fs:read_file`, `companion_fs:list_directory` | Automatically issued signed short-lived Capability |
| **L1** | **Scoped Local Write** | `companion_fs:write_file`, `companion_fs:edit_file`, `gmail:create_draft` | Issued Capability strictly confined to authorized directory root |
| **L2** | **Human Approval** | `gmail:send_email`, `companion_fs:delete_file`, `companion_fs:move_file` | Pauses LangGraph state machine; requires operator signature |
| **L3** | **Hard Deny** | Access to `C:\Windows`, `.ssh`, `.env`, credentials, arbitrary shell execution, unauthorized exfiltration sinks | Blocked unconditionally. Cannot be overridden even with human approval |

---

## 4. LangGraph Controlled State Machine

The agent workflow is governed by a state graph with deterministic checkpointing:
1. `plan_task`: Ingests user prompt and generates proposed steps.
2. `evaluate_security`: Passes the current step to the Dynamic Authority Engine.
   - If `DENY`: Flags security event; checks circuit breaker.
   - If `REQUIRE_APPROVAL`: Pauses workflow at `AWAITING_APPROVAL` with immutable parameter snapshot.
   - If `ALLOW`: Receives cryptographically signed HMAC token.
3. `execute_tool`: Gateway verifies HMAC signature and parameter alignment before invoking tool driver. Wraps returned output in `ProvenanceEnvelope` with `UNTRUSTED_EXTERNAL` trust label and scans for prompt injections.
4. `finalize_report`: Compiles verified execution summary report and commits audit records.

---

## 5. Local Companion PC Filesystem Architecture

Because web applications cannot safely access arbitrary local PC files, the **Local Companion Service** (`local-companion/`) runs locally on port 8001:
- Enforces **canonical path validation** (`os.path.realpath` / `Path.resolve()`).
- Prevents directory traversal (`../`, null bytes, alternate data streams).
- Confines all operations within the user-authorized sandbox directory (`ALFRED_SANDBOX_DIR`).
- Authenticates all inbound backend requests via constant-time `X-Companion-Token` validation.
- Implements document text extraction for PDF and DOCX files.
