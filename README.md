# 🛡️ CodeSentinel — AI-Powered Multi-Agent Security Scanner

CodeSentinel is a full-stack security scanning platform that automatically analyzes code repositories for vulnerabilities using a multi-agent AI pipeline. It combines static analysis tools, secrets detection, dependency auditing, and a local LLM to generate human-readable explanations and fix suggestions — all displayed on a real-time React dashboard.

---

## 🚀 What It Does

- Scans any public GitHub repository for security vulnerabilities
- Runs multiple specialized AI agents in parallel to detect different types of issues
- Uses LLaMA 3 running locally via Ollama to explain each vulnerability and suggest fixes
- Streams real-time scan progress to the dashboard via WebSockets
- Stores all results in PostgreSQL and visualizes trends with interactive charts

---

## 🤖 How the Agent Pipeline Works

Manual Scan triggers FastAPI backend, which enqueues a Celery task via Redis. The LangGraph Orchestrator runs three agents in parallel: SAST Agent (Semgrep + Bandit), Secrets Agent (detect-secrets), and Deps Agent (Safety + npm audit). Results are aggregated, deduplicated, and passed to the Fix Agent which calls LLaMA 3 via Ollama to generate AI explanations and fix suggestions. Final results are saved to PostgreSQL and broadcast to the React dashboard via WebSockets.

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| AI Orchestration | LangGraph, LangChain |
| Local LLM | LLaMA 3 8B via Ollama |
| SAST Scanning | Semgrep, Bandit |
| Secrets Detection | detect-secrets, pattern matching |
| Dependency Audit | Safety, npm audit |
| Backend | FastAPI, Python 3.11 |
| Task Queue | Celery + Redis |
| Database | PostgreSQL + SQLAlchemy |
| Real-time | WebSockets |
| Authentication | JWT with bcrypt |
| Frontend | React 18, Recharts, Lucide Icons |
| Automation | n8n workflows |
| CI/CD | GitHub Actions |
| Infrastructure | Docker + Docker Compose |

---

## ⚙️ Prerequisites

- Docker Desktop: https://www.docker.com/products/docker-desktop
- Ollama: https://ollama.ai
- Node.js 20+: https://nodejs.org

---

## 🛠️ Installation and Setup

### 1. Clone the repository

git clone https://github.com/VaishnaviP600/codesentinel.git
cd codesentinel

### 2. Configure environment

cp .env.example .env

Open .env and generate a strong JWT secret:

python -c "import secrets; print(secrets.token_hex(32))"

Copy the output and replace the JWT_SECRET value in .env

### 3. Download LLaMA 3 (one time only, around 4.7 GB)

ollama pull llama3
ollama serve

Leave this terminal open and open a new terminal for the next step.

### 4. Start all services

docker compose up --build

Wait until you see:
backend    | INFO: Application startup complete.
celery_worker | ready.

### 5. Open the dashboard

http://localhost:3000

Register an account and start scanning.

---

## 🔍 Running a Scan

1. Click + Manual Scan on the dashboard
2. Enter any public GitHub repository URL, for example: https://github.com/mpirnat/lets-be-bad-guys
3. Click Start Scan
4. Watch real-time progress as the status updates automatically
5. Click View to see all findings with AI-generated explanations and fix suggestions

---

## 📁 Project Structure

codesentinel/
├── backend/
│   ├── agents/
│   │   ├── orchestrator.py      - Multi-agent coordinator using asyncio
│   │   ├── sast_agent.py        - Semgrep and Bandit static analysis
│   │   ├── secrets_agent.py     - Secrets and credentials detection
│   │   ├── deps_agent.py        - Dependency vulnerability scanning
│   │   └── fix_agent.py         - LLaMA 3 AI explanation and fix generation
│   ├── core/
│   │   ├── auth.py              - JWT authentication
│   │   ├── github_client.py     - GitHub App integration
│   │   └── websocket_manager.py - Real-time WebSocket broadcasting
│   ├── db/
│   │   └── models.py            - SQLAlchemy ORM models
│   ├── tasks/
│   │   └── scan_tasks.py        - Celery async scan pipeline
│   ├── celery_app.py            - Celery app instance
│   ├── main.py                  - FastAPI application and all routes
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/               - Dashboard and Login pages
│       ├── components/          - Findings drawer, Navbar, Modal
│       ├── hooks/               - Auth context and hooks
│       └── utils/               - Axios API client
├── n8n-workflows/               - Slack and email escalation workflow
├── .github/workflows/           - GitHub Actions CI pipeline
├── docker-compose.yml
└── .env.example

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | Register a new user |
| POST | /api/auth/login | Login and receive JWT token |
| GET | /api/scans | List all scans with pagination |
| GET | /api/scans/{id}/findings | Get findings for a specific scan |
| GET | /api/stats | Dashboard statistics and trend data |
| POST | /api/scan/manual | Trigger a manual repository scan |
| WS | /ws/{scan_id} | Real-time scan status updates |

Full interactive API docs are available at http://localhost:8000/docs

---

## 🛑 Stopping the Project

docker compose down

To also clear all stored data:

docker compose down -v

---

## 📄 License

MIT License - Vaishnavi Pujala
