from typing import TypedDict


class IncidentState(TypedDict, total=False):
    incident_id: int
    dag_id: str
    run_id: str
    task_id: str
    try_number: int
    initial_error: str
    log_text: str
    dag_source: str
    pre_category: str | None
    category: str
    root_cause: str
    confidence: float
    cited_lines: list[str]
    model: str
    proposed_action: dict | None
    policy: dict
