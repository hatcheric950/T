from fastapi import APIRouter, Depends, HTTPException
from backend.database import get_db
from backend.models import LeadCreate, LeadUpdate, Lead
from backend.services import ai_engine, voice_learner
from typing import Optional
import aiosqlite
from datetime import datetime, timezone

router = APIRouter(prefix="/api/leads", tags=["leads"])

VALID_STATUSES = {"new", "contacted", "qualified", "proposal", "won", "lost", "nurture"}
VALID_VENTURES = {"hatch", "eric_digital", "ancient_coast", "nexus"}


@router.post("", status_code=201)
async def create_lead(lead: LeadCreate, db: aiosqlite.Connection = Depends(get_db)):
    if lead.venture not in VALID_VENTURES:
        raise HTTPException(status_code=422, detail=f"venture must be one of: {', '.join(VALID_VENTURES)}")
    try:
        followup = lead.next_followup.isoformat() if lead.next_followup else None
        async with db.execute(
            """INSERT INTO leads (name, contact, venture, source, notes, value, next_followup)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (lead.name, lead.contact, lead.venture, lead.source, lead.notes, lead.value, followup),
        ) as cur:
            lead_id = cur.lastrowid
        await db.commit()
        return {"id": lead_id, "status": "created"}
    finally:
        await db.close()


@router.get("")
async def list_leads(
    venture: Optional[str] = None,
    status: Optional[str] = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    try:
        query = "SELECT * FROM leads WHERE 1=1"
        params: list = []
        if venture:
            query += " AND venture = ?"
            params.append(venture)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"

        async with db.execute(query, params) as cur:
            rows = await cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


@router.patch("/{lead_id}")
async def update_lead(lead_id: int, update: LeadUpdate, db: aiosqlite.Connection = Depends(get_db)):
    try:
        async with db.execute("SELECT id FROM leads WHERE id = ?", (lead_id,)) as cur:
            if not await cur.fetchone():
                raise HTTPException(status_code=404, detail="Lead not found")

        if update.status and update.status not in VALID_STATUSES:
            raise HTTPException(status_code=422, detail=f"status must be one of: {', '.join(VALID_STATUSES)}")

        fields = []
        params = []
        for field, val in update.model_dump(exclude_none=True).items():
            if field == "next_followup" and hasattr(val, "isoformat"):
                val = val.isoformat()
            fields.append(f"{field} = ?")
            params.append(val)

        if not fields:
            raise HTTPException(status_code=422, detail="No fields to update")

        fields.append("updated_at = ?")
        params.append(datetime.now(timezone.utc).isoformat())
        params.append(lead_id)

        await db.execute(f"UPDATE leads SET {', '.join(fields)} WHERE id = ?", params)
        await db.commit()
        return {"status": "updated"}
    finally:
        await db.close()


@router.get("/followups")
async def get_followups(db: aiosqlite.Connection = Depends(get_db)):
    try:
        now = datetime.now(timezone.utc).isoformat()
        async with db.execute(
            """SELECT * FROM leads
               WHERE next_followup <= ? AND status NOT IN ('won', 'lost')
               ORDER BY next_followup ASC""",
            (now,),
        ) as cur:
            rows = await cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


@router.get("/stats")
async def get_stats(db: aiosqlite.Connection = Depends(get_db)):
    try:
        async with db.execute("SELECT venture, status, COUNT(*) as count, SUM(value) as value FROM leads GROUP BY venture, status") as cur:
            rows = await cur.fetchall()

        by_venture: dict = {}
        for row in rows:
            v = row["venture"]
            if v not in by_venture:
                by_venture[v] = {"total": 0, "pipeline_value": 0, "by_status": {}}
            by_venture[v]["total"] += row["count"]
            by_venture[v]["pipeline_value"] += row["value"] or 0
            by_venture[v]["by_status"][row["status"]] = row["count"]

        async with db.execute("SELECT COUNT(*) as n FROM leads") as cur:
            total = (await cur.fetchone())["n"]

        return {"total_leads": total, "by_venture": by_venture}
    finally:
        await db.close()


@router.post("/draft")
async def draft_outreach_for_lead(
    lead_id: int,
    channel: str = "email",
    context: str = "",
    db: aiosqlite.Connection = Depends(get_db),
):
    try:
        async with db.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)) as cur:
            lead = await cur.fetchone()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

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
            recipient_name=lead["name"],
            venture=lead["venture"],
            channel=channel,
            context=context or (lead["notes"] or "general follow-up"),
            tone="friendly",
            style_context=style_ctx,
        )
        return {"draft": draft, "lead": dict(lead)}
    finally:
        await db.close()
