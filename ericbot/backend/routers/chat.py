from fastapi import APIRouter, Depends
from backend.database import get_db
from backend.models import ChatMessage, ChatResponse
from backend.services import ai_engine, voice_learner
import aiosqlite

router = APIRouter(prefix="/api", tags=["chat"])


async def _load_style_context(db: aiosqlite.Connection) -> tuple[str, float]:
    async with db.execute(
        "SELECT category, content FROM voice_samples ORDER BY created_at DESC LIMIT 200"
    ) as cur:
        rows = await cur.fetchall()

    if not rows:
        return "", 0.0

    by_cat: dict[str, list[str]] = {}
    for row in rows:
        by_cat.setdefault(row["category"], []).append(row["content"])

    patterns = {cat: voice_learner.extract_patterns(samples) for cat, samples in by_cat.items()}
    context = voice_learner.build_style_context(patterns)
    confidence = voice_learner.confidence_score(len(rows))
    return context, confidence


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatMessage, db: aiosqlite.Connection = Depends(get_db)):
    try:
        history = []
        if payload.include_history:
            async with db.execute(
                "SELECT role, content FROM chat_history ORDER BY created_at DESC LIMIT 40"
            ) as cur:
                rows = await cur.fetchall()
            history = list(reversed([{"role": r["role"], "content": r["content"]} for r in rows]))

        style_context, confidence = await _load_style_context(db)
        reply = await ai_engine.chat(payload.message, history, style_context)

        await db.execute(
            "INSERT INTO chat_history (role, content) VALUES (?, ?)",
            ("user", payload.message),
        )
        await db.execute(
            "INSERT INTO chat_history (role, content) VALUES (?, ?)",
            ("assistant", reply),
        )
        await db.commit()

        return ChatResponse(reply=reply, voice_confidence=confidence)
    finally:
        await db.close()
