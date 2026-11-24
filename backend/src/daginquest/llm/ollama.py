import json

import httpx

from daginquest.config import get_settings


async def chat_json(messages: list[dict], schema: dict | None = None, model: str | None = None) -> dict:
    """Call Ollama /api/chat with structured JSON output. Temperature 0 for reproducibility."""
    settings = get_settings()
    payload = {
        "model": model or settings.ollama_model,
        "messages": messages,
        "stream": False,
        "format": schema or "json",
        "options": {"temperature": 0},
    }
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(f"{settings.ollama_url}/api/chat", json=payload)
        resp.raise_for_status()
    return json.loads(resp.json()["message"]["content"])
