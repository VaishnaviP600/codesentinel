"""
SAST Agent — Static Application Security Testing
Uses Semgrep (multi-language) + Bandit (Python-specific)
to find security vulnerabilities in source code.
"""

import subprocess
import json
import os
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

SEVERITY_MAP = {
    "ERROR": "high",
    "WARNING": "medium",
    "INFO": "low",
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
}


def run_semgrep(repo_path: str) -> List[Dict[str, Any]]:
    findings = []
    try:
        result = subprocess.run(
            [
                "semgrep", "--config", "auto",
                "--json", "--quiet",
                "--timeout", "60",
                repo_path
            ],
            capture_output=True, text=True, timeout=120
        )
        if result.stdout:
            data = json.loads(result.stdout)
            for r in data.get("results", []):
                findings.append({
                    "rule_id": r.get("check_id", "unknown"),
                    "title": r.get("check_id", "Security Issue").split(".")[-1].replace("-", " ").title(),
                    "description": r.get("extra", {}).get("message", ""),
                    "severity": SEVERITY_MAP.get(r.get("extra", {}).get("severity", "WARNING"), "medium"),
                    "file_path": r.get("path", "").replace(repo_path, "").lstrip("/"),
                    "line_start": r.get("start", {}).get("line"),
                    "line_end": r.get("end", {}).get("line"),
                    "code_snippet": r.get("extra", {}).get("lines", ""),
                    "cwe_id": r.get("extra", {}).get("metadata", {}).get("cwe", [None])[0] if r.get("extra", {}).get("metadata", {}).get("cwe") else None,
                    "source": "semgrep",
                    "raw_output": r
                })
    except subprocess.TimeoutExpired:
        logger.warning("[SAST] Semgrep timed out")
    except Exception as e:
        logger.error(f"[SAST] Semgrep error: {e}")
    return findings


def run_bandit(repo_path: str) -> List[Dict[str, Any]]:
    findings = []
    try:
        result = subprocess.run(
            ["bandit", "-r", repo_path, "-f", "json", "-q", "--exit-zero"],
            capture_output=True, text=True, timeout=60
        )
        if result.stdout:
            data = json.loads(result.stdout)
            for r in data.get("results", []):
                findings.append({
                    "rule_id": r.get("test_id", "unknown"),
                    "title": r.get("test_name", "Security Issue").replace("_", " ").title(),
                    "description": r.get("issue_text", ""),
                    "severity": SEVERITY_MAP.get(r.get("issue_severity", "MEDIUM"), "medium"),
                    "file_path": r.get("filename", "").replace(repo_path, "").lstrip("/"),
                    "line_start": r.get("line_number"),
                    "line_end": r.get("line_number"),
                    "code_snippet": r.get("code", ""),
                    "cwe_id": r.get("issue_cwe", {}).get("id") if r.get("issue_cwe") else None,
                    "source": "bandit",
                    "raw_output": r
                })
    except subprocess.TimeoutExpired:
        logger.warning("[SAST] Bandit timed out")
    except Exception as e:
        logger.error(f"[SAST] Bandit error: {e}")
    return findings


def run_sast_agent(repo_path: str) -> List[Dict[str, Any]]:
    logger.info(f"[SAST Agent] Starting scan on {repo_path}")
    semgrep_findings = run_semgrep(repo_path)
    bandit_findings = run_bandit(repo_path)
    all_findings = semgrep_findings + bandit_findings
    logger.info(f"[SAST Agent] Found {len(all_findings)} issues ({len(semgrep_findings)} semgrep, {len(bandit_findings)} bandit)")
    return all_findings
