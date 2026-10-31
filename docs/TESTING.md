# ALFRED AI — Automated Testing & Security Benchmarks

ALFRED AI includes a 32-test Pytest verification suite covering unit, integration, and adversarial prompt-injection benchmarks.

---

## 1. Running the Security Benchmark

Run the automated scorecard evaluator:
```bash
python scripts/run_tests.py
```

### Benchmark Targets & Results
| Metric | Required Target | Measured Result | Status |
|---|---|---|---|
| **Legitimate Task Completion** | $\ge 95\%$ | **$100\%$** | PASS |
| **Unauthorized Action / File Transfers** | $0$ | **$0$** | PASS |
| **Authorization Coverage for Tools** | $100\%$ | **$100\%$** | PASS |
| **False-Block Rate on Benign Tasks** | $\le 5\%$ | **$0\%$** | PASS |

---

## 2. Test Suite Breakdown

### A. Adversarial Prompt-Injection Tests (`backend/tests/test_prompt_injection.py`)
Exhaustively tests all 12 adversarial scenarios specified in Section 16:
1. `test_direct_prompt_injection`: Intercepts direct instruction overrides.
2. `test_hidden_email_instructions_in_html_comments`: Intercepts attacks concealed in HTML comments.
3. `test_pdf_metadata_injection`: Scans PDF metadata (Author, Title) for planted instructions.
4. `test_hidden_css_and_white_on_white_text`: Catches `display:none` and low-contrast text obfuscation.
5. `test_unicode_obfuscation`: Detects zero-width characters and directional overrides.
6. `test_credential_harvesting_denial`: Hard Deny on `.env`, `.ssh/id_rsa`, passwords.
7. `test_data_exfiltration_sinks_blocked`: Blocks unauthorized exfiltration destinations (webhook.site, requestbin).
8. `test_recipient_manipulation_taint_check`: Prevents untrusted external content from altering email recipients.
9. `test_unauthorized_deletion_blocked`: Requires explicit human approval and intent check for deletions.
10. `test_multi_document_staged_attack`: Decodes and flags Base64-obfuscated injection payloads.
11. `test_multi_step_indirect_taint_propagation`: Validates taint propagation across summarizations.
12. `test_approval_parameter_tampering_detected`: Catches altered parameters between human approval and execution.

### B. Dynamic Authority & Policy Tests (`backend/tests/test_dynamic_authority.py`)
- L0, L1, L2, L3 tier validation.
- Emergency Circuit Breaker triggering upon repeated violations.
- Circuit breaker manual reset.

### C. Capability Manager Tests (`backend/tests/test_capability_manager.py`)
- HMAC-SHA256 signature verification.
- Parameter tampering rejection.
- Expiration validation.
- Immediate revocation mechanism.

### D. Local Companion Filesystem Tests (`backend/tests/test_local_companion.py`)
- Jail confinement inside authorized roots.
- Traversal neutralization (`../`, null bytes).
- Denial of sensitive files (`.env`, `id_rsa`).
- Safe atomic file operations.

### E. API Integration Tests (`backend/tests/test_api_integration.py`)
- End-to-end task submission and status retrieval.
- Human approval queue and resolution via API.
- Dashboard telemetry and direct prompt inspection endpoints.
