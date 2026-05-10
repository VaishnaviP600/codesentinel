import json
import asyncio
from typing import TypedDict, List, Dict, Any
from agents.sast_agent import run_sast_agent
from agents.secrets_agent import run_secrets_agent
from agents.deps_agent import run_deps_agent
from agents.fix_agent import run_fix_agent
import logging

logger = logging.getLogger(__name__)


async def run_orchestrator(
    repo_path: str,
    repo_full_name: str,
    pr_number: int,
    commit_sha: str,
    scan_id: int
) -> Dict[str, Any]:

    logger.info(f"[Orchestrator] Starting parallel scan for {repo_full_name}")

    # Run all 3 agents in parallel
    sast_task = asyncio.to_thread(run_sast_agent, repo_path)
    secrets_task = asyncio.to_thread(run_secrets_agent, repo_path)
    deps_task = asyncio.to_thread(run_deps_agent, repo_path)

    sast_findings, secrets_findings, deps_findings = await asyncio.gather(
        sast_task, secrets_task, deps_task
    )

    # Tag each finding with its agent
    all_findings = []
    for f in sast_findings:
        all_findings.append({**f, "agent": "sast"})
    for f in secrets_findings:
        all_findings.append({**f, "agent": "secrets"})
    for f in deps_findings:
        all_findings.append({**f, "agent": "deps"})

    # Deduplicate
    seen = set()
    unique_findings = []
    for f in all_findings:
        key = f"{f.get('file_path')}:{f.get('line_start')}:{f.get('rule_id')}"
        if key not in seen:
            seen.add(key)
            unique_findings.append(f)

    logger.info(f"[Orchestrator] {len(unique_findings)} unique findings — enriching with LLaMA 3")

    # Enrich with AI
    enriched = run_fix_agent(unique_findings, repo_path)

    return {
        "enriched_findings": enriched,
        "status": "completed",
        "sast_findings": sast_findings,
        "secrets_findings": secrets_findings,
        "deps_findings": deps_findings,
    }
