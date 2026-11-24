from daginquest.utils.fingerprint import fingerprint


def test_same_error_different_numbers_same_fingerprint():
    a = fingerprint("etl", "load", "Timeout after 30s at 2026-11-01T10:00:00Z, pid 123")
    b = fingerprint("etl", "load", "Timeout after 45s at 2026-11-02T11:30:00Z, pid 999")
    assert a == b


def test_different_task_different_fingerprint():
    assert fingerprint("etl", "load", "boom") != fingerprint("etl", "extract", "boom")
