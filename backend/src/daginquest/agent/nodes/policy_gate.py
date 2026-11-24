from dataclasses import asdict

from daginquest.agent.state import IncidentState
from daginquest.config import get_settings
from daginquest.policy.rules import evaluate


async def policy_gate(state: IncidentState) -> dict:
    action = state.get("proposed_action")
    decision = evaluate(
        action["type"] if action else None,
        state.get("category", "INCONCLUSIVE"),
        state.get("confidence", 0.0),
        get_settings().confidence_threshold,
    )
    return {"policy": asdict(decision)}
