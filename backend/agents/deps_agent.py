"""
Dependencies Agent — Scans project dependency files
for known CVEs and vulnerable package versions.
Supports: requirements.txt, package.json, Pipfile
"""

import subprocess
import json
import os
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def scan_python_deps(repo_path: str) -> List[Dict[str, Any]]:
    findings = []
    req_files = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in {"node_modules", ".git", ".venv", "venv"}]
        for f in files:
            if f in ("requirements.txt", "requirements-dev.txt", "Pipfile"):
                req_files.append(os.path.join(root, f))

    for req_file in req_files:
        try:
            result = subprocess.run(
                ["safety", "check", "-r", req_file, "--json", "--output", "screen"],
                capture_output=True, text=True, timeout=60
            )
            output = result.stdout or result.stderr
            if output:
                try:
                    data = json.loads(output)
                    vulnerabilities = data if isinstance(data, list) else data.get("vulnerabilities", [])
                    for vuln in vulnerabilities:
                        pkg_name = vuln.get("package_name", vuln.get("name", "unknown"))
                        installed_version = vuln.get("analyzed_version", vuln.get("installed_version", "unknown"))
                        advisory = vuln.get("advisory", vuln.get("description", "Vulnerability found"))
                        cve = vuln.get("CVE", vuln.get("cve", ""))
                        severity = "high"
                        if cve:
                            severity = "critical"

                        findings.append({
                            "rule_id": f"dep-{pkg_name}-{installed_version}",
                            "title": f"Vulnerable dependency: {pkg_name}=={installed_version}",
                            "description": advisory[:500] if advisory else "Known vulnerability in package",
                            "severity": severity,
                            "file_path": req_file.replace(repo_path, "").lstrip("/"),
                            "line_start": None,
                            "line_end": None,
                            "code_snippet": f"{pkg_name}=={installed_version}",
                            "cwe_id": "CWE-1395",
                            "fix_suggestion": f"Update {pkg_name} to a non-vulnerable version. Check https://pypi.org/project/{pkg_name}/ for the latest safe version.",
                            "source": "safety",
                            "raw_output": vuln
                        })
                except json.JSONDecodeError:
                    logger.warning(f"[Deps Agent] Could not parse safety output for {req_file}")
        except subprocess.TimeoutExpired:
            logger.warning(f"[Deps Agent] safety check timed out for {req_file}")
        except FileNotFoundError:
            logger.warning("[Deps Agent] safety not installed")
        except Exception as e:
            logger.error(f"[Deps Agent] Error scanning {req_file}: {e}")

    return findings


def scan_node_deps(repo_path: str) -> List[Dict[str, Any]]:
    findings = []
    package_json_files = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in {"node_modules", ".git"}]
        for f in files:
            if f == "package.json":
                package_json_files.append(root)

    for pkg_dir in package_json_files:
        if not os.path.exists(os.path.join(pkg_dir, "node_modules")):
            continue
        try:
            result = subprocess.run(
                ["npm", "audit", "--json"],
                capture_output=True, text=True, timeout=60,
                cwd=pkg_dir
            )
            if result.stdout:
                data = json.loads(result.stdout)
                vulnerabilities = data.get("vulnerabilities", {})
                for pkg_name, vuln_info in vulnerabilities.items():
                    severity = vuln_info.get("severity", "medium")
                    via = vuln_info.get("via", [])
                    description = ""
                    if via and isinstance(via[0], dict):
                        description = via[0].get("title", "")

                    findings.append({
                        "rule_id": f"npm-{pkg_name}",
                        "title": f"Vulnerable npm package: {pkg_name}",
                        "description": description or f"Security vulnerability in {pkg_name}",
                        "severity": severity if severity in ["critical", "high", "medium", "low"] else "medium",
                        "file_path": os.path.join(pkg_dir, "package.json").replace(repo_path, "").lstrip("/"),
                        "line_start": None,
                        "line_end": None,
                        "code_snippet": f'"{pkg_name}": "{vuln_info.get("range", "unknown")}"',
                        "cwe_id": "CWE-1395",
                        "fix_suggestion": f"Run `npm audit fix` or manually update {pkg_name}.",
                        "source": "npm-audit",
                        "raw_output": vuln_info
                    })
        except Exception as e:
            logger.error(f"[Deps Agent] npm audit error in {pkg_dir}: {e}")

    return findings


def run_deps_agent(repo_path: str) -> List[Dict[str, Any]]:
    logger.info(f"[Deps Agent] Scanning dependencies in {repo_path}")
    python_findings = scan_python_deps(repo_path)
    node_findings = scan_node_deps(repo_path)
    all_findings = python_findings + node_findings
    logger.info(f"[Deps Agent] Found {len(all_findings)} vulnerable dependencies")
    return all_findings
