from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ChatMessage(BaseModel):
    message: str
    include_history: bool = True


class ChatResponse(BaseModel):
    reply: str
    voice_confidence: float


class VoiceSample(BaseModel):
    category: str = Field(..., description="email|phone|text|social|sales")
    content: str


class VoiceProfile(BaseModel):
    sample_count: int
    categories: dict
    confidence: float
    style_summary: str


class LeadCreate(BaseModel):
    name: str
    contact: Optional[str] = None
    venture: str = Field(..., description="hatch|eric_digital|ancient_coast|nexus")
    source: Optional[str] = None
    notes: Optional[str] = None
    value: float = 0.0
    next_followup: Optional[datetime] = None


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    value: Optional[float] = None
    next_followup: Optional[datetime] = None


class Lead(BaseModel):
    id: int
    name: str
    contact: Optional[str]
    venture: str
    status: str
    source: Optional[str]
    notes: Optional[str]
    value: float
    next_followup: Optional[str]
    created_at: str
    updated_at: str


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    venture: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: str = "medium"


class Task(BaseModel):
    id: int
    title: str
    description: Optional[str]
    venture: Optional[str]
    due_date: Optional[str]
    priority: str
    completed: bool
    completed_at: Optional[str]
    created_at: str


class DraftRequest(BaseModel):
    lead_id: Optional[int] = None
    recipient_name: str
    venture: str
    channel: str = Field(..., description="email|text|social|phone")
    context: str = Field(..., description="What this outreach is about")
    tone: str = "friendly"


# ── SMS auto-responder ────────────────────────────────────────────────────────


class ContactCreate(BaseModel):
    name: Optional[str] = None
    phone: str = Field(..., description="E.164 format, e.g. +15555550123")
    tier: str = Field("unknown", description="business|personal|unknown")
    venture: Optional[str] = None
    auto_send: bool = False
    # protected = True means NEVER answer in Eric's voice (spouse, etc.)
    protected: bool = False
    away_mode: bool = False
    away_reply: Optional[str] = None


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    tier: Optional[str] = None
    venture: Optional[str] = None
    auto_send: Optional[bool] = None
    protected: Optional[bool] = None
    away_mode: Optional[bool] = None
    away_reply: Optional[str] = None


class ApprovalRequest(BaseModel):
    # Optional edited text — if omitted, the original draft is sent as-is.
    edited_text: Optional[str] = None


class ManualSend(BaseModel):
    phone: str
    body: str


# ── Zoom Phone integration ────────────────────────────────────────────────────


class VoicemailApproval(BaseModel):
    edited_text: Optional[str] = None  # if omitted, original draft is sent
