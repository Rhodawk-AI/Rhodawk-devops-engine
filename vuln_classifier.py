"""
Rhodawk AI — Vulnerability Classifier
========================================
CWE taxonomy-based classification of raw findings.
Maps evidence → CWE → CVSS vector → severity tier.

Also computes the final composite security score used in dashboards.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ClassificationResult:
    cwe_id: str
    cwe_name: str
    cwe_category: str
    owasp_top10: Optional[str]
    severity: str
    cvss_base_score: float
    cvss_vector: str
    exploitation_likelihood: str   # LIKELY | POSSIBLE | UNLIKELY
    remediation_guidance: str


_CWE_DATABASE = {
    "CWE-89": {
        "name": "SQL Injection",
        "category": "Injection",
        "owasp": "A03:2021-Injection",
        "severity": "CRITICAL",
        "cvss_base": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "likelihood": "LIKELY",
        "remediation": "Use parameterized queries/prepared statements. Never concatenate user input into SQL strings.",
    },
    "CWE-79": {
        "name": "Cross-Site Scripting (XSS)",
        "category": "Injection",
        "owasp": "A03:2021-Injection",
        "severity": "HIGH",
        "cvss_base": 6.1,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
        "likelihood": "LIKELY",
        "remediation": "Escape all output. Use Content Security Policy. Validate and sanitize inputs.",
    },
    "CWE-78": {
        "name": "OS Command Injection",
        "category": "Injection",
        "owasp": "A03:2021-Injection",
        "severity": "CRITICAL",
        "cvss_base": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "likelihood": "LIKELY",
        "remediation": "Never pass user input to shell commands. Use subprocess with list arguments (shell=False).",
    },
    "CWE-22": {
        "name": "Path Traversal",
        "category": "File Handling",
        "owasp": "A01:2021-Broken Access Control",
        "severity": "HIGH",
        "cvss_base": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "likelihood": "LIKELY",
        "remediation": "Canonicalize paths. Validate against allowed directory. Use os.path.realpath and check prefix.",
    },
    "CWE-502": {
        "name": "Deserialization of Untrusted Data",
        "category": "Deserialization",
        "owasp": "A08:2021-Software and Data Integrity Failures",
        "severity": "CRITICAL",
        "cvss_base": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "likelihood": "LIKELY",
        "remediation": "Never deserialize user-controlled data with pickle/yaml.load/marshal. Use JSON with strict schema validation.",
    },
    "CWE-798": {
        "name": "Hardcoded Credentials",
        "category": "Authentication",
        "owasp": "A07:2021-Identification and Authentication Failures",
        "severity": "HIGH",
        "cvss_base": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "likelihood": "LIKELY",
        "remediation": "Move credentials to environment variables or secrets managers. Rotate immediately if exposed.",
    },
    "CWE-918": {
        "name": "Server-Side Request Forgery (SSRF)",
        "category": "Injection",
        "owasp": "A10:2021-SSRF",
        "severity": "HIGH",
        "cvss_base": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "likelihood": "POSSIBLE",
        "remediation": "Validate and allowlist URLs. Block requests to internal networks. Use a URL parser, not string matching.",
    },
    "CWE-611": {
        "name": "XML External Entity (XXE)",
        "category": "Injection",
        "owasp": "A05:2021-Security Misconfiguration",
        "severity": "HIGH",
        "cvss_base": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "likelihood": "POSSIBLE",
        "remediation": "Use defusedxml. Disable external entity processing in XML parsers.",
    },
    "CWE-295": {
        "name": "Improper Certificate Validation",
        "category": "Cryptography",
        "owasp": "A02:2021-Cryptographic Failures",
        "severity": "HIGH",
        "cvss_base": 7.4,
        "cvss_vector": "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:N",
        "likelihood": "POSSIBLE",
        "remediation": "Never set verify=False. Use proper CA bundles. Enable certificate pinning for critical connections.",
    },
    "CWE-347": {
        "name": "Improper Verification of Cryptographic Signature",
        "category": "Cryptography",
        "owasp": "A02:2021-Cryptographic Failures",
        "severity": "CRITICAL",
        "cvss_base": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "likelihood": "LIKELY",
        "remediation": "Always verify JWT signatures. Never accept 'none' algorithm. Use explicit algorithm allowlists.",
    },
    "CWE-362": {
        "name": "Race Condition",
        "category": "Concurrency",
        "owasp": None,
        "severity": "MEDIUM",
        "cvss_base": 5.9,
        "cvss_vector": "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:H/A:N",
        "likelihood": "POSSIBLE",
        "remediation": "Use locks/mutexes for shared state. Prefer atomic operations. Use thread-safe data structures.",
    },
    "CWE-190": {
        "name": "Integer Overflow",
        "category": "Memory",
        "owasp": None,
        "severity": "HIGH",
        "cvss_base": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:H",
        "likelihood": "POSSIBLE",
        "remediation": "Validate numeric ranges before arithmetic. Use checked arithmetic libraries.",
    },
    "CWE-119": {
        "name": "Buffer Overflow",
        "category": "Memory",
        "owasp": None,
        "severity": "CRITICAL",
        "cvss_base": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "likelihood": "POSSIBLE",
        "remediation": "Use bounds-checked functions. Enable stack canaries and ASLR. Use memory-safe languages.",
    },
    "CWE-416": {
        "name": "Use After Free",
        "category": "Memory",
        "owasp": None,
        "severity": "CRITICAL",
        "cvss_base": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "likelihood": "POSSIBLE",
        "remediation": "Set pointers to NULL after free. Use smart pointers (Rust/C++). Enable AddressSanitizer in CI.",
    },
    "CWE-134": {
        "name": "Format String Vulnerability",
        "category": "Injection",
        "owasp": "A03:2021-Injection",
        "severity": "HIGH",
        "cvss_base": 8.1,
        "cvss_vector": "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:N",
        "likelihood": "POSSIBLE",
        "remediation": "Never pass user input as printf format string. Use explicit format specifiers.",
    },
    "CWE-95": {
        "name": "Code Injection (eval/exec)",
        "category": "Injection",
        "owasp": "A03:2021-Injection",
        "severity": "CRITICAL",
        "cvss_base": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "likelihood": "LIKELY",
        "remediation": "Never use eval/exec on user-controlled data. Use AST parsing or safe expression evaluators.",
    },
    "CWE-200": {
        "name": "Information Exposure",
        "category": "Information Disclosure",
        "owasp": "A01:2021-Broken Access Control",
        "severity": "MEDIUM",
        "cvss_base": 5.3,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
        "likelihood": "LIKELY",
        "remediation": "Strip sensitive data from error messages. Log minimally. Use generic error responses.",
    },
    "CWE-338": {
        "name": "Weak PRNG for Security",
        "category": "Cryptography",
        "owasp": "A02:2021-Cryptographic Failures",
        "severity": "MEDIUM",
        "cvss_base": 5.9,
        "cvss_vector": "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "likelihood": "POSSIBLE",
        "remediation": "Use secrets.token_hex() or os.urandom() for security contexts. Never use random.random() for tokens.",
    },
    "CWE-328": {
        "name": "Weak Cryptographic Hash",
        "category": "Cryptography",
        "owasp": "A02:2021-Cryptographic Failures",
        "severity": "MEDIUM",
        "cvss_base": 5.9,
        "cvss_vector": "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "likelihood": "POSSIBLE",
        "remediation": "Replace MD5/SHA1 with SHA-256 or better. For passwords use bcrypt/argon2/scrypt.",
    },
    "CWE-400": {
        "name": "Uncontrolled Resource Consumption (DoS)",
        "category": "Availability",
        "owasp": None,
        "severity": "HIGH",
        "cvss_base": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H",
        "likelihood": "LIKELY",
        "remediation": "Implement rate limiting. Set resource limits (memory, CPU, time). Validate input sizes.",
    },
    "CWE-1321": {
        "name": "Prototype Pollution",
        "category": "Injection",
        "owasp": "A03:2021-Injection",
        "severity": "HIGH",
        "cvss_base": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:H/A:L",
        "likelihood": "POSSIBLE",
        "remediation": "Use Object.create(null) for object maps. Validate object keys. Use Map instead of plain objects.",
    },
    "CWE-601": {
        "name": "Open Redirect",
        "category": "URL Handling",
        "owasp": "A01:2021-Broken Access Control",
        "severity": "MEDIUM",
        "cvss_base": 6.1,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
        "likelihood": "LIKELY",
        "remediation": "Validate redirect URLs against an allowlist. Never redirect to user-supplied arbitrary URLs.",
    },
    "CWE-306": {
        "name": "Missing Authentication",
        "category": "Authentication",
        "owasp": "A07:2021-Identification and Authentication Failures",
        "severity": "CRITICAL",
        "cvss_base": 9.1,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N",
        "likelihood": "LIKELY",
        "remediation": "Require authentication on all sensitive endpoints. Use middleware to enforce auth globally.",
    },
    "CWE-74": {
        "name": "Injection (generic)",
        "category": "Injection",
        "owasp": "A03:2021-Injection",
        "severity": "HIGH",
        "cvss_base": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
        "likelihood": "POSSIBLE",
        "remediation": "Validate, escape, and parameterize all user input that reaches interpreters.",
    },
}


def classify_vulnerability(
    cwe_hint: str,
    description: str = "",
    exploit_class: str = "",
) -> ClassificationResult:
    """
    Classify a vulnerability by CWE ID, returning full taxonomy information.
    Falls back to heuristic matching from description if CWE is unknown.
    """
    cwe_data = _CWE_DATABASE.get(cwe_hint)

    if not cwe_data:
        cwe_hint, cwe_data = _infer_cwe(description, exploit_class)

    if not cwe_data:
        cwe_hint = "CWE-UNKNOWN"
        cwe_data = {
            "name": "Unknown Vulnerability", "category": "Unclassified",
            "owasp": None, "severity": "MEDIUM", "cvss_base": 5.0,
            "cvss_vector": "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:L/A:N",
            "likelihood": "POSSIBLE",
            "remediation": "Manual security review required.",
        }

    return ClassificationResult(
        cwe_id=cwe_hint,
        cwe_name=cwe_data["name"],
        cwe_category=cwe_data["category"],
        owasp_top10=cwe_data.get("owasp"),
        severity=cwe_data["severity"],
        cvss_base_score=cwe_data["cvss_base"],
        cvss_vector=cwe_data["cvss_vector"],
        exploitation_likelihood=cwe_data["likelihood"],
        remediation_guidance=cwe_data["remediation"],
    )


def _infer_cwe(description: str, exploit_class: str) -> tuple[str, Optional[dict]]:
    """Infer CWE from description keywords when CWE ID is not provided."""
    desc_lower = (description + " " + exploit_class).lower()

    inference_rules = [
        (["sql", "query injection", "database injection"], "CWE-89"),
        (["xss", "cross-site scripting", "innerhtml"], "CWE-79"),
        (["command injection", "os.system", "shell injection"], "CWE-78"),
        (["path traversal", "directory traversal", "../"], "CWE-22"),
        (["pickle", "deserializ", "yaml.load"], "CWE-502"),
        (["hardcoded", "hardcoded credential", "hardcoded password"], "CWE-798"),
        (["ssrf", "server-side request forgery"], "CWE-918"),
        (["xxe", "xml external entity"], "CWE-611"),
        (["tls", "ssl", "certificate verification"], "CWE-295"),
        (["jwt", "token forgery", "signature bypass"], "CWE-347"),
        (["race condition", "toctou"], "CWE-362"),
        (["integer overflow", "arithmetic overflow"], "CWE-190"),
        (["buffer overflow", "stack overflow", "heap overflow"], "CWE-119"),
        (["use after free", "uaf"], "CWE-416"),
        (["format string"], "CWE-134"),
        (["eval", "exec", "code injection"], "CWE-95"),
        (["prototype pollution", "__proto__"], "CWE-1321"),
        (["open redirect", "redirect"], "CWE-601"),
        (["missing auth", "unauthenticated"], "CWE-306"),
        (["weak hash", "md5", "sha1"], "CWE-328"),
        (["weak random", "math.random", "random.random"], "CWE-338"),
        (["denial of service", "dos", "resource exhaustion"], "CWE-400"),
        (["information disclosure", "data leak", "sensitive data"], "CWE-200"),
    ]

    for keywords, cwe in inference_rules:
        if any(kw in desc_lower for kw in keywords):
            return cwe, _CWE_DATABASE.get(cwe)

    return "CWE-UNKNOWN", None


def get_all_cwes() -> list[dict]:
    """Return the full CWE database as a list for the UI."""
    return [
        {
            "cwe_id": cwe_id,
            "name": data["name"],
            "category": data["category"],
            "severity": data["severity"],
            "cvss_base": data["cvss_base"],
            "owasp": data.get("owasp", ""),
        }
        for cwe_id, data in _CWE_DATABASE.items()
    ]
