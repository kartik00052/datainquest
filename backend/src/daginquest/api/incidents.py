from fastapi import APIRouter, HTTPException

from daginquest.db import repository as repo

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("")
async def list_incidents(limit: int = 50) -> list[dict]:
    return await repo.list_incidents(limit)


@router.get("/{incident_id}")
async def get_incident(incident_id: int) -> dict:
    incident = await repo.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="incident not found")
    return incident
