from daginquest.policy.rules import evaluate


def test_safe_action_requires_approval():
    d = evaluate("retry_task", "TRANSIENT_NETWORK", 0.9, 0.6)
    assert d.allowed and d.requires_approval


def test_low_confidence_blocked():
    assert not evaluate("retry_task", "TRANSIENT_NETWORK", 0.2, 0.6).allowed


def test_unknown_action_blocked():
    assert not evaluate("drop_table", "TRANSIENT_NETWORK", 0.99, 0.6).allowed


def test_unsafe_category_blocked():
    assert not evaluate("retry_task", "SCHEMA_SQL", 0.99, 0.6).allowed
