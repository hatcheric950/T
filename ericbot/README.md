# 🤖 EricBot — AI Clone & Business Development Engine

A personal AI assistant that learns how you talk, hunts for new business, retains
customers, keeps you accountable — and now **triages your incoming texts**.

Built for Eric's multi-venture empire:
- 🌿 **Hatch Property Maintenance LLC** — Lawn care, landscaping, pressure washing
- 💻 **Eric.Digital** — Web design, AI automation, cybersecurity
- 🏠 **Ancient Coast Property Management** — Property management
- 🤖 **NEXUS** — AI agency infrastructure

---

## 🚀 Quick Start

```bash
cd ericbot
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your ANTHROPIC_API_KEY (+ Twilio for SMS)
cd backend && python -m backend.server   # → http://localhost:8000
```

Docker (production, runs 24/7):

```bash
docker-compose up -d
```

---

## 📱 SMS Auto-Responder

EricBot can watch your Twilio number and handle inbound texts based on **who's
texting you**. Every contact has a *tier* that decides how their messages are
handled:

| Tier | What EricBot does |
|------|-------------------|
| **business** | Drafts a reply in your voice. If the message is *routine* (a "thanks", a simple ack) **and** you've opted that contact into auto-send **and** the global switch is armed, it sends automatically. Anything touching **price, scheduling, commitments, or complaints** goes to the **approval queue** for one-tap review. |
| **personal** | **Never answered in your voice.** Optionally sends one *honest* away-reply ("tied up, I'll hit you back"), and always creates a high-priority reminder so *you* reply yourself. |
| **unknown** | Logged and flagged with a reminder. No automatic reply. |

### Why personal contacts are walled off

A bot quietly impersonating you to your spouse, family, or friends — people who
think they're talking to *you* — is a trust problem, not a time-saver. EricBot
will help you not drop the ball (reminders, honest "I'm busy" replies) but it
will **not ghostwrite your personal relationships**. The only fully-automatic,
in-your-voice replies that ever go out are *routine business* messages you've
explicitly opted into.

### Safety switches (all default to OFF)

- `SMS_AUTO_SEND_ENABLED` — master kill-switch. Even an opted-in business
  contact gets nothing sent automatically unless this is `true`.
- Per-contact `auto_send` — opt a single business contact into routine auto-replies.
- Per-contact `away_mode` — opt a personal contact into the honest away-reply.
- `TWILIO_VALIDATE_SIGNATURE` — reject inbound webhooks that fail Twilio's
  signature check (turn on once your public URL is live).

### Wiring up Twilio

1. Fill in `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` in `.env`.
2. Point your Twilio number's **Messaging webhook** at
   `https://your-host/api/sms/webhook` (HTTP POST).
3. Add your contacts (Inbox tab or `POST /api/sms/contacts`) and set their tiers.
4. Flip `SMS_AUTO_SEND_ENABLED=true` only when you're ready.

---

## 🎤 Voice Training

The more real samples you feed it, the more it sounds like you.

```bash
python scripts/train_voice.py --interactive
python scripts/train_voice.py --category email --file my_emails.txt   # --- delimited
python scripts/train_voice.py --category text --dir ./texts/
python scripts/train_voice.py --profile
```

Categories: `email`, `phone`, `text`, `social`, `sales`.

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | System health check |
| POST | `/api/chat` | Chat with EricBot |
| POST | `/api/voice/ingest` | Feed voice samples |
| GET | `/api/voice/profile` | View learned style |
| POST/GET | `/api/leads` | Add / list leads |
| PATCH | `/api/leads/{id}` | Update lead status |
| GET | `/api/leads/followups` | Due follow-ups |
| GET | `/api/leads/stats` | Pipeline stats |
| POST | `/api/draft` | AI-generate outreach |
| POST/GET | `/api/tasks` | Add / list tasks |
| POST | `/api/tasks/{id}/complete` | Mark task done |
| GET | `/api/tasks/accountability` | Accountability report + AI nudge |
| GET | `/api/dashboard` | Full dashboard data |
| **POST** | **`/api/sms/webhook`** | **Twilio inbound-SMS webhook** |
| **POST/GET** | **`/api/sms/contacts`** | **Add / list contacts (with tier)** |
| **PATCH** | **`/api/sms/contacts/{id}`** | **Update tier / auto_send / away_mode** |
| **GET** | **`/api/sms/pending`** | **Drafts awaiting approval** |
| **POST** | **`/api/sms/pending/{id}/approve`** | **Approve (optionally edited) & send** |
| **POST** | **`/api/sms/pending/{id}/reject`** | **Discard a draft** |
| **GET** | **`/api/sms/messages`** | **Message log** |
| **POST** | **`/api/sms/send`** | **Manual send** |
| **GET** | **`/api/sms/status`** | **Gateway + auto-send state** |

---

## 🔄 Automated Behaviors (Scheduler)

| Time | Action |
|------|--------|
| 7:00 AM | Daily accountability nudge |
| Every 2hrs (8AM–6PM) | Check for due follow-ups |

---

## 🗺 Roadmap

### Phase 1
- [x] Core chatbot with Eric's personality
- [x] Voice learning engine
- [x] Lead pipeline management
- [x] Accountability system
- [x] AI-powered outreach drafting
- [x] React command center

### Phase 2
- [ ] Email integration (auto-send approved drafts)
- [x] **SMS integration via Twilio** — inbound auto-responder with contact tiering
- [ ] Google Maps API scraping for local business leads
- [ ] Automated social media posting
- [ ] Voice-to-text for phone call logging

### Phase 3
- [ ] Multi-channel customer retention campaigns
- [ ] Revenue forecasting per venture
- [ ] QuickBooks integration
- [ ] Mobile app (React Native)
- [ ] WhatsApp Business integration

---

## ✅ Tests

```bash
python smoke_test_sms.py   # verifies SMS routing + the personal-contact safety guarantees
```

---

## ⚡ Tech Stack

Python 3.12 · FastAPI · SQLite · Anthropic Claude · APScheduler · Twilio · React · Docker
