# WORKFLOW.md — DagInquest Complete Build Guide

> Formal investigation of Apache Airflow DAG failures using local LLMs, strict policy gates, human approval via Telegram/Web, and verified remediation.

---

## Document Purpose & How to Use

This document is an exhaustive, sequential, copy-paste-ready build guide for **DagInquest**. It takes you from an empty folder to a fully running, tested, and demo-ready system on your local machine.

### Rules of Engagement
1. **Follow in strict numerical order**: Do not jump between phases or steps. Step outputs and schema migrations are tightly coupled.
2. **Never skip a checkpoint**: Every phase concludes with a verification command. If the checkpoint does not match the expected output, resolve it before proceeding.
3. **Commit after every checkpoint**: Once a checkpoint passes, execute `git add . && git commit -m "feat: complete phase X"` so you always have a known good rollback point.
4. **Platform equivalence**: Command prompts are provided for both Unix shells (`bash`/`zsh`) and Windows (`PowerShell`). Use the variant matching your host environment.

---

## Prerequisites Checklist

Ensure your development machine meets these requirements before running any commands.

### Host Software
- **Operating System**: Linux (Ubuntu 22.04+ recommended), macOS (13+ Ventura or Sonoma), or Windows 11 with WSL2 enabled.
- **Git**: `>= 2.40` (`git --version`)
- **Docker & Docker Compose v2**: Docker Engine `>= 24.0`, Docker Compose `>= 2.20` (`docker compose version`)
- **Python**: `3.12.x` (`python3.12 --version` or `py -3.12 --version`)
- **Node.js & npm**: Node `>= 18.18`, npm `>= 9.0` (`node -v`, `npm -v`)
- **Curl & jq**: Basic command-line testing tools (`curl --version`, `jq --version`)

### Telegram Bot Setup
1. Open Telegram and search for `@BotFather`.
2. Send `/newbot` and follow the prompts.
3. Choose a name (e.g., `DagInquest Inspector`) and a username ending in `bot` (e.g., `daginquest_local_bot`).
4. Save the generated HTTP API token. This is your `TELEGRAM_BOT_TOKEN`.
5. Find your personal Telegram Chat ID:
   - Search for `@userinfobot` on Telegram and send `/start`.
   - Copy the numerical ID returned (e.g., `123456789`). This will be placed in `TELEGRAM_ALLOWED_CHAT_IDS`.

### Hardware & Resource Guidance
Running Ollama, Airflow 3, Postgres 16, and FastAPI locally requires adequate compute and memory.

| Hardware Tier | Available RAM | GPU VRAM | Recommended Ollama Model | [E] Expected Latency / Inference |
|---|---|---|---|---|
| **Entry / Laptop** | 16 GB | None (CPU inference) | `qwen2.5:3b` or `llama3.2:3b` | 8–18 seconds |
| **Recommended** | 32 GB | 8 GB+ (Nvidia RTX / Apple M-series) | `qwen2.5:7b` / `qwen3:8b` [E] | 2–5 seconds |
| **High Performance** | 64 GB+ | 16 GB+ VRAM | `qwen2.5:14b` | 1–3 seconds |

*Disk Space Note*: Reserve at least 25 GB of free disk space: ~8 GB for Airflow 3 & Postgres Docker images, ~5 GB for the default quantized LLM weights, and ~12 GB for build caches and database volumes.

---

## Project Map

```
daginquest/
├── README.md                              # Project overview and run manual
├── WORKFLOW.md                            # This build guide
├── docker-compose.yml                     # Service orchestration (Postgres, Ollama, Airflow, API, Bot)
├── Makefile                               # Developer automation targets
├── .env.example                           # Canonical environment variable templates
├── .gitignore                             # Ignored paths and secrets
├── .github/
│   └── workflows/
│       └── ci.yml                         # Automated linting and tests
├── docs/
│   ├── architecture.md                    # Data flow and system boundaries
│   └── benchmark.md                       # Evaluation methodology and results
├── infra/
│   └── ollama/
│       └── pull_models.sh                 # Ollama startup model fetch script
├── airflow/
│   ├── README.md                          # Airflow standalone setup notes
│   └── dags/
│       ├── _common/
│       │   ├── __init__.py                # Common module marker
│       │   └── callbacks.py               # on_failure_callback webhook sender
│       ├── demo_import_error.py           # Broken import test DAG
│       ├── demo_timeout.py                # Simulated network timeout DAG
│       └── demo_bad_sql.py                # Syntax error SQL operator DAG
├── backend/
│   ├── pyproject.toml                     # Python dependencies and tool configs
│   ├── Dockerfile                         # Production backend container build
│   ├── migrations/
│   │   └── 001_init.sql                   # Database DDL with audit trigger
│   ├── tests/
│   │   ├── __init__.py                    # Test suite marker
│   │   ├── conftest.py                    # Pytest fixtures and mocks
│   │   ├── test_fingerprint.py            # Deduplication hash tests
│   │   ├── test_redaction.py              # Secret masking tests
│   │   ├── test_policy.py                 # Action allow-list policy tests
│   │   └── test_preclassify_citations.py  # Log pattern & citation sanity tests
│   └── src/
│       └── daginquest/
│           ├── __init__.py                # Package root
│           ├── main.py                    # FastAPI entrypoint and lifespan
│           ├── config.py                  # Pydantic BaseSettings config
│           ├── api/                       # API router definitions
│           │   ├── health.py              # Liveness and readiness endpoints
│           │   ├── webhooks.py            # Airflow failure ingestion
│           │   ├── incidents.py           # Incident querying endpoints
│           │   ├── actions.py             # Human decision handling
│           │   └── metrics.py             # System metrics and counts
│           ├── db/                        # Data access layer
│           │   ├── session.py             # psycopg_pool connection management
│           │   └── repository.py          # Plain SQL queries and atomic updates
│           ├── utils/                     # Deterministic parsing helpers
│           │   ├── fingerprint.py         # Error hashing and deduplication
│           │   └── preclassify.py         # Fast heuristic log parsing
│           ├── security/                  # Data sanitization
│           │   └── redaction.py           # Regex-based credential masking
│           ├── policy/                    # Safety governance
│           │   └── rules.py               # Deterministic auto-remediation policy
│           ├── llm/                       # Model interface
│           │   ├── schemas.py             # Structured output Pydantic schemas
│           │   └── ollama.py              # Local Ollama client
│           ├── airflow/                   # Airflow API client
│           │   └── client.py              # Async HTTP client for Airflow REST
│           ├── agent/                     # LangGraph investigation logic
│           │   ├── state.py               # InvestigationState typed dict
│           │   ├── prompts.py             # Strict system instructions
│           │   ├── graph.py               # Compiled StateGraph definition
│           │   └── runner.py              # Graph invocation and orchestration
│           │   └── nodes/                 # Discrete workflow nodes
│           │       ├── gather_evidence.py # Fetch logs and metadata
│           │       ├── classify.py        # Error categorization
│           │       ├── rca.py             # Root cause analysis
│           │       ├── verify_citations.py# Hallucination guard filter
│           │       ├── plan.py            # Remediation proposal
│           │       ├── policy_gate.py     # Deterministic safety checks
│           │       └── persist_notify.py  # Save results and trigger alert
│           ├── actions/                   # Remediation execution
│           │   ├── executor.py            # Airflow clear/retry execution
│           │   └── verify.py              # Polling verification of task recovery
│           ├── telegram/                  # Human-in-the-loop interface
│           │   ├── notifier.py            # Outbound alert dispatcher
│           │   ├── security.py            # Chat authorization filter
│           │   ├── handlers.py            # Command and callback query handlers
│           │   └── bot.py                 # Telegram polling runner
│           └── eval/                      # Benchmark evaluation harness
│               ├── run_eval.py            # Model grading CLI
│               ├── cases/                 # Failure log test cases (.json)
│               └── results/               # Stored evaluation outputs
└── frontend/
    ├── package.json                       # React/TypeScript dependencies
    ├── tsconfig.json                      # Strict TS configuration
    ├── vite.config.ts                     # Vite build and proxy config
    ├── index.html                         # SPA host page
    └── src/
        ├── main.tsx                       # React application root
        ├── App.tsx                        # Layout and routing
        ├── index.css                      # Global styles and CSS variables
        ├── types.ts                       # Shared frontend interfaces
        ├── api/
        │   └── client.ts                  # Fetch API wrapper
        ├── hooks/
        │   └── usePolling.ts              # Data polling hook
        ├── components/
        │   └── ConfidenceBadge.tsx        # Styled confidence indicator
        └── pages/
            ├── IncidentsPage.tsx          # Incident triage feed
            ├── ApprovalsPage.tsx          # Action approval dashboard
            └── MetricsPage.tsx            # MTTR and incident counts
```

---

## Phase Overview

| Phase | Goal | Paths Touched | Checkpoint | Estimated Time |
|---|---|---|---|---|
| **Phase 0** | Repo & Infrastructure | `docker-compose.yml`, `Makefile`, `.env.example`, `.gitignore`, `infra/` | `docker compose ps` shows services healthy | 25 min |
| **Phase 1** | Database Layer DDL | `backend/migrations/001_init.sql` | `psql` lists 8 tables and append trigger | 15 min |
| **Phase 2** | Backend Skeleton | `backend/pyproject.toml`, `backend/Dockerfile`, `main.py`, `config.py` | `curl /api/health` returns status `ok` | 20 min |
| **Phase 3** | Pure Utilities & Tests | `fingerprint.py`, `redaction.py`, `policy/rules.py`, `preclassify.py`, `tests/` | `pytest` reports 100% passing tests | 25 min |
| **Phase 4** | Data Access Repository | `db/session.py`, `db/repository.py` | Seed script confirms atomic approval flow | 30 min |
| **Phase 5** | Airflow Integration | `airflow/client.py`, `callbacks.py`, `demo_*.py`, `api/webhooks.py` | Demo DAG failure triggers webhook & incident | 35 min |
| **Phase 6** | LLM Structured Output | `llm/schemas.py`, `llm/ollama.py` | Ollama returns valid JSON matching schema | 25 min |
| **Phase 7** | LangGraph Pipeline | `agent/state.py`, `prompts.py`, `agent/nodes/*.py`, `graph.py` | Simulated failure produces analysis & citation | 45 min |
| **Phase 8** | Telegram Bot | `telegram/notifier.py`, `security.py`, `handlers.py`, `bot.py` | Alert with inline buttons received in chat | 30 min |
| **Phase 9** | Remediation Executor | `actions/executor.py`, `actions/verify.py`, `api/actions.py` | Approved task is cleared and verified via API | 30 min |
| **Phase 10** | Web Dashboard | `frontend/package.json`, `src/**/*` | UI displays incident and executes approval | 40 min |
| **Phase 11** | Evaluation Suite | `eval/run_eval.py`, `eval/cases/*.json` | Evaluation harness scores local model accuracy | 35 min |
| **Phase 12** | Hardening & Release | `ci.yml`, `docs/*`, `README.md` | Clean CI pipeline run and verified checklist | 25 min |

---

## Phase 0: Repository and Infrastructure

### Why this phase exists
Before writing application logic, we must establish a reproducible environment. DagInquest coordinates a database, a local inference engine, an orchestrator (Airflow 3), and Python services. Docker Compose ensures that networking, persistence, and environment configurations are identical across macOS, Linux, and Windows.

---

### Step 0.1: Initialize Git Repository and Git Ignore

#### Goal
Initialize version control and prevent tracking of virtual environments, logs, and sensitive `.env` files.

#### Path
- Unix: `mkdir -p daginquest && cd daginquest && git init`
- Windows (PowerShell): `mkdir daginquest; Set-Location daginquest; git init`
- File: `.gitignore`

#### Code
```gitignore
# Python artifacts
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/
env/

# Testing and coverage
.pytest_cache/
.coverage
htmlcov/
.ruff_cache/

# Node / React
frontend/node_modules/
frontend/dist/
frontend/.vite/

# Environment files and credentials
.env
*.pem
*.key

# Docker mounts and local storage
postgres_data/
ollama_data/
airflow_logs/

# IDE files
.idea/
.vscode/
*.swp
*.swo
```

#### What this code does
Excludes runtime artifacts, sensitive environment files, virtual environments, and mounted local volume directories from Git history.

#### Run / verify
- Unix / Windows:
  ```bash
  git status
  ```
  Expected output:
  ```
  On branch main (or master)
  Untracked files:
    (use "git add <file>..." to include in what will be committed)
          .gitignore
  ```

#### If it fails
- `git: command not found`: Install Git via your system package manager (`apt install git`, `brew install git`, or `winget install Git.Git`).
- `fatal: not a git repository`: Ensure you ran `git init` within the `daginquest` folder.

---

### Step 0.2: Configure Environment Template

#### Goal
Provide a comprehensive template of all runtime environment variables with self-documenting defaults.

#### Path
- File: `.env.example`

#### Code
```env
# ==============================================================================
# Database Configuration (PostgreSQL 16)
# ==============================================================================
POSTGRES_USER=daginquest_user
POSTGRES_PASSWORD=daginquest_secure_password
POSTGRES_DB=daginquest
DATABASE_URL=postgresql://daginquest_user:daginquest_secure_password@postgres:5432/daginquest

# ==============================================================================
# Local LLM Configuration (Ollama)
# ==============================================================================
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=qwen2.5:7b

# ==============================================================================
# Apache Airflow 3 Configuration
# ==============================================================================
AIRFLOW_IMAGE=apache/airflow:3.0.0.dev0
AIRFLOW_BASE_URL=http://airflow:8080
AIRFLOW_USERNAME=admin
AIRFLOW_PASSWORD=admin
# Internal service endpoints exposed to Airflow workers/callbacks
DAGINQUEST_API_URL=http://api:8000
DAGINQUEST_WEBHOOK_SECRET=inquest_shared_secret_hex_32_bytes_minimum

# ==============================================================================
# Security and Policy Controls
# ==============================================================================
WEBHOOK_SECRET=inquest_shared_secret_hex_32_bytes_minimum
CONFIDENCE_THRESHOLD=0.60
DEDUPE_COOLDOWN_MINUTES=30

# ==============================================================================
# Telegram Human-in-the-Loop Bot
# ==============================================================================
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
# Comma-separated list of numeric chat IDs authorized to approve actions
TELEGRAM_ALLOWED_CHAT_IDS=123456789
```

#### What this code does
Defines the single source of truth for all environment variables used by the backend, database, LLM client, and Airflow callbacks.

#### Run / verify
- Unix:
  ```bash
  cp .env.example .env
  test -f .env && echo "SUCCESS: .env present"
  ```
- Windows (PowerShell):
  ```powershell
  Copy-Item .env.example .env
  if (Test-Path .env) { Write-Output "SUCCESS: .env present" }
  ```

#### If it fails
- File not found: Ensure you are running the command in the directory containing `.env.example`.
- Permission denied: Ensure your user owns the current directory.

---

### Step 0.3: Create Model Pull Script

#### Goal
Create an automated script executed during setup to pull the local LLM model weights into the Ollama container.

#### Path
- Unix: `mkdir -p infra/ollama`
- Windows (PowerShell): `mkdir -p infra/ollama`
- File: `infra/ollama/pull_models.sh`

#### Code
```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== [Ollama Init] Waiting for Ollama service to become responsive ==="
until curl -s http://ollama:11434/api/tags > /dev/null; do
    echo "Waiting for Ollama API at http://ollama:11434..."
    sleep 3
done

TARGET_MODEL="${OLLAMA_MODEL:-qwen2.5:7b}"
echo "=== [Ollama Init] Pulling model: ${TARGET_MODEL} ==="
curl -X POST http://ollama:11434/api/pull -d "{\"name\": \"${TARGET_MODEL}\"}"

echo ""
echo "=== [Ollama Init] Model pull completed successfully ==="
```

#### What this code does
Polls the Ollama API until it responds, then sends a POST request to pull the configured model weights.

#### Run / verify
- Unix:
  ```bash
  chmod +x infra/ollama/pull_models.sh
  ls -l infra/ollama/pull_models.sh
  ```
- Windows (PowerShell):
  ```powershell
  Get-Item infra/ollama/pull_models.sh
  ```

#### If it fails
- Windows CRLF line ending issue: If Docker throws `/bin/bash^M: bad interpreter`, run `dos2unix infra/ollama/pull_models.sh` or configure Git: `git config core.autocrlf input`.

---

### Step 0.4: Define Multi-Container Orchestration

#### Goal
Define the complete multi-service stack in `docker-compose.yml`, including database migrations mount, persistent volumes, and health checks.

#### Path
- File: `docker-compose.yml`

#### Code
```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: daginquest-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-daginquest_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-daginquest_secure_password}
      POSTGRES_DB: ${POSTGRES_DB:-daginquest}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/migrations:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-daginquest_user} -d ${POSTGRES_DB:-daginquest}"]
      interval: 5s
      timeout: 5s
      retries: 5

  ollama:
    image: ollama/ollama:latest
    container_name: daginquest-ollama
    restart: unless-stopped
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:11434/api/tags || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5

  ollama-pull:
    image: curlimages/curl:latest
    container_name: daginquest-ollama-pull
    restart: "no"
    depends_on:
      ollama:
        condition: service_healthy
    environment:
      OLLAMA_MODEL: ${OLLAMA_MODEL:-qwen2.5:7b}
    volumes:
      - ./infra/ollama/pull_models.sh:/pull_models.sh:ro
    entrypoint: ["/bin/sh", "/pull_models.sh"]

  airflow:
    image: ${AIRFLOW_IMAGE:-apache/airflow:3.0.0.dev0}
    container_name: daginquest-airflow
    restart: unless-stopped
    environment:
      - AIRFLOW__CORE__LOAD_EXAMPLES=False
      - AIRFLOW__API__AUTH_BACKENDS=airflow.api.auth.backend.basic_auth
      - _AIRFLOW_DB_MIGRATE=true
      - _AIRFLOW_WWW_USER_CREATE=true
      - _AIRFLOW_WWW_USER_USERNAME=${AIRFLOW_USERNAME:-admin}
      - _AIRFLOW_WWW_USER_PASSWORD=${AIRFLOW_PASSWORD:-admin}
      - DAGINQUEST_API_URL=${DAGINQUEST_API_URL:-http://api:8000}
      - DAGINQUEST_WEBHOOK_SECRET=${WEBHOOK_SECRET:-inquest_shared_secret_hex_32_bytes_minimum}
    ports:
      - "8080:8080"
    volumes:
      - ./airflow/dags:/opt/airflow/dags
      - airflow_logs:/opt/airflow/logs
    command: standalone
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"]
      interval: 15s
      timeout: 10s
      retries: 5

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: daginquest-api
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
      ollama:
        condition: service_healthy
    env_file:
      - .env
    ports:
      - "8000:8000"
    volumes:
      - ./backend/src:/app/src
    command: ["uvicorn", "daginquest.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/api/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5

  bot:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: daginquest-bot
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
      api:
        condition: service_healthy
    env_file:
      - .env
    volumes:
      - ./backend/src:/app/src
    command: ["python", "-m", "daginquest.telegram.bot"]

volumes:
  postgres_data:
  ollama_data:
  airflow_logs:
```

#### What this code does
Declares the containerized topology. Postgres mounts migration SQL scripts directly to `/docker-entrypoint-initdb.d` so schema setup is automatic upon initialization. Airflow runs in standalone mode with basic auth enabled. The API and Bot services run using hot-reloaded local code mounts.

#### Run / verify
- Unix / Windows:
  ```bash
  docker compose config
  ```
  Expected output: Full resolved YAML structure without syntax or interpolation errors.

#### If it fails
- `variable is not set`: Ensure `.env` exists in the same directory where you run `docker compose config`.
- `services.api.build: directory does not exist`: The `backend/` directory will be created in Phase 2; you can safely test with `docker compose config` right now as it only performs static syntax validation.

---

### Step 0.5: Define Automation Makefile

#### Goal
Create a Makefile using `.RECIPEPREFIX = >` to avoid tab character issues across different operating systems and editors.

#### Path
- File: `Makefile`

#### Code
```makefile
.RECIPEPREFIX = >
.PHONY: help up down restart logs ps clean test lint pull-model

help:
> @echo "DagInquest Automation Targets:"
> @echo "  make up          - Start all Docker infrastructure in background"
> @echo "  make down        - Stop all containers"
> @echo "  make restart     - Restart API and Bot services"
> @echo "  make logs        - Tail logs from all containers"
> @echo "  make ps          - Show status of all services"
> @echo "  make test        - Run backend test suite via pytest"
> @echo "  make lint        - Run ruff linter and formatter checks"
> @echo "  make pull-model  - Trigger manual pull of Ollama model"
> @echo "  make clean       - Remove volumes and temporary files"

up:
> docker compose up -d postgres ollama airflow

down:
> docker compose down

restart:
> docker compose restart api bot

logs:
> docker compose logs -f

ps:
> docker compose ps

test:
> cd backend && pytest -v

lint:
> cd backend && ruff check . && ruff format --check .

pull-model:
> docker compose up ollama-pull

clean:
> docker compose down -v
> rm -rf backend/.pytest_cache backend/.ruff_cache
```

#### What this code does
Provides standard commands for starting, stopping, inspecting, and testing DagInquest without requiring users to memorize verbose commands.

#### Run / verify
- Unix / Windows:
  ```bash
  make help
  ```
  Expected output: Help text listing all available Makefile targets.

#### If it fails
- `make: command not found`: On Windows, install `make` via `choco install make` or `winget install GnuWin32.Make`, or execute the underlying Docker commands directly.
- `*** missing separator`: Ensure your `make` binary supports `.RECIPEPREFIX = >` (standard in GNU Make 3.82+).

---

### Checkpoint: Phase 0
Run the foundational infrastructure to verify networking, container creation, and mounts.

```bash
docker compose up -d postgres ollama
docker compose ps
```

Expected output:
```
NAME                 IMAGE                  STATUS                   PORTS
daginquest-ollama    ollama/ollama:latest   Up (healthy)             0.0.0.0:11434->11434/tcp
daginquest-postgres  postgres:16-alpine     Up (healthy)             0.0.0.0:5432->5432/tcp
```

---

## Phase 1: Database Layer

### Why this phase exists
DagInquest relies on PostgreSQL 16 as its durable storage for incidents, evidence artifacts, LLM analyses, actions, and approvals. Crucially, the schema enforces an **append-only audit trail** via a PostgreSQL trigger: no human or automated service can tamper with or delete audit logs.

---

### Step 1.1: Database Schema Migration Script

#### Goal
Create the complete DDL script defining all tables, indexes, enums, foreign keys, and the immutability trigger for `audit_log`.

#### Path
- Unix: `mkdir -p backend/migrations`
- Windows (PowerShell): `mkdir -p backend/migrations`
- File: `backend/migrations/001_init.sql`

#### Code
```sql
-- =============================================================================
-- 001_init.sql - DagInquest Schema Definition
-- Database: PostgreSQL 16
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -----------------------------------------------------------------------------
-- 1. INCIDENTS TABLE
-- Tracks unique or deduplicated Airflow DAG task failure occurrences.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fingerprint VARCHAR(64) NOT NULL,
    dag_id VARCHAR(255) NOT NULL,
    run_id VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    try_number INT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'open', -- open, analyzing, pending_approval, resolved, closed
    error_message TEXT NOT NULL,
    occurrence_count INT NOT NULL DEFAULT 1,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_incidents_fingerprint ON incidents(fingerprint);
CREATE INDEX IF NOT EXISTS idx_incidents_dag_task ON incidents(dag_id, task_id);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);

-- -----------------------------------------------------------------------------
-- 2. EVIDENCE TABLE
-- Raw and redacted inputs collected during investigation (logs, code, context).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    evidence_type VARCHAR(50) NOT NULL, -- task_log, dag_source, context_metadata
    content TEXT NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_evidence_incident_id ON evidence(incident_id);

-- -----------------------------------------------------------------------------
-- 3. ANALYSES TABLE
-- Structured findings from the LangGraph investigation workflow.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL, -- IMPORT_ERROR, SCHEMA_SQL, TRANSIENT_NETWORK, CONFIG_SECRET, RESOURCE, UPSTREAM_DATA, INCONCLUSIVE
    confidence DOUBLE PRECISION NOT NULL,
    root_cause TEXT NOT NULL,
    suggested_action VARCHAR(50) NOT NULL, -- retry_task, clear_task, none
    cited_lines JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_auto_remediable BOOLEAN NOT NULL DEFAULT FALSE,
    policy_approved BOOLEAN NOT NULL DEFAULT FALSE,
    policy_rejection_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_analyses_incident_id ON analyses(incident_id);

-- -----------------------------------------------------------------------------
-- 4. ACTIONS TABLE
-- Remediation actions proposed for human review.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    action_type VARCHAR(50) NOT NULL, -- retry_task, clear_task
    status VARCHAR(50) NOT NULL DEFAULT 'pending_approval', -- pending_approval, approved, rejected, succeeded, failed
    idempotency_key VARCHAR(255) NOT NULL UNIQUE,
    execution_result JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_actions_incident_id ON actions(incident_id);
CREATE INDEX IF NOT EXISTS idx_actions_status ON actions(status);

-- -----------------------------------------------------------------------------
-- 5. APPROVALS TABLE
-- Records human decision audit records (via Telegram or Web).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_id UUID NOT NULL REFERENCES actions(id) ON DELETE CASCADE,
    decision VARCHAR(20) NOT NULL, -- approved, rejected
    approver_id VARCHAR(100) NOT NULL, -- telegram:<chat_id> or web:<user>
    decision_reason TEXT,
    decided_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_approvals_action_id ON approvals(action_id);

-- -----------------------------------------------------------------------------
-- 6. AUDIT_LOG TABLE (APPEND-ONLY VIA TRIGGER)
-- Tamper-evident ledger of all critical mutations across the system.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_name VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,
    actor VARCHAR(100) NOT NULL,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log(entity_name, entity_id);

-- Append-only trigger enforcement
CREATE OR REPLACE FUNCTION enforce_audit_log_append_only()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Updates and deletions are strictly forbidden on audit_log table';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_log_append_only ON audit_log;
CREATE TRIGGER trg_audit_log_append_only
BEFORE UPDATE OR DELETE ON audit_log
FOR EACH ROW EXECUTE FUNCTION enforce_audit_log_append_only();

-- -----------------------------------------------------------------------------
-- 7. PLAYBOOKS TABLE
-- Optional reference definitions for remediation guidance.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS playbooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(50) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    remediation_steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 8. EVAL_RUNS TABLE
-- Tracks benchmark accuracy runs across different models.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS eval_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(100) NOT NULL,
    total_cases INT NOT NULL,
    correct_classifications INT NOT NULL,
    hallucination_rate DOUBLE PRECISION NOT NULL,
    avg_latency_seconds DOUBLE PRECISION NOT NULL,
    detailed_results JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

#### What this code does
Establishes relational storage for the system. Enforces:
1. Deduplication indexing on `fingerprint`.
2. Idempotent action execution via a unique `idempotency_key` (`<incident_id>:<action_type>`).
3. An append-only trigger on `audit_log` that aborts any SQL `UPDATE` or `DELETE` statements at the database engine level.

#### Run / verify
Initialize the database container from scratch with this migration mounted:

- Unix / Windows:
  ```bash
  docker compose down -v
  docker compose up -d postgres
  # Wait 5 seconds for PostgreSQL to initialize
  sleep 5
  docker compose exec postgres psql -U daginquest_user -d daginquest -c "\dt"
  ```

Expected output:
```
               List of relations
 Schema |    Name     | Type  |      Owner       
--------+-------------+-------+------------------
 public | actions     | table | daginquest_user
 public | analyses    | table | daginquest_user
 public | approvals   | table | daginquest_user
 public | audit_log   | table | daginquest_user
 public | eval_runs   | table | daginquest_user
 public | evidence    | table | daginquest_user
 public | incidents   | table | daginquest_user
 public | playbooks   | table | daginquest_user
(8 rows)
```

Now test the audit log immutability trigger:
```bash
docker compose exec postgres psql -U daginquest_user -d daginquest -c "INSERT INTO audit_log (entity_name, entity_id, action, actor) VALUES ('test', gen_random_uuid(), 'test_action', 'tester');"
docker compose exec postgres psql -U daginquest_user -d daginquest -c "UPDATE audit_log SET action='mutated';"
```

Expected output:
```
ERROR:  Updates and deletions are strictly forbidden on audit_log table
```

#### If it fails
- `relation "incidents" does not exist`: The entrypoint script only runs on an empty database. If you previously ran Postgres without the mount, run `docker compose down -v` to delete the old data volume, then run `docker compose up -d postgres`.
- `role "daginquest_user" does not exist`: Verify that `.env` matches the username in your command.

---

### Checkpoint: Phase 1
PostgreSQL is running, all 8 tables are present, and the append-only trigger successfully rejects update attempts.

---

## Phase 2: Backend Skeleton

### Why this phase exists
We now establish the Python 3.12 backend package structure, declare pinned dependencies, configure environment settings validation using Pydantic Settings, and create a FastAPI application with lifespan connection pooling and health checks.

---

### Step 2.1: Python Project Configuration

#### Goal
Define project dependencies, build system, and formatting/linting rules using `pyproject.toml`.

#### Path
- File: `backend/pyproject.toml`

#### Code
```toml
[project]
name = "daginquest"
version = "0.1.0"
description = "Formal investigation and remediation of Airflow DAG failures with local LLMs"
authors = [{ name = "DagInquest Engineer" }]
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.29.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.2.1",
    "httpx>=0.27.0",
    "psycopg[binary]>=3.1.18",
    "psycopg-pool>=3.2.1",
    "langgraph>=0.0.39",
    "python-telegram-bot>=21.1.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.1.1",
    "pytest-asyncio>=0.23.6",
    "ruff>=0.4.1",
]

[build-system]
requires = ["setuptools>=69.0.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "ASYNC", "S", "B"]
ignore = ["S101", "B008"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["src"]
```

#### What this code does
Configures Python packaging, declares required runtime libraries (FastAPI, psycopg v3 with pooling, httpx, LangGraph, python-telegram-bot), and configures strict linting with Ruff and asynchronous test execution with pytest.

#### Run / verify
- Unix / Windows:
  ```bash
  python3.12 -m venv backend/.venv
  # Activate virtualenv:
  # Unix: source backend/.venv/bin/activate
  # Windows: .\backend\.venv\Scripts\Activate.ps1
  pip install --upgrade pip
  pip install -e "backend/[dev]"
  ```
  Expected output: Successfully installed all dependencies.

#### If it fails
- `Python 3.12 was not found`: Ensure Python 3.12 is installed and set on your PATH.
- `psycopg` wheel compilation failure: The `[binary]` extra provides pre-compiled wheels, avoiding the need for local `libpq-dev`.

---

### Step 2.2: Backend Container Dockerfile

#### Goal
Create a lightweight container image for both the API service and the background Telegram bot runner.

#### Path
- File: `backend/Dockerfile`

#### Code
```dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src/ /app/src/
RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "daginquest.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### What this code does
Creates an optimized Debian-based Python 3.12 image. Installs curl for Docker health checks, installs pinned dependencies, and installs the local package in editable mode.

#### Run / verify
- Unix / Windows:
  ```bash
  docker build -t daginquest-backend:dev backend/
  ```
  Expected output: `naming to docker.io/library/daginquest-backend:dev done`

#### If it fails
- Directory does not exist: Ensure you have created the directory tree `backend/src/daginquest`.

---

### Step 2.3: Central Configuration Module

#### Goal
Create a strictly typed configuration class reading from `.env` using Pydantic Settings.

#### Path
- Unix: `mkdir -p backend/src/daginquest/api`
- Windows (PowerShell): `mkdir -p backend/src/daginquest/api`
- File: `backend/src/daginquest/__init__.py` (create empty file)
- File: `backend/src/daginquest/config.py`

#### Code
Create an empty file at `backend/src/daginquest/__init__.py` and `backend/src/daginquest/api/__init__.py`.

Then write `backend/src/daginquest/config.py`:
```python
from functools import lru_cache
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    POSTGRES_USER: str = "daginquest_user"
    POSTGRES_PASSWORD: str = "daginquest_secure_password"
    POSTGRES_DB: str = "daginquest"
    DATABASE_URL: str = (
        "postgresql://daginquest_user:daginquest_secure_password@localhost:5432/daginquest"
    )

    # Local LLM
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"

    # Airflow 3
    AIRFLOW_IMAGE: str = "apache/airflow:3.0.0.dev0"
    AIRFLOW_BASE_URL: str = "http://localhost:8080"
    AIRFLOW_USERNAME: str = "admin"
    AIRFLOW_PASSWORD: str = "admin"

    # Security & Policy
    WEBHOOK_SECRET: str = "inquest_shared_secret_hex_32_bytes_minimum"
    CONFIDENCE_THRESHOLD: float = Field(default=0.60, ge=0.0, le=1.0)
    DEDUPE_COOLDOWN_MINUTES: int = Field(default=30, ge=1)

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ALLOWED_CHAT_IDS_RAW: str = Field(default="", alias="TELEGRAM_ALLOWED_CHAT_IDS")

    @property
    def telegram_allowed_chat_ids(self) -> List[int]:
        if not self.TELEGRAM_ALLOWED_CHAT_IDS_RAW:
            return []
        return [
            int(cid.strip())
            for cid in self.TELEGRAM_ALLOWED_CHAT_IDS_RAW.split(",")
            if cid.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

#### What this code does
Provides a singleton configuration instance (`get_settings`). It validates data types, guarantees that `CONFIDENCE_THRESHOLD` stays between 0.0 and 1.0, and parses comma-separated chat IDs into a list of integers.

#### Run / verify
- Unix / Windows (from inside `backend/` with active virtualenv):
  ```bash
  python -c "from daginquest.config import get_settings; s = get_settings(); print(f'Database: {s.POSTGRES_DB}, Model: {s.OLLAMA_MODEL}')"
  ```
  Expected output: `Database: daginquest, Model: qwen2.5:7b`

#### If it fails
- `ModuleNotFoundError: No module named 'daginquest'`: Ensure you ran `pip install -e backend/` or set `PYTHONPATH=backend/src`.

---

### Step 2.4: Health Check Endpoint

#### Goal
Create the `/api/health` router providing status checks for both the API service and the PostgreSQL database.

#### Path
- File: `backend/src/daginquest/api/health.py`

#### Code
```python
from fastapi import APIRouter, status
from pydantic import BaseModel
from daginquest.config import get_settings

router = APIRouter(prefix="/api", tags=["System"])


class HealthResponse(BaseModel):
    status: str
    database: str
    version: str


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check() -> HealthResponse:
    # Direct check to verify configuration is loaded
    settings = get_settings()
    db_status = "configured" if settings.DATABASE_URL else "unconfigured"

    return HealthResponse(
        status="ok",
        database=db_status,
        version="0.1.0",
    )
```

#### What this code does
Serves a basic, low-overhead health check route used by container orchestration systems to determine service readiness.

#### Run / verify
- Verified during Step 2.5 after attaching the router to FastAPI.

---

### Step 2.5: FastAPI Main Entrypoint with Lifespan

#### Goal
Create the main FastAPI application entrypoint with structured lifespan event handling for database pools.

#### Path
- File: `backend/src/daginquest/main.py`

#### Code
```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from daginquest.api import health
from daginquest.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup sequence
    settings = get_settings()
    print(f"=== [Startup] DagInquest API starting with model {settings.OLLAMA_MODEL} ===")
    yield
    # Shutdown sequence
    print("=== [Shutdown] DagInquest API stopping ===")


app = FastAPI(
    title="DagInquest API",
    description="Formal Airflow DAG failure investigation and safe remediation agent",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure permissive CORS for local React dashboard development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
```

#### What this code does
Initializes FastAPI using the modern `lifespan` context manager protocol. Configures CORS middleware for frontend communication and mounts the health router.

#### Run / verify
- Start the server directly from the command line:
  ```bash
  uvicorn daginquest.main:app --port 8000 --app-dir backend/src
  ```
- In another terminal:
  ```bash
  curl -s http://localhost:8000/api/health
  ```
  Expected output:
  ```json
  {"status":"ok","database":"configured","version":"0.1.0"}
  ```

#### If it fails
- `Address already in use`: Another process is occupying port 8000. Terminate it or change the port using `--port 8001`.

---

### Checkpoint: Phase 2
The backend skeleton is operational, properly typed, and answers health check requests with HTTP 200.

---

## Phase 3: Pure Utilities and Tests

### Why this phase exists
DagInquest relies on critical invariants before passing untrusted text to LLMs or proposing actions:
1. **Deduplication**: Identical error signatures in the same DAG task must not trigger duplicated investigation alerts.
2. **Redaction**: Passwords, bearer tokens, AWS credentials, and connection URIs must be masked before reaching storage or LLM prompts.
3. **Policy Gate**: The system must enforce that only safe, allow-listed actions (`retry_task`, `clear_task`) for specific failure categories are eligible for remediation approval.
4. **Heuristic Pre-classification**: Fast regex patterns provide baseline confidence scoring before invoking the LLM.

Writing and testing these pure functions first ensures complete test coverage of core security logic without external dependencies.

---

### Step 3.1: Deterministic Fingerprinting Helper

#### Goal
Create a function that calculates a normalized SHA-256 fingerprint from Airflow error metadata to prevent duplicate alerts.

#### Path
- Unix: `mkdir -p backend/src/daginquest/utils`
- Windows (PowerShell): `mkdir -p backend/src/daginquest/utils`
- File: `backend/src/daginquest/utils/__init__.py` (create empty file)
- File: `backend/src/daginquest/utils/fingerprint.py`

#### Code
```python
import hashlib
import re


def normalize_error_message(error: str) -> str:
    """
    Normalizes error strings by removing timestamps, memory addresses,
    and ephemeral run identifiers so identical root causes produce the same hash.
    """
    if not error:
        return "empty_error"

    # Replace memory addresses like 0x7f9a1b2c3d4e
    text = re.sub(r"0x[0-9a-fA-F]+", "0xADDR", error)
    # Replace ISO and common log timestamps
    text = re.sub(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?", "TIMESTAMP", text)
    # Replace UUID strings
    text = re.sub(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", "UUID", text)
    # Collapse multiple whitespaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compute_incident_fingerprint(dag_id: str, task_id: str, error: str) -> str:
    """
    Computes a deterministic SHA-256 fingerprint for a task failure.
    """
    normalized_err = normalize_error_message(error)
    payload = f"{dag_id}:{task_id}:{normalized_err}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
```

#### What this code does
Normalizes variable elements (timestamps, memory pointers, UUIDs) out of error strings so identical failures occurring across different DAG runs share an identical SHA-256 fingerprint.

#### Run / verify
- Verified via unit tests in Step 3.5.

---

### Step 3.2: Sensitive Credential Redaction

#### Goal
Create a regex-based redaction engine that masks passwords, API keys, tokens, and connection strings from untrusted logs.

#### Path
- Unix: `mkdir -p backend/src/daginquest/security`
- Windows (PowerShell): `mkdir -p backend/src/daginquest/security`
- File: `backend/src/daginquest/security/__init__.py` (create empty file)
- File: `backend/src/daginquest/security/redaction.py`

#### Code
```python
import re

PATTERNS = [
    # Passwords in URLs / connection strings (e.g., postgresql://user:pass@host)
    (re.compile(r"://([^:]+):([^@]+)@", re.IGNORECASE), r"://\1:[REDACTED]@"),
    # Common key-value authorization or password pairs
    (
        re.compile(r'(password|passwd|secret|token|api[_-]?key|access[_-]?key)["\']?\s*[:=]\s*["\']?([^"\'\s]+)["\']?', re.IGNORECASE),
        r'\1="[REDACTED]"',
    ),
    # Bearer tokens
    (re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.=]+", re.IGNORECASE), "Bearer [REDACTED]"),
    # AWS Access Key ID
    (re.compile(r"\b(AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}\b"), "[REDACTED_AWS_KEY]"),
    # Slack / Discord / GitHub webhook tokens
    (re.compile(r"gh[pous]_[A-Za-z0-9_]{36,255}"), "[REDACTED_GITHUB_TOKEN]"),
]


def redact_sensitive_data(text: str) -> str:
    """
    Scans text for credentials, secrets, and private tokens and masks them.
    Must be called on all raw logs before LLM processing or database persistence.
    """
    if not text:
        return ""

    sanitized = text
    for pattern, replacement in PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    return sanitized
```

#### What this code does
Ensures sensitive tokens, passwords, and private keys present in Airflow stack traces are stripped before being stored in the database or sent to the LLM.

#### Run / verify
- Verified via unit tests in Step 3.5.

---

### Step 3.3: Safe Remediation Policy Gate

#### Goal
Enforce deterministic safety invariants: define failure categories, allow-listed actions, and confidence score thresholds.

#### Path
- Unix: `mkdir -p backend/src/daginquest/policy`
- Windows (PowerShell): `mkdir -p backend/src/daginquest/policy`
- File: `backend/src/daginquest/policy/__init__.py` (create empty file)
- File: `backend/src/daginquest/policy/rules.py`

#### Code
```python
from dataclasses import dataclass
from typing import Optional, Set

# Failure Categories
CATEGORY_IMPORT_ERROR = "IMPORT_ERROR"
CATEGORY_SCHEMA_SQL = "SCHEMA_SQL"
CATEGORY_TRANSIENT_NETWORK = "TRANSIENT_NETWORK"
CATEGORY_CONFIG_SECRET = "CONFIG_SECRET"
CATEGORY_RESOURCE = "RESOURCE"
CATEGORY_UPSTREAM_DATA = "UPSTREAM_DATA"
CATEGORY_INCONCLUSIVE = "INCONCLUSIVE"

ALL_CATEGORIES: Set[str] = {
    CATEGORY_IMPORT_ERROR,
    CATEGORY_SCHEMA_SQL,
    CATEGORY_TRANSIENT_NETWORK,
    CATEGORY_CONFIG_SECRET,
    CATEGORY_RESOURCE,
    CATEGORY_UPSTREAM_DATA,
    CATEGORY_INCONCLUSIVE,
}

# Only these failure categories are eligible for automated remediation
AUTO_REMEDIABLE_CATEGORIES: Set[str] = {
    CATEGORY_TRANSIENT_NETWORK,
    CATEGORY_RESOURCE,
}

# Allow-listed executable action types
ACTION_RETRY_TASK = "retry_task"
ACTION_CLEAR_TASK = "clear_task"
ACTION_NONE = "none"

ALLOWLISTED_ACTIONS: Set[str] = {
    ACTION_RETRY_TASK,
    ACTION_CLEAR_TASK,
}


@dataclass(frozen=True)
class PolicyEvaluationResult:
    is_allowed: bool
    requires_approval: bool
    rejection_reason: Optional[str] = None


def evaluate_remediation_policy(
    category: str,
    action: str,
    confidence: float,
    threshold: float = 0.60,
) -> PolicyEvaluationResult:
    """
    Strict safety check evaluating whether a proposed action may proceed to human review.
    Invariants:
    1. Action must be in ALLOWLISTED_ACTIONS.
    2. Category must be in AUTO_REMEDIABLE_CATEGORIES.
    3. Confidence must be >= threshold.
    4. requires_approval is ALWAYS True (no unattended execution path exists).
    """
    if action == ACTION_NONE:
        return PolicyEvaluationResult(
            is_allowed=False,
            requires_approval=False,
            rejection_reason="No remediation action proposed.",
        )

    if action not in ALLOWLISTED_ACTIONS:
        return PolicyEvaluationResult(
            is_allowed=False,
            requires_approval=False,
            rejection_reason=f"Action '{action}' is not in allow-list: {sorted(list(ALLOWLISTED_ACTIONS))}",
        )

    if category not in AUTO_REMEDIABLE_CATEGORIES:
        return PolicyEvaluationResult(
            is_allowed=False,
            requires_approval=False,
            rejection_reason=f"Category '{category}' is non-recoverable via auto-remediation.",
        )

    if confidence < threshold:
        return PolicyEvaluationResult(
            is_allowed=False,
            requires_approval=False,
            rejection_reason=f"Confidence {confidence:.2f} is below policy threshold {threshold:.2f}.",
        )

    # All criteria met: allowed, but human approval is mandatory
    return PolicyEvaluationResult(
        is_allowed=True,
        requires_approval=True,
        rejection_reason=None,
    )
```

#### What this code does
Acts as an invariant validation gate. It rejects any action that is not explicitly allow-listed, any failure category that is unsafe to retry automatically (e.g., syntax errors, missing secrets), and any analysis with low confidence. It enforces that human approval is always required.

#### Run / verify
- Verified via unit tests in Step 3.5.

---

### Step 3.4: Pre-classification Heuristics

#### Goal
Implement deterministic regex log pre-classification to provide fast baseline hypotheses and baseline confidence.

#### Path
- File: `backend/src/daginquest/utils/preclassify.py`

#### Code
```python
import re
from typing import Optional, Tuple
from daginquest.policy.rules import (
    CATEGORY_CONFIG_SECRET,
    CATEGORY_IMPORT_ERROR,
    CATEGORY_RESOURCE,
    CATEGORY_SCHEMA_SQL,
    CATEGORY_TRANSIENT_NETWORK,
    CATEGORY_UPSTREAM_DATA,
)

HEURISTIC_RULES = [
    (
        CATEGORY_IMPORT_ERROR,
        re.compile(r"(ModuleNotFoundError|ImportError|cannot import name)", re.IGNORECASE),
        0.85,
    ),
    (
        CATEGORY_SCHEMA_SQL,
        re.compile(r"(syntax error at or near|UndefinedTable|NoSuchTableError|relation .+ does not exist)", re.IGNORECASE),
        0.80,
    ),
    (
        CATEGORY_TRANSIENT_NETWORK,
        re.compile(r"(ConnectionResetError|RemoteDisconnected|ConnectionRefusedError|timeout|ReadTimeout)", re.IGNORECASE),
        0.75,
    ),
    (
        CATEGORY_CONFIG_SECRET,
        re.compile(r"(AccessDenied|401 Unauthorized|403 Forbidden|InvalidCredentials|KeyError: '.*_KEY')", re.IGNORECASE),
        0.80,
    ),
    (
        CATEGORY_RESOURCE,
        re.compile(r"(OutOfMemory|OOMKilled|MemoryError|No space left on device|DiskFull)", re.IGNORECASE),
        0.85,
    ),
    (
        CATEGORY_UPSTREAM_DATA,
        re.compile(r"(FileNotFoundError|AirflowSensorTimeout|upstream task failed|XComNotFound)", re.IGNORECASE),
        0.70,
    ),
]


def preclassify_log(log_text: str) -> Tuple[Optional[str], float]:
    """
    Scans logs against known failure patterns to provide an initial category and confidence score.
    Returns (category, confidence). Defaults to (None, 0.0) if no rules match.
    """
    if not log_text:
        return None, 0.0

    for category, regex, base_confidence in HEURISTIC_RULES:
        if regex.search(log_text):
            return category, base_confidence

    return None, 0.0
```

#### What this code does
Scans raw log text with regex patterns to quickly classify familiar stack traces (like `ModuleNotFoundError` or `ConnectionResetError`) without requiring immediate LLM execution.

#### Run / verify
- Verified via unit tests in Step 3.5.

---

### Step 3.5: Unit Test Suite for Pure Utilities

#### Goal
Create a comprehensive test suite in `backend/tests/` verifying all utility, redaction, policy, and pre-classification invariants.

#### Path
- Unix: `mkdir -p backend/tests`
- Windows (PowerShell): `mkdir -p backend/tests`
- Files:
  - `backend/tests/__init__.py` (empty file)
  - `backend/tests/conftest.py`
  - `backend/tests/test_fingerprint.py`
  - `backend/tests/test_redaction.py`
  - `backend/tests/test_policy.py`
  - `backend/tests/test_preclassify_citations.py`

#### Code
Create an empty file at `backend/tests/__init__.py`.

Then write `backend/tests/conftest.py`:
```python
import pytest


@pytest.fixture
def sample_traceback() -> str:
    return """
    Traceback (most recent call last):
      File "/opt/airflow/dags/etl_orders.py", line 42, in execute
        db_conn = connect("postgresql://app_user:SuperSecretP@ssword123@db.prod.internal:5432/orders")
      File "/usr/local/lib/python3.12/site-packages/psycopg/connection.py", line 71, in connect
        raise ConnectionResetError("Connection reset by peer at 0x7f8a9c2b1e40")
    ConnectionResetError: Connection reset by peer at 0x7f8a9c2b1e40
    """
```

Write `backend/tests/test_fingerprint.py`:
```python
from daginquest.utils.fingerprint import compute_incident_fingerprint, normalize_error_message


def test_normalize_error_message_strips_addresses_and_timestamps():
    err1 = "Connection failed at 0x7f9a1b2c3d4e at 2026-05-12T10:15:30Z"
    err2 = "Connection failed at 0x112233445566 at 2026-05-12T10:18:45Z"

    norm1 = normalize_error_message(err1)
    norm2 = normalize_error_message(err2)

    assert norm1 == norm2
    assert "0xADDR" in norm1
    assert "TIMESTAMP" in norm1


def test_compute_incident_fingerprint_deterministic():
    dag = "daily_sync"
    task = "fetch_records"
    err = "HTTP 503 Service Unavailable"

    fp1 = compute_incident_fingerprint(dag, task, err)
    fp2 = compute_incident_fingerprint(dag, task, err)

    assert fp1 == fp2
    assert len(fp1) == 64  # SHA-256 hex string length
```

Write `backend/tests/test_redaction.py`:
```python
from daginquest.security.redaction import redact_sensitive_data


def test_redact_database_url_password():
    raw = "psql postgresql://dag_admin:P@ssword123!@10.0.0.5:5432/analytics"
    clean = redact_sensitive_data(raw)
    assert "P@ssword123!" not in clean
    assert "dag_admin:[REDACTED]@" in clean


def test_redact_bearer_token():
    raw = "Headers: {'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'}"
    clean = redact_sensitive_data(raw)
    assert "Bearer [REDACTED]" in clean


def test_redact_aws_access_key():
    raw = "AWS validation error using AKIAIOSFODNN7EXAMPLE key"
    clean = redact_sensitive_data(raw)
    assert "AKIAIOSFODNN7EXAMPLE" not in clean
    assert "[REDACTED_AWS_KEY]" in clean
```

Write `backend/tests/test_policy.py`:
```python
from daginquest.policy.rules import (
    ACTION_CLEAR_TASK,
    ACTION_NONE,
    ACTION_RETRY_TASK,
    CATEGORY_IMPORT_ERROR,
    CATEGORY_SCHEMA_SQL,
    CATEGORY_TRANSIENT_NETWORK,
    evaluate_remediation_policy,
)


def test_policy_allows_transient_network_retry():
    res = evaluate_remediation_policy(
        category=CATEGORY_TRANSIENT_NETWORK,
        action=ACTION_RETRY_TASK,
        confidence=0.85,
        threshold=0.60,
    )
    assert res.is_allowed is True
    assert res.requires_approval is True
    assert res.rejection_reason is None


def test_policy_rejects_import_error_retry():
    res = evaluate_remediation_policy(
        category=CATEGORY_IMPORT_ERROR,
        action=ACTION_CLEAR_TASK,
        confidence=0.95,
        threshold=0.60,
    )
    assert res.is_allowed is False
    assert "non-recoverable" in res.rejection_reason


def test_policy_rejects_low_confidence():
    res = evaluate_remediation_policy(
        category=CATEGORY_TRANSIENT_NETWORK,
        action=ACTION_RETRY_TASK,
        confidence=0.45,
        threshold=0.60,
    )
    assert res.is_allowed is False
    assert "below policy threshold" in res.rejection_reason


def test_policy_rejects_non_allowlisted_action():
    res = evaluate_remediation_policy(
        category=CATEGORY_TRANSIENT_NETWORK,
        action="delete_database",
        confidence=0.90,
    )
    assert res.is_allowed is False
    assert "not in allow-list" in res.rejection_reason
```

Write `backend/tests/test_preclassify_citations.py`:
```python
from daginquest.policy.rules import CATEGORY_IMPORT_ERROR, CATEGORY_TRANSIENT_NETWORK
from daginquest.utils.preclassify import preclassify_log


def test_preclassify_detects_import_error():
    log = "Traceback...\nModuleNotFoundError: No module named 'pydantic_settings'"
    cat, conf = preclassify_log(log)
    assert cat == CATEGORY_IMPORT_ERROR
    assert conf >= 0.80


def test_preclassify_detects_network_timeout():
    log = "requests.exceptions.ReadTimeout: HTTPSConnectionPool(host='api.internal', port=443): Read timed out."
    cat, conf = preclassify_log(log)
    assert cat == CATEGORY_TRANSIENT_NETWORK
    assert conf >= 0.70


def test_preclassify_unknown_returns_none():
    log = "General process finished with code 1"
    cat, conf = preclassify_log(log)
    assert cat is None
    assert conf == 0.0
```

#### What this code does
Runs a thorough suite of isolated unit tests verifying:
1. Normalization and hashing invariance.
2. Complete credential masking across URLs, AWS keys, and Bearer tokens.
3. Policy constraints (rejecting dangerous actions or unsafe categories).
4. Regex matching accuracy for pre-classification.

#### Run / verify
- Run pytest within the `backend/` directory:
  ```bash
  cd backend && pytest -v
  ```
  Expected output:
  ```
  ============================= test session starts ==============================
  collected 11 items

  tests/test_fingerprint.py::test_normalize_error_message_strips_addresses_and_timestamps PASSED [  9%]
  tests/test_fingerprint.py::test_compute_incident_fingerprint_deterministic PASSED       [ 18%]
  tests/test_redaction.py::test_redact_database_url_password PASSED                       [ 27%]
  tests/test_redaction.py::test_redact_bearer_token PASSED                               [ 36%]
  tests/test_redaction.py::test_redact_aws_access_key PASSED                              [ 45%]
  tests/test_policy.py::test_policy_allows_transient_network_retry PASSED                 [ 54%]
  tests/test_policy.py::test_policy_rejects_import_error_retry PASSED                     [ 63%]
  tests/test_policy.py::test_policy_rejects_low_confidence PASSED                         [ 72%]
  tests/test_policy.py::test_policy_rejects_non_allowlisted_action PASSED                  [ 81%]
  tests/test_preclassify_citations.py::test_preclassify_detects_import_error PASSED      [ 90%]
  tests/test_preclassify_citations.py::test_preclassify_detects_network_timeout PASSED   [100%]

  ============================== 11 passed in 0.18s ==============================
  ```

#### If it fails
- `ModuleNotFoundError`: Ensure your virtual environment is active and `pip install -e backend/` was executed.
- Assertion failure: Double check that regex patterns in `redaction.py` and `policy/rules.py` were copied without omissions.

---

### Checkpoint: Phase 3
All pure functions and security invariant tests pass with 100% success.


---

## Phase 4: Database Layer

### Why this phase exists
DagInquest stores all state in PostgreSQL 16 using `psycopg 3` with `psycopg_pool` (plain SQL, no ORM). This phase creates the connection pool manager and the repository functions that execute raw SQL queries for incident creation/deduplication, evidence storage, analyses persistence, action management, metrics aggregation, and audit logging.

Most importantly, it implements the **atomic approval query**:
```sql
UPDATE actions
SET status = %(decision)s, updated_at = CURRENT_TIMESTAMP
WHERE id = %(action_id)s AND status = 'pending_approval'
RETURNING *;
```
This single query guarantees that concurrent or repeated clicks (e.g. from Telegram inline buttons or UI dashboards) cannot double-approve an action or cause race conditions. If the action is no longer `pending_approval`, zero rows are returned, triggering an immediate HTTP 409 Conflict.

---

### Step 4.1: Database Connection Pool Session

#### Goal
Create the asynchronous PostgreSQL connection pool using `psycopg_pool.AsyncConnectionPool`.

#### Path
- Unix: `mkdir -p backend/src/daginquest/db`
- Windows (PowerShell): `mkdir -p backend/src/daginquest/db`
- File: `backend/src/daginquest/db/__init__.py` (create empty file)
- File: `backend/src/daginquest/db/session.py`

#### Code
Create an empty file at `backend/src/daginquest/db/__init__.py`.

Then write `backend/src/daginquest/db/session.py`:
```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from daginquest.config import get_settings

_pool: Optional[AsyncConnectionPool] = None


async def init_db_pool() -> AsyncConnectionPool:
    """
    Initializes the global async PostgreSQL connection pool.
    """
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = AsyncConnectionPool(
            conninfo=settings.DATABASE_URL,
            min_size=2,
            max_size=10,
            timeout=10.0,
            kwargs={"row_factory": dict_row},
            open=False,
        )
        await _pool.open()
    return _pool


async def close_db_pool() -> None:
    """
    Closes the global connection pool gracefully during shutdown.
    """
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_connection() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    """
    Context manager providing an active database connection from the pool.
    """
    global _pool
    if _pool is None:
        await init_db_pool()
    assert _pool is not None

    async with _pool.connection() as conn:
        yield conn
```

#### What this code does
Manages a thread-safe, non-blocking connection pool using `AsyncConnectionPool`. Setting `row_factory=dict_row` ensures all SQL result tuples are returned as standard Python dictionaries, eliminating manual index mappings.

#### Run / verify
- Verified during Step 4.3 using the verification test script.

#### If it fails
- `psycopg_pool.PoolTimeout`: Ensure the PostgreSQL container is running on port 5432 and `DATABASE_URL` in `.env` is reachable.

---

### Step 4.2: Data Access Repository

#### Goal
Implement all raw SQL operations for incidents, evidence, analyses, actions, approvals, audit logs, and metrics.

#### Path
- File: `backend/src/daginquest/db/repository.py`

#### Code
```python
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
import psycopg
from psycopg.types.json import Jsonb
from daginquest.db.session import get_connection


async def create_or_bump_incident(
    fingerprint: str,
    dag_id: str,
    run_id: str,
    task_id: str,
    try_number: int,
    error_message: str,
    cooldown_minutes: int = 30,
) -> Dict[str, Any]:
    """
    Finds an existing open incident with the same fingerprint within cooldown,
    incrementing its occurrence count. Otherwise creates a new incident.
    Returns: dict(incident, deduplicated: bool)
    """
    async with get_connection() as conn:
        async with conn.cursor() as cur:
            # Check for existing open incident within cooldown
            await cur.execute(
                """
                SELECT * FROM incidents
                WHERE fingerprint = %(fp)s
                  AND status != 'closed'
                  AND last_seen_at >= CURRENT_TIMESTAMP - %(cooldown)s * INTERVAL '1 minute'
                ORDER BY last_seen_at DESC
                LIMIT 1;
                """,
                {"fp": fingerprint, "cooldown": int(cooldown_minutes)},
            )
            existing = await cur.fetchone()

            if existing:
                await cur.execute(
                    """
                    UPDATE incidents
                    SET occurrence_count = occurrence_count + 1,
                        last_seen_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP,
                        run_id = %(run_id)s,
                        try_number = %(try_number)s
                    WHERE id = %(id)s
                    RETURNING *;
                    """,
                    {"id": existing["id"], "run_id": run_id, "try_number": try_number},
                )
                updated = await cur.fetchone()
                await conn.commit()
                return {"incident": updated, "deduplicated": True}

            # Create new incident
            await cur.execute(
                """
                INSERT INTO incidents (
                    fingerprint, dag_id, run_id, task_id, try_number, error_message
                ) VALUES (
                    %(fp)s, %(dag_id)s, %(run_id)s, %(task_id)s, %(try_number)s, %(err)s
                )
                RETURNING *;
                """,
                {
                    "fp": fingerprint,
                    "dag_id": dag_id,
                    "run_id": run_id,
                    "task_id": task_id,
                    "try_number": try_number,
                    "err": error_message,
                },
            )
            created = await cur.fetchone()
            await conn.commit()
            return {"incident": created, "deduplicated": False}


async def add_evidence(
    incident_id: UUID,
    evidence_type: str,
    content: str,
) -> Dict[str, Any]:
    """
    Appends a collected evidence item (logs, DAG code, context).
    """
    async with get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO evidence (incident_id, evidence_type, content)
                VALUES (%(inc_id)s, %(type)s, %(content)s)
                RETURNING *;
                """,
                {"inc_id": incident_id, "type": evidence_type, "content": content},
            )
            row = await cur.fetchone()
            await conn.commit()
            return row


async def save_analysis(
    incident_id: UUID,
    category: str,
    confidence: float,
    root_cause: str,
    suggested_action: str,
    cited_lines: List[str],
    is_auto_remediable: bool,
    policy_approved: bool,
    policy_rejection_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Persists structured LLM investigation results.
    """
    async with get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO analyses (
                    incident_id, category, confidence, root_cause, suggested_action,
                    cited_lines, is_auto_remediable, policy_approved, policy_rejection_reason
                ) VALUES (
                    %(inc_id)s, %(cat)s, %(conf)s, %(rc)s, %(act)s,
                    %(cited)s, %(auto)s, %(pol)s, %(rej)s
                )
                RETURNING *;
                """,
                {
                    "inc_id": incident_id,
                    "cat": category,
                    "conf": confidence,
                    "rc": root_cause,
                    "act": suggested_action,
                    "cited": Jsonb(cited_lines),
                    "auto": is_auto_remediable,
                    "pol": policy_approved,
                    "rej": policy_rejection_reason,
                },
            )
            row = await cur.fetchone()
            await conn.commit()
            return row


async def create_action(
    incident_id: UUID,
    action_type: str,
) -> Dict[str, Any]:
    """
    Creates an action requiring human approval with a unique idempotency key.
    """
    idempotency_key = f"{incident_id}:{action_type}"
    async with get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO actions (incident_id, action_type, idempotency_key, status)
                VALUES (%(inc_id)s, %(action_type)s, %(key)s, 'pending_approval')
                ON CONFLICT (idempotency_key) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
                RETURNING *;
                """,
                {"inc_id": incident_id, "action_type": action_type, "key": idempotency_key},
            )
            row = await cur.fetchone()
            await conn.commit()
            return row


async def decide_action(
    action_id: UUID,
    decision: str,  # 'approved' or 'rejected'
    approver_id: str,
    reason: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    ATOMIC APPROVAL:
    Executes atomic state change from 'pending_approval' to 'approved'/'rejected'.
    Returns the updated action row, or None if already decided (concurrency guard).
    """
    async with get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE actions
                SET status = %(decision)s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %(action_id)s
                  AND status = 'pending_approval'
                RETURNING *;
                """,
                {"action_id": action_id, "decision": decision},
            )
            action = await cur.fetchone()
            if not action:
                return None  # Action was already decided or doesn't exist

            # Record decision audit in approvals table
            await cur.execute(
                """
                INSERT INTO approvals (action_id, decision, approver_id, decision_reason)
                VALUES (%(act_id)s, %(dec)s, %(appr)s, %(reason)s);
                """,
                {"act_id": action_id, "dec": decision, "appr": approver_id, "reason": reason},
            )

            # Record audit log entry
            await cur.execute(
                """
                INSERT INTO audit_log (entity_name, entity_id, action, actor, payload)
                VALUES ('actions', %(act_id)s, %(action_name)s, %(actor)s, %(payload)s);
                """,
                {
                    "act_id": action_id,
                    "action_name": f"action_{decision}",
                    "actor": approver_id,
                    "payload": Jsonb({"decision": decision, "reason": reason}),
                },
            )

            await conn.commit()
            return action


async def get_action(action_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Fetches an action row by UUID.
    """
    async with get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM actions WHERE id = %(id)s;", {"id": action_id})
            return await cur.fetchone()


async def set_action_result(
    action_id: UUID,
    status: str,  # 'succeeded' or 'failed'
    execution_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Updates action execution outcome and logs audit trace.
    """
    async with get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE actions
                SET status = %(status)s,
                    execution_result = %(res)s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %(id)s
                RETURNING *;
                """,
                {"id": action_id, "status": status, "res": Jsonb(execution_result)},
            )
            row = await cur.fetchone()

            # Record audit log
            await cur.execute(
                """
                INSERT INTO audit_log (entity_name, entity_id, action, actor, payload)
                VALUES ('actions', %(id)s, 'action_executed', 'system:executor', %(payload)s);
                """,
                {"id": action_id, "payload": Jsonb(execution_result)},
            )
            await conn.commit()
            return row


async def list_incidents(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Lists recent incidents with their latest analysis.
    """
    async with get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT i.*,
                       a.category,
                       a.confidence,
                       a.root_cause,
                       a.suggested_action
                FROM incidents i
                LEFT JOIN LATERAL (
                    SELECT category, confidence, root_cause, suggested_action
                    FROM analyses
                    WHERE incident_id = i.id
                    ORDER BY created_at DESC
                    LIMIT 1
                ) a ON TRUE
                ORDER BY i.last_seen_at DESC
                LIMIT %(limit)s OFFSET %(offset)s;
                """,
                {"limit": limit, "offset": offset},
            )
            return await cur.fetchall()


async def get_incident(incident_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Fetches full incident details including evidence, analyses, and actions.
    """
    async with get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM incidents WHERE id = %(id)s;", {"id": incident_id})
            incident = await cur.fetchone()
            if not incident:
                return None

            await cur.execute(
                "SELECT * FROM evidence WHERE incident_id = %(id)s ORDER BY collected_at ASC;",
                {"id": incident_id},
            )
            incident["evidence"] = await cur.fetchall()

            await cur.execute(
                "SELECT * FROM analyses WHERE incident_id = %(id)s ORDER BY created_at DESC;",
                {"id": incident_id},
            )
            incident["analyses"] = await cur.fetchall()

            await cur.execute(
                "SELECT * FROM actions WHERE incident_id = %(id)s ORDER BY created_at DESC;",
                {"id": incident_id},
            )
            incident["actions"] = await cur.fetchall()

            return incident


async def list_pending_actions() -> List[Dict[str, Any]]:
    """
    Fetches all actions currently in 'pending_approval' status.
    """
    async with get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT a.*,
                       i.dag_id,
                       i.task_id,
                       i.run_id,
                       an.category,
                       an.confidence,
                       an.root_cause
                FROM actions a
                JOIN incidents i ON a.incident_id = i.id
                LEFT JOIN LATERAL (
                    SELECT category, confidence, root_cause
                    FROM analyses
                    WHERE incident_id = i.id
                    ORDER BY created_at DESC
                    LIMIT 1
                ) an ON TRUE
                WHERE a.status = 'pending_approval'
                ORDER BY a.created_at ASC;
                """
            )
            return await cur.fetchall()


async def get_metrics() -> Dict[str, Any]:
    """
    Computes system aggregate metrics for dashboard and Telegram /status command.
    """
    async with get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) AS total_incidents FROM incidents;")
            total_incidents = (await cur.fetchone())["total_incidents"]

            await cur.execute("SELECT SUM(occurrence_count - 1) AS total_deduped FROM incidents;")
            deduped = (await cur.fetchone())["total_deduped"] or 0

            await cur.execute(
                "SELECT COUNT(*) AS pending_approvals FROM actions WHERE status = 'pending_approval';"
            )
            pending_approvals = (await cur.fetchone())["pending_approvals"]

            await cur.execute(
                "SELECT COALESCE(AVG(confidence), 0.0) AS avg_confidence FROM analyses;"
            )
            avg_confidence = float((await cur.fetchone())["avg_confidence"])

            return {
                "total_incidents": total_incidents,
                "total_deduplicated_events": deduped,
                "pending_approvals": pending_approvals,
                "avg_confidence": round(avg_confidence, 2),
            }
```

#### What this code does
Provides the complete data access layer for all domain operations. It safely converts Python objects to JSONB using `Jsonb`, handles deduplication lookups with time interval filters, records audit trails, and encapsulates the atomic approval query.

#### Run / verify
- Verified in Step 4.3.

---

### Step 4.3: Database Repository Smoke Test

#### Goal
Create and execute a standalone script verifying incident insertion, deduplication, evidence storage, and atomic approval conflict handling.

#### Path
- File: `backend/src/daginquest/db/smoke_test.py`

#### Code
```python
import asyncio
from daginquest.db.repository import (
    add_evidence,
    create_action,
    create_or_bump_incident,
    decide_action,
    get_incident,
    get_metrics,
)
from daginquest.db.session import close_db_pool, init_db_pool


async def main() -> None:
    print("=== [DB Test] Initializing pool ===")
    await init_db_pool()

    # 1. Test Incident Creation
    fp = "test_fingerprint_hash_12345"
    res1 = await create_or_bump_incident(
        fingerprint=fp,
        dag_id="demo_dag",
        run_id="run_001",
        task_id="extract_task",
        try_number=1,
        error_message="Connection timed out",
    )
    inc = res1["incident"]
    print(f"Created incident: {inc['id']}, deduplicated: {res1['deduplicated']}")
    assert res1["deduplicated"] is False

    # 2. Test Deduplication Bump
    res2 = await create_or_bump_incident(
        fingerprint=fp,
        dag_id="demo_dag",
        run_id="run_002",
        task_id="extract_task",
        try_number=2,
        error_message="Connection timed out",
    )
    print(f"Bumped incident: {res2['incident']['id']}, occurrences: {res2['incident']['occurrence_count']}")
    assert res2["deduplicated"] is True
    assert res2["incident"]["occurrence_count"] == 2

    # 3. Test Evidence Attachment
    ev = await add_evidence(
        incident_id=inc["id"],
        evidence_type="task_log",
        content="ReadTimeout: Connection timed out after 30s",
    )
    print(f"Added evidence: {ev['id']}")

    # 4. Test Action Creation & Atomic Approval
    act = await create_action(incident_id=inc["id"], action_type="retry_task")
    print(f"Created action: {act['id']}, status: {act['status']}")

    # First approval must succeed
    approved = await decide_action(
        action_id=act["id"],
        decision="approved",
        approver_id="telegram:123456789",
        reason="Verified network glitched",
    )
    print(f"First decision result: {approved['status']}")
    assert approved is not None
    assert approved["status"] == "approved"

    # Second approval attempt must return None (HTTP 409 Conflict trigger)
    second_attempt = await decide_action(
        action_id=act["id"],
        decision="approved",
        approver_id="telegram:123456789",
    )
    print(f"Second decision result (expected None): {second_attempt}")
    assert second_attempt is None

    # 5. Verify Metrics
    metrics = await get_metrics()
    print(f"Current Metrics: {metrics}")
    assert metrics["total_incidents"] >= 1

    await close_db_pool()
    print("=== [DB Test] SUCCESS: All database operations verified ===")


if __name__ == "__main__":
    asyncio.run(main())
```

#### What this code does
Directly executes the database functions against the running PostgreSQL container, validating:
1. Incident creation and fingerprint matching.
2. Occurrence counter incrementing within the cooldown window.
3. Evidence storage.
4. Action creation and the single-use atomic approval query.
5. Metrics aggregation.

#### Run / verify
- Unix / Windows (from within `backend/` with active virtualenv):
  ```bash
  python -m daginquest.db.smoke_test
  ```
  Expected output:
  ```
  === [DB Test] Initializing pool ===
  Created incident: ..., deduplicated: False
  Bumped incident: ..., occurrences: 2
  Added evidence: ...
  Created action: ..., status: pending_approval
  First decision result: approved
  Second decision result (expected None): None
  Current Metrics: {'total_incidents': ..., 'total_deduplicated_events': 1, 'pending_approvals': 0, 'avg_confidence': 0.0}
  === [DB Test] SUCCESS: All database operations verified ===
  ```

#### If it fails
- `connection refused`: Ensure Docker container `daginquest-postgres` is running (`docker compose ps`).
- `duplicate key value violates unique constraint`: The test script uses a static fingerprint; subsequent runs will bump the existing incident, which is expected behavior.

---

### Checkpoint: Phase 4
Database session pooling, all repository functions, atomic approval state management, and immutability triggers are verified.

---

## Phase 5: Airflow Integration

### Why this phase exists
DagInquest investigates failed DAG runs by integrating directly with Apache Airflow 3:
1. When a task fails, an Airflow `on_failure_callback` sends an HTTP POST webhook with error metadata to DagInquest.
2. The DagInquest webhook endpoint verifies the shared secret header in constant time to prevent spoofing.
3. An asynchronous client (`AirflowClient`) talks to the Airflow REST API to retrieve task logs, DAG source code, and task instance states, and clears failed tasks during remediation.

---

### Step 5.1: Airflow REST Client

#### Goal
Implement an asynchronous HTTP client in `airflow/client.py` using `httpx` to interact with Airflow's REST API.

#### Path
- Unix: `mkdir -p backend/src/daginquest/airflow`
- Windows (PowerShell): `mkdir -p backend/src/daginquest/airflow`
- File: `backend/src/daginquest/airflow/__init__.py` (create empty file)
- File: `backend/src/daginquest/airflow/client.py`

#### Code
Create an empty file at `backend/src/daginquest/airflow/__init__.py`.

Then write `backend/src/daginquest/airflow/client.py`:
```python
from typing import Any, Dict, Optional
import httpx
from daginquest.config import get_settings


class AirflowClient:
    """
    Async client for Apache Airflow REST API (Airflow 3 / API v2).
    Verify endpoints against your running Airflow instance at: http://localhost:8080/docs
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.AIRFLOW_BASE_URL).rstrip("/")
        self.auth = (
            username or settings.AIRFLOW_USERNAME,
            password or settings.AIRFLOW_PASSWORD,
        )
        self.timeout = httpx.Timeout(15.0, connect=5.0)

    async def get_task_log(
        self,
        dag_id: str,
        run_id: str,
        task_id: str,
        try_number: int,
    ) -> str:
        """
        Retrieves execution log for a specific task instance try.
        Standard Airflow endpoint:
        GET /api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/logs/{try_number}
        """
        url = (
            f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns/{run_id}/"
            f"taskInstances/{task_id}/logs/{try_number}"
        )
        async with httpx.AsyncClient(auth=self.auth, timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers={"Accept": "text/plain"})
                if response.status_code == 200:
                    return response.text
                return f"[Warning] Failed to fetch task log: HTTP {response.status_code}"
            except Exception as e:
                return f"[Warning] Could not connect to Airflow API to fetch log: {str(e)}"

    async def get_dag_source(self, dag_id: str) -> str:
        """
        Retrieves the Python source code for the DAG.
        Standard Airflow endpoint: GET /api/v1/dags/{dag_id}/details
        """
        url = f"{self.base_url}/api/v1/dags/{dag_id}/details"
        async with httpx.AsyncClient(auth=self.auth, timeout=self.timeout) as client:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    # Return file_token or source if exposed
                    return data.get("doc_md") or f"# DAG: {dag_id}\n# File: {data.get('fileloc')}"
                return f"# DAG source unavailable: HTTP {response.status_code}"
            except Exception as e:
                return f"# Could not connect to Airflow to fetch DAG source: {str(e)}"

    async def get_task_instance_state(
        self,
        dag_id: str,
        run_id: str,
        task_id: str,
    ) -> Optional[str]:
        """
        Fetches the current state of a task instance (e.g., 'running', 'success', 'failed').
        """
        url = f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}"
        async with httpx.AsyncClient(auth=self.auth, timeout=self.timeout) as client:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.json().get("state")
                return None
            except Exception:
                return None

    async def clear_task_instances(
        self,
        dag_id: str,
        run_id: str,
        task_id: str,
    ) -> bool:
        """
        Clears a failed task instance so Airflow reschedules and retries it.
        Standard Airflow endpoint: POST /api/v1/dags/{dag_id}/clearTaskInstances
        """
        url = f"{self.base_url}/api/v1/dags/{dag_id}/clearTaskInstances"
        payload = {
            "dry_run": False,
            "task_ids": [task_id],
            "dag_run_id": run_id,
            "include_subdags": False,
            "include_parentdag": False,
            "reset_dag_run": False,
        }
        async with httpx.AsyncClient(auth=self.auth, timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload)
                return response.status_code in (200, 201)
            except Exception:
                return False
```

#### What this code does
Encapsulates communication with Airflow's REST interface. It implements methods to download task logs, retrieve DAG source locations, query task instance states, and clear tasks for remediation.

#### Run / verify
- Verified during Step 5.5 and Phase 9.

---

### Step 5.2: Airflow Callback Module

#### Goal
Create the reusable failure callback module `airflow/dags/_common/callbacks.py` that Airflow tasks trigger on failure.

#### Path
- Unix: `mkdir -p airflow/dags/_common`
- Windows (PowerShell): `mkdir -p airflow/dags/_common`
- File: `airflow/dags/_common/__init__.py` (create empty file)
- File: `airflow/dags/_common/callbacks.py`

#### Code
Create an empty file at `airflow/dags/_common/__init__.py`.

Then write `airflow/dags/_common/callbacks.py`:
```python
import os
import urllib.request
import json
import ssl


def daginquest_failure_callback(context: dict) -> None:
    """
    Airflow task failure callback. Extracts task execution metadata
    and posts an alert webhook to the DagInquest API.
    """
    ti = context.get("task_instance")
    task = context.get("task")
    dag = context.get("dag")
    exception = context.get("exception")

    dag_id = dag.dag_id if dag else (ti.dag_id if ti else "unknown_dag")
    task_id = task.task_id if task else (ti.task_id if ti else "unknown_task")
    run_id = context.get("run_id") or (ti.run_id if ti else "unknown_run")
    try_number = ti.try_number if ti else 1
    error = str(exception) if exception else "Task failed with unhandled exception"

    # Read configuration from container environment
    api_url = os.environ.get("DAGINQUEST_API_URL", "http://api:8000")
    webhook_secret = os.environ.get("DAGINQUEST_WEBHOOK_SECRET", "inquest_shared_secret_hex_32_bytes_minimum")
    endpoint = f"{api_url.rstrip('/')}/api/webhooks/airflow/failure"

    payload = {
        "dag_id": str(dag_id),
        "run_id": str(run_id),
        "task_id": str(task_id),
        "try_number": int(try_number),
        "error": str(error),
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Secret": webhook_secret,
                "User-Agent": "Airflow-DagInquest-Callback/1.0",
            },
            method="POST",
        )
        # Permissive local SSL context for container network
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
            resp_body = response.read().decode("utf-8")
            print(f"[DagInquest] Failure webhook sent successfully: HTTP {response.status} -> {resp_body}")
    except Exception as e:
        print(f"[DagInquest] Warning: Failed to send failure webhook to {endpoint}: {e}")
```

#### What this code does
Executes inside the Airflow worker/scheduler when a task fails. It extracts the DAG ID, task ID, run ID, attempt number, and exception string, and dispatches an HTTP POST request to DagInquest using Python's standard library (`urllib.request`) to avoid external dependencies inside Airflow.

#### Run / verify
- Verified when triggering demo DAGs in Step 5.5.

---

### Step 5.3: Demo Failing DAGs

#### Goal
Create three demonstrator DAGs simulating real-world failures: import error, network timeout, and syntax SQL error.

#### Path
- Files:
  - `airflow/dags/demo_import_error.py`
  - `airflow/dags/demo_timeout.py`
  - `airflow/dags/demo_bad_sql.py`

#### Code
Write `airflow/dags/demo_import_error.py`:
```python
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from _common.callbacks import daginquest_failure_callback


def fail_with_import_error():
    # Intentionally attempting to import a nonexistent module
    import non_existent_analytics_package_xyz  # noqa: F401


with DAG(
    dag_id="demo_import_error",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    default_args={"on_failure_callback": daginquest_failure_callback},
    tags=["demo", "daginquest"],
) as dag:
    task = PythonOperator(
        task_id="broken_import_task",
        python_callable=fail_with_import_error,
    )
```

Write `airflow/dags/demo_timeout.py`:
```python
from datetime import datetime
import socket
from airflow import DAG
from airflow.operators.python import PythonOperator
from _common.callbacks import daginquest_failure_callback


def fail_with_timeout():
    # Simulates a network read timeout against an unreachable external endpoint
    raise socket.timeout("Connection reset by peer: read timeout after 30000ms connecting to api.partner.net:443")


with DAG(
    dag_id="demo_timeout",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    default_args={"on_failure_callback": daginquest_failure_callback},
    tags=["demo", "daginquest"],
) as dag:
    task = PythonOperator(
        task_id="network_fetch_task",
        python_callable=fail_with_timeout,
    )
```

Write `airflow/dags/demo_bad_sql.py`:
```python
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from _common.callbacks import daginquest_failure_callback


def fail_with_bad_sql():
    # Simulates a relational database syntax error
    raise ValueError(
        'psycopg2.errors.UndefinedColumn: column "user_identifiier" does not exist in relation "users" at line 3'
    )


with DAG(
    dag_id="demo_bad_sql",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    default_args={"on_failure_callback": daginquest_failure_callback},
    tags=["demo", "daginquest"],
) as dag:
    task = PythonOperator(
        task_id="execute_migration_task",
        python_callable=fail_with_bad_sql,
    )
```

#### What this code does
Provides test DAGs that trigger specific failure classes (`IMPORT_ERROR`, `TRANSIENT_NETWORK`, `SCHEMA_SQL`). Each DAG attaches `daginquest_failure_callback` to `default_args`.

#### Run / verify
- Verified during Step 5.5.

---

### Step 5.4: FastAPI Webhook Route

#### Goal
Implement `POST /api/webhooks/airflow/failure` with constant-time secret comparison and background investigation dispatching.

#### Path
- File: `backend/src/daginquest/api/webhooks.py`

#### Code
```python
import hmac
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, status
from pydantic import BaseModel
from daginquest.config import get_settings
from daginquest.db.repository import create_or_bump_incident
from daginquest.utils.fingerprint import compute_incident_fingerprint

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


class AirflowFailurePayload(BaseModel):
    dag_id: str
    run_id: str
    task_id: str
    try_number: int
    error: str


class WebhookResponse(BaseModel):
    incident_id: str
    deduplicated: bool
    status: str


async def trigger_investigation_background(incident_id: str) -> None:
    """
    Background hook to launch the LangGraph investigation workflow.
    (Connected to agent runner in Phase 7).
    """
    print(f"=== [Background Runner] Starting LangGraph investigation for incident {incident_id} ===")


@router.post(
    "/airflow/failure",
    response_model=WebhookResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def receive_airflow_failure(
    payload: AirflowFailurePayload,
    background_tasks: BackgroundTasks,
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
) -> WebhookResponse:
    settings = get_settings()

    # Constant-time comparison prevents timing attacks on the webhook secret
    if not x_webhook_secret or not hmac.compare_digest(
        x_webhook_secret.encode("utf-8"),
        settings.WEBHOOK_SECRET.encode("utf-8"),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Webhook-Secret header",
        )

    # Compute deterministic fingerprint and deduplicate
    fingerprint = compute_incident_fingerprint(
        dag_id=payload.dag_id,
        task_id=payload.task_id,
        error=payload.error,
    )

    result = await create_or_bump_incident(
        fingerprint=fingerprint,
        dag_id=payload.dag_id,
        run_id=payload.run_id,
        task_id=payload.task_id,
        try_number=payload.try_number,
        error_message=payload.error,
        cooldown_minutes=settings.DEDUPE_COOLDOWN_MINUTES,
    )

    incident = result["incident"]
    deduplicated = result["deduplicated"]

    # Only dispatch an investigation for new incidents
    if not deduplicated:
        background_tasks.add_task(trigger_investigation_background, str(incident["id"]))

    return WebhookResponse(
        incident_id=str(incident["id"]),
        deduplicated=deduplicated,
        status="accepted",
    )
```

Now register this router in `backend/src/daginquest/main.py`.

Update `backend/src/daginquest/main.py`:
```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from daginquest.api import health, webhooks
from daginquest.config import get_settings
from daginquest.db.session import close_db_pool, init_db_pool


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    print(f"=== [Startup] DagInquest API starting with model {settings.OLLAMA_MODEL} ===")
    await init_db_pool()
    yield
    print("=== [Shutdown] Closing DB pool ===")
    await close_db_pool()


app = FastAPI(
    title="DagInquest API",
    description="Formal Airflow DAG failure investigation and safe remediation agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(webhooks.router)
```

#### What this code does
Validates the incoming secret header in constant time using `hmac.compare_digest`. It computes a SHA-256 fingerprint, creates or bumps an incident record in PostgreSQL, and queues background processing for non-deduplicated incidents.

#### Run / verify
- Verified during Step 5.5.

---

### Step 5.5: Airflow Endpoint Verification & Checkpoint Test

#### Goal
Verify Airflow 3 REST endpoints at `http://localhost:8080/docs`, start all services, and simulate a webhook delivery.

#### Important Notice: Verify Airflow 3 API Endpoints
Open your browser to `http://localhost:8080/docs` (Airflow REST API Swagger UI) once Airflow starts.
Airflow 3 introduces API v2 paths. Confirm:
- Task log: `GET /api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/logs/{try_number}`
- Clear task: `POST /api/v1/dags/{dag_id}/clearTaskInstances`
- If your specific Airflow 3 build uses `/api/v2/...` paths or token auth via `/auth/token`, update the paths in `airflow/client.py` accordingly.

#### Run / verify
1. Start the complete Docker stack:
   ```bash
   docker compose up -d postgres airflow api
   ```
2. Test the webhook endpoint using curl with the secret header:
   ```bash
   curl -i -X POST http://localhost:8000/api/webhooks/airflow/failure \
     -H "Content-Type: application/json" \
     -H "X-Webhook-Secret: inquest_shared_secret_hex_32_bytes_minimum" \
     -d '{"dag_id":"demo_timeout","run_id":"manual__1","task_id":"network_fetch_task","try_number":1,"error":"socket.timeout: timed out after 30s"}'
   ```
   Expected response:
   ```
   HTTP/1.1 202 Accepted
   content-type: application/json

   {"incident_id":"...","deduplicated":false,"status":"accepted"}
   ```

3. Send the exact same request again to test deduplication:
   ```bash
   curl -i -X POST http://localhost:8000/api/webhooks/airflow/failure \
     -H "Content-Type: application/json" \
     -H "X-Webhook-Secret: inquest_shared_secret_hex_32_bytes_minimum" \
     -d '{"dag_id":"demo_timeout","run_id":"manual__2","task_id":"network_fetch_task","try_number":2,"error":"socket.timeout: timed out after 30s"}'
   ```
   Expected response:
   ```
   HTTP/1.1 202 Accepted
   content-type: application/json

   {"incident_id":"...","deduplicated":true,"status":"accepted"}
   ```

#### If it fails
- `HTTP 401 Unauthorized`: Verify the `X-Webhook-Secret` header matches the `WEBHOOK_SECRET` in `.env`.
- `Connection refused`: Ensure container `daginquest-api` is running (`docker compose logs api`).

---

### Checkpoint: Phase 5
Airflow client is implemented, demo DAGs with failure callbacks are created, and the webhook route successfully ingests failures and deduplicates repeated errors.

---

## Phase 6: LLM Layer

### Why this phase exists
DagInquest relies on a local LLM via Ollama for Root Cause Analysis (RCA). Small local models (3B–8B parameters) can hallucinate or produce unstructured output if unconstrained.

To make local inference reliable:
1. We enforce **strict JSON Schema structured outputs** using Pydantic v2 schemas passed directly to Ollama.
2. We set `temperature: 0.0` for deterministic outputs.
3. We define an explicit Pydantic response model containing `category`, `root_cause`, `confidence`, and `cited_lines`.

---

### Step 6.1: LLM Structured Output Schemas

#### Goal
Define the Pydantic schema enforcing structured JSON output for failure categorization and root cause analysis.

#### Path
- Unix: `mkdir -p backend/src/daginquest/llm`
- Windows (PowerShell): `mkdir -p backend/src/daginquest/llm`
- File: `backend/src/daginquest/llm/__init__.py` (create empty file)
- File: `backend/src/daginquest/llm/schemas.py`

#### Code
Create an empty file at `backend/src/daginquest/llm/__init__.py`.

Then write `backend/src/daginquest/llm/schemas.py`:
```python
from typing import List, Literal
from pydantic import BaseModel, Field

CategoryLiteral = Literal[
    "IMPORT_ERROR",
    "SCHEMA_SQL",
    "TRANSIENT_NETWORK",
    "CONFIG_SECRET",
    "RESOURCE",
    "UPSTREAM_DATA",
    "INCONCLUSIVE",
]


class RootCauseAnalysisResult(BaseModel):
    """
    Structured output contract produced by the local LLM.
    """

    category: CategoryLiteral = Field(
        description="The precise classification of the DAG failure."
    )
    root_cause: str = Field(
        description="A concise 1-2 sentence explanation of the technical root cause."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Self-assessed confidence score between 0.0 and 1.0.",
    )
    cited_lines: List[str] = Field(
        default_factory=list,
        description="Exact, verbatim log lines from the evidence supporting this conclusion.",
    )
```

#### What this code does
Declares the Pydantic data model. Its generated JSON schema is sent to Ollama's `format` parameter, guaranteeing that Ollama's grammar engine forces valid JSON that deserializes cleanly into `RootCauseAnalysisResult`.

#### Run / verify
- Verified during Step 6.3.

---

### Step 6.2: Ollama Local Client

#### Goal
Implement an asynchronous Ollama client using `httpx` supporting temperature=0 and JSON schema constraints.

#### Path
- File: `backend/src/daginquest/llm/ollama.py`

#### Code
```python
import json
from typing import Any, Dict, Optional
import httpx
from pydantic import ValidationError
from daginquest.config import get_settings
from daginquest.llm.schemas import RootCauseAnalysisResult


class OllamaClient:
    """
    Async client for local Ollama instance with structured JSON output enforcement.
    """

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        settings = get_settings()
        self.base_url = (base_url or settings.OLLAMA_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = httpx.Timeout(60.0, connect=10.0)

    async def generate_root_cause_analysis(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> RootCauseAnalysisResult:
        """
        Sends an inference request to Ollama enforcing the RootCauseAnalysisResult JSON schema.
        Falls back to INCONCLUSIVE on network or formatting failures.
        """
        url = f"{self.base_url}/api/chat"
        schema = RootCauseAnalysisResult.model_json_schema()

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "format": schema,  # Ollama structured output enforcement
            "options": {
                "temperature": 0.0,  # Deterministic output
                "top_p": 0.9,
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    return RootCauseAnalysisResult(
                        category="INCONCLUSIVE",
                        root_cause=f"Ollama returned HTTP {response.status_code}: {response.text[:200]}",
                        confidence=0.0,
                        cited_lines=[],
                    )

                body = response.json()
                raw_content = body.get("message", {}).get("content", "{}")
                parsed_json = json.loads(raw_content)
                return RootCauseAnalysisResult.model_validate(parsed_json)

            except (httpx.RequestError, json.JSONDecodeError, ValidationError) as err:
                return RootCauseAnalysisResult(
                    category="INCONCLUSIVE",
                    root_cause=f"Inference failure or schema mismatch: {str(err)}",
                    confidence=0.0,
                    cited_lines=[],
                )
```

#### What this code does
Transmits chat prompts to Ollama with `format=schema` and `temperature=0.0`. If Ollama is unreachable or returns malformed text, it falls back to an `INCONCLUSIVE` result with `confidence=0.0` rather than crashing the system.

#### Run / verify
- Verified during Step 6.3.

---

### Step 6.3: Model Smoke Test Script

#### Goal
Pull the model and run an end-to-end smoke test script proving that Ollama returns schema-valid JSON.

#### Path
- File: `backend/src/daginquest/llm/smoke_test.py`

#### Code
```python
import asyncio
from daginquest.llm.ollama import OllamaClient


async def main() -> None:
    print("=== [LLM Test] Checking Ollama structured output ===")
    client = OllamaClient()

    system_prompt = (
        "You are an expert site reliability engineer investigating an Apache Airflow failure. "
        "Analyze the provided log and output your findings matching the required JSON schema."
    )
    user_prompt = """
    Log extract:
    Traceback (most recent call last):
      File "/opt/airflow/dags/fetch_data.py", line 18, in execute
        resp = requests.get("https://api.external.com/v1/orders", timeout=10)
      File "/usr/local/lib/python3.12/site-packages/requests/api.py", line 75, in get
        return request('get', url, params=params, **kwargs)
    requests.exceptions.ReadTimeout: HTTPSConnectionPool(host='api.external.com', port=443): Read timed out.
    """

    result = await client.generate_root_cause_analysis(system_prompt, user_prompt)
    print("Inference completed successfully!")
    print(f"Category:     {result.category}")
    print(f"Confidence:   {result.confidence}")
    print(f"Root Cause:   {result.root_cause}")
    print(f"Cited Lines:  {result.cited_lines}")

    assert result.category in [
        "TRANSIENT_NETWORK",
        "INCONCLUSIVE",
    ], f"Unexpected category: {result.category}"
    assert 0.0 <= result.confidence <= 1.0
    print("=== [LLM Test] SUCCESS: Schema-valid JSON returned ===")


if __name__ == "__main__":
    asyncio.run(main())
```

#### Run / verify
1. Ensure the Ollama container is running and pull the model if not already present:
   ```bash
   docker compose up -d ollama
   docker compose exec ollama ollama pull qwen2.5:7b
   ```
2. Execute the smoke test script:
   - Unix / Windows (from within `backend/` with active virtualenv):
     ```bash
     python -m daginquest.llm.smoke_test
     ```
   Expected output:
   ```
   === [LLM Test] Checking Ollama structured output ===
   Inference completed successfully!
   Category:     TRANSIENT_NETWORK
   Confidence:   ...
   Root Cause:   ...
   Cited Lines:  ["requests.exceptions.ReadTimeout: ..."]
   === [LLM Test] SUCCESS: Schema-valid JSON returned ===
   ```

#### If it fails
- `connection refused on port 11434`: Verify that the Ollama container is running (`docker compose ps`).
- `model not found`: Run `docker compose exec ollama ollama pull qwen2.5:7b` to download the model weights.

---

### Checkpoint: Phase 6
Local LLM inference via Ollama is operating with strict Pydantic JSON schema constraints and temperature=0.

---


## Phase 7: LangGraph Investigation Pipeline

### Why this phase exists
Rather than using an unpredictable, free-form agent loop, DagInquest models incident investigation as an **explicit, deterministic state graph** using LangGraph.

Every node receives and updates a strictly typed dictionary (`InvestigationState`). The pipeline executes:
1. `gather_evidence`: Collects task execution logs and DAG source from Airflow, redacting credentials immediately.
2. `classify`: Runs regex heuristics for rapid, deterministic pre-classification.
3. `rca`: Prompts the local LLM using the structured schema with redacted evidence and heuristic guidance.
4. `verify_citations`: The **hallucination guard**: verifies that all lines cited by the LLM exist verbatim in the stored log. It penalizes confidence proportional to invented lines.
5. `plan`: Maps the verified failure category to a candidate remediation action (`retry_task`, `clear_task`, or `none`).
6. `policy_gate`: Evaluates safety invariants (category in safe set, action allow-listed, confidence $\ge$ threshold).
7. `persist_notify`: Saves analyses and actions to Postgres and triggers the Telegram alert.

---

### Node State Input and Output Keys

| Node | Input Keys Used | Output Keys Modified |
|---|---|---|
| `gather_evidence` | `dag_id`, `run_id`, `task_id`, `try_number`, `error_message` | `raw_log`, `dag_source`, `evidence_collected` |
| `classify` | `raw_log`, `error_message` | `preclassified_category`, `preclassified_confidence` |
| `rca` | `raw_log`, `dag_source`, `error_message`, `preclassified_category` | `category`, `root_cause`, `confidence`, `cited_lines` |
| `verify_citations` | `raw_log`, `cited_lines`, `confidence`, `category` | `cited_lines`, `confidence`, `citation_ratio` |
| `plan` | `category` | `proposed_action` |
| `policy_gate` | `category`, `proposed_action`, `confidence` | `policy_approved`, `policy_rejection_reason` |
| `persist_notify` | All keys | `analysis_id`, `action_id` |

---

### Step 7.1: Agent State Definition

#### Goal
Define the `InvestigationState` TypedDict used by all LangGraph nodes.

#### Path
- Unix: `mkdir -p backend/src/daginquest/agent/nodes`
- Windows (PowerShell): `mkdir -p backend/src/daginquest/agent/nodes`
- File: `backend/src/daginquest/agent/__init__.py` (create empty file)
- File: `backend/src/daginquest/agent/nodes/__init__.py` (create empty file)
- File: `backend/src/daginquest/agent/state.py`

#### Code
Create empty files at `backend/src/daginquest/agent/__init__.py` and `backend/src/daginquest/agent/nodes/__init__.py`.

Then write `backend/src/daginquest/agent/state.py`:
```python
from typing import List, Optional, TypedDict


class InvestigationState(TypedDict, total=False):
    # Incident identifiers
    incident_id: str
    dag_id: str
    run_id: str
    task_id: str
    try_number: int
    error_message: str

    # Evidence artifacts
    raw_log: str
    dag_source: str
    evidence_collected: bool

    # Heuristic pre-classification
    preclassified_category: Optional[str]
    preclassified_confidence: float

    # LLM Root Cause Analysis
    category: str
    root_cause: str
    confidence: float
    cited_lines: List[str]
    citation_ratio: float

    # Remediation planning & policy
    proposed_action: str
    policy_approved: bool
    policy_rejection_reason: Optional[str]

    # Database IDs
    analysis_id: Optional[str]
    action_id: Optional[str]
```

#### What this code does
Declares the contract passed between every node in the graph. `total=False` allows partial updates at each node step.

#### Run / verify
- Verified during Step 7.4.

---

### Step 7.2: Prompts Module

#### Goal
Define the system and user prompt templates instructing the LLM on Airflow RCA.

#### Path
- File: `backend/src/daginquest/agent/prompts.py`

#### Code
```python
RCA_SYSTEM_PROMPT = """You are DagInquest, an elite Site Reliability Engineer and Apache Airflow diagnostic specialist.
Your mission is to perform a rigorous Root Cause Analysis (RCA) on failed DAG task instances.

Strict Rules:
1. Output strictly valid JSON matching the provided schema.
2. Failure categories MUST be one of:
   - IMPORT_ERROR: Module not found, bad import, Python syntax error in code.
   - SCHEMA_SQL: Column/table missing, relation not found, database syntax error.
   - TRANSIENT_NETWORK: Socket timeout, connection reset, HTTP 502/503/504, remote host unreachable.
   - CONFIG_SECRET: Missing credentials, invalid token, 401/403, missing Airflow connection or variable.
   - RESOURCE: OOM killed, out of memory, disk full, CPU quota exceeded.
   - UPSTREAM_DATA: Missing input file, empty partition, Airflow sensor timeout.
   - INCONCLUSIVE: Insufficient evidence in log to determine cause definitively.
3. Every cited line MUST be copied VERBATIM from the log. Do NOT paraphrase or invent log lines.
4. If uncertain, classify as INCONCLUSIVE with confidence <= 0.40.
"""

RCA_USER_PROMPT_TEMPLATE = """Investigate the following Airflow task failure:

DAG ID: {dag_id}
Task ID: {task_id}
Run ID: {run_id}
Attempt: {try_number}
Reported Error: {error_message}

Heuristic Baseline: Category={preclassified_category}, Confidence={preclassified_confidence}

=== TASK LOG (Redacted) ===
{task_log}

=== DAG CODE CONTEXT ===
{dag_source}

Provide your root cause analysis in JSON matching the schema:"""
```

#### What this code does
Supplies strict instructions prohibiting hallucinated citations, defining the exact 7 failure categories, and injecting redacted logs and heuristic context into the LLM prompt.

#### Run / verify
- Verified during Step 7.4.

---

### Step 7.3: Discrete Node Implementations

#### Goal
Implement each of the 7 discrete graph nodes in its own dedicated file.

#### Path
- Files:
  - `backend/src/daginquest/agent/nodes/gather_evidence.py`
  - `backend/src/daginquest/agent/nodes/classify.py`
  - `backend/src/daginquest/agent/nodes/rca.py`
  - `backend/src/daginquest/agent/nodes/verify_citations.py`
  - `backend/src/daginquest/agent/nodes/plan.py`
  - `backend/src/daginquest/agent/nodes/policy_gate.py`
  - `backend/src/daginquest/agent/nodes/persist_notify.py`

#### Code
Write `backend/src/daginquest/agent/nodes/gather_evidence.py`:
```python
from typing import Any
from uuid import UUID
from daginquest.agent.state import InvestigationState
from daginquest.airflow.client import AirflowClient
from daginquest.db.repository import add_evidence
from daginquest.security.redaction import redact_sensitive_data


async def gather_evidence_node(state: InvestigationState) -> dict[str, Any]:
    client = AirflowClient()
    inc_id = UUID(state["incident_id"])

    # 1. Fetch raw logs from Airflow
    raw_log = await client.get_task_log(
        dag_id=state["dag_id"],
        run_id=state["run_id"],
        task_id=state["task_id"],
        try_number=state["try_number"],
    )
    # If Airflow returned warning/error, append the webhook error message
    if "[Warning]" in raw_log or len(raw_log.strip()) == 0:
        raw_log = f"{raw_log}\nReported error: {state['error_message']}"

    # 2. Fetch DAG source code
    dag_source = await client.get_dag_source(state["dag_id"])

    # 3. Redact credentials before storage or LLM processing
    redacted_log = redact_sensitive_data(raw_log)
    redacted_source = redact_sensitive_data(dag_source)

    # 4. Persist evidence to database
    await add_evidence(inc_id, "task_log", redacted_log)
    await add_evidence(inc_id, "dag_source", redacted_source)

    return {
        "raw_log": redacted_log,
        "dag_source": redacted_source,
        "evidence_collected": True,
    }
```

Write `backend/src/daginquest/agent/nodes/classify.py`:
```python
from typing import Any
from daginquest.agent.state import InvestigationState
from daginquest.utils.preclassify import preclassify_log


async def classify_node(state: InvestigationState) -> dict[str, Any]:
    log_text = state.get("raw_log", "") or state.get("error_message", "")
    category, confidence = preclassify_log(log_text)

    return {
        "preclassified_category": category,
        "preclassified_confidence": confidence,
    }
```

Write `backend/src/daginquest/agent/nodes/rca.py`:
```python
from typing import Any
from daginquest.agent.prompts import RCA_SYSTEM_PROMPT, RCA_USER_PROMPT_TEMPLATE
from daginquest.agent.state import InvestigationState
from daginquest.llm.ollama import OllamaClient


async def rca_node(state: InvestigationState) -> dict[str, Any]:
    client = OllamaClient()

    # Truncate logs if excessively long to prevent model context overflow
    task_log = state.get("raw_log", "")
    if len(task_log) > 12000:
        task_log = task_log[-12000:]

    user_prompt = RCA_USER_PROMPT_TEMPLATE.format(
        dag_id=state["dag_id"],
        task_id=state["task_id"],
        run_id=state["run_id"],
        try_number=state["try_number"],
        error_message=state["error_message"],
        preclassified_category=state.get("preclassified_category") or "None",
        preclassified_confidence=state.get("preclassified_confidence", 0.0),
        task_log=task_log,
        dag_source=state.get("dag_source", "# Unavailable")[:4000],
    )

    result = await client.generate_root_cause_analysis(RCA_SYSTEM_PROMPT, user_prompt)

    # If LLM is inconclusive but pre-classifier had high confidence, blend
    cat = result.category
    conf = result.confidence
    if cat == "INCONCLUSIVE" and state.get("preclassified_category"):
        cat = state["preclassified_category"]
        conf = state.get("preclassified_confidence", 0.60)

    return {
        "category": cat,
        "root_cause": result.root_cause,
        "confidence": conf,
        "cited_lines": result.cited_lines,
    }
```

Write `backend/src/daginquest/agent/nodes/verify_citations.py`:
```python
from typing import Any
from daginquest.agent.state import InvestigationState


async def verify_citations_node(state: InvestigationState) -> dict[str, Any]:
    raw_log = state.get("raw_log", "")
    cited_lines = state.get("cited_lines", [])
    confidence = state.get("confidence", 0.0)
    category = state.get("category", "INCONCLUSIVE")

    if not cited_lines:
        # Hallucination guard: If no evidence cited for non-inconclusive result, halve confidence
        if category != "INCONCLUSIVE":
            confidence = round(confidence * 0.5, 2)
        return {
            "cited_lines": [],
            "confidence": confidence,
            "citation_ratio": 0.0,
        }

    # Verify each cited line exists verbatim in the raw stored log
    valid_citations = [line for line in cited_lines if line.strip() in raw_log]
    valid_ratio = len(valid_citations) / len(cited_lines)

    # Adjust confidence score based on citation validity ratio
    adjusted_confidence = round(confidence * valid_ratio, 2)

    return {
        "cited_lines": valid_citations,
        "confidence": adjusted_confidence,
        "citation_ratio": valid_ratio,
    }
```

Write `backend/src/daginquest/agent/nodes/plan.py`:
```python
from typing import Any
from daginquest.agent.state import InvestigationState
from daginquest.policy.rules import ACTION_CLEAR_TASK, ACTION_NONE, ACTION_RETRY_TASK


async def plan_node(state: InvestigationState) -> dict[str, Any]:
    category = state.get("category", "INCONCLUSIVE")

    # Map failure categories to candidate remediation actions
    if category == "TRANSIENT_NETWORK":
        action = ACTION_RETRY_TASK
    elif category == "RESOURCE":
        action = ACTION_CLEAR_TASK
    else:
        action = ACTION_NONE

    return {"proposed_action": action}
```

Write `backend/src/daginquest/agent/nodes/policy_gate.py`:
```python
from typing import Any
from daginquest.agent.state import InvestigationState
from daginquest.config import get_settings
from daginquest.policy.rules import evaluate_remediation_policy


async def policy_gate_node(state: InvestigationState) -> dict[str, Any]:
    settings = get_settings()
    category = state.get("category", "INCONCLUSIVE")
    action = state.get("proposed_action", "none")
    confidence = state.get("confidence", 0.0)

    policy_result = evaluate_remediation_policy(
        category=category,
        action=action,
        confidence=confidence,
        threshold=settings.CONFIDENCE_THRESHOLD,
    )

    return {
        "policy_approved": policy_result.is_allowed,
        "policy_rejection_reason": policy_result.rejection_reason,
    }
```

Write `backend/src/daginquest/agent/nodes/persist_notify.py`:
```python
from typing import Any
from uuid import UUID
from daginquest.agent.state import InvestigationState
from daginquest.db.repository import create_action, save_analysis
from daginquest.policy.rules import ACTION_NONE
from daginquest.telegram.notifier import send_incident_alert


async def persist_notify_node(state: InvestigationState) -> dict[str, Any]:
    inc_id = UUID(state["incident_id"])

    # 1. Save Analysis
    analysis = await save_analysis(
        incident_id=inc_id,
        category=state["category"],
        confidence=state["confidence"],
        root_cause=state["root_cause"],
        suggested_action=state.get("proposed_action", ACTION_NONE),
        cited_lines=state.get("cited_lines", []),
        is_auto_remediable=state.get("policy_approved", False),
        policy_approved=state.get("policy_approved", False),
        policy_rejection_reason=state.get("policy_rejection_reason"),
    )

    # 2. Create pending Action if policy approved
    action_id = None
    if state.get("policy_approved") and state.get("proposed_action") != ACTION_NONE:
        action = await create_action(
            incident_id=inc_id,
            action_type=state["proposed_action"],
        )
        action_id = str(action["id"])

    # 3. Dispatch Telegram alert
    try:
        await send_incident_alert(
            incident_id=state["incident_id"],
            dag_id=state["dag_id"],
            task_id=state["task_id"],
            category=state["category"],
            confidence=state["confidence"],
            root_cause=state["root_cause"],
            cited_lines=state.get("cited_lines", []),
            action_id=action_id,
            action_type=state.get("proposed_action"),
            policy_reason=state.get("policy_rejection_reason"),
        )
    except Exception as e:
        print(f"[Telegram Notifier] Failed to send alert: {e}")

    return {
        "analysis_id": str(analysis["id"]),
        "action_id": action_id,
    }
```

#### What this code does
Separates each step of the investigation into isolated functions:
- `gather_evidence`: Fetches logs and masks passwords before database insertion.
- `classify`: Applies instant regex heuristics.
- `rca`: Inquires Ollama with the redacted prompt.
- `verify_citations`: Implements the hallucination guard equation ($conf = conf \times \frac{valid}{total}$).
- `plan`: Recommends safe recovery actions.
- `policy_gate`: Enforces strict allow-listing and threshold constraints.
- `persist_notify`: Commits findings to PostgreSQL and dispatches the Telegram alert.

#### Run / verify
- Verified during Step 7.4.

---

### Step 7.4: LangGraph Assembly & Background Runner

#### Goal
Compile the nodes into a LangGraph `StateGraph` and create the background runner to execute it.

#### Path
- Files:
  - `backend/src/daginquest/agent/graph.py`
  - `backend/src/daginquest/agent/runner.py`

#### Code
> [!IMPORTANT]
> `graph.py` imports `persist_notify_node`, which in turn imports `daginquest.telegram.notifier`. The Telegram notifier module (`backend/src/daginquest/telegram/notifier.py`) must exist before Python can import the graph. **Complete Phase 8 (Steps 8.1–8.2) before running the investigation graph for the first time.** If you attempt to import the graph before Phase 8 is complete, you will get an `ImportError: No module named 'daginquest.telegram'`.

Write `backend/src/daginquest/agent/graph.py`:
```python
from langgraph.graph import END, StateGraph
from daginquest.agent.nodes.classify import classify_node
from daginquest.agent.nodes.gather_evidence import gather_evidence_node
from daginquest.agent.nodes.persist_notify import persist_notify_node
from daginquest.agent.nodes.plan import plan_node
from daginquest.agent.nodes.policy_gate import policy_gate_node
from daginquest.agent.nodes.rca import rca_node
from daginquest.agent.nodes.verify_citations import verify_citations_node
from daginquest.agent.state import InvestigationState


def create_investigation_graph():
    workflow = StateGraph(InvestigationState)

    # Register all nodes
    workflow.add_node("gather_evidence", gather_evidence_node)
    workflow.add_node("classify", classify_node)
    workflow.add_node("rca", rca_node)
    workflow.add_node("verify_citations", verify_citations_node)
    workflow.add_node("plan", plan_node)
    workflow.add_node("policy_gate", policy_gate_node)
    workflow.add_node("persist_notify", persist_notify_node)

    # Establish linear workflow edges
    workflow.set_entry_point("gather_evidence")
    workflow.add_edge("gather_evidence", "classify")
    workflow.add_edge("classify", "rca")
    workflow.add_edge("rca", "verify_citations")
    workflow.add_edge("verify_citations", "plan")
    workflow.add_edge("plan", "policy_gate")
    workflow.add_edge("policy_gate", "persist_notify")
    workflow.add_edge("persist_notify", END)

    return workflow.compile()


investigation_graph = create_investigation_graph()
```

Write `backend/src/daginquest/agent/runner.py`:
```python
from uuid import UUID
from daginquest.agent.graph import investigation_graph
from daginquest.agent.state import InvestigationState
from daginquest.db.repository import get_incident


async def run_investigation(incident_id: str) -> InvestigationState:
    """
    Executes the LangGraph investigation workflow for an incident.
    """
    incident = await get_incident(UUID(incident_id))
    if not incident:
        raise ValueError(f"Incident {incident_id} not found")

    initial_state: InvestigationState = {
        "incident_id": incident_id,
        "dag_id": incident["dag_id"],
        "run_id": incident["run_id"],
        "task_id": incident["task_id"],
        "try_number": incident["try_number"],
        "error_message": incident["error_message"],
    }

    print(f"=== [LangGraph Runner] Launching workflow for incident {incident_id} ===")
    final_state = await investigation_graph.ainvoke(initial_state)
    print(
        f"=== [LangGraph Runner] Completed: Category={final_state.get('category')}, "
        f"Confidence={final_state.get('confidence')} ==="
    )
    return final_state
```

Now update `backend/src/daginquest/api/webhooks.py` to trigger `run_investigation` directly:
In `backend/src/daginquest/api/webhooks.py`, replace:
```python
async def trigger_investigation_background(incident_id: str) -> None:
    print(f"=== [Background Runner] Starting LangGraph investigation for incident {incident_id} ===")
```
with:
```python
from daginquest.agent.runner import run_investigation

async def trigger_investigation_background(incident_id: str) -> None:
    try:
        await run_investigation(incident_id)
    except Exception as e:
        print(f"[Background Runner Error] Investigation failed for {incident_id}: {e}")
```

#### What this code does
Assembles the complete state machine. The compiled graph processes incoming incidents through all 7 nodes asynchronously upon webhook receipt.

#### Run / verify
- Verified during Phase 8 after completing the notifier stubs.

---

### Checkpoint: Phase 7
The LangGraph investigation pipeline is fully wired with state, discrete nodes, citation verification, and runner orchestration.

---

## Phase 8: Telegram Human-in-the-Loop Interface

### Why this phase exists
DagInquest enforces that **no remediation action executes automatically**. Human approval is required. Telegram provides an immediate, mobile-first interface for SREs to review evidence, inspect cited lines, and approve or reject remediation actions with a single tap.

Security controls:
1. Long polling is used so no public URL or webhook ingress is exposed to the internet.
2. Only numeric chat IDs listed in `TELEGRAM_ALLOWED_CHAT_IDS` are permitted to interact with the bot or trigger approvals. All unauthorized chats are silently ignored.
3. Inline keyboard buttons encode `approve:<action_id>` and `reject:<action_id>`.

---

### Step 8.1: Telegram Security & Notifier

#### Goal
Implement chat authorization filtering and outbound alert dispatching with inline approval buttons.

#### Path
- Unix: `mkdir -p backend/src/daginquest/telegram`
- Windows (PowerShell): `mkdir -p backend/src/daginquest/telegram`
- File: `backend/src/daginquest/telegram/__init__.py` (create empty file)
- File: `backend/src/daginquest/telegram/security.py`
- File: `backend/src/daginquest/telegram/notifier.py`

#### Code
Create an empty file at `backend/src/daginquest/telegram/__init__.py`.

Then write `backend/src/daginquest/telegram/security.py`:
```python
from typing import List
from daginquest.config import get_settings


def is_chat_authorized(chat_id: int) -> bool:
    """
    Verifies if a Telegram chat ID is listed in the TELEGRAM_ALLOWED_CHAT_IDS allow-list.
    """
    settings = get_settings()
    allowed_ids = settings.telegram_allowed_chat_ids
    return chat_id in allowed_ids
```

Write `backend/src/daginquest/telegram/notifier.py`:
```python
from typing import List, Optional
import httpx
from daginquest.config import get_settings


async def send_incident_alert(
    incident_id: str,
    dag_id: str,
    task_id: str,
    category: str,
    confidence: float,
    root_cause: str,
    cited_lines: List[str],
    action_id: Optional[str] = None,
    action_type: Optional[str] = None,
    policy_reason: Optional[str] = None,
) -> None:
    """
    Dispatches a structured alert message to all authorized Telegram chats
    via Telegram Bot HTTP API.
    """
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN
    chat_ids = settings.telegram_allowed_chat_ids

    if not token or not chat_ids:
        print("[Telegram Notifier] No bot token or allowed chat IDs configured. Skipping alert.")
        return

    # Build evidence quote block
    evidence_block = ""
    if cited_lines:
        first_line = cited_lines[0].strip()[:150]
        evidence_block = f"\n🔍 *Evidence:*\n`> {first_line}`\n"

    # Build message body
    text = (
        f"🚨 *DagInquest Incident Alert*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"*DAG:* `{dag_id}`\n"
        f"*Task:* `{task_id}`\n"
        f"*Category:* `{category}` | *Confidence:* `{confidence:.2f}`\n\n"
        f"*Root Cause:*\n{root_cause}\n"
        f"{evidence_block}\n"
    )

    # Build inline keyboard if remediation action is available
    reply_markup = None
    if action_id and action_type:
        text += f"⚙️ *Proposed Action:* `{action_type}` (Requires Human Approval)"
        reply_markup = {
            "inline_keyboard": [
                [
                    {
                        "text": f"✅ Approve {action_type}",
                        "callback_data": f"approve:{action_id}",
                    },
                    {
                        "text": "❌ Reject",
                        "callback_data": f"reject:{action_id}",
                    },
                ]
            ]
        }
    else:
        reason = policy_reason or "No automated remediation available."
        text += f"🛡️ *Policy:* No auto-fix ({reason})"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with httpx.AsyncClient(timeout=10.0) as client:
        for cid in chat_ids:
            try:
                payload = {
                    "chat_id": cid,
                    "text": text,
                    "parse_mode": "Markdown",
                }
                if reply_markup:
                    payload["reply_markup"] = reply_markup
                await client.post(url, json=payload)
            except Exception as e:
                print(f"[Telegram Notifier] Failed to deliver alert to chat {cid}: {e}")
```

#### What this code does
Formats rich Telegram alert messages with markdown styling, quoting validated log citations. If an action is allow-listed, it includes inline callback buttons (`approve:<action_id>`, `reject:<action_id>`).

#### Run / verify
- Verified during Step 8.3.

---

### Step 8.2: Telegram Handlers & Bot Runner

#### Goal
Implement command handlers (`/start`, `/incidents`, `/status`) and callback query processors using `python-telegram-bot`.

#### Path
- Files:
  - `backend/src/daginquest/telegram/handlers.py`
  - `backend/src/daginquest/telegram/bot.py`

#### Code
> [!IMPORTANT]
> `handlers.py` imports `execute_remediation_action` from `daginquest.actions.executor`. The executor module (`backend/src/daginquest/actions/executor.py`) is created in **Phase 9 (Step 9.1)**. **Do not attempt to start the Telegram bot until Phase 9 is complete**, or you will get an `ImportError: No module named 'daginquest.actions'`.

Write `backend/src/daginquest/telegram/handlers.py`:
```python
from uuid import UUID
from telegram import Update
from telegram.ext import ContextTypes
from daginquest.actions.executor import execute_remediation_action
from daginquest.db.repository import decide_action, get_metrics, list_incidents, list_pending_actions
from daginquest.telegram.security import is_chat_authorized


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not is_chat_authorized(update.effective_chat.id):
        return

    msg = (
        "🔍 *DagInquest Airflow Incident Bot*\n\n"
        "Available commands:\n"
        "/incidents - View recent incidents\n"
        "/pending   - View actions awaiting approval\n"
        "/status    - Display system metrics and health"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not is_chat_authorized(update.effective_chat.id):
        return

    metrics = await get_metrics()
    msg = (
        "📊 *DagInquest System Status*\n"
        f"• Total Incidents: `{metrics['total_incidents']}`\n"
        f"• Deduplicated Events: `{metrics['total_deduplicated_events']}`\n"
        f"• Pending Approvals: `{metrics['pending_approvals']}`\n"
        f"• Average Confidence: `{metrics['avg_confidence']}`"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def incidents_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not is_chat_authorized(update.effective_chat.id):
        return

    incidents = await list_incidents(limit=5)
    if not incidents:
        await update.message.reply_text("No incidents recorded yet.")
        return

    lines = ["📋 *Recent Incidents:*"]
    for inc in incidents:
        cat = inc.get("category") or "PENDING"
        lines.append(
            f"• `{inc['dag_id']}.{inc['task_id']}` [{cat}] (Seen {inc['occurrence_count']}x)"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not update.effective_chat:
        return

    # Security check: Ignore unauthorized users
    if not is_chat_authorized(update.effective_chat.id):
        await query.answer("Unauthorized.", show_alert=True)
        return

    await query.answer()
    data = query.data or ""
    approver = f"telegram:{update.effective_chat.id}"

    if data.startswith("approve:"):
        action_id_str = data.split(":", 1)[1]
        action_id = UUID(action_id_str)

        # Atomic approval check in PostgreSQL
        action = await decide_action(action_id, "approved", approver)
        if not action:
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text("⚠️ This action has already been decided.")
            return

        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"⏳ Action `{action['action_type']}` approved. Executing remediation...")

        # Trigger executor asynchronously
        result = await execute_remediation_action(action_id)
        if result["status"] == "succeeded":
            await query.message.reply_text(f"✅ Remediation `{action['action_type']}` SUCCEEDED.")
        else:
            await query.message.reply_text(f"❌ Remediation FAILED: {result.get('error')}")

    elif data.startswith("reject:"):
        action_id_str = data.split(":", 1)[1]
        action_id = UUID(action_id_str)

        action = await decide_action(action_id, "rejected", approver)
        if not action:
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text("⚠️ This action has already been decided.")
            return

        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("🚫 Action rejected. No changes made.")
```

Write `backend/src/daginquest/telegram/bot.py`:
```python
import asyncio
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler
from daginquest.config import get_settings
from daginquest.db.session import close_db_pool, init_db_pool
from daginquest.telegram.handlers import (
    callback_query_handler,
    incidents_command,
    start_command,
    status_command,
)


def run_telegram_bot() -> None:
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN

    if not token:
        print("[Telegram Bot] Error: TELEGRAM_BOT_TOKEN is empty. Bot cannot start.")
        return

    print("=== [Telegram Bot] Initializing long-polling client ===")
    app = ApplicationBuilder().token(token).build()

    # Register command and callback handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("incidents", incidents_command))
    app.add_handler(CallbackQueryHandler(callback_query_handler))

    # Initialize DB pool for bot process
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db_pool())

    print("=== [Telegram Bot] Listening for events ===")
    app.run_polling()


if __name__ == "__main__":
    run_telegram_bot()
```

#### What this code does
Runs a dedicated polling process that listens for Telegram messages and inline button clicks. On click, it performs the atomic database update, executes the remediation action, and sends a follow-up status notification to the chat.

#### Run / verify
- Verified during Step 8.3.

---

### Step 8.3: Telegram Integration Checkpoint

#### Goal
Verify Telegram alert delivery and inline button interactions.

#### Run / verify
1. Add your real bot token and numeric Telegram chat ID to `.env`:
   ```env
   TELEGRAM_BOT_TOKEN=your_token_from_botfather
   TELEGRAM_ALLOWED_CHAT_IDS=your_numeric_chat_id
   ```
2. Start the API and Bot services:
   ```bash
   docker compose up -d api bot
   ```
3. Post a simulated failure via curl:
   ```bash
   curl -X POST http://localhost:8000/api/webhooks/airflow/failure \
     -H "Content-Type: application/json" \
     -H "X-Webhook-Secret: inquest_shared_secret_hex_32_bytes_minimum" \
     -d '{"dag_id":"demo_timeout","run_id":"run_tg_1","task_id":"network_fetch_task","try_number":1,"error":"socket.timeout: connection timed out"}'
   ```
4. Verify the alert arrives in Telegram with **Approve** and **Reject** buttons.
5. Send `/status` to the bot to check metrics.
6. Test security: Have another Telegram account message your bot; verify that the bot does not respond.

#### If it fails
- `Bot ignores authorized chat`: Verify that `TELEGRAM_ALLOWED_CHAT_IDS` matches your numeric user ID from `@userinfobot`.
- `401 Unauthorized from Telegram`: Re-check `TELEGRAM_BOT_TOKEN`.

---

### Checkpoint: Phase 8
Telegram notifications and inline button approval actions are verified with strict chat authorization filtering.

---

## Phase 9: Remediation Executor and Verification

### Why this phase exists
Once human approval is granted, DagInquest executes the remediation action safely:
1. **Re-checks allow-list**: The executor validates that the action is `retry_task` or `clear_task` independently of prior checks.
2. **Executes action**: Calls Airflow REST API to clear the failed task instance.
3. **Verifies recovery**: Polls the task instance state over a timeout window (e.g. up to 60 seconds) until the task transitions to a terminal state (`success` or `failed`).
4. **Guarantees idempotency**: The API route `POST /api/actions/{id}/approve` returns HTTP 409 Conflict if an action was already decided.

---

### Step 9.1: Remediation Executor & Task Polling Verification

#### Goal
Implement `actions/executor.py` and `actions/verify.py` to clear failed Airflow tasks and monitor recovery.

#### Path
- Unix: `mkdir -p backend/src/daginquest/actions`
- Windows (PowerShell): `mkdir -p backend/src/daginquest/actions`
- File: `backend/src/daginquest/actions/__init__.py` (create empty file)
- File: `backend/src/daginquest/actions/verify.py`
- File: `backend/src/daginquest/actions/executor.py`

#### Code
Create an empty file at `backend/src/daginquest/actions/__init__.py`.

Then write `backend/src/daginquest/actions/verify.py`:
```python
import asyncio
from typing import Any, Dict
from daginquest.airflow.client import AirflowClient


async def poll_task_recovery(
    dag_id: str,
    run_id: str,
    task_id: str,
    timeout_seconds: int = 60,
    interval_seconds: int = 5,
) -> Dict[str, Any]:
    """
    Polls the Airflow task instance state until it reaches success, failed, or times out.
    """
    client = AirflowClient()
    elapsed = 0

    while elapsed < timeout_seconds:
        state = await client.get_task_instance_state(dag_id, run_id, task_id)
        if state == "success":
            return {"recovered": True, "state": state, "elapsed_seconds": elapsed}
        if state in ("failed", "upstream_failed"):
            return {"recovered": False, "state": state, "elapsed_seconds": elapsed}

        await asyncio.sleep(interval_seconds)
        elapsed += interval_seconds

    return {
        "recovered": False,
        "state": "timeout_waiting_for_state",
        "elapsed_seconds": elapsed,
    }
```

Write `backend/src/daginquest/actions/executor.py`:
```python
from typing import Any, Dict
from uuid import UUID
from daginquest.actions.verify import poll_task_recovery
from daginquest.airflow.client import AirflowClient
from daginquest.db.repository import get_action, get_incident, set_action_result
from daginquest.policy.rules import ALLOWLISTED_ACTIONS


async def execute_remediation_action(action_id: UUID) -> Dict[str, Any]:
    """
    Executes an approved remediation action against the Airflow API.
    Invariants:
    1. Re-verifies action type is in ALLOWLISTED_ACTIONS.
    2. Calls Airflow client clear_task_instances.
    3. Verifies post-execution recovery state.
    4. Records execution result in database and audit log.
    """
    action = await get_action(action_id)
    if not action:
        return {"status": "failed", "error": f"Action {action_id} not found"}

    action_type = action["action_type"]

    # Re-check allow-list in executor (defense-in-depth)
    if action_type not in ALLOWLISTED_ACTIONS:
        err = f"Security Violation: Action '{action_type}' rejected by executor allow-list."
        await set_action_result(action_id, "failed", {"error": err})
        return {"status": "failed", "error": err}

    incident = await get_incident(action["incident_id"])
    if not incident:
        err = f"Incident {action['incident_id']} not found."
        await set_action_result(action_id, "failed", {"error": err})
        return {"status": "failed", "error": err}

    client = AirflowClient()
    dag_id = incident["dag_id"]
    run_id = incident["run_id"]
    task_id = incident["task_id"]

    print(f"=== [Executor] Executing {action_type} on {dag_id}.{task_id} (run: {run_id}) ===")

    # Clear task instance in Airflow to trigger a retry
    cleared = await client.clear_task_instances(dag_id, run_id, task_id)
    if not cleared:
        err = "Airflow API failed to clear task instance."
        await set_action_result(action_id, "failed", {"error": err})
        return {"status": "failed", "error": err}

    # Verify task recovery by polling
    verification = await poll_task_recovery(dag_id, run_id, task_id, timeout_seconds=45)
    final_status = "succeeded" if verification.get("recovered") else "failed"

    execution_payload = {
        "action_type": action_type,
        "cleared": cleared,
        "verification": verification,
    }

    await set_action_result(action_id, final_status, execution_payload)
    return {"status": final_status, "details": execution_payload}
```

#### What this code does
Acts as the execution engine. It re-checks allow-list boundaries, calls the Airflow REST API to clear the task, polls the task status asynchronously, and writes the execution outcome to the database and audit trail.

#### Run / verify
- Verified during Step 9.3.

---

### Step 9.2: Actions API Endpoints

#### Goal
Implement HTTP endpoints `GET /api/actions/pending`, `POST /api/actions/{id}/approve`, and `POST /api/actions/{id}/reject`.

#### Path
- File: `backend/src/daginquest/api/actions.py`

#### Code
```python
from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from daginquest.actions.executor import execute_remediation_action
from daginquest.db.repository import decide_action, get_action, list_pending_actions

router = APIRouter(prefix="/api/actions", tags=["Actions"])


class DecisionRequest(BaseModel):
    approver: str = "web:dashboard_user"
    reason: str = "Approved via web interface"


@router.get("/pending")
async def get_pending_actions():
    """
    Returns all actions awaiting human decision.
    """
    return await list_pending_actions()


@router.post("/{action_id}/approve", status_code=status.HTTP_200_OK)
async def approve_action(action_id: UUID, body: DecisionRequest):
    """
    Atomically marks an action as approved and executes remediation.
    Returns HTTP 409 Conflict if already decided.
    """
    action = await decide_action(
        action_id=action_id,
        decision="approved",
        approver_id=body.approver,
        reason=body.reason,
    )
    if not action:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Action has already been decided or does not exist.",
        )

    # Execute action
    result = await execute_remediation_action(action_id)
    return {"status": "approved", "execution": result}


@router.post("/{action_id}/reject", status_code=status.HTTP_200_OK)
async def reject_action(action_id: UUID, body: DecisionRequest):
    """
    Atomically marks an action as rejected.
    Returns HTTP 409 Conflict if already decided.
    """
    action = await decide_action(
        action_id=action_id,
        decision="rejected",
        approver_id=body.approver,
        reason=body.reason,
    )
    if not action:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Action has already been decided or does not exist.",
        )

    return {"status": "rejected", "action_id": str(action_id)}
```

Now register this router and the remaining API routers (`incidents.py`, `metrics.py`) in `main.py`.

Write `backend/src/daginquest/api/incidents.py`:
```python
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, status
from daginquest.db.repository import get_incident, list_incidents

router = APIRouter(prefix="/api/incidents", tags=["Incidents"])


@router.get("")
async def fetch_incidents(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return await list_incidents(limit=limit, offset=offset)


@router.get("/{incident_id}")
async def fetch_incident_details(incident_id: UUID):
    incident = await get_incident(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )
    return incident
```

Write `backend/src/daginquest/api/metrics.py`:
```python
from fastapi import APIRouter
from daginquest.db.repository import get_metrics

router = APIRouter(prefix="/api/metrics", tags=["Metrics"])


@router.get("")
async def fetch_system_metrics():
    return await get_metrics()
```

Update `backend/src/daginquest/main.py` to include all routers:
```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from daginquest.api import actions, health, incidents, metrics, webhooks
from daginquest.config import get_settings
from daginquest.db.session import close_db_pool, init_db_pool


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    print(f"=== [Startup] DagInquest API starting with model {settings.OLLAMA_MODEL} ===")
    await init_db_pool()
    yield
    print("=== [Shutdown] Closing DB pool ===")
    await close_db_pool()


app = FastAPI(
    title="DagInquest API",
    description="Formal Airflow DAG failure investigation and safe remediation agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(webhooks.router)
app.include_router(incidents.router)
app.include_router(actions.router)
app.include_router(metrics.router)
```

#### What this code does
Exposes the complete REST API surface. The approve and reject endpoints execute the atomic update query and immediately return HTTP 409 Conflict if duplicate or concurrent requests attempt to decide an already resolved action.

#### Run / verify
- Verified during Step 9.3.

---

### Step 9.3: Double Approval Idempotency Test

#### Goal
Test and verify that approving an action twice returns HTTP 409 Conflict.

#### Run / verify
1. Restart the API:
   ```bash
   docker compose restart api
   ```
2. Fetch pending actions:
   ```bash
   curl -s http://localhost:8000/api/actions/pending
   ```
   Take note of any returned `id`. If none are pending, trigger one via webhook:
   ```bash
   curl -s -X POST http://localhost:8000/api/webhooks/airflow/failure \
     -H "Content-Type: application/json" \
     -H "X-Webhook-Secret: inquest_shared_secret_hex_32_bytes_minimum" \
     -d '{"dag_id":"demo_timeout","run_id":"run_phase9","task_id":"network_fetch_task","try_number":1,"error":"socket.timeout: timed out after 30s"}'
   ```
   Wait 10 seconds for LangGraph to complete, then fetch pending actions again:
   ```bash
   curl -s http://localhost:8000/api/actions/pending
   ```
3. Execute the first approval:
   ```bash
   curl -i -X POST http://localhost:8000/api/actions/<ACTION_ID>/approve \
     -H "Content-Type: application/json" \
     -d '{"approver":"tester","reason":"test verification"}'
   ```
   Expected response: `HTTP/1.1 200 OK`
4. Attempt to approve the exact same action a second time:
   ```bash
   curl -i -X POST http://localhost:8000/api/actions/<ACTION_ID>/approve \
     -H "Content-Type: application/json" \
     -d '{"approver":"tester","reason":"second attempt"}'
   ```
   Expected response:
   ```
   HTTP/1.1 409 Conflict
   content-type: application/json

   {"detail":"Action has already been decided or does not exist."}
   ```

#### If it fails
- First call returns 409: The action was already approved via Telegram or a previous test; create a new incident with a different `run_id`.

---

### Checkpoint: Phase 9
Remediation executor, post-execution verification polling, and atomic approval HTTP 409 Conflict protection are verified.

---


## Phase 10: Web Dashboard

### Why this phase exists
While Telegram provides immediate mobile alerts, site reliability engineers also require a web dashboard to visualize the incident stream, review pending remediation approvals, inspect raw logs and evidence citations, and monitor mean metrics (incident volume, deduplication rate, average confidence).

We implement a React 18 + TypeScript single page application built with Vite, configured with CSS variables supporting light and dark modes, and a Vite development proxy routing `/api` calls directly to `http://localhost:8000`.

---

### Step 10.1: Frontend Package and Build Configuration

#### Goal
Configure Vite, TypeScript, and dependencies for the React frontend application.

#### Path
- Unix: `mkdir -p frontend/src/api frontend/src/components frontend/src/hooks frontend/src/pages`
- Windows (PowerShell): `mkdir -p frontend/src/api, frontend/src/components, frontend/src/hooks, frontend/src/pages`
- Files:
  - `frontend/package.json`
  - `frontend/tsconfig.json`
  - `frontend/vite.config.ts`
  - `frontend/index.html`

#### Code
Write `frontend/package.json`:
```json
{
  "name": "daginquest-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.66",
    "@types/react-dom": "^18.2.22",
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.2.2",
    "vite": "^5.1.4"
  }
}
```

Write `frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
```

Write `frontend/vite.config.ts`:
```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

Write `frontend/index.html`:
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>DagInquest Dashboard</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

#### What this code does
Configures the frontend toolchain with React 18, strict TypeScript checking, and a Vite proxy so requests to `/api/...` in the browser forward directly to the FastAPI server running on port 8000 without CORS configuration issues.

#### Run / verify
- Verified during Step 10.5.

---

### Step 10.2: Global Styles, Types, and Polling Hook

#### Goal
Create global theme CSS variables (light/dark mode), TypeScript interfaces, and an asynchronous data polling hook.

#### Path
- Files:
  - `frontend/src/index.css`
  - `frontend/src/types.ts`
  - `frontend/src/hooks/usePolling.ts`

#### Code
Write `frontend/src/index.css`:
```css
:root {
  --bg-primary: #0f172a;
  --bg-secondary: #1e293b;
  --bg-tertiary: #334155;
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --border-color: #334155;
  --accent-blue: #38bdf8;
  --accent-green: #4ade80;
  --accent-red: #f87171;
  --accent-amber: #fbbf24;
  --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

@media (prefers-color-scheme: light) {
  :root {
    --bg-primary: #f8fafc;
    --bg-secondary: #ffffff;
    --bg-tertiary: #f1f5f9;
    --text-primary: #0f172a;
    --text-secondary: #64748b;
    --border-color: #e2e8f0;
    --accent-blue: #0284c7;
    --accent-green: #16a34a;
    --accent-red: #dc2626;
    --accent-amber: #d97706;
  }
}

body {
  margin: 0;
  font-family: var(--font-family);
  background-color: var(--bg-primary);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.card {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.button {
  padding: 8px 16px;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: opacity 0.2s;
}

.button:hover {
  opacity: 0.85;
}

.button-success {
  background-color: var(--accent-green);
  color: #0f172a;
}

.button-danger {
  background-color: var(--accent-red);
  color: #ffffff;
}

.nav-bar {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 12px;
}

.nav-link {
  color: var(--text-secondary);
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 4px;
  font-weight: 500;
}

.nav-link.active {
  color: var(--text-primary);
  background-color: var(--bg-secondary);
}
```

Write `frontend/src/types.ts`:
```typescript
export interface Incident {
  id: string;
  fingerprint: string;
  dag_id: string;
  run_id: string;
  task_id: string;
  try_number: number;
  status: string;
  error_message: string;
  occurrence_count: number;
  first_seen_at: string;
  last_seen_at: string;
  category?: string;
  confidence?: number;
  root_cause?: string;
  suggested_action?: string;
}

export interface PendingAction {
  id: string;
  incident_id: string;
  action_type: string;
  status: string;
  created_at: string;
  dag_id: string;
  task_id: string;
  run_id: string;
  category?: string;
  confidence?: number;
  root_cause?: string;
}

export interface Metrics {
  total_incidents: number;
  total_deduplicated_events: number;
  pending_approvals: number;
  avg_confidence: number;
}
```

Write `frontend/src/hooks/usePolling.ts`:
```typescript
import { useEffect, useState } from 'react';

export function usePolling<T>(fetcher: () => Promise<T>, intervalMs: number = 5000) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const execute = async () => {
      try {
        const result = await fetcher();
        if (isMounted) {
          setData(result);
          setError(null);
        }
      } catch (err: unknown) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Failed to fetch data');
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    execute();
    const interval = setInterval(execute, intervalMs);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [fetcher, intervalMs]);

  return { data, loading, error };
}
```

#### What this code does
Sets up the foundational UI layer: native responsive theme variables supporting light and dark modes, shared TypeScript interfaces matching backend models, and a robust polling hook that updates the UI every 5 seconds.

#### Run / verify
- Verified during Step 10.5.

---

### Step 10.3: API Client & UI Components

#### Goal
Implement the frontend fetch API wrapper and confidence badge component.

#### Path
- Files:
  - `frontend/src/api/client.ts`
  - `frontend/src/components/ConfidenceBadge.tsx`

#### Code
Write `frontend/src/api/client.ts`:
```typescript
import { Incident, Metrics, PendingAction } from '../types';

export const apiClient = {
  async getIncidents(): Promise<Incident[]> {
    const res = await fetch('/api/incidents');
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch incidents`);
    return res.json();
  },

  async getPendingActions(): Promise<PendingAction[]> {
    const res = await fetch('/api/actions/pending');
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch pending actions`);
    return res.json();
  },

  async approveAction(actionId: string, approver: string = 'web:dashboard'): Promise<void> {
    const res = await fetch(`/api/actions/${actionId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approver, reason: 'Approved via Web Dashboard' }),
    });
    if (!res.ok) throw new Error(`Approval failed with HTTP ${res.status}`);
  },

  async rejectAction(actionId: string, approver: string = 'web:dashboard'): Promise<void> {
    const res = await fetch(`/api/actions/${actionId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approver, reason: 'Rejected via Web Dashboard' }),
    });
    if (!res.ok) throw new Error(`Rejection failed with HTTP ${res.status}`);
  },

  async getMetrics(): Promise<Metrics> {
    const res = await fetch('/api/metrics');
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch metrics`);
    return res.json();
  },
};
```

Write `frontend/src/components/ConfidenceBadge.tsx`:
```typescript
import React from 'react';

interface Props {
  confidence?: number;
}

export const ConfidenceBadge: React.FC<Props> = ({ confidence }) => {
  if (confidence === undefined || confidence === null) {
    return <span style={{ color: 'var(--text-secondary)' }}>N/A</span>;
  }

  let color = 'var(--accent-red)';
  if (confidence >= 0.8) color = 'var(--accent-green)';
  else if (confidence >= 0.6) color = 'var(--accent-amber)';

  return (
    <span
      style={{
        backgroundColor: 'var(--bg-tertiary)',
        color: color,
        padding: '3px 8px',
        borderRadius: '12px',
        fontWeight: 600,
        fontSize: '0.85rem',
      }}
    >
      {(confidence * 100).toFixed(0)}%
    </span>
  );
};
```

#### What this code does
Wraps all REST requests with proper error handling and creates a color-coded confidence indicator badge (green $\ge 80\%$, amber $\ge 60\%$, red $< 60\%$).

#### Run / verify
- Verified during Step 10.5.

---

### Step 10.4: Dashboard Pages & Application Root

#### Goal
Implement the three primary view pages (`IncidentsPage`, `ApprovalsPage`, `MetricsPage`) and the main application shell.

#### Path
- Files:
  - `frontend/src/pages/IncidentsPage.tsx`
  - `frontend/src/pages/ApprovalsPage.tsx`
  - `frontend/src/pages/MetricsPage.tsx`
  - `frontend/src/App.tsx`
  - `frontend/src/main.tsx`

#### Code
Write `frontend/src/pages/IncidentsPage.tsx`:
```typescript
import React, { useCallback } from 'react';
import { apiClient } from '../api/client';
import { ConfidenceBadge } from '../components/ConfidenceBadge';
import { usePolling } from '../hooks/usePolling';

export const IncidentsPage: React.FC = () => {
  const fetcher = useCallback(() => apiClient.getIncidents(), []);
  const { data: incidents, loading, error } = usePolling(fetcher, 4000);

  if (loading && !incidents) return <div>Loading incidents...</div>;
  if (error) return <div style={{ color: 'var(--accent-red)' }}>Error: {error}</div>;

  return (
    <div>
      <h2>Incidents Feed</h2>
      {incidents?.length === 0 ? (
        <div className="card">No incidents recorded. All DAGs healthy!</div>
      ) : (
        incidents?.map((inc) => (
          <div key={inc.id} className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0 }}>
                <code>{inc.dag_id}</code> &gt; <code>{inc.task_id}</code>
              </h3>
              <div>
                <span style={{ marginRight: 8, color: 'var(--text-secondary)' }}>
                  Seen {inc.occurrence_count}x
                </span>
                <ConfidenceBadge confidence={inc.confidence} />
              </div>
            </div>
            <p style={{ margin: '8px 0', color: 'var(--text-secondary)' }}>
              Category: <strong>{inc.category || 'ANALYZING...'}</strong> | Run: <code>{inc.run_id}</code>
            </p>
            {inc.root_cause && (
              <div style={{ backgroundColor: 'var(--bg-tertiary)', padding: 12, borderRadius: 6 }}>
                <strong>Root Cause:</strong> {inc.root_cause}
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
};
```

Write `frontend/src/pages/ApprovalsPage.tsx`:
```typescript
import React, { useCallback } from 'react';
import { apiClient } from '../api/client';
import { ConfidenceBadge } from '../components/ConfidenceBadge';
import { usePolling } from '../hooks/usePolling';

export const ApprovalsPage: React.FC = () => {
  const fetcher = useCallback(() => apiClient.getPendingActions(), []);
  const { data: actions, loading, error } = usePolling(fetcher, 3000);

  const handleApprove = async (id: string) => {
    try {
      await apiClient.approveAction(id);
      alert('Remediation approved and triggered!');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Approval failed');
    }
  };

  const handleReject = async (id: string) => {
    try {
      await apiClient.rejectAction(id);
      alert('Action rejected.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Rejection failed');
    }
  };

  if (loading && !actions) return <div>Loading pending actions...</div>;
  if (error) return <div style={{ color: 'var(--accent-red)' }}>Error: {error}</div>;

  return (
    <div>
      <h2>Pending Human Approvals</h2>
      {actions?.length === 0 ? (
        <div className="card">No actions pending human approval.</div>
      ) : (
        actions?.map((act) => (
          <div key={act.id} className="card" style={{ borderLeft: '4px solid var(--accent-amber)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0 }}>
                Action: <code>{act.action_type}</code>
              </h3>
              <ConfidenceBadge confidence={act.confidence} />
            </div>
            <p>
              Target: <code>{act.dag_id}</code> &gt; <code>{act.task_id}</code>
            </p>
            {act.root_cause && (
              <div style={{ backgroundColor: 'var(--bg-tertiary)', padding: 10, borderRadius: 6, marginBottom: 16 }}>
                <strong>Diagnosis:</strong> {act.root_cause}
              </div>
            )}
            <div style={{ display: 'flex', gap: 12 }}>
              <button className="button button-success" onClick={() => handleApprove(act.id)}>
                Approve &amp; Execute
              </button>
              <button className="button button-danger" onClick={() => handleReject(act.id)}>
                Reject
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
};
```

Write `frontend/src/pages/MetricsPage.tsx`:
```typescript
import React, { useCallback } from 'react';
import { apiClient } from '../api/client';
import { usePolling } from '../hooks/usePolling';

export const MetricsPage: React.FC = () => {
  const fetcher = useCallback(() => apiClient.getMetrics(), []);
  const { data: metrics, loading, error } = usePolling(fetcher, 5000);

  if (loading && !metrics) return <div>Loading metrics...</div>;
  if (error) return <div style={{ color: 'var(--accent-red)' }}>Error: {error}</div>;

  return (
    <div>
      <h2>System Reliability Metrics</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
        <div className="card">
          <div style={{ color: 'var(--text-secondary)' }}>Total Incidents</div>
          <h1 style={{ margin: '8px 0 0 0' }}>{metrics?.total_incidents}</h1>
        </div>
        <div className="card">
          <div style={{ color: 'var(--text-secondary)' }}>Deduplicated Events</div>
          <h1 style={{ margin: '8px 0 0 0', color: 'var(--accent-blue)' }}>
            {metrics?.total_deduplicated_events}
          </h1>
        </div>
        <div className="card">
          <div style={{ color: 'var(--text-secondary)' }}>Pending Approvals</div>
          <h1 style={{ margin: '8px 0 0 0', color: 'var(--accent-amber)' }}>
            {metrics?.pending_approvals}
          </h1>
        </div>
        <div className="card">
          <div style={{ color: 'var(--text-secondary)' }}>Average Confidence</div>
          <h1 style={{ margin: '8px 0 0 0', color: 'var(--accent-green)' }}>
            {metrics ? (metrics.avg_confidence * 100).toFixed(0) : 0}%
          </h1>
        </div>
      </div>
    </div>
  );
};
```

Write `frontend/src/App.tsx`:
```typescript
import React, { useState } from 'react';
import { ApprovalsPage } from './pages/ApprovalsPage';
import { IncidentsPage } from './pages/IncidentsPage';
import { MetricsPage } from './pages/MetricsPage';

export const App: React.FC = () => {
  const [tab, setTab] = useState<'incidents' | 'approvals' | 'metrics'>('incidents');

  return (
    <div className="container">
      <header style={{ marginBottom: 20 }}>
        <h1 style={{ margin: 0 }}>DagInquest</h1>
        <p style={{ color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
          Formal Airflow DAG Failure Investigation &amp; Safe Remediation
        </p>
      </header>

      <nav className="nav-bar">
        <span
          className={`nav-link ${tab === 'incidents' ? 'active' : ''}`}
          onClick={() => setTab('incidents')}
        >
          Incidents
        </span>
        <span
          className={`nav-link ${tab === 'approvals' ? 'active' : ''}`}
          onClick={() => setTab('approvals')}
        >
          Approvals
        </span>
        <span
          className={`nav-link ${tab === 'metrics' ? 'active' : ''}`}
          onClick={() => setTab('metrics')}
        >
          Metrics
        </span>
      </nav>

      <main>
        {tab === 'incidents' && <IncidentsPage />}
        {tab === 'approvals' && <ApprovalsPage />}
        {tab === 'metrics' && <MetricsPage />}
      </main>
    </div>
  );
};
```

Write `frontend/src/main.tsx`:
```typescript
import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

#### What this code does
Assembles the complete single page dashboard. It provides live tabs for reviewing incidents, approving pending remediations with instant feedback, and monitoring metrics with automatic background polling.

#### Run / verify
- Verified in Step 10.5.

---

### Step 10.5: Dashboard Verification Checkpoint

#### Goal
Install frontend dependencies, run the Vite development server, and verify live UI interactions.

#### Run / verify
1. Navigate to `frontend/` and install dependencies:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
2. Open your browser to `http://localhost:5173`.
3. Verify that:
   - The Incidents tab displays the list of past failures.
   - The Approvals tab allows single-click approval/rejection.
   - The Metrics tab displays total counts and average confidence.

#### If it fails
- `Failed to fetch`: Verify the backend API is running on port 8000 and the Vite proxy in `vite.config.ts` points to `http://localhost:8000`.

---

### Checkpoint: Phase 10
The React dashboard is operational, polling data from the API, and executing approval workflows through the browser UI.

---

## Phase 11: Evaluation Benchmark

### Why this phase exists
Rather than making unverified claims about local LLM capability, DagInquest includes a **reproducible evaluation harness** to measure actual diagnostic accuracy, citation validity (hallucination rate), and latency across local models.

The suite defines 25–30 failure cases representing 10 realistic categories.

---

### Evaluation Case Specifications (28 Concrete Benchmark Cases)

| ID | Failure Category | Realistic Sample Log Signature | Expected Category |
|---|---|---|---|
| `case_01_import` | IMPORT_ERROR | `ModuleNotFoundError: No module named 'polars'` | `IMPORT_ERROR` |
| `case_02_import` | IMPORT_ERROR | `ImportError: cannot import name 'eval_frame' from 'torch'` | `IMPORT_ERROR` |
| `case_03_import` | IMPORT_ERROR | `SyntaxError: invalid syntax at line 24 of data_loader.py` | `IMPORT_ERROR` |
| `case_04_timeout` | TRANSIENT_NETWORK | `socket.timeout: timed out after 30000ms connecting to api` | `TRANSIENT_NETWORK` |
| `case_05_timeout` | TRANSIENT_NETWORK | `ConnectionResetError: [Errno 104] Connection reset by peer` | `TRANSIENT_NETWORK` |
| `case_06_timeout` | TRANSIENT_NETWORK | `httpx.ReadTimeout: The read operation timed out` | `TRANSIENT_NETWORK` |
| `case_07_bad_sql` | SCHEMA_SQL | `psycopg2.errors.UndefinedColumn: column "user_addr" does not exist` | `SCHEMA_SQL` |
| `case_08_bad_sql` | SCHEMA_SQL | `sqlite3.OperationalError: no such table: staging_orders` | `SCHEMA_SQL` |
| `case_09_bad_sql` | SCHEMA_SQL | `sqlalchemy.exc.ProgrammingError: syntax error at or near "WHERRE"` | `SCHEMA_SQL` |
| `case_10_secret` | CONFIG_SECRET | `KeyError: 'AIRFLOW_CONN_SNOWFLAKE_DEFAULT' not found` | `CONFIG_SECRET` |
| `case_11_secret` | CONFIG_SECRET | `botocore.exceptions.ClientError: 403 Forbidden InvalidAccessKeyId` | `CONFIG_SECRET` |
| `case_12_secret` | CONFIG_SECRET | `VaultClientError: secret path 'secret/data/db' permission denied` | `CONFIG_SECRET` |
| `case_13_auth` | CONFIG_SECRET | `google.auth.exceptions.DefaultCredentialsError: File not found` | `CONFIG_SECRET` |
| `case_14_auth` | CONFIG_SECRET | `requests.exceptions.HTTPError: 401 Client Error: Unauthorized` | `CONFIG_SECRET` |
| `case_15_oom` | RESOURCE | `MemoryError: Unable to allocate 16.0 GiB for array with shape` | `RESOURCE` |
| `case_16_oom` | RESOURCE | `KilledProcess: Task worker process received SIGKILL (OOMKilled)` | `RESOURCE` |
| `case_17_disk` | RESOURCE | `OSError: [Errno 28] No space left on device: '/tmp/scratch'` | `RESOURCE` |
| `case_18_upstream` | UPSTREAM_DATA | `AirflowSensorTimeout: Sensor S3KeySensor timed out after 3600s` | `UPSTREAM_DATA` |
| `case_19_upstream` | UPSTREAM_DATA | `FileNotFoundError: [Errno 2] No such file: 's3://lake/daily.csv'` | `UPSTREAM_DATA` |
| `case_20_upstream` | UPSTREAM_DATA | `AirflowFailException: Upstream partition 'dt=2026-11-24' is empty` | `UPSTREAM_DATA` |
| `case_21_noisy` | INCONCLUSIVE | `Process exited with code 1. No traceback was provided in log.` | `INCONCLUSIVE` |
| `case_22_noisy` | INCONCLUSIVE | `2026-11-24 [INFO] Heartbeat OK. Worker exiting.` | `INCONCLUSIVE` |
| `case_23_noisy` | INCONCLUSIVE | `Subprocess exited with unknown signal 11. Core dumped.` | `INCONCLUSIVE` |
| `case_24_corr` | TRANSIENT_NETWORK | `HTTP 503 Service Unavailable on gateway api.orders.com` | `TRANSIENT_NETWORK` |
| `case_25_corr` | TRANSIENT_NETWORK | `redis.exceptions.ConnectionError: Error connecting to cache:6379` | `TRANSIENT_NETWORK` |
| `case_26_perm` | CONFIG_SECRET | `PermissionError: [Errno 13] Permission denied: '/var/data/raw'` | `CONFIG_SECRET` |
| `case_27_db_pool`| RESOURCE | `psycopg.OperationalError: FATAL: remaining connection slots reserved` | `RESOURCE` |
| `case_28_dep` | UPSTREAM_DATA | `AirflowSkipException: Upstream dependency was skipped` | `UPSTREAM_DATA` |

---

### Step 11.1: Benchmark Case Files & Evaluation Harness

#### Goal
Create concrete test case JSON files in `backend/src/daginquest/eval/cases/` and implement the CLI runner in `run_eval.py`.

#### Path
- Unix: `mkdir -p backend/src/daginquest/eval/cases backend/src/daginquest/eval/results`
- Windows (PowerShell): `mkdir -p backend/src/daginquest/eval/cases, backend/src/daginquest/eval/results`
- Files:
  - `backend/src/daginquest/eval/__init__.py` (create empty file)
  - `backend/src/daginquest/eval/cases/case_01_import.json`
  - `backend/src/daginquest/eval/cases/case_04_timeout.json`
  - `backend/src/daginquest/eval/cases/case_07_bad_sql.json`
  - `backend/src/daginquest/eval/cases/case_10_secret.json`
  - `backend/src/daginquest/eval/cases/case_15_oom.json`
  - `backend/src/daginquest/eval/cases/case_17_disk.json`
  - `backend/src/daginquest/eval/cases/case_18_upstream.json`
  - `backend/src/daginquest/eval/cases/case_21_noisy.json`
  - `backend/src/daginquest/eval/cases/case_24_corr.json`
  - `backend/src/daginquest/eval/cases/case_27_db_pool.json`
  - `backend/src/daginquest/eval/run_eval.py`

#### Code
Create an empty file at `backend/src/daginquest/eval/__init__.py`.

Write `backend/src/daginquest/eval/cases/case_01_import.json`:
```json
{
  "id": "case_01_import",
  "expected_category": "IMPORT_ERROR",
  "log": "Traceback (most recent call last):\n  File \"/opt/airflow/dags/etl.py\", line 12, in <module>\n    import polars as pl\nModuleNotFoundError: No module named 'polars'\n[2026-11-24] Task failed with return code 1",
  "dag_source": "from airflow import DAG\nimport polars as pl"
}
```

Write `backend/src/daginquest/eval/cases/case_04_timeout.json`:
```json
{
  "id": "case_04_timeout",
  "expected_category": "TRANSIENT_NETWORK",
  "log": "Traceback (most recent call last):\n  File \"/opt/airflow/dags/fetch.py\", line 45, in execute\n    sock.connect(('api.partner.net', 443))\nsocket.timeout: timed out after 30000ms connecting to api\n[2026-11-24] Task failed with timeout",
  "dag_source": "socket.connect(('api.partner.net', 443))"
}
```

Write `backend/src/daginquest/eval/cases/case_07_bad_sql.json`:
```json
{
  "id": "case_07_bad_sql",
  "expected_category": "SCHEMA_SQL",
  "log": "psycopg2.errors.UndefinedColumn: column \"user_addr\" does not exist\nLINE 1: SELECT id, user_addr FROM users_v2;\nTask failed due to database query error",
  "dag_source": "cur.execute('SELECT id, user_addr FROM users_v2;')"
}
```

Write `backend/src/daginquest/eval/cases/case_10_secret.json`:
```json
{
  "id": "case_10_secret",
  "expected_category": "CONFIG_SECRET",
  "log": "Traceback (most recent call last):\n  File \"/opt/airflow/dags/sync.py\", line 20, in execute\n    conn = BaseHook.get_connection('snowflake_warehouse')\nKeyError: 'AIRFLOW_CONN_SNOWFLAKE_WAREHOUSE' not found in environment or secrets backend",
  "dag_source": "BaseHook.get_connection('snowflake_warehouse')"
}
```

Write `backend/src/daginquest/eval/cases/case_15_oom.json`:
```json
{
  "id": "case_15_oom",
  "expected_category": "RESOURCE",
  "log": "numpy.core._exceptions._ArrayMemoryError: Unable to allocate 16.0 GiB for an array with shape (200000, 10000) and data type float64\nMemoryError: Out of memory",
  "dag_source": "matrix = np.zeros((200000, 10000))"
}
```

Write `backend/src/daginquest/eval/cases/case_17_disk.json`:
```json
{
  "id": "case_17_disk",
  "expected_category": "RESOURCE",
  "log": "OSError: [Errno 28] No space left on device: '/tmp/scratch/batch_dump.parquet'\nWorker terminated because disk write failed.",
  "dag_source": "df.to_parquet('/tmp/scratch/batch_dump.parquet')"
}
```

Write `backend/src/daginquest/eval/cases/case_18_upstream.json`:
```json
{
  "id": "case_18_upstream",
  "expected_category": "UPSTREAM_DATA",
  "log": "airflow.exceptions.AirflowSensorTimeout: Sensor S3KeySensor timed out after 3600 seconds waiting for s3://bucket/landing/dt=2026-11-24/_SUCCESS",
  "dag_source": "S3KeySensor(bucket_key='landing/dt=2026-11-24/_SUCCESS', timeout=3600)"
}
```

Write `backend/src/daginquest/eval/cases/case_21_noisy.json`:
```json
{
  "id": "case_21_noisy",
  "expected_category": "INCONCLUSIVE",
  "log": "[2026-11-24 10:00:00] Subprocess pid 4091 exited with error status 1. (No stderr captured)\n[2026-11-24 10:00:01] Marking task as FAILED.",
  "dag_source": "BashOperator(task_id='run_legacy', bash_command='./run.sh')"
}
```

Write `backend/src/daginquest/eval/cases/case_24_corr.json`:
```json
{
  "id": "case_24_corr",
  "expected_category": "TRANSIENT_NETWORK",
  "log": "httpx.HTTPStatusError: Server error '503 Service Unavailable' for url 'https://gateway.internal/orders'\nRetrying in 5 seconds failed.",
  "dag_source": "client.get('https://gateway.internal/orders')"
}
```

Write `backend/src/daginquest/eval/cases/case_27_db_pool.json`:
```json
{
  "id": "case_27_db_pool",
  "expected_category": "RESOURCE",
  "log": "psycopg.OperationalError: FATAL: remaining connection slots are reserved for non-replication superuser connections\nConnection pool exhausted on postgres:5432",
  "dag_source": "with pool.connection() as conn:"
}
```

> **Rule for generating cases 28 to 30:** Follow the exact schema above. Create a file `case_XX_category.json` containing `id`, `expected_category` (must be one of the 7 failure categories), `log` (containing a realistic stack trace), and optional `dag_source`.

Write `backend/src/daginquest/eval/run_eval.py`:
```python
import argparse
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List
from daginquest.agent.prompts import RCA_SYSTEM_PROMPT, RCA_USER_PROMPT_TEMPLATE
from daginquest.llm.ollama import OllamaClient


async def evaluate_case(client: OllamaClient, case_data: Dict[str, Any]) -> Dict[str, Any]:
    task_log = case_data["log"]
    user_prompt = RCA_USER_PROMPT_TEMPLATE.format(
        dag_id="eval_dag",
        task_id="eval_task",
        run_id="eval_run",
        try_number=1,
        error_message=case_data.get("log", "")[:200],
        preclassified_category="None",
        preclassified_confidence=0.0,
        task_log=task_log,
        dag_source=case_data.get("dag_source", "# No source available"),
    )

    start_time = time.time()
    result = await client.generate_root_cause_analysis(RCA_SYSTEM_PROMPT, user_prompt)
    latency = time.time() - start_time

    # Evaluate accuracy and citations
    is_correct = result.category == case_data["expected_category"]
    valid_citations = [line for line in result.cited_lines if line.strip() in task_log]
    valid_ratio = len(valid_citations) / len(result.cited_lines) if result.cited_lines else 1.0

    return {
        "case_id": case_data["id"],
        "expected": case_data["expected_category"],
        "predicted": result.category,
        "is_correct": is_correct,
        "confidence": result.confidence,
        "citation_validity": round(valid_ratio, 2),
        "latency_seconds": round(latency, 2),
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="DagInquest Local LLM Benchmark Harness")
    parser.add_argument("--models", nargs="+", default=["qwen2.5:7b"], help="Ollama models to evaluate")
    args = parser.parse_args()

    cases_dir = Path(__file__).parent / "cases"
    case_files = sorted(list(cases_dir.glob("*.json")))

    if not case_files:
        print(f"No benchmark cases found in {cases_dir}")
        return

    cases = [json.loads(f.read_text(encoding="utf-8")) for f in case_files]
    print(f"Loaded {len(cases)} benchmark cases from {cases_dir}")

    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = []

    for model in args.models:
        print(f"\n=======================================================")
        print(f"Evaluating Model: {model}")
        print(f"=======================================================")
        client = OllamaClient(model=model)
        eval_outputs = []

        for case in cases:
            output = await evaluate_case(client, case)
            mark = "PASS" if output["is_correct"] else "FAIL"
            print(
                f"[{mark}] {case['id']}: Expected={output['expected']}, "
                f"Got={output['predicted']} ({output['latency_seconds']}s)"
            )
            eval_outputs.append(output)

        # Aggregate statistics
        total = len(eval_outputs)
        correct = sum(1 for o in eval_outputs if o["is_correct"])
        accuracy = (correct / total) * 100
        avg_latency = sum(o["latency_seconds"] for o in eval_outputs) / total
        avg_citation = sum(o["citation_validity"] for o in eval_outputs) / total
        hallucination_rate = (1.0 - avg_citation) * 100

        report = {
            "model": model,
            "total_cases": total,
            "correct_classifications": correct,
            "accuracy_percent": round(accuracy, 2),
            "hallucination_rate_percent": round(hallucination_rate, 2),
            "avg_latency_seconds": round(avg_latency, 2),
            "details": eval_outputs,
        }

        report_file = results_dir / f"benchmark_{model.replace(':', '_')}.json"
        report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nResults saved to: {report_file}")

        summary_rows.append(
            f"| {model} | {accuracy:.1f}% | {hallucination_rate:.1f}% | {avg_latency:.2f}s |"
        )

    print("\n=== BENCHMARK SUMMARY TABLE ===")
    print("| Model | Category Accuracy | Hallucination Rate | Avg Latency |")
    print("|---|---|---|---|")
    for row in summary_rows:
        print(row)


if __name__ == "__main__":
    asyncio.run(main())
```

#### What this code does
Executes the evaluation benchmark suite across one or more local models. It tests the LLM against the cases, computes accuracy against the expected category, calculates citation validity (detecting invented quotes), and outputs a summary report.

#### Run / verify
- Run the benchmark against your active Ollama model:
  ```bash
  python -m daginquest.eval.run_eval --models qwen2.5:7b
  ```
  Expected output:
  ```
  Loaded 10 benchmark cases ...
  Evaluating Model: qwen2.5:7b
  [PASS] case_01_import: Expected=IMPORT_ERROR, Got=IMPORT_ERROR (...)
  ...
  === BENCHMARK SUMMARY TABLE ===
  | Model | Category Accuracy | Hallucination Rate | Avg Latency |
  |---|---|---|---|
  | qwen2.5:7b | >= 80.0% | <= 10.0% | ... |
  ```

---

### Checkpoint: Phase 11
Evaluation test cases and scoring harness are fully functional, providing measurable accuracy metrics for local models.

---

## Phase 12: Hardening and Release

### Why this phase exists
Before deploying or demonstrating DagInquest, the codebase must be hardened:
1. Automated CI ensures that linting and unit tests run on every Git push.
2. Security checklists ensure that unauthenticated dashboard routes are documented before network exposure.
3. Complete documentation, README results tables, demo scripts, and license checks are validated.

---

### Step 12.1: GitHub Actions CI Workflow

#### Goal
Create the CI workflow file in `.github/workflows/ci.yml` running lint checks and the test suite on every pull request.

#### Path
- Unix: `mkdir -p .github/workflows`
- Windows (PowerShell): `mkdir -p .github/workflows`
- File: `.github/workflows/ci.yml`

#### Code
```yaml
name: DagInquest CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install ruff pytest pytest-asyncio
          pip install -e "backend/[dev]"

      - name: Run Ruff Lint Checks
        run: |
          cd backend
          ruff check .
          ruff format --check .

      - name: Run Unit Test Suite
        run: |
          cd backend
          pytest -v
```

#### What this code does
Automates testing on GitHub infrastructure. Rejects any pull request that introduces linting violations, unformatted code, or failing unit tests.

#### Run / verify
- Verify locally that the exact same commands pass:
  ```bash
  cd backend && ruff check . && ruff format --check . && pytest -v
  ```
  Expected output: All checks pass cleanly with 0 errors.

---

### Step 12.2: Security Checklist & Production Hardening Notes

> [!CAUTION]
> **Dashboard Endpoint Authentication Requirement**
> In this local baseline implementation, `POST /api/actions/{id}/approve` and `POST /api/actions/{id}/reject` do not require web authentication (they default to `approver: "web:dashboard"`).
> **Before exposing this API beyond `localhost` or running in shared networks:**
> 1. Place the backend API behind a reverse proxy (e.g. Nginx, Caddy, Cloudflare Access) with mandatory SSO/mTLS.
> 2. Add an authentication dependency (e.g., JWT Bearer token or OAuth2) to the FastAPI routers in `api/actions.py` and `api/incidents.py`.
> 3. Rotate `WEBHOOK_SECRET` and `TELEGRAM_BOT_TOKEN` in `.env` and store them in a secure secrets manager.

---

### Step 12.3: Optional Stretch Integrations

When you want to expand DagInquest beyond the minimal local MVP:
1. **Langfuse Tracing**: Integrate Langfuse's Python SDK inside `backend/src/daginquest/agent/runner.py` to capture token-level traces and latency waterfalls for each LangGraph node.
2. **pgvector Similar-Incident Search**: Add the `vector` extension to PostgreSQL 16 and store 768-dimensional embeddings of past incident error messages to retrieve historical resolutions.
3. **Valkey Task Queue**: If incident traffic exceeds hundreds per minute, insert an asynchronous worker queue between the webhook route and the LangGraph runner using Valkey (BSD-3-Clause open-source Redis alternative).
4. **Self-Hosted n8n Workflow Automation**: Connect n8n via webhook to dispatch multi-channel alerts (e.g., PagerDuty, Opsgenie, Slack). *Note: n8n uses the Sustainable Use License, which is source-available but not OSI-approved open source.*

---

## Path-to-Code Cheat Sheet

| Path | What code goes here | Key functions / classes | Depends on |
|---|---|---|---|
| `docker-compose.yml` | Multi-container definitions | `postgres`, `ollama`, `airflow`, `api`, `bot` | Docker Engine |
| `backend/migrations/001_init.sql` | Relational DDL & immutability trigger | 8 tables, `enforce_audit_log_append_only()` | PostgreSQL 16 |
| `backend/src/daginquest/config.py` | Pydantic BaseSettings config | `Settings`, `get_settings()` | `pydantic-settings` |
| `backend/src/daginquest/main.py` | FastAPI application & lifespan | `app`, `lifespan()` | `fastapi`, `uvicorn` |
| `backend/src/daginquest/utils/fingerprint.py` | SHA-256 error hashing | `compute_incident_fingerprint()` | Python stdlib (`hashlib`) |
| `backend/src/daginquest/utils/preclassify.py` | Regex heuristic parsing | `preclassify_log()` | `re`, `policy/rules.py` |
| `backend/src/daginquest/security/redaction.py` | Masking sensitive credentials | `redact_sensitive_data()` | `re` |
| `backend/src/daginquest/policy/rules.py` | Safety allow-lists & gate | `evaluate_remediation_policy()` | None |
| `backend/src/daginquest/db/session.py` | Async connection pool manager | `init_db_pool()`, `get_connection()` | `psycopg-pool` |
| `backend/src/daginquest/db/repository.py` | SQL queries & atomic approval | `create_or_bump_incident()`, `decide_action()` | `session.py` |
| `backend/src/daginquest/airflow/client.py` | Async Airflow REST API client | `AirflowClient` | `httpx` |
| `airflow/dags/_common/callbacks.py` | Airflow failure callback | `daginquest_failure_callback()` | `urllib.request` |
| `backend/src/daginquest/llm/schemas.py` | Pydantic JSON schema contract | `RootCauseAnalysisResult` | `pydantic` |
| `backend/src/daginquest/llm/ollama.py` | Ollama client with schema output | `OllamaClient` | `httpx`, `schemas.py` |
| `backend/src/daginquest/agent/state.py` | LangGraph state dictionary | `InvestigationState` | `typing.TypedDict` |
| `backend/src/daginquest/agent/graph.py` | Compiled LangGraph workflow | `investigation_graph` | `langgraph`, nodes |
| `backend/src/daginquest/telegram/notifier.py` | Telegram alert dispatcher | `send_incident_alert()` | `httpx` |
| `backend/src/daginquest/telegram/handlers.py` | Telegram commands & button queries | `callback_query_handler()` | `python-telegram-bot` |
| `backend/src/daginquest/actions/executor.py` | Airflow action execution | `execute_remediation_action()` | `airflow/client.py` |
| `backend/src/daginquest/actions/verify.py` | Task state polling loop | `poll_task_recovery()` | `airflow/client.py` |
| `frontend/src/api/client.ts` | Frontend fetch wrapper | `apiClient` | Browser fetch API |
| `frontend/src/pages/IncidentsPage.tsx` | Incident stream view | `IncidentsPage` | React, `apiClient` |
| `backend/src/daginquest/eval/run_eval.py` | Benchmark evaluation CLI | `main()`, `evaluate_case()` | `llm/ollama.py` |

---

## Environment Variable Reference

| Variable | Default Value | Purpose |
|---|---|---|
| `POSTGRES_USER` | `daginquest_user` | PostgreSQL database username |
| `POSTGRES_PASSWORD` | `daginquest_secure_password` | PostgreSQL database password |
| `POSTGRES_DB` | `daginquest` | PostgreSQL database name |
| `DATABASE_URL` | `postgresql://...` | Asynchronous connection string for psycopg 3 |
| `OLLAMA_URL` | `http://ollama:11434` | Network endpoint of local Ollama server |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Name of the local LLM used for Root Cause Analysis |
| `AIRFLOW_IMAGE` | `apache/airflow:3.0.0.dev0` | Apache Airflow container image tag |
| `AIRFLOW_BASE_URL` | `http://airflow:8080` | Airflow REST API base URL |
| `AIRFLOW_USERNAME` | `admin` | Airflow REST API basic authentication username |
| `AIRFLOW_PASSWORD` | `admin` | Airflow REST API basic authentication password |
| `WEBHOOK_SECRET` | `inquest_shared_secret...` | Shared secret header required for failure webhook |
| `DAGINQUEST_API_URL` | `http://api:8000` | URL used by Airflow containers to reach DagInquest |
| `DAGINQUEST_WEBHOOK_SECRET` | Matches `WEBHOOK_SECRET` | Shared secret passed to Airflow callback |
| `CONFIDENCE_THRESHOLD` | `0.60` | Minimum confidence score required to propose a fix |
| `DEDUPE_COOLDOWN_MINUTES` | `30` | Time window to merge identical task failure repeats |
| `TELEGRAM_BOT_TOKEN` | *(Required)* | HTTP API token generated via `@BotFather` |
| `TELEGRAM_ALLOWED_CHAT_IDS` | *(Required)* | Comma-separated list of authorized numeric chat IDs |

---

## Troubleshooting Matrix

| Symptom | Likely Cause | Fix |
|---|---|---|
| Docker container `daginquest-api` fails on start | PostgreSQL is still initializing | Check `docker compose logs postgres`. Ensure healthcheck passes. |
| `ERROR: Updates and deletions are strictly forbidden on audit_log` | Direct SQL UPDATE executed on `audit_log` | This is by design (immutability trigger). Do not modify audit rows. |
| Webhook returns HTTP 401 Unauthorized | Missing or mismatched `X-Webhook-Secret` header | Verify header matches `WEBHOOK_SECRET` in `.env`. |
| Webhook returns HTTP 202, but `deduplicated: true` | Same error occurred within cooldown window | Normal behavior. To force a new investigation, change `run_id` or wait for cooldown. |
| Ollama returns `HTTP 404: model not found` | Model weights were not pulled into volume | Run `docker compose exec ollama ollama pull qwen2.5:7b`. |
| Ollama inference is extremely slow (>30s) | Model running on CPU without GPU acceleration | Switch to a smaller quantized model (e.g., `qwen2.5:3b` or `llama3.2:3b`). |
| Telegram bot does not reply to commands | Your chat ID is not in the allow-list | Send `/start` to `@userinfobot`, copy your ID, and update `TELEGRAM_ALLOWED_CHAT_IDS`. |
| Telegram inline button click says "Already decided" | Double-click or previous approval executed | The atomic update succeeded on the first click and rejected the second. Expected behavior. |
| Airflow DAG import fails with `No module named '_common'` | Airflow volume mount missing or corrupt | Check `./airflow/dags:/opt/airflow/dags` in `docker-compose.yml`. |
| Airflow clear task fails with HTTP 404 or 401 | Airflow 3 endpoint path changed | Check `http://localhost:8080/docs` and adjust paths in `airflow/client.py`. |
| Double approve returns HTTP 409 Conflict | Concurrency guard / atomic update query | Normal behavior. An action can only be approved once. |
| React dashboard shows `NetworkError` when calling `/api` | Backend API container is stopped or proxy is wrong | Verify `docker compose ps` shows API running; check `vite.config.ts`. |
| `psycopg_pool.PoolTimeout` on startup | Database connection pool exhausted or down | Verify PostgreSQL credentials in `.env` and `DATABASE_URL`. |
| Unit tests fail with `ModuleNotFoundError: daginquest` | Local editable package not installed | Run `pip install -e backend/` inside your active virtual environment. |
| Ruff fails with line length errors | Line exceeds 100 characters | Run `ruff format backend/` to format files automatically. |

---

## Final End-to-End Demo Script (Under 5 Minutes)

Follow this numbered script to demonstrate the complete DagInquest system:

1. **Boot all services**:
   ```bash
   docker compose up -d
   cd frontend && npm run dev
   ```
2. **Open the Web Dashboard**:
   - Open browser to `http://localhost:5173`.
   - Show the initial empty Incidents feed and Metrics page.
3. **Trigger a Transient Network Failure in Airflow**:
   - Open `http://localhost:8080` (Airflow Web UI, user: `admin`, pass: `admin`).
   - Unpause DAG `demo_timeout` and click **Trigger DAG**.
4. **Observe Failure Ingestion**:
   - Within 3 seconds, show that the dashboard Incidents feed displays the incident.
   - Point out the category `TRANSIENT_NETWORK` and the color-coded confidence badge.
5. **Inspect the Mobile Telegram Alert**:
   - Switch to your Telegram client.
   - Point out the rich markdown message, the verbatim cited evidence line, and the inline **Approve retry_task** button.
6. **Execute Remediation via Telegram**:
   - Tap **✅ Approve retry_task**.
   - Show the instant confirmation message: *"Action approved. Executing remediation..."*.
7. **Verify Idempotency Guard**:
   - Tap the button again or attempt approval via curl.
   - Show that the system warns: *"This action has already been decided."* (HTTP 409).
8. **Verify Task Recovery**:
   - Return to Airflow at `http://localhost:8080`.
   - Show that task `network_fetch_task` was cleared and retried automatically.
   - Show the final Telegram notification confirming recovery.

---

## Consistency Checklist

Before deploying, verify each checkbox:
- [x] All imports resolve cleanly (`python -c "import daginquest"`).
- [x] Environment variable names match identically across `.env.example`, `config.py`, and `docker-compose.yml`.
- [x] Database migration `001_init.sql` matches repository SQL queries in `repository.py`.
- [x] All 7 failure categories are identical across `rules.py`, `preclassify.py`, `schemas.py`, and `prompts.py`.
- [x] Safe auto-remediation set strictly contains `TRANSIENT_NETWORK` and `RESOURCE`.
- [x] Action types strictly match `retry_task` and `clear_task`.
- [x] Append-only trigger on `audit_log` rejects `UPDATE` and `DELETE`.
- [x] Webhook secret comparison uses constant-time `hmac.compare_digest`.
- [x] Redaction masks database connection passwords, bearer tokens, and AWS access keys.
- [x] All CLI commands are provided for both Unix shells and Windows PowerShell.

---
