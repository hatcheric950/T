from fastapi import APIRouter, Depends, HTTPException
from backend.database import get_db
from backend.models import TaskCreate
from backend.services import ai_engine
from datetime import datetime, timezone, timedelta
import aiosqlite

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("", status_code=201)
async def create_task(task: TaskCreate, db: aiosqlite.Connection = Depends(get_db)):
    try:
        due = task.due_date.isoformat() if task.due_date else None
        async with db.execute(
            "INSERT INTO tasks (title, description, venture, due_date, priority) VALUES (?, ?, ?, ?, ?)",
            (task.title, task.description, task.venture, due, task.priority),
        ) as cur:
            task_id = cur.lastrowid
        await db.commit()
        return {"id": task_id, "status": "created"}
    finally:
        await db.close()


@router.get("")
async def list_tasks(include_completed: bool = False, db: aiosqlite.Connection = Depends(get_db)):
    try:
        query = "SELECT * FROM tasks"
        if not include_completed:
            query += " WHERE completed = 0"
        query += " ORDER BY due_date ASC, priority DESC, created_at ASC"
        async with db.execute(query) as cur:
            rows = await cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


@router.post("/{task_id}/complete")
async def complete_task(task_id: int, db: aiosqlite.Connection = Depends(get_db)):
    try:
        async with db.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)) as cur:
            if not await cur.fetchone():
                raise HTTPException(status_code=404, detail="Task not found")
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "UPDATE tasks SET completed = 1, completed_at = ? WHERE id = ?",
            (now, task_id),
        )
        await db.commit()
        return {"status": "completed"}
    finally:
        await db.close()


@router.get("/accountability")
async def accountability_report(db: aiosqlite.Connection = Depends(get_db)):
    try:
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        now = datetime.now(timezone.utc).isoformat()

        async with db.execute(
            "SELECT COUNT(*) as n FROM tasks WHERE completed = 1 AND completed_at >= ?", (week_ago,)
        ) as cur:
            completed = (await cur.fetchone())["n"]

        async with db.execute("SELECT COUNT(*) as n FROM tasks WHERE completed = 0") as cur:
            pending = (await cur.fetchone())["n"]

        async with db.execute(
            "SELECT COUNT(*) as n FROM tasks WHERE completed = 0 AND due_date < ?", (now,)
        ) as cur:
            overdue = (await cur.fetchone())["n"]

        async with db.execute(
            "SELECT COUNT(*) as n FROM leads WHERE created_at >= ?", (week_ago,)
        ) as cur:
            new_leads = (await cur.fetchone())["n"]

        async with db.execute(
            "SELECT COUNT(*) as n FROM leads WHERE next_followup <= ? AND status NOT IN ('won','lost')", (now,)
        ) as cur:
            followups_due = (await cur.fetchone())["n"]

        nudge = await ai_engine.generate_accountability_nudge(
            completed_tasks=completed,
            pending_tasks=pending,
            overdue_tasks=overdue,
            leads_this_week=new_leads,
            followups_due=followups_due,
        )

        return {
            "stats": {
                "completed_this_week": completed,
                "pending": pending,
                "overdue": overdue,
                "new_leads_this_week": new_leads,
                "followups_due": followups_due,
            },
            "nudge": nudge,
        }
    finally:
        await db.close()
