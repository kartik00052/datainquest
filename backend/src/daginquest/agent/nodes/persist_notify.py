from daginquest.agent.state import IncidentState
from daginquest.db import repository as repo
from daginquest.telegram import notifier


async def persist_notify(state: IncidentState) -> dict:
    incident_id = state["incident_id"]
    await repo.save_analysis(
        incident_id, state.get("model", ""), state["category"], state["root_cause"],
        state["confidence"], state.get("cited_lines", []),
        {"pre_category": state.get("pre_category"), "policy": state.get("policy")},
    )
    action_id = None
    policy = state.get("policy", {})
    action = state.get("proposed_action")
    if action and policy.get("allowed"):
        action_id = await repo.create_action(incident_id, action["type"], action["params"], policy["risk"])
    await notifier.send_incident_alert(state, action_id, policy)
    return {}
