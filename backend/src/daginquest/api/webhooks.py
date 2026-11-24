import hmac

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException
from pydantic import BaseModel

from daginquest.agent.runner import run_investigation
from daginquest.config import get_settings
from daginquest.db import repository as repo
from daginquest.utils.fingerprint import fingerprint

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


class FailurePayload(BaseModel):
    dag_id: str
    run_id: str
    task_id: str
    try_number: int = 1
    error: str = ""


@router.post("/airflow/failure", status_code=202)
async def airflow_failure(
    payload: FailurePayload,
    background: BackgroundTasks,
    x_webhook_secret: str = Header(default=""),
) -> dict:
    settings = get_settings()
    if not hmac.compare_digest(x_webhook_secret, settings.webhook_secret):
        raise HTTPException(status_code=401, detail="invalid webhook secret")

    fp = fingerprint(payload.dag_id, payload.task_id, payload.error)
    incident_id, is_new = await repo.create_or_bump_incident(
        fp, payload.dag_id, payload.run_id, payload.task_id, payload.try_number,
        settings.dedupe_cooldown_minutes,
    )
    if is_new:
        background.add_task(run_investigation, incident_id, payload.model_dump())
    return {"incident_id": incident_id, "deduplicated": not is_new}
