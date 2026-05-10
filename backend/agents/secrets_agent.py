"""
Secrets Agent — Detects hardcoded secrets, API keys,
passwords, tokens, and credentials in source code.
Uses detect-secrets library.
"""

import subprocess
import json
import os
import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

SECRET_PATTERNS = [
    (r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{4,}["\']', "Hardcoded Password", "high"),
    (r'(?i)(api_key|apikey|api-key)\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded API Key", "critical"),
    (r'(?i)(secret|secret_key)\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded Secret", "critical"),
    (r'(?i)(token|access_token|auth_token)\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded Token", "high"),
    (r'(?i)(aws_access_key_id)\s*=\s*["\']AKIA[0-9A-Z]{16}["\']', "AWS Access Key", "critical"),
    (r'(?i)(private_key|rsa_key)\s*=\s*["\'][^"\']{16,}["\']', "Hardcoded Private Key", "critical"),
    (r'mongodb(\+srv)?://[^:]+:[^@]+@', "MongoDB Connection String with Credentials", "critical"),
    (r'postgres(ql)?://[^:]+:[^@]+@', "PostgreSQL Connection String with Credentials", "high"),
]

SKIP_EXTENSIONS = {".lock", ".sum", ".mod", ".txt", ".md", ".png", ".jpg", ".gif", ".svg"}
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build"}


def run_detect_secrets(repo_path: str) -> List[Dict[str, Any]]:
    findings = []
    try:
        result = subprocess.run(
            ["detect-secrets", "scan", repo_path],
            capture_output=True, text=True, timeout=60
        )
        if result.stdout:
            data = json.loads(result.stdout)
            results = data.get("results", {})
            for file_path, secrets in results.items():
                for secret in secrets:
                    findings.append({
                        "rule_id": f"secret-{secret.get('type', 'unknown').lower().replace(' ', '-')}",
                        "title": f"Potential {secret.get('type', 'Secret')} Detected",
                        "description": f"A {secret.get('type', 'secret')} was found in {file_path}. Secrets hardcoded in source code can be exposed via version control.",
                        "severity": "critical" if "key" in secret.get("type", "").lower() or "password" in secret.get("type", "").lower() else "high",
                        "file_path": file_path.replace(repo_path, "").lstrip("/"),
                        "line_start": secret.get("line_number"),
                        "line_end": secret.get("line_number"),
                        "code_snippet": f"[Redacted for security - line {secret.get('line_number')}]",
                        "cwe_id": "CWE-798",
                        "source": "detect-secrets",
                        "raw_output": secret
                    })
    except Exception as e:
        logger.error(f"[Secrets Agent] detect-secrets error: {e}")
    return findings


def run_pattern_scan(repo_path: str) -> List[Dict[str, Any]]:
    findings = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for filename in files:
            if any(filename.endswith(ext) for ext in SKIP_EXTENSIONS):
                continue
            file_path = os.path.join(root, filename)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                for line_num, line in enumerate(lines, 1):
                    for pattern, title, severity in SECRET_PATTERNS:
                        if re.search(pattern, line):
                            snippet = line.strip()
                            # Redact actual value
                            snippet = re.sub(r'(=\s*["\'])[^"\']+(["\'])', r'\1[REDACTED]\2', snippet)
                            findings.append({
                                "rule_id": f"pattern-{title.lower().replace(' ', '-')}",
                                "title": title,
                                "description": f"{title} found hardcoded in source. This is a critical security risk if committed to version control.",
                                "severity": severity,
                                "file_path": file_path.replace(repo_path, "").lstrip("/"),
                                "line_start": line_num,
                                "line_end": line_num,
                                "code_snippet": snippet,
                                "cwe_id": "CWE-798",
                                "source": "pattern-scan",
                                "raw_output": {"pattern": pattern, "line": line_num}
                            })
            except Exception:
                continue
    return findings


def run_secrets_agent(repo_path: str) -> List[Dict[str, Any]]:
    logger.info(f"[Secrets Agent] Scanning {repo_path}")
    ds_findings = run_detect_secrets(repo_path)
    pattern_findings = run_pattern_scan(repo_path)
    all_findings = ds_findings + pattern_findings

    # Deduplicate by file + line
    seen = set()
    unique = []
    for f in all_findings:
        key = f"{f['file_path']}:{f['line_start']}"
        if key not in seen:
            seen.add(key)
            unique.append(f)

    logger.info(f"[Secrets Agent] Found {len(unique)} secrets")
    return unique
