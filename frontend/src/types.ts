export interface Incident {
  id: number;
  dag_id: string;
  task_id: string;
  run_id: string;
  status: string;
  category: string | null;
  root_cause: string | null;
  confidence: number | null;
  occurrences: number;
  created_at: string;
}

export interface PendingAction {
  id: number;
  incident_id: number;
  type: string;
  risk: string;
  dag_id: string;
  task_id: string;
  root_cause: string | null;
  confidence: number | null;
}

export interface Metrics {
  total_incidents: number;
  open_incidents: number;
  deduplicated_alerts: number;
  avg_confidence: number;
  actions_succeeded: number;
}
