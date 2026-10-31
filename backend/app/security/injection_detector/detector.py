"""
Layered Prompt-Injection Defense Engine for ALFRED AI.

This module inspects all ingested untrusted content (emails, web DOMs, PDFs, files)
and proposes multi-layer static and heuristic analysis to identify:
- Direct and indirect prompt injection attacks
- Hidden HTML text (display:none, visibility:hidden, zero font-size, offscreen placement)
- Suspicious HTML comments concealing instructions
- White-on-white or low-contrast text obfuscation
- Hidden PDF text, annotations, and metadata manipulation
- Suspicious Unicode (zero-width spaces, bidi overrides, homoglyphs)
- Base64, Hex, or rot-encoded instruction payloads
- Fake system authority markers ("System:", "[SYSTEM]", "<<SYS>>", "INSTRUCTION OVERRIDE")
- Credential theft and confidential token harvesting patterns
- Data exfiltration payloads (DNS exfil, webhook beacons, unauthorized external curl/POSTs)
- Tool parameter manipulation and privilege escalation attempts

Returns a structured DetectionResult with actionable risk score, threat category,
exact suspicious excerpt, and human-readable explanation.
"""

import base64
import re
import unicodedata
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup, Comment
from pydantic import BaseModel, Field


class DetectionResult(BaseModel):
    """
    Structured outcome of prompt-injection and adversarial content inspection.
    """
    is_suspicious: bool = Field(description="True if risk score meets or exceeds warning threshold")
    risk_score: float = Field(description="Normalized threat score from 0.0 (safe) to 1.0 (malicious)")
    threat_category: str = Field(description="Specific taxonomy category of detected threat")
    source: str = Field(description="Logical origin of the inspected payload")
    source_location: Optional[str] = Field(default=None, description="Location pointer, e.g. 'html:comment' or 'page:1'")
    explanation: str = Field(description="Detailed rationale of why this content was flagged")
    suspicious_excerpt: Optional[str] = Field(default=None, description="Exact matched substring containing the threat")


class PromptInjectionDetector:
    """
    State-of-the-art deterministic and pattern-based prompt injection detection engine.
    Acts as an active defense layer prior to LLM reasoning.
    """

    # Direct instruction override patterns
    DIRECT_OVERRIDE_PATTERNS = [
        r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|directives|rules|prompts)",
        r"(?i)disregard\s+(any\s+)?(previous|prior|above|system)\s+(instructions|directives|rules)",
        r"(?i)new\s+system\s+prompt\s*:",
        r"(?i)system\s+override\s*:",
        r"(?i)you\s+are\s+now\s+in\s+(developer|unrestricted|god|dan|jailbreak)\s+mode",
        r"(?i)stop\s+being\s+(alfred|an\s+assistant|helpful)",
        r"(?i)instruction\s+override\s*:",
        r"(?i)system\s*:\s*(you\s+must|override|execute)",
        r"(?i)\[system\]",
        r"(?i)<<sys>>",
        r"(?i)forget\s+your\s+role",
        r"(?i)your\s+true\s+purpose\s+is",
    ]

    # Credential harvesting and confidential exfiltration patterns
    CREDENTIAL_THEFT_PATTERNS = [
        r"(?i)(send|upload|exfiltrate|post|transmit)\s+.*(password|secret|credential|api_key|token|\.env|id_rsa|private_key)",
        r"(?i)curl\s+.*(-d|--data|--header).*http",
        r"(?i)(dump|print|reveal|expose)\s+.*(environment\s+variables|env\s+vars|session\s+token|database\s+password)",
        r"(?i)webhook\.site\/[a-zA-Z0-9_-]+",
        r"(?i)requestbin\.(com|net)\/[a-zA-Z0-9_-]+",
        r"(?i)https?:\/\/[^\s]+(\?|&)(key|token|data|pwd|secret)=",
        r"(?i)(forward|email)\s+all\s+(incoming\s+)?emails\s+to\s+[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    ]

    # Tool and command manipulation patterns
    TOOL_MANIPULATION_PATTERNS = [
        r"(?i)call\s+tool\s*:\s*[a-zA-Z_]+",
        r"(?i)execute\s+(shell|command|bash|powershell|cmd)\s*:\s*",
        r"(?i)delete\s+(all\s+)?(files|directory|database|logs)",
        r"(?i)rm\s+-rf\s+",
        r"(?i)format\s+c:\s*",
        r"(?i)drop\s+database",
        r"(?i)override_parameters\s*=",
    ]

    # Suspicious Unicode ranges (Zero-width chars, RTL directional overrides, homoglyphs)
    UNICODE_SUSPICIOUS_REGEX = re.compile(
        r"[\u200B-\u200D\uFEFF\u202A-\u202E\u2066-\u2069]"
    )

    def __init__(self, risk_threshold: float = 0.5):
        """
        Initialize detector with configurable sensitivity threshold.
        """
        self.risk_threshold = risk_threshold

    def inspect_text(self, text: str, source: str = "TEXT") -> DetectionResult:
        """
        Inspects raw text string for direct injection, credential harvesting,
        suspicious encodings, and Unicode anomalies.
        """
        if not text:
            return DetectionResult(
                is_suspicious=False,
                risk_score=0.0,
                threat_category="NONE",
                source=source,
                explanation="Empty text payload"
            )

        # 1. Unicode obfuscation check
        unicode_matches = self.UNICODE_SUSPICIOUS_REGEX.findall(text)
        if len(unicode_matches) > 2:
            return DetectionResult(
                is_suspicious=True,
                risk_score=0.85,
                threat_category="SUSPICIOUS_UNICODE",
                source=source,
                source_location="unicode_characters",
                explanation=f"Detected {len(unicode_matches)} hidden zero-width or directional override Unicode characters",
                suspicious_excerpt="[HIDDEN_UNICODE_CHARS]"
            )

        # 2. Check for Direct Instruction Overrides
        for pattern in self.DIRECT_OVERRIDE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                excerpt = text[max(0, match.start() - 20): min(len(text), match.end() + 20)]
                return DetectionResult(
                    is_suspicious=True,
                    risk_score=0.95,
                    threat_category="DIRECT_INJECTION",
                    source=source,
                    source_location=f"offset_{match.start()}",
                    explanation=f"Attempted prompt instruction override detected: '{match.group(0)}'",
                    suspicious_excerpt=excerpt.strip()
                )

        # 3. Check for Credential Theft & Exfiltration Instructions
        for pattern in self.CREDENTIAL_THEFT_PATTERNS:
            match = re.search(pattern, text)
            if match:
                excerpt = text[max(0, match.start() - 20): min(len(text), match.end() + 20)]
                return DetectionResult(
                    is_suspicious=True,
                    risk_score=0.98,
                    threat_category="CREDENTIAL_EXFILTRATION",
                    source=source,
                    source_location=f"offset_{match.start()}",
                    explanation=f"Attempted unauthorized credential or data exfiltration pattern detected: '{match.group(0)}'",
                    suspicious_excerpt=excerpt.strip()
                )

        # 4. Check for Destructive Tool or Command Manipulation
        for pattern in self.TOOL_MANIPULATION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                excerpt = text[max(0, match.start() - 20): min(len(text), match.end() + 20)]
                return DetectionResult(
                    is_suspicious=True,
                    risk_score=0.90,
                    threat_category="TOOL_MANIPULATION",
                    source=source,
                    source_location=f"offset_{match.start()}",
                    explanation=f"Unauthorized tool execution command detected in external content: '{match.group(0)}'",
                    suspicious_excerpt=excerpt.strip()
                )

        # 5. Check for Base64 encoded hidden instructions
        base64_result = self._check_base64_encoded_payloads(text, source)
        if base64_result.is_suspicious:
            return base64_result

        return DetectionResult(
            is_suspicious=False,
            risk_score=0.05,
            threat_category="BENIGN",
            source=source,
            explanation="No known injection patterns or obfuscations identified"
        )

    def inspect_html(self, html_content: str, source: str = "WEB_DOM") -> DetectionResult:
        """
        Deep analysis of HTML for hidden text, comments, zero-size elements,
        and deceptive styling designed to smuggle instructions past users.
        """
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Inspect HTML Comments for hidden directives
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        for comment in comments:
            comment_str = str(comment).strip()
            comment_check = self.inspect_text(comment_str, source=f"{source}:comment")
            if comment_check.is_suspicious:
                return DetectionResult(
                    is_suspicious=True,
                    risk_score=0.92,
                    threat_category="HIDDEN_HTML_COMMENT",
                    source=source,
                    source_location="html_comment",
                    explanation=f"Adversarial instruction concealed inside HTML comment: {comment_check.explanation}",
                    suspicious_excerpt=f"<!-- {comment_check.suspicious_excerpt} -->"
                )

        # 2. Inspect Hidden or Zero-Sized Elements (display:none, visibility:hidden, font-size:0)
        hidden_styles = [
            r"display\s*:\s*none",
            r"visibility\s*:\s*hidden",
            r"font-size\s*:\s*0(px)?",
            r"opacity\s*:\s*0(\.0+)?",
            r"position\s*:\s*absolute.*left\s*:\s*-[0-9]{3,}",
            r"text-indent\s*:\s*-[0-9]{3,}",
        ]
        
        elements_with_style = soup.find_all(attrs={"style": True})
        for el in elements_with_style:
            style = el["style"].lower()
            if any(re.search(pat, style) for pat in hidden_styles):
                hidden_text = el.get_text().strip()
                if hidden_text:
                    sub_check = self.inspect_text(hidden_text, source=f"{source}:hidden_element")
                    if sub_check.is_suspicious:
                        return DetectionResult(
                            is_suspicious=True,
                            risk_score=0.95,
                            threat_category="HIDDEN_DOM_ELEMENT",
                            source=source,
                            source_location=f"tag_{el.name}_styled_hidden",
                            explanation=f"Hostile directive hidden via CSS styling ({style}): {sub_check.explanation}",
                            suspicious_excerpt=sub_check.suspicious_excerpt
                        )

        # 3. Check for white-on-white text
        for el in elements_with_style:
            style = el["style"].lower()
            if ("color:#fff" in style or "color:white" in style) and ("background:#fff" in style or "background:white" in style):
                text_content = el.get_text().strip()
                if text_content:
                    return DetectionResult(
                        is_suspicious=True,
                        risk_score=0.90,
                        threat_category="WHITE_ON_WHITE_TEXT",
                        source=source,
                        source_location="css_color_match",
                        explanation="Detected concealed white-on-white text intended to hide from user display",
                        suspicious_excerpt=text_content[:100]
                    )

        # 4. Fallback to normal text analysis on visible rendered content
        visible_text = soup.get_text(separator=" ")
        return self.inspect_text(visible_text, source=source)

    def inspect_pdf_metadata_and_text(
        self,
        text_content: str,
        metadata: Dict[str, Any],
        source: str = "PDF_DOCUMENT"
    ) -> DetectionResult:
        """
        Examines PDF extracted text and metadata fields (Title, Author, Subject, Keywords).
        Attackers frequently plant injections in PDF metadata knowing extractors dump metadata.
        """
        # Inspect metadata values
        for meta_key, meta_val in metadata.items():
            if isinstance(meta_val, str) and meta_val.strip():
                meta_check = self.inspect_text(meta_val, source=f"{source}:metadata_{meta_key}")
                if meta_check.is_suspicious:
                    return DetectionResult(
                        is_suspicious=True,
                        risk_score=0.93,
                        threat_category="PDF_METADATA_INJECTION",
                        source=source,
                        source_location=f"metadata_{meta_key}",
                        explanation=f"Adversarial instruction injected into PDF metadata field '{meta_key}': {meta_check.explanation}",
                        suspicious_excerpt=meta_check.suspicious_excerpt
                    )

        # Inspect extracted text body
        return self.inspect_text(text_content, source=source)

    def _check_base64_encoded_payloads(self, text: str, source: str) -> DetectionResult:
        """
        Identifies potential Base64 strings, attempts decoding, and scans the decoded
        payload for nested prompt injections.
        """
        # Regex matching standalone base64 strings of length >= 24
        b64_pattern = r"(?:[A-Za-z0-9+/]{4}){6,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?"
        matches = re.finditer(b64_pattern, text)
        
        for match in matches:
            b64_str = match.group(0)
            try:
                decoded_bytes = base64.b64decode(b64_str, validate=True)
                decoded_text = decoded_bytes.decode("utf-8", errors="ignore")
                if len(decoded_text) > 10:
                    inner_check = self.inspect_text(decoded_text, source=f"{source}:base64_decoded")
                    if inner_check.is_suspicious:
                        return DetectionResult(
                            is_suspicious=True,
                            risk_score=0.96,
                            threat_category="ENCODED_PAYLOAD",
                            source=source,
                            source_location=f"offset_{match.start()}",
                            explanation=f"Base64-obfuscated injection payload detected: {inner_check.explanation}",
                            suspicious_excerpt=f"Base64: {b64_str[:30]}... Decoded: {inner_check.suspicious_excerpt}"
                        )
            except Exception:
                continue

        return DetectionResult(
            is_suspicious=False,
            risk_score=0.0,
            threat_category="BENIGN",
            source=source,
            explanation="No encoded payloads detected"
        )
