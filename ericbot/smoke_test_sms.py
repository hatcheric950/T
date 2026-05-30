"""Smoke test for the SMS auto-responder routing. Stubs AI + Twilio so no
external calls are made. Run: python smoke_test_sms.py"""
import os
import tempfile

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["SMS_AUTO_SEND_ENABLED"] = "true"

from fastapi.testclient import TestClient
from backend import server
from backend.services import ai_engine, sms, auto_responder

# ── Stub out external calls ───────────────────────────────────────────────────
sent_box = []

async def fake_draft(*a, **k): return "Hey, sounds good — talk soon."
async def fake_away(*a, **k): return "Tied up right now, I'll hit you back shortly."
async def fake_classify(body):
    return {"routine": "thanks" in body.lower(), "intent": "test"}

def fake_send(to, body):
    sent_box.append((to, body))
    return {"sent": True, "sid": "SMfake"}

ai_engine.draft_sms_reply = fake_draft
ai_engine.generate_away_reply = fake_away
ai_engine.classify_sms = fake_classify
# auto_responder calls sms.send_sms by module attribute
sms.send_sms = fake_send
auto_responder.sms.send_sms = fake_send

failures = []
def check(name, cond):
    print(("  ✓ " if cond else "  ✗ ") + name)
    if not cond: failures.append(name)

with TestClient(server.app) as client:
    # ---- PERSONAL: must NEVER auto-reply in Eric's voice ----------------------
    print("\n[personal contact — the wife scenario]")
    client.post("/api/sms/contacts", json={"name": "Wife", "phone": "+15550000001", "tier": "personal"})
    sent_box.clear()
    r = client.post("/api/sms/webhook", data={"From": "+15550000001", "Body": "you coming home for dinner?"})
    check("webhook accepted", r.status_code == 200)
    msgs = client.get("/api/sms/messages", params={"phone": "+15550000001"}).json()
    out_msgs = [m for m in msgs if m["direction"] == "out"]
    check("no impersonation reply sent", len(sent_box) == 0)
    check("no outbound in-voice message logged", len(out_msgs) == 0)
    tasks = client.get("/api/tasks").json()
    check("reminder created for Eric to reply himself", any("Wife" in t["title"] for t in tasks))

    # ---- PERSONAL with away_mode: honest away-reply only ----------------------
    print("\n[personal contact with away_mode on]")
    client.post("/api/sms/contacts", json={"name": "Mom", "phone": "+15550000002", "tier": "personal", "away_mode": True})
    sent_box.clear()
    client.post("/api/sms/webhook", data={"From": "+15550000002", "Body": "call me when you can"})
    check("exactly one honest away-reply sent", len(sent_box) == 1)
    msgs = client.get("/api/sms/messages", params={"phone": "+15550000002"}).json()
    check("away-reply logged as away_reply (not in-voice)", any(m["status"] == "away_reply" for m in msgs))
    check("no in-voice reply (pending/auto_sent/approved) to personal contact",
          not any(m["status"] in ("pending", "auto_sent", "approved") for m in msgs))

    # ---- BUSINESS routine + auto_send on: auto-sends ---------------------------
    print("\n[business contact — routine message, auto_send on]")
    client.post("/api/sms/contacts", json={"name": "Client Bob", "phone": "+15550000003", "tier": "business", "venture": "hatch", "auto_send": True})
    sent_box.clear()
    client.post("/api/sms/webhook", data={"From": "+15550000003", "Body": "thanks for the quick work!"})
    check("routine business reply auto-sent", len(sent_box) == 1)
    pending = client.get("/api/sms/pending").json()
    check("nothing queued (it auto-sent)", all(p["phone"] != "+15550000003" for p in pending))

    # ---- BUSINESS non-routine: queues for approval -----------------------------
    print("\n[business contact — non-routine message]")
    sent_box.clear()
    client.post("/api/sms/webhook", data={"From": "+15550000003", "Body": "how much for pressure washing my driveway?"})
    check("pricing question NOT auto-sent", len(sent_box) == 0)
    pending = client.get("/api/sms/pending").json()
    mine = [p for p in pending if p["phone"] == "+15550000003"]
    check("queued for one-tap approval", len(mine) == 1)

    # ---- Approve the queued draft ----------------------------------------------
    print("\n[approving a queued draft]")
    sent_box.clear()
    pid = mine[0]["id"]
    r = client.post(f"/api/sms/pending/{pid}/approve", json={})
    check("approval sends the message", r.json().get("sent") is True and len(sent_box) == 1)
    pending2 = client.get("/api/sms/pending").json()
    check("resolved out of the queue", all(p["id"] != pid for p in pending2))

    # ---- UNKNOWN sender: reminder only -----------------------------------------
    print("\n[unknown sender]")
    sent_box.clear()
    client.post("/api/sms/webhook", data={"From": "+15559999999", "Body": "hey is this eric?"})
    check("unknown sender gets no auto-reply", len(sent_box) == 0)

print("\n" + ("FAILED: " + ", ".join(failures) if failures else "ALL CHECKS PASSED ✓"))
raise SystemExit(1 if failures else 0)
