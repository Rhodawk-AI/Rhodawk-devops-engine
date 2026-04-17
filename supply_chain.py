"""
Rhodawk AI — Supply Chain Security Gate
========================================
Every AI-generated diff that touches requirements.txt or any import statement
passes through this gate before a PR is opened.

Capabilities:
  1. pip-audit — CVE scanning against OSV/PyPA advisory database
  2. Typosquatting detection — 50+ known typosquatting patterns vs PyPI top packages
  3. New dependency analysis — flags packages added by the AI that weren't in original
  4. Package metadata validation — checks for packages with no public source repo (red flag)

This catches supply chain attacks where an LLM hallucinates a plausible-sounding
package name that happens to be a malicious clone.
"""

import re
import requests
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# Top PyPI packages that are commonly typosquatted
_KNOWN_PACKAGES = {
    "requests", "numpy", "pandas", "flask", "django", "fastapi", "sqlalchemy",
    "boto3", "pytest", "setuptools", "pip", "wheel", "cryptography", "pillow",
    "scipy", "matplotlib", "tensorflow", "torch", "scikit-learn", "pydantic",
    "click", "rich", "httpx", "aiohttp", "celery", "redis", "pymongo", "psycopg2",
    "uvicorn", "gunicorn", "twisted", "paramiko", "fabric", "ansible", "docker",
    "kubernetes", "airflow", "prefect", "dask", "ray", "transformers", "openai",
    "anthropic", "langchain", "gradio", "streamlit", "beautifulsoup4", "lxml",
    "selenium", "playwright", "scrapy", "arrow", "pendulum", "pyyaml", "toml",
    "dotenv", "python-dotenv", "jwt", "pyjwt", "bcrypt", "passlib", "itsdangerous",
}

# Levenshtein distance threshold for typosquatting detection
_TYPO_THRESHOLD = 2


def _levenshtein(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (c1 != c2)))
        prev = curr
    return prev[-1]


def _extract_new_packages(diff_text: str, original_requirements: str = "") -> list[str]:
    """Extract package names added by the AI diff to requirements.txt"""
    added = []
    in_requirements_block = False

    for line in diff_text.splitlines():
        if "requirements.txt" in line:
            in_requirements_block = True
        if in_requirements_block and line.startswith("+") and not line.startswith("+++"):
            pkg_line = line[1:].strip()
            if pkg_line and not pkg_line.startswith("#"):
                pkg_name = re.split(r"[>=<!~\[]", pkg_line)[0].strip().lower()
                if pkg_name and pkg_name not in original_requirements.lower():
                    added.append(pkg_name)

    return added


def _check_typosquatting(package_name: str) -> Optional[str]:
    """Check if a package name looks like a typosquat of a known package."""
    pkg = package_name.lower().replace("-", "").replace("_", "")

    for known in _KNOWN_PACKAGES:
        known_clean = known.lower().replace("-", "").replace("_", "")
        if pkg == known_clean:
            return None  # exact match — it's fine
        dist = _levenshtein(pkg, known_clean)
        if 0 < dist <= _TYPO_THRESHOLD and len(pkg) > 3:
            return f"'{package_name}' is {dist} edit(s) from known package '{known}' — possible typosquat"

    return None


def _run_pip_audit(packages: list[str]) -> list[dict]:
    """Run pip-audit against a list of package names to check for CVEs."""
    if not packages:
        return []

    try:
        result = subprocess.run(
            ["pip-audit", "--requirement", "/dev/stdin", "--format=json", "--no-deps"],
            input="\n".join(packages),
            capture_output=True,
            text=True,
            timeout=60,
            shell=False,
        )
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            vulns = []
            for dep in data.get("dependencies", []):
                for vuln in dep.get("vulns", []):
                    vulns.append({
                        "package": dep["name"],
                        "version": dep.get("version", "unknown"),
                        "vuln_id": vuln.get("id", ""),
                        "description": vuln.get("description", "")[:200],
                        "severity": vuln.get("aliases", ["UNKNOWN"])[0] if vuln.get("aliases") else "UNKNOWN",
                    })
            return vulns
    except FileNotFoundError:
        pass  # pip-audit not installed
    except Exception:
        pass

    return []


def _check_import_additions(diff_text: str) -> list[str]:
    """Detect new import statements added by the AI."""
    new_imports = []
    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            clean = line[1:].strip()
            if clean.startswith("import ") or clean.startswith("from "):
                # Extract module name
                match = re.match(r"(?:from|import)\s+(\w+)", clean)
                if match:
                    new_imports.append(match.group(1))
    return list(set(new_imports))


def _check_package_metadata(package_name: str) -> Optional[str]:
    try:
        resp = requests.get(f"https://pypi.org/pypi/{package_name}/json", timeout=10)
        if resp.status_code == 404:
            return f"Package '{package_name}' not found on PyPI — likely hallucinated"
        resp.raise_for_status()
        data = resp.json()
        info = data.get("info", {})
        urls = info.get("project_urls") or {}
        source_url = urls.get("Source") or urls.get("Source Code") or urls.get("Repository") or info.get("home_page")
        if not source_url:
            return f"Package '{package_name}' has no source repository — possible malicious package"
        upload_times = []
        for releases in (data.get("releases") or {}).values():
            for release in releases:
                ts = release.get("upload_time_iso_8601")
                if ts:
                    try:
                        upload_times.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))
                    except ValueError:
                        pass
        if upload_times:
            first_upload = min(upload_times)
            age_days = (datetime.now(timezone.utc) - first_upload).days
            if age_days < 30:
                return f"Package '{package_name}' is only {age_days} day(s) old — suspiciously new dependency"
    except Exception:
        return None
    return None


@dataclass
class SupplyChainReport:
    passed: bool
    new_packages: list[str] = field(default_factory=list)
    typosquat_findings: list[str] = field(default_factory=list)
    cve_findings: list[dict] = field(default_factory=list)
    new_imports: list[str] = field(default_factory=list)
    metadata_findings: list[str] = field(default_factory=list)
    blocked_reason: Optional[str] = None

    def summary(self) -> str:
        if self.passed:
            return f"Supply chain OK. Checked {len(self.new_packages)} new package(s)."
        return f"Supply chain BLOCKED: {self.blocked_reason}"


def run_supply_chain_gate(diff_text: str, repo_dir: str = "") -> SupplyChainReport:
    """
    Run the full supply chain gate on an AI-generated diff.
    Returns SupplyChainReport. If passed=False, the PR must NOT be opened.
    """
    import os
    original_reqs = ""
    req_path = os.path.join(repo_dir, "requirements.txt") if repo_dir else ""
    if req_path and os.path.exists(req_path):
        try:
            with open(req_path) as f:
                original_reqs = f.read()
        except OSError:
            pass

    new_packages = _extract_new_packages(diff_text, original_reqs)
    new_imports = _check_import_additions(diff_text)

    typosquat_findings = []
    for pkg in new_packages:
        finding = _check_typosquatting(pkg)
        if finding:
            typosquat_findings.append(finding)
    for imp in new_imports:
        finding = _check_typosquatting(imp)
        if finding:
            typosquat_findings.append(f"[import] {finding}")

    if typosquat_findings:
        return SupplyChainReport(
            passed=False,
            new_packages=new_packages,
            typosquat_findings=typosquat_findings,
            new_imports=new_imports,
            blocked_reason=f"Typosquatting detected: {typosquat_findings[0]}",
        )

    cve_findings = _run_pip_audit(new_packages)
    critical_cves = [c for c in cve_findings if "CVE" in c.get("vuln_id", "")]

    metadata_findings = []
    for pkg in new_packages:
        finding = _check_package_metadata(pkg)
        if finding:
            metadata_findings.append(finding)

    if metadata_findings:
        return SupplyChainReport(
            passed=False,
            new_packages=new_packages,
            cve_findings=cve_findings,
            new_imports=new_imports,
            metadata_findings=metadata_findings,
            blocked_reason=f"Package metadata risk: {metadata_findings[0]}",
        )

    if critical_cves:
        return SupplyChainReport(
            passed=False,
            new_packages=new_packages,
            cve_findings=cve_findings,
            new_imports=new_imports,
            metadata_findings=metadata_findings,
            blocked_reason=f"CVE found in added package '{critical_cves[0]['package']}': {critical_cves[0]['vuln_id']}",
        )

    return SupplyChainReport(
        passed=True,
        new_packages=new_packages,
        cve_findings=cve_findings,
        new_imports=new_imports,
        metadata_findings=metadata_findings,
    )
