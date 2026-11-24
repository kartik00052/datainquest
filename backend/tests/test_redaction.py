from daginquest.security.redaction import redact


def test_redacts_secrets_and_urls():
    text = "password=hunter2 token: abc123 postgresql://u:p@host/db AKIAABCDEFGHIJKLMNOP"
    out = redact(text)
    assert "hunter2" not in out and "abc123" not in out
    assert "u:p@host" not in out and "AKIAABCDEFGHIJKLMNOP" not in out
