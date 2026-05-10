"""
CodeSentinel — FastAPI Backend
Endpoints:
  POST /webhook/github          — GitHub App webhook receiver
  POST /api/auth/register       — User registration
  POST /api/auth/login          — Login (returns JWT)
  GET  /api/scans               — List all scans
  GET  /api/scans/{id}          — Scan details
  GET  /api/scans/{id}/findings — Findings for a scan
  GET  /api/stats               — Dashboard stats
  POST /api/scan/manual         — Trigger manual scan
  WS   /ws/{scan_id}            — Real-time scan updates
"""

import json
import os
import hashlib
import hmac
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from db.models import (
    get_db, init_db, User, Repository, Scan, Finding,
    ScanStatusEnum, SeverityEnum
)
from core.auth import hash_password, verify_password, create_access_token, get_current_user
from core.websocket_manager import manager
from tasks.scan_tasks import run_scan_task

app = FastAPI(title="CodeSentinel API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")


@app.on_event("startup")
async def startup():
    init_db()


# ─── Auth ────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


@app.post("/api/auth/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(username=req.username, email=req.email, hashed_password=hash_password(req.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id), "username": user.username})
    return {"access_token": token, "token_type": "bearer", "username": user.username}


@app.post("/api/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id), "username": user.username})
    return {"access_token": token, "token_type": "bearer", "username": user.username}


# ─── GitHub Webhook ───────────────────────────────────────────────────────────

@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    payload_bytes = await request.body()

    # Verify signature
    sig = request.headers.get("X-Hub-Signature-256", "")
    if GITHUB_WEBHOOK_SECRET:
        expected = "sha256=" + hmac.new(GITHUB_WEBHOOK_SECRET.encode(), payload_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event = request.headers.get("X-GitHub-Event", "")
    payload = json.loads(payload_bytes)

    if event == "pull_request" and payload.get("action") in ("opened", "synchronize", "reopened"):
        pr = payload["pull_request"]
        repo_data = payload["repository"]
        installation_id = str(payload.get("installation", {}).get("id", ""))

        # Upsert repository
        repo = db.query(Repository).filter(
            Repository.github_repo_id == str(repo_data["id"])
        ).first()
        if not repo:
            repo = Repository(
                github_repo_id=str(repo_data["id"]),
                full_name=repo_data["full_name"],
                owner=repo_data["owner"]["login"],
                name=repo_data["name"],
                installation_id=installation_id
            )
            db.add(repo)
            db.commit()
            db.refresh(repo)

        # Create scan record
        scan = Scan(
            repo_id=repo.id,
            pr_number=pr["number"],
            pr_title=pr["title"],
            commit_sha=pr["head"]["sha"],
            branch=pr["head"]["ref"],
            status=ScanStatusEnum.pending
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)

        # Enqueue scan task
        run_scan_task.delay(
            scan_id=scan.id,
            repo_full_name=repo_data["full_name"],
            pr_number=pr["number"],
            commit_sha=pr["head"]["sha"],
            clone_url=repo_data["clone_url"],
            installation_id=installation_id
        )

        return {"message": "Scan enqueued", "scan_id": scan.id}

    return {"message": f"Event '{event}' ignored"}


# ─── Scans API ────────────────────────────────────────────────────────────────

@app.get("/api/scans")
def list_scans(
    page: int = 1, limit: int = 20,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    offset = (page - 1) * limit
    scans = (
        db.query(Scan)
        .order_by(desc(Scan.started_at))
        .offset(offset).limit(limit).all()
    )
    total = db.query(func.count(Scan.id)).scalar()
    return {
        "scans": [
            {
                "id": s.id,
                "repo": s.repository.full_name if s.repository else "unknown",
                "pr_number": s.pr_number,
                "pr_title": s.pr_title,
                "branch": s.branch,
                "status": s.status,
                "total_findings": s.total_findings,
                "critical_count": s.critical_count,
                "high_count": s.high_count,
                "medium_count": s.medium_count,
                "low_count": s.low_count,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            }
            for s in scans
        ],
        "total": total,
        "page": page,
        "limit": limit
    }


@app.get("/api/scans/{scan_id}/findings")
def get_findings(
    scan_id: int,
    severity: Optional[str] = None,
    agent: Optional[str] = None,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    query = db.query(Finding).filter(Finding.scan_id == scan_id)
    if severity:
        query = query.filter(Finding.severity == severity)
    if agent:
        query = query.filter(Finding.agent == agent)
    findings = query.order_by(Finding.severity).all()
    return [
        {
            "id": f.id,
            "agent": f.agent,
            "rule_id": f.rule_id,
            "title": f.title,
            "description": f.description,
            "severity": f.severity,
            "file_path": f.file_path,
            "line_start": f.line_start,
            "code_snippet": f.code_snippet,
            "fix_suggestion": f.fix_suggestion,
            "ai_explanation": f.ai_explanation,
            "cwe_id": f.cwe_id,
        }
        for f in findings
    ]


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db), _: dict = Depends(get_current_user)):
    total_scans = db.query(func.count(Scan.id)).scalar()
    total_findings = db.query(func.sum(Scan.total_findings)).scalar() or 0
    critical_findings = db.query(func.sum(Scan.critical_count)).scalar() or 0
    recent_scans = (
        db.query(Scan)
        .order_by(desc(Scan.started_at))
        .limit(7).all()
    )
    trend = [
        {
            "date": s.started_at.strftime("%m/%d") if s.started_at else "",
            "findings": s.total_findings or 0,
            "critical": s.critical_count or 0,
        }
        for s in reversed(recent_scans)
    ]
    repos_scanned = db.query(func.count(Repository.id)).scalar()

    return {
        "total_scans": total_scans,
        "total_findings": total_findings,
        "critical_findings": critical_findings,
        "repos_scanned": repos_scanned,
        "trend": trend
    }


class ManualScanRequest(BaseModel):
    repo_url: str
    branch: Optional[str] = "main"


@app.post("/api/scan/manual")
def manual_scan(
    req: ManualScanRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    repo_name = req.repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    owner = req.repo_url.rstrip("/").split("/")[-2] if "/" in req.repo_url else "unknown"
    full_name = f"{owner}/{repo_name}"

    repo = db.query(Repository).filter(Repository.full_name == full_name).first()
    if not repo:
        repo = Repository(
            github_repo_id=f"manual-{full_name}",
            full_name=full_name,
            owner=owner,
            name=repo_name,
            installation_id=""
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)

    scan = Scan(
        repo_id=repo.id,
        user_id=int(current_user["sub"]),
        pr_number=0,
        pr_title="Manual scan",
        commit_sha="manual",
        branch=req.branch,
        status=ScanStatusEnum.pending
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    run_scan_task.delay(
        scan_id=scan.id,
        repo_full_name=full_name,
        pr_number=0,
        commit_sha="manual",
        clone_url=req.repo_url,
        installation_id=""
    )

    return {"message": "Manual scan started", "scan_id": scan.id}


# ─── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws/{scan_id}")
async def websocket_endpoint(websocket: WebSocket, scan_id: int):
    await manager.connect(websocket, scan_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, scan_id)
