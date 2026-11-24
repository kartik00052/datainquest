import logging

from daginquest.actions.verify import verify_recovery
from daginquest.airflow.client import AirflowClient
from daginquest.db import repository as repo
from daginquest.policy.rules import ALLOWED_ACTIONS
from daginquest.telegram import notifier

log = logging.getLogger("daginquest.executor")


async def execute_action(action_id: int) -> dict:
    """Runs only after approval. Allow-list re-checked here as a second line of defence."""
    action = await repo.get_action(action_id)
    if not action or action["status"] != "approved":
        raise RuntimeError("action is not approved")
    if action["type"] not in ALLOWED_ACTIONS:
        await repo.set_action_result(action_id, "failed", {"error": "action not allow-listed"})
        return {"ok": False}

    params = action["params"]
    client = AirflowClient()
    try:
        await client.clear_task(params["dag_id"], params["run_id"], params["task_id"])
        state = await verify_recovery(client, params)
        ok = state == "success"
        await repo.set_action_result(action_id, "succeeded" if ok else "failed", {"final_state": state})
        await notifier.send_text(
            f"Action #{action_id} ({action['type']}) finished: task state = {state}"
        )
        return {"ok": ok, "state": state}
    except Exception as exc:
        log.exception("action %s failed", action_id)
        await repo.set_action_result(action_id, "failed", {"error": str(exc)[:500]})
        await notifier.send_text(f"Action #{action_id} failed: {str(exc)[:200]}")
        return {"ok": False}
