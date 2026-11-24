"""Outbound Telegram messages via plain HTTPS, so the API needs no bot process."""
import html

import httpx

from daginquest.config import get_settings


async def _send(payload: dict) -> None:
    s = get_settings()
    if not s.telegram_bot_token:
        return
    async with httpx.AsyncClient(timeout=15) as client:
        for chat_id in s.allowed_chat_ids:
            await client.post(
                f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage",
                json={**payload, "chat_id": chat_id, "parse_mode": "HTML"},
            )


async def send_text(text: str) -> None:
    await _send({"text": html.escape(text)})


async def send_incident_alert(state: dict, action_id: int | None, policy: dict) -> None:
    lines = [
        f"<b>Incident #{state['incident_id']}</b>  {html.escape(state['dag_id'])}."
        f"{html.escape(state['task_id'])}",
        f"Category: <b>{html.escape(state['category'])}</b>  "
        f"Confidence: {state['confidence']:.2f}",
        f"Cause: {html.escape(state['root_cause'])}",
    ]
    for line in state.get("cited_lines", [])[:3]:
        lines.append(f"<code>{html.escape(line[:200])}</code>")
    lines.append(f"Policy: {html.escape(policy.get('reason', ''))}")
    payload: dict = {"text": "\n".join(lines)}
    if action_id:
        payload["reply_markup"] = {
            "inline_keyboard": [[
                {"text": "Approve retry", "callback_data": f"approve:{action_id}"},
                {"text": "Reject", "callback_data": f"reject:{action_id}"},
            ]]
        }
    await _send(payload)
