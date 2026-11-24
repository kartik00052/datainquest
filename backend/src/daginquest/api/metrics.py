from fastapi import APIRouter

from daginquest.db import repository as repo

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("")
async def metrics() -> dict:
    return await repo.get_metrics()
