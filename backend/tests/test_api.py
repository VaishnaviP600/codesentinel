"""
Basic tests for CodeSentinel API.
Run with: pytest tests/ -v
"""

import pytest
from fastapi.testclient import TestClient
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Mock environment before importing app
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test-secret")

from main import app

client = TestClient(app)


def test_root_redirect():
    """API should be reachable."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_register_and_login():
    """User registration and login should return a JWT."""
    # Register
    reg = client.post("/api/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123"
    })
    assert reg.status_code == 200
    assert "access_token" in reg.json()

    # Login
    login = client.post("/api/auth/login", data={
        "username": "testuser",
        "password": "testpass123"
    })
    assert login.status_code == 200
    assert "access_token" in login.json()


def test_protected_route_without_token():
    """Stats endpoint should require auth."""
    response = client.get("/api/stats")
    assert response.status_code == 401


def test_webhook_invalid_signature():
    """Webhook with wrong signature should be rejected when secret is set."""
    os.environ["GITHUB_WEBHOOK_SECRET"] = "mysecret"
    response = client.post(
        "/webhook/github",
        json={"action": "opened"},
        headers={"X-Hub-Signature-256": "sha256=invalidsig", "X-GitHub-Event": "pull_request"}
    )
    assert response.status_code == 401
    del os.environ["GITHUB_WEBHOOK_SECRET"]
