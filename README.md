# 🛡️ CodeSentinel — AI-Powered Multi-Agent Security Scanner

> A production-grade security scanner that automatically reviews every GitHub Pull Request using a multi-agent AI pipeline powered by **LLaMA 3**, **LangGraph**, **Semgrep**, **Bandit**, **n8n**, and a real-time **React** dashboard.

---

## 🏗️ Architecture

```
GitHub PR Opened
      ↓
GitHub Webhook → FastAPI → Celery Task Queue (Redis)
                                    ↓
                         LangGraph Orchestrator
                        /          |           \
               SAST Agent    Secrets Agent   Deps Agent
              (Semgrep+       (detect-       (safety +
               Bandit)         secrets)      npm audit)
                        \          |           /
                         Aggregate & Deduplicate
                                    ↓
                           Fix Agent (LLaMA 3 via Ollama)
                           → AI Explanation + Fix Suggestion
                                    ↓
                    ┌───────────────┼───────────────┐
                    ↓               ↓               ↓
              GitHub PR         PostgreSQL      WebSocket
              Comment           (Store)      → React Dashboard
                                    ↓
                              n8n Workflow
                          (Slack + Email Alert)
```

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| **AI Agents** | LangGraph, LangChain |
| **Local LLM** | LLaMA 3 8B via Ollama |
| **SAST** | Semgrep, Bandit |
| **Secrets** | detect-secrets, pattern scan |
| **Deps** | Safety, npm audit |
| **Backend** | FastAPI, Python 3.11 |
| **Task Queue** | Celery + Redis |
| **Database** | PostgreSQL + SQLAlchemy |
| **Real-time** | WebSockets |
| **Auth** | JWT (PyJWT + bcrypt) |
| **Frontend** | React 18, Recharts, Lucide |
| **Automation** | n8n workflows |
| **CI/CD** | GitHub Actions |
| **Infra** | Docker + Docker Compose |

---

## ⚡ Prerequisites

Install these before starting:

| Tool | Install |
|---|---|
| Docker Desktop | https://www.docker.com/products/docker-desktop |
| Ollama | https://ollama.ai |
| Node.js 20+ | https://nodejs.org |
| Python 3.11+ | Already on your Mac via conda |

---

## 🚀 Quick Start (15 minutes)

### Step 1 — Clone & configure

```bash
git clone https://github.com/VaishnaviP600/codesentinel.git
cd codesentinel
cp .env.example .env
```

Edit `.env` and set a strong `JWT_SECRET`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
# Copy output into JWT_SECRET in .env
```

### Step 2 — Pull and start LLaMA 3 locally

```bash
# Install Ollama from https://ollama.ai first, then:
ollama pull llama3
ollama serve
# Ollama runs at http://localhost:11434
```

### Step 3 — Start all services with Docker Compose

```bash
docker compose up --build
```

This starts:
- **PostgreSQL** on port 5432
- **Redis** on port 6379
- **FastAPI backend** on port 8000
- **Celery worker** (background scan jobs)
- **React frontend** on port 3000

### Step 4 — Open the dashboard

Visit **http://localhost:3000**

Register an account → you're in!

---

## 🔧 Running Without Docker (Development)

### Backend

```bash
cd backend
conda create -n codesentinel python=3.11 -y
conda activate codesentinel
pip install -r requirements.txt

# Start PostgreSQL and Redis separately (or via Docker):
docker run -d -p 5432:5432 -e POSTGRES_USER=codesentinel -e POSTGRES_PASSWORD=codesentinel123 -e POSTGRES_DB=codesentinel postgres:15
docker run -d -p 6379:6379 redis:7-alpine

# Run backend
uvicorn main:app --reload --port 8000

# In a new terminal, run Celery worker
celery -A tasks.celery_app worker --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
npm start
# Opens at http://localhost:3000
```

---

## 🔫 Manual Scan (No GitHub App needed)

You don't need to configure a GitHub App to try the full pipeline. Use **Manual Scan** mode:

1. Open the dashboard → click **"+ Manual Scan"**
2. Enter any public GitHub repo URL, e.g.:
   ```
   https://github.com/juice-shop/juice-shop
   ```
3. Click **Start Scan** — watch the real-time progress via WebSocket
4. Click **View** on any scan to see AI-powered findings with fix suggestions

---

## 🤖 GitHub App Setup (For Automatic PR Scanning)

To have CodeSentinel auto-scan every PR:

### 1. Create a GitHub App

Go to: https://github.com/settings/apps/new

Settings:
- **Name:** CodeSentinel (your-username)
- **Homepage URL:** http://localhost:8000
- **Webhook URL:** Your public URL + `/webhook/github`
  - For local dev use: `npx smee -u $(npx smee --url) --path /webhook/github --port 8000`
- **Webhook secret:** Any random string → put in `.env` as `GITHUB_WEBHOOK_SECRET`
- **Permissions:**
  - Pull requests: Read & Write
  - Contents: Read
  - Checks: Read & Write
- **Subscribe to events:** Pull request

### 2. Generate a private key

On your GitHub App page → **Generate a private key** → download `.pem` file

```bash
# Convert to single line for .env
cat your-app.private-key.pem | tr '\n' '\\n'
# Paste output as GITHUB_PRIVATE_KEY in .env
```

### 3. Add credentials to .env

```
GITHUB_APP_ID=your_app_id
GITHUB_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----
GITHUB_WEBHOOK_SECRET=your_webhook_secret
```

### 4. Install the app on your repo

Go to your GitHub App → **Install App** → select your repo

Now every PR will trigger an automatic scan! ✅

---

## 🔁 n8n Automation Setup (Critical Finding Alerts)

### Install & run n8n

```bash
docker run -d --name n8n -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  n8nio/n8n
```

Open: http://localhost:5678

### Import the workflow

1. Open n8n → **Workflows** → **Import from File**
2. Select `n8n-workflows/critical-escalation.json`
3. Configure:
   - **Slack node:** Add your Slack webhook URL (from https://api.slack.com/apps)
   - **Email node:** Add SMTP credentials in n8n credentials
4. Activate the workflow

Now whenever a scan finds critical issues, n8n automatically sends Slack + email alerts! 🚨

---

## 🧪 Running Tests

```bash
cd backend
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

---

## 📁 Project Structure

```
codesentinel/
├── backend/
│   ├── agents/
│   │   ├── orchestrator.py     ← LangGraph multi-agent coordinator
│   │   ├── sast_agent.py       ← Semgrep + Bandit static analysis
│   │   ├── secrets_agent.py    ← detect-secrets + pattern scan
│   │   ├── deps_agent.py       ← Safety + npm audit
│   │   └── fix_agent.py        ← LLaMA 3 via Ollama AI enrichment
│   ├── api/
│   ├── core/
│   │   ├── auth.py             ← JWT authentication
│   │   ├── github_client.py    ← GitHub App integration
│   │   └── websocket_manager.py← Real-time WebSocket broadcasting
│   ├── db/
│   │   └── models.py           ← SQLAlchemy ORM models
│   ├── tasks/
│   │   └── scan_tasks.py       ← Celery async scan pipeline
│   ├── tests/
│   │   └── test_api.py
│   ├── main.py                 ← FastAPI app + all routes
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx   ← Main dashboard with charts
│   │   │   └── Login.jsx       ← Auth page
│   │   ├── components/
│   │   │   ├── FindingsDrawer.jsx ← Findings panel with live WS
│   │   │   ├── ManualScanModal.jsx
│   │   │   └── Navbar.jsx
│   │   ├── hooks/
│   │   │   └── useAuth.js      ← Auth context + hook
│   │   └── utils/
│   │       └── api.js          ← Axios API client
│   ├── package.json
│   └── Dockerfile
├── n8n-workflows/
│   └── critical-escalation.json ← n8n Slack/email automation
├── .github/
│   └── workflows/
│       └── ci.yml              ← GitHub Actions CI pipeline
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🎯 What This Demonstrates (For Interviews)

| Concept | Where |
|---|---|
| Multi-agent design (LangGraph) | `agents/orchestrator.py` |
| Local LLM inference (Ollama/LLaMA 3) | `agents/fix_agent.py` |
| Event-driven architecture | GitHub webhook → Celery |
| Async task processing | `tasks/scan_tasks.py` |
| Real-time WebSocket streaming | `core/websocket_manager.py` |
| GitHub App integration | `core/github_client.py` |
| SAST pipeline chaining | `agents/sast_agent.py` |
| JWT authentication | `core/auth.py` |
| Docker Compose orchestration | `docker-compose.yml` |
| n8n automation workflow | `n8n-workflows/` |
| CI/CD pipeline | `.github/workflows/ci.yml` |
| React + Recharts dashboard | `frontend/src/` |

---

## 💡 Tips

- **Ollama must be running** before starting Docker services (it runs on the host, not in Docker)
- Use `docker compose logs -f celery_worker` to watch scan jobs in real time
- The `juice-shop` repo is a great test target — it's intentionally vulnerable
- Add `OLLAMA_URL=http://host.docker.internal:11434` if Ollama isn't reachable from Docker

---

## 📄 License

MIT — built by Vaishnavi Pujala
