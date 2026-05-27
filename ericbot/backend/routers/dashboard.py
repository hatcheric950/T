from fastapi import APIRouter, Depends
from backend.database import get_db
from backend.services import voice_learner
from datetime import datetime, timezone, timedelta
import aiosqlite

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.post("/draft")
async def draft_outreach(
    recipient_name: str,
    venture: str,
    channel: str = "email",
    context: str = "",
    tone: str = "friendly",
    db: aiosqlite.Connection = Depends(get_db),
):
    from backend.services import ai_engine
    try:
        async with db.execute(
            "SELECT category, content FROM voice_samples ORDER BY created_at DESC LIMIT 200"
        ) as cur:
            samples = await cur.fetchall()

        style_ctx = ""
        if samples:
            by_cat: dict[str, list[str]] = {}
            for s in samples:
                by_cat.setdefault(s["category"], []).append(s["content"])
            patterns = {cat: voice_learner.extract_patterns(v) for cat, v in by_cat.items()}
            style_ctx = voice_learner.build_style_context(patterns)

        draft = await ai_engine.draft_outreach(
            recipient_name=recipient_name,
            venture=venture,
            channel=channel,
            context=context,
            tone=tone,
            style_context=style_ctx,
        )
        return {"draft": draft}
    finally:
        await db.close()


@router.get("/dashboard")
async def dashboard(db: aiosqlite.Connection = Depends(get_db)):
    try:
        now = datetime.now(timezone.utc).isoformat()
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

        async with db.execute("SELECT COUNT(*) as n FROM leads") as cur:
            total_leads = (await cur.fetchone())["n"]

        async with db.execute(
            "SELECT COUNT(*) as n FROM leads WHERE status = 'new'"
        ) as cur:
            new_leads = (await cur.fetchone())["n"]

        async with db.execute(
            "SELECT COUNT(*) as n FROM leads WHERE next_followup <= ? AND status NOT IN ('won','lost')",
            (now,),
        ) as cur:
            followups_due = (await cur.fetchone())["n"]

        async with db.execute(
            "SELECT SUM(value) as v FROM leads WHERE status = 'won'"
        ) as cur:
            won_value = (await cur.fetchone())["v"] or 0

        async with db.execute(
            "SELECT COUNT(*) as n FROM tasks WHERE completed = 0"
        ) as cur:
            pending_tasks = (await cur.fetchone())["n"]

        async with db.execute(
            "SELECT COUNT(*) as n FROM tasks WHERE completed = 0 AND due_date < ?", (now,)
        ) as cur:
            overdue_tasks = (await cur.fetchone())["n"]

        async with db.execute("SELECT COUNT(*) as n FROM voice_samples") as cur:
            voice_samples = (await cur.fetchone())["n"]

        async with db.execute(
            "SELECT venture, COUNT(*) as n FROM leads WHERE status NOT IN ('won','lost') GROUP BY venture"
        ) as cur:
            pipeline_rows = await cur.fetchall()
        pipeline = {r["venture"]: r["n"] for r in pipeline_rows}

        async with db.execute(
            "SELECT * FROM leads WHERE next_followup <= ? AND status NOT IN ('won','lost') ORDER BY next_followup ASC LIMIT 5",
            (now,),
        ) as cur:
            urgent = [dict(r) for r in await cur.fetchall()]

        async with db.execute(
            "SELECT * FROM tasks WHERE completed = 0 ORDER BY due_date ASC, priority DESC LIMIT 5"
        ) as cur:
            top_tasks = [dict(r) for r in await cur.fetchall()]

        return {
            "metrics": {
                "total_leads": total_leads,
                "new_leads": new_leads,
                "followups_due": followups_due,
                "won_revenue": won_value,
                "pending_tasks": pending_tasks,
                "overdue_tasks": overdue_tasks,
                "voice_samples": voice_samples,
                "voice_confidence": voice_learner.confidence_score(voice_samples),
            },
            "pipeline_by_venture": pipeline,
            "urgent_followups": urgent,
            "top_tasks": top_tasks,
        }
    finally:
        await db.close()
