from daginquest.agent.state import IncidentState


def citation_ratio(cited: list[str], log_text: str) -> float:
    if not cited:
        return 0.0
    haystack = log_text
    valid = sum(1 for line in cited if line.strip() and line.strip() in haystack)
    return valid / len(cited)


async def verify_citations(state: IncidentState) -> dict:
    """Hallucination guard: cited lines must exist in the stored log, or confidence drops."""
    cited = state.get("cited_lines", [])
    ratio = citation_ratio(cited, state.get("log_text", ""))
    confidence = state.get("confidence", 0.0)
    if state.get("category") != "INCONCLUSIVE":
        confidence *= ratio if cited else 0.5
    kept = [c for c in cited if c.strip() and c.strip() in state.get("log_text", "")]
    return {"confidence": round(confidence, 3), "cited_lines": kept}
