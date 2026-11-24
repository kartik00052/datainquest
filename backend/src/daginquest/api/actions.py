from fastapi import APIRouter, BackgroundTasks, HTTPException

from daginquest.actions.executor import execute_action
from daginquest.db import repository as repo

router = APIRouter(prefix="/api/actions", tags=["actions"])


@router.get("/pending")
async def pending_actions() -> list[dict]:
    return await repo.list_pending_actions()


@router.post("/{action_id}/approve")
async def approve(action_id: int, background: BackgroundTasks) -> dict:
    action = await repo.decide_action(action_id, "approved", "dashboard", "dashboard")
    if not action:
        raise HTTPException(status_code=409, detail="action already decided or missing")
    background.add_task(execute_action, action_id)
    return {"action_id": action_id, "status": "approved"}


@router.post("/{action_id}/reject")
async def reject(action_id: int) -> dict:
    action = await repo.decide_action(action_id, "rejected", "dashboard", "dashboard")
    if not action:
        raise HTTPException(status_code=409, detail="action already decided or missing")
    return {"action_id": action_id, "status": "rejected"}
