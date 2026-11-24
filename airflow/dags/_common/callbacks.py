"""Failure callback: posts the failure to the DagInquest API (never raises)."""
import os

import requests

API_URL = os.environ.get("DAGINQUEST_API_URL", "http://api:8000")
SECRET = os.environ.get("DAGINQUEST_WEBHOOK_SECRET", "")


def notify_failure(context: dict) -> None:
    try:
        ti = context["ti"]
        exception = context.get("exception")
        payload = {
            "dag_id": ti.dag_id,
            "run_id": ti.run_id,
            "task_id": ti.task_id,
            "try_number": getattr(ti, "try_number", 1) or 1,
            "error": str(exception)[:2000] if exception else "",
        }
        requests.post(
            f"{API_URL}/api/webhooks/airflow/failure",
            json=payload,
            headers={"X-Webhook-Secret": SECRET},
            timeout=10,
        )
    except Exception:
        pass  # an alerting problem must never break the pipeline itself
