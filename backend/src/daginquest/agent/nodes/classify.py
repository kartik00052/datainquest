from daginquest.agent.state import IncidentState
from daginquest.utils.preclassify import preclassify


async def classify(state: IncidentState) -> dict:
    return {"pre_category": preclassify(state.get("log_text", ""))}
