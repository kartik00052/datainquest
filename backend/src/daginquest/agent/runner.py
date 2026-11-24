import logging

from daginquest.agent.graph import graph
from daginquest.db import repository as repo
from daginquest.telegram import notifier

log = logging.getLogger("daginquest.runner")


async def run_investigation(incident_id: int, payload: dict) -> None:
    state = {
        "incident_id": incident_id,
        "dag_id": payload["dag_id"],
        "run_id": payload["run_id"],
        "task_id": payload["task_id"],
        "try_number": payload.get("try_number", 1),
        "initial_error": payload.get("error", ""),
    }
    try:
        await graph.ainvoke(state)
    except Exception as exc:  # a failure must never be silent
        log.exception("investigation failed for incident %s", incident_id)
        await repo.audit("agent", "investigation_failed", incident_id, {"error": str(exc)[:500]})
        last_line = (payload.get("error") or "no error text").strip().splitlines()[-1][:300]
        await notifier.send_text(
            f"Incident #{incident_id} ({payload['dag_id']}.{payload['task_id']}) failed; "
            f"analysis unavailable.\nLast error: {last_line}"
        )
