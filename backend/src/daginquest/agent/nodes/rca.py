from daginquest.agent.prompts import RCA_SYSTEM, rca_user_prompt
from daginquest.agent.state import IncidentState
from daginquest.config import get_settings
from daginquest.llm.ollama import chat_json
from daginquest.llm.schemas import RCAResult
from daginquest.utils.preclassify import preclassify


async def analyze(log_text: str, dag_source: str = "", model: str | None = None) -> RCAResult:
    """Reusable by the graph and by the eval harness."""
    hint = preclassify(log_text)
    messages = [
        {"role": "system", "content": RCA_SYSTEM},
        {"role": "user", "content": rca_user_prompt(log_text, dag_source, hint)},
    ]
    try:
        raw = await chat_json(messages, schema=RCAResult.model_json_schema(), model=model)
        result = RCAResult.model_validate(raw)
    except Exception:
        return RCAResult(
            category=hint or "INCONCLUSIVE",  # type: ignore[arg-type]
            root_cause="LLM unavailable or returned invalid output; heuristic result only.",
            confidence=0.3 if hint else 0.0,
        )
    if result.category == "INCONCLUSIVE" and hint:
        result.category = hint  # type: ignore[assignment]
        result.confidence = min(result.confidence, 0.5)
    return result


async def rca(state: IncidentState) -> dict:
    result = await analyze(state.get("log_text", ""), state.get("dag_source", ""))
    return {
        "category": result.category,
        "root_cause": result.root_cause,
        "confidence": result.confidence,
        "cited_lines": result.cited_lines,
        "model": get_settings().ollama_model,
    }
