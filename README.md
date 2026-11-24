# DagInquest

*Formal investigation of DAG failures.*

Self-hosted agent that investigates failed Airflow runs with a local LLM (Ollama),
asks for approval on Telegram, runs allow-listed fixes, and verifies recovery.

## Quick start
```bash
cp .env.example .env            # fill TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_CHAT_IDS
make up                         # postgres, ollama, airflow, api, bot
make pull-models                # downloads the model named in .env
# open Airflow at http://localhost:8080, trigger demo_import_error / demo_timeout
cd frontend && npm install && npm run dev   # dashboard on http://localhost:5173
```

## Layout
- `backend/`   FastAPI API, LangGraph agent, Telegram bot, eval benchmark
- `airflow/`   demo DAGs + failure callback that calls the API
- `frontend/`  React + TypeScript dashboard
- `infra/`     helper scripts
- `docs/`      architecture and benchmark notes

## Safety rules
1. Only allow-listed actions (`retry_task`, `clear_task`) ever execute.
2. Every write action needs a Telegram or dashboard approval.
3. LLM-cited log lines must exist in the stored log, or confidence is reduced.
4. "INCONCLUSIVE" is a valid answer.
