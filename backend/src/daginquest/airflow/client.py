"""Thin Airflow 3 REST client.

NOTE: endpoint paths follow the Airflow 3 REST API v2 as best known; confirm them
against your running instance (http://localhost:8080/docs) and adjust if needed.
"""
import httpx

from daginquest.config import get_settings


class AirflowClient:
    def __init__(self) -> None:
        s = get_settings()
        self.base = s.airflow_base_url.rstrip("/")
        self._user, self._pass = s.airflow_username, s.airflow_password
        self._token: str | None = None

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        resp = await client.post(
            f"{self.base}/auth/token", json={"username": self._user, "password": self._pass}
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        async with httpx.AsyncClient(timeout=30) as client:
            for attempt in range(2):
                if self._token is None:
                    self._token = await self._get_token(client)
                headers = {"Authorization": f"Bearer {self._token}", **kwargs.pop("headers", {})}
                resp = await client.request(method, f"{self.base}{path}", headers=headers, **kwargs)
                if resp.status_code == 401 and attempt == 0:
                    self._token = None
                    continue
                resp.raise_for_status()
                return resp
        raise RuntimeError("unreachable")

    async def get_task_log(self, dag_id: str, run_id: str, task_id: str, try_number: int) -> str:
        path = f"/api/v2/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/logs/{try_number}"
        resp = await self._request("GET", path, headers={"Accept": "application/json"})
        try:
            data = resp.json()
        except ValueError:
            return resp.text
        content = data.get("content", data)
        if isinstance(content, list):
            return "\n".join(str(item.get("event", item)) if isinstance(item, dict) else str(item) for item in content)
        return str(content)

    async def get_dag_source(self, dag_id: str) -> str:
        resp = await self._request("GET", f"/api/v2/dagSources/{dag_id}")
        data = resp.json()
        return data.get("content", "")

    async def get_task_state(self, dag_id: str, run_id: str, task_id: str) -> str:
        path = f"/api/v2/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}"
        resp = await self._request("GET", path)
        return resp.json().get("state") or "unknown"

    async def clear_task(self, dag_id: str, run_id: str, task_id: str) -> dict:
        body = {"dry_run": False, "dag_run_id": run_id, "task_ids": [task_id], "only_failed": True}
        resp = await self._request("POST", f"/api/v2/dags/{dag_id}/clearTaskInstances", json=body)
        return resp.json()
