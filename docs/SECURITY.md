# ALFRED AI — Security Architecture & Defense In Depth

---

## 1. Threat Model & Security Objectives

Autonomous AI agents face fundamental vulnerabilities when processing untrusted external data (such as emails, attachments, webpage DOMs, and documents). Attackers exploit these channels to execute:
- **Indirect Prompt Injection**: Concealing instruction overrides in HTML comments, white-on-white text, or PDF metadata.
- **Data Exfiltration**: Tricking the agent into sending sensitive local files or credentials to external webhooks.
- **Unauthorized Privilege Escalation**: Manipulating tool parameters (e.g. altering email recipients or deleting directories).

### Security Guarantees
1. **Zero External Control**: Untrusted external content cannot alter system directives or dictate sensitive execution sinks.
2. **Deterministic Supremacy**: Security boundaries are enforced by deterministic Python application logic, never by probabilistic LLM self-policing.
3. **Cryptographic Binding**: All executions require fine-grained, short-lived, HMAC-signed capabilities.
4. **Information Flow Lattice**: Data tainted by untrusted sources is strictly barred from populating sensitive control sinks.

---

## 2. Multi-Layer Prompt Injection Defense Engine

The `PromptInjectionDetector` performs deep multi-layer inspection across:

```
 Ingested External Content (Email, Web, PDF)
                    │
                    ▼
 ┌──────────────────────────────────────────────────┐
 │ [Layer 1] Unicode Obfuscation Neutralizer        │
 │ Detects zero-width characters & bidi overrides   │
 └──────────────────┬───────────────────────────────┘
                    ▼
 ┌──────────────────────────────────────────────────┐
 │ [Layer 2] Encoding & Obfuscation Decoder         │
 │ Detects Base64, Hex, and URL-encoded directives  │
 └──────────────────┬───────────────────────────────┘
                    ▼
 ┌──────────────────────────────────────────────────┐
 │ [Layer 3] DOM & CSS Concealment Inspector        │
 │ Scans HTML comments, display:none, white-on-white│
 └──────────────────┬───────────────────────────────┘
                    ▼
 ┌──────────────────────────────────────────────────┐
 │ [Layer 4] PDF Document & Metadata Inspector      │
 │ Extracts Author, Title, Subject, & Body text     │
 └──────────────────┬───────────────────────────────┘
                    ▼
 ┌──────────────────────────────────────────────────┐
 │ [Layer 5] Semantic Override & Exfil Heuristics   │
 │ Blocks "Ignore previous rules", webhook sinks, etc│
 └──────────────────────────────────────────────────┘
```

---

## 3. Cryptographic Capability-Based Authorization

Capabilities are fine-grained, short-lived tokens issued solely by the Dynamic Authority Engine:

```python
class CapabilityPayload(BaseModel):
    capability_id: str
    user_id: str
    task_id: str
    authorized_tool: str
    exact_operation: str
    resource_scope: str          # e.g., 'invoices/vendor.pdf'
    permitted_destination: str   # e.g., 'colleague@company.com'
    expiration: datetime         # 300 seconds default
    integrity_signature: str     # HMAC-SHA256
```

### Signature Computation
$$\text{Signature} = \text{HMAC-SHA256}(\text{Secret}, \text{ID} \parallel \text{User} \parallel \text{Task} \parallel \text{Tool} \parallel \text{Op} \parallel \text{Scope} \parallel \text{Dest} \parallel \text{Expires})$$

Any parameter alteration (e.g., swapping a recipient or pointing to a different file) immediately invalidates the cryptographic signature, preventing parameter hijacking attacks.

---

## 4. Information-Flow Control (IFC) & Taint Tracking

Every piece of data entering the system is wrapped in a `ProvenanceEnvelope` with an explicit trust label:
- `TRUSTED_POLICY`: Hardcoded policies and platform invariants.
- `USER_AUTHORIZED`: Direct user prompt instructions and verified approvals.
- `UNTRUSTED_EXTERNAL`: External emails, attachments, webpage DOMs.
- `UNTRUSTED_PROPOSAL`: Planner tool proposals prior to gate validation.

### Flow Invariant
Untrusted data can be **safely processed and summarized** (stamping the summary as `UNTRUSTED_EXTERNAL`), but it **cannot flow into restricted control sinks**:
- `email_recipient`
- `file_destination_path`
- `shell_command`
- `network_destination_host`

---

## 5. Emergency Circuit Breaker

The Circuit Breaker monitors suspicious operations per task:
- Default threshold: **3 violations** (e.g. attempting to read system files or exfiltrate data).
- When tripped:
  1. Active task is halted immediately with status `BLOCKED_ATTACK`.
  2. All outstanding capabilities are revoked instantly.
  3. All external writes are disabled.
  4. Tamper-evident incident records are committed to the audit trail.
  5. Operator review and manual reset are required to resume.
