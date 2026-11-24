"""Deterministic regex pre-classifier. Small local LLMs only handle what this cannot."""
import re

RULES: list[tuple[str, re.Pattern]] = [
    ("IMPORT_ERROR", re.compile(r"ModuleNotFoundError|ImportError|No module named", re.I)),
    ("SCHEMA_SQL", re.compile(r"column .* does not exist|relation .* does not exist|syntax error at", re.I)),
    ("TRANSIENT_NETWORK", re.compile(r"timed? ?out|Connection (reset|refused)|Temporary failure|ReadTimeout", re.I)),
    ("CONFIG_SECRET", re.compile(r"The conn_id .* isn't defined|Variable .* does not exist|authentication failed", re.I)),
    ("RESOURCE", re.compile(r"OutOfMemory|Killed|No space left on device|MemoryError", re.I)),
    ("UPSTREAM_DATA", re.compile(r"No such file|FileNotFound|sensor.*(timeout|timed out)|empty (dataset|table)", re.I)),
]


def preclassify(log_text: str) -> str | None:
    for category, pattern in RULES:
        if pattern.search(log_text):
            return category
    return None
