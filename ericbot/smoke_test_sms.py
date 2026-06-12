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
sms.send_sms = fake_send
auto_responder.sms.send_sms = fake_send

failures = []
def check(name, cond):
    print(("  ✓ " if cond else "  ✗ ") + name)
    if not cond: failures.append(name)

with TestClient(server.app) as client:

    # ── PROTECTED (the wife): never in-voice ----------------------------------
    print("\n[protected contact — the wife]")
    client.post("/api/sms/contacts", json={"name": "Wife", "phone": "+15550000001",
                                            "tier": "personal", "protected": True})
    sent_box.clear()
    r = client.post("/api/sms/webhook", data={"From": "+15550000001",
                                               "Body": "you coming home for dinner?"})
    check("webhook accepted", r.status_code == 200)
    check("no in-voice reply sent", len(sent_box) == 0)
    msgs = client.get("/api/sms/messages", params={"phone": "+15550000001"}).json()
    out_msgs = [m for m in msgs if m["direction"] == "out"]
    check("no outbound message logged", len(out_msgs) == 0)
    tasks = client.get("/api/tasks").json()
    check("reminder created for Eric to reply himself", any("Wife" in t["title"] for t in tasks))
    pending = client.get("/api/sms/pending").json()
    check("nothing queued (protected = no draft)", all(p["phone"] != "+15550000001" for p in pending))

    # ── PROTECTED with away_mode: honest away-reply only ----------------------
    print("\n[protected contact with away_mode]")
    client.post("/api/sms/contacts", json={"name": "Mom", "phone": "+15550000002",
                                            "tier": "personal", "protected": True, "away_mode": True})
    sent_box.clear()
    client.post("/api/sms/webhook", data={"From": "+15550000002", "Body": "call me"})
    check("exactly one honest away-reply sent", len(sent_box) == 1)
    msgs = client.get("/api/sms/messages", params={"phone": "+15550000002"}).json()
    check("logged as away_reply status", any(m["status"] == "away_reply" for m in msgs))
    check("no in-voice (pending/auto_sent/approved) to protected contact",
          not any(m["status"] in ("pending", "auto_sent", "approved") for m in msgs))
    pending = client.get("/api/sms/pending").json()
    check("protected contact not in approval queue", all(p["phone"] != "+15550000002" for p in pending))

    # ── PERSONAL (not protected): drafts in voice, queues for approval --------
    print("\n[personal contact (not protected) — drafts in voice]")
    client.post("/api/sms/contacts", json={"name": "Brother", "phone": "+15550000003",
                                            "tier": "personal", "protected": False})
    sent_box.clear()
    client.post("/api/sms/webhook", data={"From": "+15550000003", "Body": "hey what's up man"})
    check("no auto-send (personal tier)", len(sent_box) == 0)
    pending = client.get("/api/sms/pending").json()
    mine = [p for p in pending if p["phone"] == "+15550000003"]
    check("queued for approval in Eric's voice", len(mine) == 1)

    # ── BUSINESS routine + auto_send: fires automatically --------------------
    print("\n[business contact — routine, auto_send on]")
    client.post("/api/sms/contacts", json={"name": "Client Bob", "phone": "+15550000004",
                                            "tier": "business", "venture": "hatch", "auto_send": True})
    sent_box.clear()
    client.post("/api/sms/webhook", data={"From": "+15550000004", "Body": "thanks!"})
    check("routine business auto-sent", len(sent_box) == 1)

    # ── BUSINESS non-routine: queues -----------------------------------------
    print("\n[business contact — pricing question]")
    sent_box.clear()
    client.post("/api/sms/webhook", data={"From": "+15550000004",
                                          "Body": "how much for pressure washing?"})
    check("pricing question NOT auto-sent", len(sent_box) == 0)
    pending = client.get("/api/sms/pending").json()
    check("queued for approval", any(p["phone"] == "+15550000004" for p in pending))

    # ── UNKNOWN sender: drafts in voice, queues ------------------------------
    print("\n[unknown sender]")
    sent_box.clear()
    client.post("/api/sms/webhook", data={"From": "+15559999999", "Body": "hey is this eric?"})
    check("unknown sender not auto-sent", len(sent_box) == 0)
    pending = client.get("/api/sms/pending").json()
    check("unknown sender queued for approval", any(p["phone"] == "+15559999999" for p in pending))

    # ── Approve a draft -------------------------------------------------------
    print("\n[approving a queued draft]")
    sent_box.clear()
    target = next(p for p in client.get("/api/sms/pending").json() if p["phone"] == "+15559999999")
    r = client.post(f"/api/sms/pending/{target['id']}/approve", json={})
    check("approval sends", r.json().get("sent") is True and len(sent_box) == 1)

print("\n" + ("FAILED: " + ", ".join(failures) if failures else "ALL CHECKS PASSED ✓"))
raise SystemExit(1 if failures else 0)
