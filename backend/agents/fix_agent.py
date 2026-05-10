"""
Fix Agent — Enriches findings with AI-powered explanations
and fix suggestions using LLaMA 3 running locally via Ollama.
No API key required. Completely free and private.
"""

import httpx
import json
import os
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = "llama3"

SYSTEM_PROMPT = """You are an expert security engineer and code reviewer.
You will be given a security finding from a code scan.
Your job is to:
1. Explain WHY this is dangerous in 2-3 simple sentences
2. Provide a concrete, minimal code fix
3. Suggest best practices to prevent this class of vulnerability

Be concise. Use plain English. Format your response as JSON with keys:
- explanation: string (2-3 sentences, plain English)
- fix_suggestion: string (actual code or command)
- best_practice: string (1 sentence tip)

Respond with ONLY valid JSON, no markdown, no preamble."""


def call_ollama(prompt: str) -> Dict[str, str]:
    try:
        response = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "system": SYSTEM_PROMPT,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 400
                }
            },
            timeout=60.0
        )
        response.raise_for_status()
        result = response.json()
        raw = result.get("response", "{}")
        # Strip any markdown fences if model adds them
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(raw)
    except httpx.ConnectError:
        logger.warning("[Fix Agent] Ollama not running - skipping AI enrichment")
        return {}
    except json.JSONDecodeError:
        logger.warning("[Fix Agent] Could not parse LLaMA response as JSON")
        return {}
    except Exception as e:
        logger.error(f"[Fix Agent] Ollama error: {e}")
        return {}


def build_prompt(finding: Dict[str, Any]) -> str:
    return f"""Security Finding:
Title: {finding.get('title', 'Unknown')}
Severity: {finding.get('severity', 'unknown').upper()}
File: {finding.get('file_path', 'unknown')}
Line: {finding.get('line_start', 'unknown')}
Description: {finding.get('description', 'No description')}
Code snippet:
{finding.get('code_snippet', 'N/A')}
CWE: {finding.get('cwe_id', 'N/A')}

Provide explanation, fix_suggestion, and best_practice as JSON."""


def run_fix_agent(findings: List[Dict[str, Any]], repo_path: str) -> List[Dict[str, Any]]:
    logger.info(f"[Fix Agent] Enriching {len(findings)} findings via LLaMA 3 (Ollama)")

    # Only enrich high/critical findings with AI to save time
    priority_severities = {"critical", "high"}
    enriched = []

    for finding in findings:
        if finding.get("severity") in priority_severities:
            prompt = build_prompt(finding)
            ai_result = call_ollama(prompt)

            if ai_result:
                finding["ai_explanation"] = ai_result.get("explanation", "")
                if not finding.get("fix_suggestion"):
                    finding["fix_suggestion"] = ai_result.get("fix_suggestion", "")
                finding["best_practice"] = ai_result.get("best_practice", "")
            else:
                finding["ai_explanation"] = finding.get("description", "")

        enriched.append(finding)

    logger.info(f"[Fix Agent] Enrichment complete for {len(enriched)} findings")
    return enriched
