import os
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db, get_db
from backend.routers import chat, voice, leads, tasks, dashboard, sms, calls
from backend.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _daily_nudge():
    import aiosqlite
    from backend.services import ai_engine, voice_learner
    from datetime import datetime, timezone, timedelta

    db = await get_db()
    try:
        now = datetime.now(timezone.utc).isoformat()
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        async with db.execute("SELECT COUNT(*) as n FROM tasks WHERE completed=1 AND completed_at>=?", (week_ago,)) as c:
            completed = (await c.fetchone())["n"]
        async with db.execute("SELECT COUNT(*) as n FROM tasks WHERE completed=0") as c:
            pending = (await c.fetchone())["n"]
        async with db.execute("SELECT COUNT(*) as n FROM tasks WHERE completed=0 AND due_date<?", (now,)) as c:
            overdue = (await c.fetchone())["n"]
        async with db.execute("SELECT COUNT(*) as n FROM leads WHERE created_at>=?", (week_ago,)) as c:
            new_leads = (await c.fetchone())["n"]
        async with db.execute("SELECT COUNT(*) as n FROM leads WHERE next_followup<=? AND status NOT IN ('won','lost')", (now,)) as c:
            followups = (await c.fetchone())["n"]
        nudge = await ai_engine.generate_accountability_nudge(completed, pending, overdue, new_leads, followups)
        logger.info("Daily nudge: %s", nudge)
        eric_phone = os.getenv("ERIC_PHONE_NUMBER", "")
        if eric_phone:
            from backend.services import sms as sms_svc
            result = sms_svc.send_sms(eric_phone, nudge)
            logger.info("Daily nudge SMS result: %s", result)
    finally:
        await db.close()


async def _followup_check():
    import aiosqlite
    from datetime import datetime, timezone

    db = await get_db()
    try:
        now = datetime.now(timezone.utc).isoformat()
        async with db.execute(
            "SELECT name, contact, venture FROM leads WHERE next_followup<=? AND status NOT IN ('won','lost')",
            (now,),
        ) as cur:
            rows = await cur.fetchall()
        if rows:
            logger.info("Follow-ups due: %d lead(s)", len(rows))
            for r in rows:
                logger.info("  → %s (%s) [%s]", r["name"], r["contact"], r["venture"])
    finally:
        await db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Database initialized")
    start_scheduler(_daily_nudge, _followup_check)
    yield
    stop_scheduler()


app = FastAPI(
    title="EricBot",
    description="Eric's AI Clone & Business Development Engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(voice.router)
app.include_router(leads.router)
app.include_router(tasks.router)
app.include_router(dashboard.router)
app.include_router(sms.router)
app.include_router(calls.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "EricBot"}


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("backend.server:app", host=host, port=port, reload=False)
