"""Shared helper: build Eric's voice style context from stored samples."""
import aiosqlite
from backend.services import voice_learner


async def load_style_context(db: aiosqlite.Connection) -> tuple[str, float]:
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
