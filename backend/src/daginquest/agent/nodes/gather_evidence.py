from daginquest.agent.state import IncidentState
from daginquest.airflow.client import AirflowClient
from daginquest.config import get_settings
from daginquest.db import repository as repo
from daginquest.security.redaction import redact


async def gather_evidence(state: IncidentState) -> dict:
    settings = get_settings()
    client = AirflowClient()
    try:
        log_text = await client.get_task_log(
            state["dag_id"], state["run_id"], state["task_id"], state.get("try_number", 1)
        )
    except Exception:  # Airflow unreachable: fall back to the callback's error text
        log_text = state.get("initial_error", "")
    try:
        dag_source = await client.get_dag_source(state["dag_id"])
    except Exception:
        dag_source = ""

    log_text = redact(log_text)[-settings.log_max_chars:]
    dag_source = redact(dag_source)
    await repo.add_evidence(state["incident_id"], "task_log", log_text)
    if dag_source:
        await repo.add_evidence(state["incident_id"], "dag_source", dag_source)
    return {"log_text": log_text, "dag_source": dag_source}
