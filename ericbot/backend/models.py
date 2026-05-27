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
