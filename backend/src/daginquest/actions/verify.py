import asyncio

from daginquest.airflow.client import AirflowClient

TERMINAL = {"success", "failed", "upstream_failed", "skipped"}


async def verify_recovery(client: AirflowClient, params: dict, timeout_s: int = 300, poll_s: int = 10) -> str:
    """Poll the task instance until it reaches a terminal state or the timeout expires."""
    state = "unknown"
    waited = 0
    await asyncio.sleep(poll_s)  # give the scheduler time to pick the cleared task up
    while waited < timeout_s:
        state = await client.get_task_state(params["dag_id"], params["run_id"], params["task_id"])
        if state in TERMINAL:
            return state
        await asyncio.sleep(poll_s)
        waited += poll_s
    return state
