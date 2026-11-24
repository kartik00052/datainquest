import re

_PATTERNS = [
    (re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key)\s*[=:]\s*\S+"), r"\1=<redacted>"),
    (re.compile(r"(?i)bearer\s+[a-z0-9._\-]+"), "Bearer <redacted>"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "<aws-key-redacted>"),
    (re.compile(r"(?i)(postgres(ql)?|mysql|redis|amqp)://[^\s'\"]+"), r"\1://<redacted>"),
]


def redact(text: str) -> str:
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text
