import hashlib
import re

_NOISE = [
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I), "<uuid>"),
    (re.compile(r"\b0x[0-9a-f]+\b", re.I), "<hex>"),
    (re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?"), "<ts>"),
    (re.compile(r"\d+"), "<n>"),
]


def normalize_error(text: str) -> str:
    for pattern, repl in _NOISE:
        text = pattern.sub(repl, text)
    return " ".join(text.split())[:500]


def fingerprint(dag_id: str, task_id: str, error: str) -> str:
    raw = f"{dag_id}|{task_id}|{normalize_error(error)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
