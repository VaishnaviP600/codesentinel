"""
GitHub Client — Handles all GitHub App interactions:
- Webhook signature verification
- Installation access tokens
- Posting PR review comments
- Creating check runs
"""

import os
import time
import hmac
import hashlib
import httpx
import jwt as pyjwt
from typing import Optional
import logging

logger = logging.getLogger(__name__)

GITHUB_APP_ID = os.getenv("GITHUB_APP_ID", "")
GITHUB_PRIVATE_KEY = os.getenv("GITHUB_PRIVATE_KEY", "").replace("\\n", "\n")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
GITHUB_API_URL = "https://api.github.com"


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    if not GITHUB_WEBHOOK_SECRET:
        return True  # Skip verification in dev mode
    expected = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def generate_jwt() -> str:
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (10 * 60),
        "iss": GITHUB_APP_ID
    }
    return pyjwt.encode(payload, GITHUB_PRIVATE_KEY, algorithm="RS256")


async def get_installation_token(installation_id: str) -> Optional[str]:
    if not GITHUB_APP_ID or not GITHUB_PRIVATE_KEY:
        logger.warning("GitHub App credentials not configured")
        return None
    try:
        app_jwt = generate_jwt()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GITHUB_API_URL}/app/installations/{installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {app_jwt}",
                    "Accept": "application/vnd.github+json",
                }
            )
            response.raise_for_status()
            return response.json().get("token")
    except Exception as e:
        logger.error(f"Failed to get installation token: {e}")
        return None


async def post_pr_comment(repo_full_name: str, pr_number: int, comment: str, installation_id: str):
    token = await get_installation_token(installation_id)
    if not token:
        logger.warning("No GitHub token — skipping PR comment")
        return

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GITHUB_API_URL}/repos/{repo_full_name}/issues/{pr_number}/comments",
                headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github+json",
                },
                json={"body": comment}
            )
            response.raise_for_status()
            logger.info(f"Posted PR comment to {repo_full_name}#{pr_number}")
    except Exception as e:
        logger.error(f"Failed to post PR comment: {e}")


async def update_check_run(repo_full_name: str, commit_sha: str,
                           conclusion: str, summary: str, installation_id: str):
    token = await get_installation_token(installation_id)
    if not token:
        return

    try:
        async with httpx.AsyncClient() as client:
            # Create check run
            create_resp = await client.post(
                f"{GITHUB_API_URL}/repos/{repo_full_name}/check-runs",
                headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github+json",
                },
                json={
                    "name": "CodeSentinel Security Scan",
                    "head_sha": commit_sha,
                    "status": "completed",
                    "conclusion": conclusion,
                    "output": {
                        "title": "Security Scan Results",
                        "summary": summary
                    }
                }
            )
            create_resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to update check run: {e}")
