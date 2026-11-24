import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from daginquest.actions.executor import execute_action
from daginquest.db import repository as repo
from daginquest.telegram.security import allowed_only


@allowed_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "DagInquest ready.\n/incidents - recent incidents\n/incident <id> - details\n/status - metrics"
    )


@allowed_only
async def incidents(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = await repo.list_incidents(10)
    if not rows:
        await update.message.reply_text("No incidents yet.")
        return
    text = "\n".join(
        f"#{r['id']} {r['dag_id']}.{r['task_id']} [{r['status']}] {r['category'] or '-'}" for r in rows
    )
    await update.message.reply_text(text)


@allowed_only
async def incident(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /incident <id>")
        return
    row = await repo.get_incident(int(context.args[0]))
    if not row:
        await update.message.reply_text("Not found.")
        return
    await update.message.reply_text(
        f"#{row['id']} {row['dag_id']}.{row['task_id']}\nStatus: {row['status']}\n"
        f"Category: {row['category']}  Confidence: {row['confidence']}\nCause: {row['root_cause']}"
    )


@allowed_only
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    m = await repo.get_metrics()
    await update.message.reply_text(
        f"Incidents: {m['total_incidents']} (open {m['open_incidents']})\n"
        f"Deduplicated alerts: {m['deduplicated_alerts']}\n"
        f"Actions succeeded: {m['actions_succeeded']}"
    )


@allowed_only
async def decision_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    verb, _, raw_id = (query.data or "").partition(":")
    if verb not in {"approve", "reject"} or not raw_id.isdigit():
        return
    action_id = int(raw_id)
    decision = "approved" if verb == "approve" else "rejected"
    row = await repo.decide_action(action_id, decision, str(update.effective_user.id), "telegram")
    if not row:
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"Action #{action_id} was already decided.")
        return
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(f"Action #{action_id} {decision}.")
    if decision == "approved":
        asyncio.create_task(execute_action(action_id))
