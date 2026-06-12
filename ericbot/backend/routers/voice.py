from fastapi import APIRouter, Depends, HTTPException
from backend.database import get_db
from backend.models import VoiceSample, VoiceProfile
from backend.services import voice_learner
import aiosqlite

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.post("/ingest", status_code=201)
async def ingest_sample(sample: VoiceSample, db: aiosqlite.Connection = Depends(get_db)):
    if sample.category not in voice_learner.VALID_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"category must be one of: {', '.join(voice_learner.VALID_CATEGORIES)}",
        )
    try:
        await db.execute(
            "INSERT INTO voice_samples (category, content) VALUES (?, ?)",
            (sample.category, sample.content.strip()),
        )
        await db.commit()
        async with db.execute("SELECT COUNT(*) as n FROM voice_samples") as cur:
            row = await cur.fetchone()
        return {"status": "ingested", "total_samples": row["n"]}
    finally:
        await db.close()


@router.get("/profile", response_model=VoiceProfile)
async def get_profile(db: aiosqlite.Connection = Depends(get_db)):
    try:
        async with db.execute(
            "SELECT category, content FROM voice_samples ORDER BY created_at DESC LIMIT 500"
        ) as cur:
            rows = await cur.fetchall()

        if not rows:
            return VoiceProfile(
                sample_count=0,
                categories={},
                confidence=0.0,
                style_summary="No samples yet. Feed me your emails, texts, and calls.",
            )

        by_cat: dict[str, list[str]] = {}
        for row in rows:
            by_cat.setdefault(row["category"], []).append(row["content"])

        patterns = {cat: voice_learner.extract_patterns(samples) for cat, samples in by_cat.items()}
        confidence = voice_learner.confidence_score(len(rows))
        summary = voice_learner.build_style_context(patterns)

        return VoiceProfile(
            sample_count=len(rows),
            categories={cat: len(samples) for cat, samples in by_cat.items()},
            confidence=confidence,
            style_summary=summary,
        )
    finally:
        await db.close()
