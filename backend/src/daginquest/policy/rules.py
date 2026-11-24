from dataclasses import dataclass

ALLOWED_ACTIONS = {"retry_task", "clear_task"}
SAFE_CATEGORIES = {"TRANSIENT_NETWORK", "RESOURCE"}


@dataclass
class PolicyDecision:
    allowed: bool
    requires_approval: bool
    risk: str
    reason: str


def evaluate(action_type: str | None, category: str, confidence: float, threshold: float) -> PolicyDecision:
    if action_type is None:
        return PolicyDecision(False, False, "none", "no remediation proposed; notify only")
    if action_type not in ALLOWED_ACTIONS:
        return PolicyDecision(False, False, "high", f"action '{action_type}' is not allow-listed")
    if category not in SAFE_CATEGORIES:
        return PolicyDecision(False, False, "medium", f"category {category} is not auto-remediable")
    if confidence < threshold:
        return PolicyDecision(False, False, "medium", "confidence below threshold")
    # Every write action requires human approval, no exceptions.
    return PolicyDecision(True, True, "low", "allow-listed action; approval required")
