RCA_SYSTEM = """You are an Airflow incident analyst. Diagnose the failed task from the evidence only.
Rules:
- Choose the best category, or INCONCLUSIVE if the evidence is insufficient. Never guess.
- cited_lines must be exact lines copied from the log.
- confidence reflects how directly the log supports the root cause (0.0 to 1.0).
Return JSON only."""


def rca_user_prompt(log_text: str, dag_source: str, hint: str | None) -> str:
    hint_part = f"Heuristic hint (may be wrong): {hint}\n\n" if hint else ""
    return (
        f"{hint_part}=== TASK LOG (tail) ===\n{log_text}\n\n"
        f"=== DAG SOURCE ===\n{dag_source[:4000]}\n"
    )
