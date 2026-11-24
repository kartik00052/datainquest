# Architecture

```mermaid
flowchart LR
  AF[Airflow on_failure_callback] --> API[FastAPI webhook]
  API --> FP[Fingerprint + dedupe]
  FP --> G[LangGraph investigation]
  G --> E[gather evidence] --> C[pre-classify] --> R[LLM RCA]
  R --> V[verify citations] --> P[plan] --> PG{policy gate}
  PG --> N[persist + Telegram alert]
  N --> A[Approve / Reject]
  A --> X[executor: allow-listed Airflow action]
  X --> VER[verify task state] --> N
```

Two phases keep it robust: the graph investigates and stores a pending action;
approval triggers the executor separately (atomic status transition = idempotent).
Upgrade path: add a LangGraph Postgres checkpointer and `interrupt` for resumable runs.
