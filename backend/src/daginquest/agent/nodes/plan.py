from daginquest.agent.state import IncidentState

CATEGORY_TO_ACTION = {"TRANSIENT_NETWORK": "retry_task", "RESOURCE": "retry_task"}


async def plan(state: IncidentState) -> dict:
    action_type = CATEGORY_TO_ACTION.get(state.get("category", ""))
    if not action_type:
        return {"proposed_action": None}
    return {
        "proposed_action": {
            "type": action_type,
            "params": {
                "dag_id": state["dag_id"],
                "run_id": state["run_id"],
                "task_id": state["task_id"],
            },
        }
    }
