CREATE TABLE incidents (
  id BIGSERIAL PRIMARY KEY,
  fingerprint TEXT NOT NULL,
  dag_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  try_number INT NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'open',
  severity TEXT NOT NULL DEFAULT 'medium',
  category TEXT,
  root_cause TEXT,
  confidence REAL,
  occurrences INT NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_incidents_fp ON incidents (fingerprint, created_at DESC);

CREATE TABLE evidence (
  id BIGSERIAL PRIMARY KEY,
  incident_id BIGINT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  content TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE analyses (
  id BIGSERIAL PRIMARY KEY,
  incident_id BIGINT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  model TEXT NOT NULL,
  category TEXT NOT NULL,
  root_cause TEXT NOT NULL,
  confidence REAL NOT NULL,
  cited_lines JSONB NOT NULL DEFAULT '[]',
  raw JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE actions (
  id BIGSERIAL PRIMARY KEY,
  incident_id BIGINT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  type TEXT NOT NULL,
  params JSONB NOT NULL DEFAULT '{}',
  risk TEXT NOT NULL DEFAULT 'low',
  status TEXT NOT NULL DEFAULT 'pending_approval',
  idempotency_key TEXT NOT NULL UNIQUE,
  result JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE approvals (
  id BIGSERIAL PRIMARY KEY,
  action_id BIGINT NOT NULL REFERENCES actions(id) ON DELETE CASCADE,
  channel TEXT NOT NULL,
  user_id TEXT NOT NULL,
  decision TEXT NOT NULL,
  reason TEXT,
  decided_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  actor TEXT NOT NULL,
  event TEXT NOT NULL,
  incident_id BIGINT,
  details JSONB NOT NULL DEFAULT '{}'
);

CREATE FUNCTION audit_log_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'audit_log is append-only';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_no_mutation
  BEFORE UPDATE OR DELETE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION audit_log_immutable();

CREATE TABLE playbooks (
  id BIGSERIAL PRIMARY KEY,
  signature TEXT NOT NULL UNIQUE,
  fix_summary TEXT NOT NULL,
  hits INT NOT NULL DEFAULT 0
);

CREATE TABLE eval_runs (
  id BIGSERIAL PRIMARY KEY,
  model TEXT NOT NULL,
  suite TEXT NOT NULL,
  total INT NOT NULL,
  correct INT NOT NULL,
  accuracy REAL NOT NULL,
  details JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
