"""All SQL lives here. Plain psycopg, no ORM, so queries stay explicit and testable."""
import hashlib

from psycopg.types.json import Jsonb

from daginquest.db.session import get_pool


async def create_or_bump_incident(
    fp: str, dag_id: str, run_id: str, task_id: str, try_number: int, cooldown_min: int
) -> tuple[int, bool]:
    async with get_pool().connection() as conn:
        cur = await conn.execute(
            """UPDATE incidents SET occurrences = occurrences + 1, updated_at = now()
               WHERE id = (SELECT id FROM incidents WHERE fingerprint = %s
                           AND created_at > now() - make_interval(mins => %s)
                           ORDER BY created_at DESC LIMIT 1)
               RETURNING id""",
            (fp, cooldown_min),
        )
        row = await cur.fetchone()
        if row:
            return row["id"], False
        cur = await conn.execute(
            """INSERT INTO incidents (fingerprint, dag_id, run_id, task_id, try_number)
               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (fp, dag_id, run_id, task_id, try_number),
        )
        row = await cur.fetchone()
        await _audit(conn, "system", "incident_created", row["id"], {"dag_id": dag_id})
        return row["id"], True


async def add_evidence(incident_id: int, kind: str, content: str) -> None:
    digest = hashlib.sha256(content.encode()).hexdigest()
    async with get_pool().connection() as conn:
        await conn.execute(
            "INSERT INTO evidence (incident_id, kind, content, content_hash) VALUES (%s,%s,%s,%s)",
            (incident_id, kind, content, digest),
        )


async def save_analysis(
    incident_id: int, model: str, category: str, root_cause: str,
    confidence: float, cited_lines: list[str], raw: dict,
) -> None:
    async with get_pool().connection() as conn:
        await conn.execute(
            """INSERT INTO analyses (incident_id, model, category, root_cause, confidence,
                                     cited_lines, raw) VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (incident_id, model, category, root_cause, confidence, Jsonb(cited_lines), Jsonb(raw)),
        )
        await conn.execute(
            """UPDATE incidents SET category=%s, root_cause=%s, confidence=%s,
                      status='analyzed', updated_at=now() WHERE id=%s""",
            (category, root_cause, confidence, incident_id),
        )
        await _audit(conn, "agent", "analysis_saved", incident_id, {"category": category})


async def create_action(incident_id: int, type_: str, params: dict, risk: str) -> int | None:
    key = f"{incident_id}:{type_}"
    async with get_pool().connection() as conn:
        cur = await conn.execute(
            """INSERT INTO actions (incident_id, type, params, risk, idempotency_key)
               VALUES (%s,%s,%s,%s,%s) ON CONFLICT (idempotency_key) DO NOTHING RETURNING id""",
            (incident_id, type_, Jsonb(params), risk, key),
        )
        row = await cur.fetchone()
        return row["id"] if row else None


async def decide_action(action_id: int, decision: str, user_id: str, channel: str) -> dict | None:
    """Atomic transition pending_approval -> approved/rejected. None if already decided."""
    async with get_pool().connection() as conn:
        cur = await conn.execute(
            """UPDATE actions SET status=%s, updated_at=now()
               WHERE id=%s AND status='pending_approval' RETURNING *""",
            (decision, action_id),
        )
        row = await cur.fetchone()
        if not row:
            return None
        await conn.execute(
            "INSERT INTO approvals (action_id, channel, user_id, decision) VALUES (%s,%s,%s,%s)",
            (action_id, channel, user_id, decision),
        )
        await _audit(conn, user_id, f"action_{decision}", row["incident_id"], {"action_id": action_id})
        return row


async def get_action(action_id: int) -> dict | None:
    async with get_pool().connection() as conn:
        cur = await conn.execute("SELECT * FROM actions WHERE id=%s", (action_id,))
        return await cur.fetchone()


async def set_action_result(action_id: int, status: str, result: dict) -> None:
    async with get_pool().connection() as conn:
        cur = await conn.execute(
            "UPDATE actions SET status=%s, result=%s, updated_at=now() WHERE id=%s RETURNING incident_id",
            (status, Jsonb(result), action_id),
        )
        row = await cur.fetchone()
        if row:
            new_status = "resolved" if status == "succeeded" else "needs_attention"
            await conn.execute("UPDATE incidents SET status=%s WHERE id=%s", (new_status, row["incident_id"]))
            await _audit(conn, "executor", f"action_{status}", row["incident_id"], result)


async def list_incidents(limit: int = 50) -> list[dict]:
    async with get_pool().connection() as conn:
        cur = await conn.execute("SELECT * FROM incidents ORDER BY created_at DESC LIMIT %s", (limit,))
        return await cur.fetchall()


async def get_incident(incident_id: int) -> dict | None:
    async with get_pool().connection() as conn:
        cur = await conn.execute("SELECT * FROM incidents WHERE id=%s", (incident_id,))
        incident = await cur.fetchone()
        if not incident:
            return None
        cur = await conn.execute("SELECT * FROM actions WHERE incident_id=%s ORDER BY id", (incident_id,))
        incident["actions"] = await cur.fetchall()
        cur = await conn.execute(
            "SELECT kind, left(content, 4000) AS content FROM evidence WHERE incident_id=%s", (incident_id,)
        )
        incident["evidence"] = await cur.fetchall()
        return incident


async def list_pending_actions() -> list[dict]:
    async with get_pool().connection() as conn:
        cur = await conn.execute(
            """SELECT a.*, i.dag_id, i.task_id, i.root_cause, i.confidence
               FROM actions a JOIN incidents i ON i.id = a.incident_id
               WHERE a.status='pending_approval' ORDER BY a.id DESC"""
        )
        return await cur.fetchall()


async def get_metrics() -> dict:
    async with get_pool().connection() as conn:
        cur = await conn.execute(
            """SELECT count(*) AS total_incidents,
                      count(*) FILTER (WHERE status IN ('open','analyzed')) AS open_incidents,
                      coalesce(sum(occurrences - 1), 0) AS deduplicated_alerts,
                      coalesce(avg(confidence), 0) AS avg_confidence
               FROM incidents"""
        )
        metrics = await cur.fetchone()
        cur = await conn.execute("SELECT count(*) AS n FROM actions WHERE status='succeeded'")
        metrics["actions_succeeded"] = (await cur.fetchone())["n"]
        return metrics


async def audit(actor: str, event: str, incident_id: int | None, details: dict) -> None:
    async with get_pool().connection() as conn:
        await _audit(conn, actor, event, incident_id, details)


async def _audit(conn, actor: str, event: str, incident_id: int | None, details: dict) -> None:
    await conn.execute(
        "INSERT INTO audit_log (actor, event, incident_id, details) VALUES (%s,%s,%s,%s)",
        (actor, event, incident_id, Jsonb(details)),
    )
