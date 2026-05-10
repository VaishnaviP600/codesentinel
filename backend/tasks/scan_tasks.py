"""
Celery Tasks — Async job queue for scan execution.
When GitHub webhook fires, the API enqueues a scan task here.
Celery worker picks it up, runs the agent pipeline,
saves results to DB, posts PR comment, and broadcasts via WebSocket.
"""

import asyncio
import os
import json
import tempfile
import shutil
from celery import Celery
from sqlalchemy.orm import Session
from db.models import SessionLocal, Scan, Finding, Repository, ScanStatusEnum
from agents.orchestrator import run_orchestrator
from core.github_client import post_pr_comment, update_check_run
from core.websocket_manager import broadcast_scan_update
import logging

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("codesentinel", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_max_tasks_per_child=10,
)


def get_db() -> Session:
    return SessionLocal()


@celery_app.task(bind=True, max_retries=2, soft_time_limit=600)
def run_scan_task(self, scan_id: int, repo_full_name: str, pr_number: int,
                  commit_sha: str, clone_url: str, installation_id: str):
    db = get_db()
    repo_path = None

    try:
        # Update scan status to running
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            logger.error(f"Scan {scan_id} not found")
            return

        scan.status = ScanStatusEnum.running
        db.commit()

        # Broadcast status update via WebSocket
        asyncio.run(broadcast_scan_update(scan_id, {"status": "running", "scan_id": scan_id}))

        # Clone the repository to a temp directory
        repo_path = tempfile.mkdtemp(prefix=f"codesentinel_{scan_id}_")
        logger.info(f"Cloning {repo_full_name} to {repo_path}")

        import subprocess
        subprocess.run(
            ["git", "clone", "--depth", "1", clone_url, repo_path],
            check=True, capture_output=True, timeout=60
        )

        # Run the full agent pipeline
        final_state = asyncio.run(
            run_orchestrator(repo_path, repo_full_name, pr_number, commit_sha, scan_id)
        )

        findings = final_state.get("enriched_findings", [])

        # Count by severity
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for f in findings:
            sev = f.get("severity", "low")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        # Save findings to DB
        for f in findings:
            finding = Finding(
                scan_id=scan_id,
                agent=f.get("agent", "unknown"),
                rule_id=f.get("rule_id"),
                title=f.get("title", "Unknown Issue"),
                description=f.get("description", ""),
                severity=f.get("severity", "low"),
                file_path=f.get("file_path"),
                line_start=f.get("line_start"),
                line_end=f.get("line_end"),
                code_snippet=f.get("code_snippet", ""),
                fix_suggestion=f.get("fix_suggestion", ""),
                ai_explanation=f.get("ai_explanation", ""),
                cwe_id=str(f.get("cwe_id", "") or "")[:50] or None,
                raw_output=f.get("raw_output", {})
            )
            db.add(finding)

        # Update scan record
        from datetime import datetime
        scan.status = ScanStatusEnum.completed
        scan.completed_at = datetime.utcnow()
        scan.total_findings = len(findings)
        scan.critical_count = severity_counts.get("critical", 0)
        scan.high_count = severity_counts.get("high", 0)
        scan.medium_count = severity_counts.get("medium", 0)
        scan.low_count = severity_counts.get("low", 0)
        db.commit()

        # Post comment to GitHub PR
        comment = build_pr_comment(findings, scan_id)
        asyncio.run(post_pr_comment(repo_full_name, pr_number, comment, installation_id))

        # Broadcast completion
        asyncio.run(broadcast_scan_update(scan_id, {
            "status": "completed",
            "scan_id": scan_id,
            "total_findings": len(findings),
            "severity_counts": severity_counts
        }))

        logger.info(f"Scan {scan_id} completed: {len(findings)} findings")

    except Exception as e:
        logger.error(f"Scan {scan_id} failed: {e}")
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if scan:
            scan.status = ScanStatusEnum.failed
            db.commit()
        asyncio.run(broadcast_scan_update(scan_id, {"status": "failed", "scan_id": scan_id, "error": str(e)}))
        raise self.retry(exc=e, countdown=30)

    finally:
        db.close()
        if repo_path and os.path.exists(repo_path):
            shutil.rmtree(repo_path, ignore_errors=True)


def build_pr_comment(findings: list, scan_id: int) -> str:
    if not findings:
        return "## ✅ CodeSentinel Security Scan\n\nNo security issues found! Your code looks clean."

    critical = [f for f in findings if f.get("severity") == "critical"]
    high = [f for f in findings if f.get("severity") == "high"]
    medium = [f for f in findings if f.get("severity") == "medium"]
    low = [f for f in findings if f.get("severity") in ("low", "info")]

    emoji_map = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}

    lines = [
        "## 🛡️ CodeSentinel Security Scan Results\n",
        f"| Severity | Count |",
        f"|----------|-------|",
        f"| 🔴 Critical | {len(critical)} |",
        f"| 🟠 High | {len(high)} |",
        f"| 🟡 Medium | {len(medium)} |",
        f"| 🟢 Low | {len(low)} |",
        f"\n**Total findings: {len(findings)}**\n",
    ]

    # Show top 5 critical/high findings inline
    top_findings = (critical + high)[:5]
    if top_findings:
        lines.append("### 🚨 Priority Issues\n")
        for f in top_findings:
            emoji = emoji_map.get(f.get("severity", "low"), "⚪")
            lines.append(f"**{emoji} {f.get('title')}**")
            lines.append(f"- **File:** `{f.get('file_path', 'unknown')}` (line {f.get('line_start', '?')})")
            if f.get("ai_explanation"):
                lines.append(f"- **Why it matters:** {f.get('ai_explanation')}")
            if f.get("fix_suggestion"):
                lines.append(f"- **Fix:** {f.get('fix_suggestion')}")
            lines.append("")

    lines.append(f"\n---\n*Scan ID: {scan_id} | Powered by CodeSentinel + LLaMA 3*")
    return "\n".join(lines)
