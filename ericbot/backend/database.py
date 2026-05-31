import os
import aiosqlite
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", "ericbot.db")


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS voice_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT,
                venture TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new',
                source TEXT,
                notes TEXT,
                value REAL DEFAULT 0,
                next_followup TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                venture TEXT,
                due_date TIMESTAMP,
                priority TEXT DEFAULT 'medium',
                completed INTEGER DEFAULT 0,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- SMS auto-responder ---------------------------------------------

            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone TEXT NOT NULL UNIQUE,
                -- tier: business | personal | unknown
                --   business : may auto-send routine replies
                --   personal : draft in voice + queue, no auto-send
                --   unknown  : draft in voice + queue, no auto-send
                tier TEXT NOT NULL DEFAULT 'unknown',
                venture TEXT,
                -- per-contact opt-in for auto-sending routine BUSINESS replies
                auto_send INTEGER DEFAULT 0,
                -- protected = 1 means NEVER answer in Eric's voice.
                -- Only use this for people where impersonation would be a trust
                -- issue (e.g. spouse). protected contacts get an honest
                -- away-reply (if away_mode is on) + a reminder to Eric.
                protected INTEGER DEFAULT 0,
                -- per-contact honest away-reply (only sent when protected=1)
                away_mode INTEGER DEFAULT 0,
                away_reply TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sms_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER,
                phone TEXT NOT NULL,
                direction TEXT NOT NULL,           -- 'in' | 'out'
                body TEXT NOT NULL,
                -- received | auto_sent | pending | approved | away_reply | manual
                status TEXT NOT NULL DEFAULT 'received',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS pending_replies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER,
                phone TEXT NOT NULL,
                inbound_message_id INTEGER,
                draft TEXT NOT NULL,
                intent TEXT,
                resolved INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.commit()
