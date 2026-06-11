from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path


def _fmt_ts(ts: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def _shorten(s: str, n: int) -> str:
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def run(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="hermes audit",
                                description="Inspect Hermes watcher audit log")
    p.add_argument("--db", default="/var/lib/hermes/state.db", help="Path to state.db")
    p.add_argument("--limit", type=int, default=25, help="Rows to show (default 25)")
    p.add_argument("--since-hours", type=float, default=0, help="Only show rows in the last N hours")
    p.add_argument("--decision", help="Filter by decision (e.g. shadow_would_send)")
    p.add_argument("--sender", help="Filter by sender (substring match)")
    p.add_argument("--show-drafts", action="store_true", help="Print the drafted reply for each row")
    args = p.parse_args(argv)

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"no audit db at {db_path}", file=sys.stderr)
        return 1

    where = []
    params: list = []
    if args.since_hours:
        where.append("ts >= ?")
        params.append(time.time() - args.since_hours * 3600)
    if args.decision:
        where.append("decision = ?")
        params.append(args.decision)
    if args.sender:
        where.append("sender LIKE ?")
        params.append(f"%{args.sender.lower()}%")
    sql = "SELECT ts, channel, sender, decision, sent, cost_usd, draft FROM audit"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY ts DESC LIMIT ?"
    params.append(args.limit)

    conn = sqlite3.connect(db_path)
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    if not rows:
        print("(no matching rows)")
        return 0

    print(f"{'time':<19}  {'ch':<5}  {'sender':<32}  {'decision':<24}  sent  cost")
    print("-" * 110)
    for ts, channel, sender, decision, sent, cost, draft in reversed(rows):
        print(f"{_fmt_ts(ts):<19}  {channel:<5}  {_shorten(sender,32):<32}  "
              f"{decision:<24}  {'yes' if sent else 'no ':<4}  ${cost:.4f}")
        if args.show_drafts and draft:
            print(f"  └─ {_shorten(draft, 200)}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
