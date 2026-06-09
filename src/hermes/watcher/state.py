from __future__ import annotations

import time
from pathlib import Path

import aiosqlite


SCHEMA = """
CREATE TABLE IF NOT EXISTS seen (
    message_id TEXT PRIMARY KEY,
    ts REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    channel TEXT NOT NULL,
    sender TEXT NOT NULL,
    message_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    draft TEXT,
    sent INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS audit_ts ON audit(ts);
CREATE INDEX IF NOT EXISTS audit_sender ON audit(sender);
CREATE TABLE IF NOT EXISTS classify_cache (
    message_id TEXT PRIMARY KEY,
    wants_reply INTEGER NOT NULL,
    ts REAL NOT NULL
);
"""


class State:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def open(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.executescript(SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        assert self._db is not None, "State not opened"
        return self._db

    async def mark_seen(self, message_id: str) -> bool:
        """Return True if newly inserted, False if duplicate."""
        try:
            await self.db.execute(
                "INSERT INTO seen(message_id, ts) VALUES(?,?)", (message_id, time.time())
            )
            await self.db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def hourly_sent_count(self) -> int:
        cutoff = time.time() - 3600
        async with self.db.execute(
            "SELECT COUNT(*) FROM audit WHERE sent=1 AND ts>=?", (cutoff,)
        ) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row else 0

    async def daily_sender_count(self, sender: str) -> int:
        cutoff = time.time() - 86400
        async with self.db.execute(
            "SELECT COUNT(*) FROM audit WHERE sent=1 AND sender=? AND ts>=?",
            (sender.lower(), cutoff),
        ) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row else 0

    async def daily_sms_cost(self) -> float:
        cutoff = time.time() - 86400
        async with self.db.execute(
            "SELECT COALESCE(SUM(cost_usd),0) FROM audit WHERE channel='sms' AND ts>=?",
            (cutoff,),
        ) as cur:
            row = await cur.fetchone()
            return float(row[0]) if row else 0.0

    async def log_audit(
        self,
        *,
        channel: str,
        sender: str,
        message_id: str,
        decision: str,
        draft: str = "",
        sent: bool = False,
        cost_usd: float = 0.0,
    ) -> None:
        await self.db.execute(
            "INSERT INTO audit(ts,channel,sender,message_id,decision,draft,sent,cost_usd)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (time.time(), channel, sender.lower(), message_id, decision,
             draft, 1 if sent else 0, cost_usd),
        )
        await self.db.commit()

    async def get_classification(self, message_id: str) -> bool | None:
        async with self.db.execute(
            "SELECT wants_reply FROM classify_cache WHERE message_id=?", (message_id,)
        ) as cur:
            row = await cur.fetchone()
            return bool(row[0]) if row else None

    async def cache_classification(self, message_id: str, wants_reply: bool) -> None:
        await self.db.execute(
            "INSERT OR REPLACE INTO classify_cache(message_id,wants_reply,ts) VALUES(?,?,?)",
            (message_id, 1 if wants_reply else 0, time.time()),
        )
        await self.db.commit()
