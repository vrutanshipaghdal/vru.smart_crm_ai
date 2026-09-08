from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class InteractionBase(BaseModel):
    type: str = "Note" # Call, Email, WhatsApp, Meeting, Note
    direction: str = "Outbound" # Inbound, Outbound
    content: str

class InteractionCreate(InteractionBase):
    pass

class InteractionResponse(InteractionBase):
    id: int
    lead_id: int
    sentiment_detected: Optional[str] = "Neutral"
    created_at: datetime

    class Config:
        from_attributes = True

class FollowUpBase(BaseModel):
    due_date: datetime
    reminder_note: Optional[str] = None

class FollowUpCreate(FollowUpBase):
    pass

class FollowUpResponse(FollowUpBase):
    id: int
    lead_id: int
    is_completed: bool
    created_at: datetime
    lead_name: Optional[str] = None
    company: Optional[str] = None

    class Config:
        from_attributes = True

class AIAnalysisResponse(BaseModel):
    id: int
    lead_id: int
    lead_score: int
    score_category: str
    sentiment: str
    priority: str
    suggested_action: Optional[str] = None
    key_insights: Optional[str] = None
    summary: Optional[str] = None
    draft_reply: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class LeadCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    requirement: Optional[str] = None
    budget: Optional[float] = 0.0
    source: Optional[str] = "Website"
    # Optional sales-user overrides.  When omitted, AI determines both values.
    sentiment: Optional[str] = None
    priority: Optional[str] = None

class LeadStatusUpdate(BaseModel):
    status: str

class LeadCloseDeal(BaseModel):
    status: str # Won or Lost
    lost_reason: Optional[str] = None
    deal_value: Optional[float] = 0.0

class EmailSendRequest(BaseModel):
    subject: str = "Following up from Smart CRM"
    body: str

class LeadResponse(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    requirement: Optional[str] = None
    budget: float
    source: str
    status: str
    is_customer: bool
    lost_reason: Optional[str] = None
    deal_value: float
    created_at: datetime
    updated_at: datetime
    latest_analysis: Optional[AIAnalysisResponse] = None
    interactions: List[InteractionResponse] = []
    follow_ups: List[FollowUpResponse] = []

    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_leads: int
    high_priority_leads: int
    pending_followups: int
    won_deals: int
    lost_deals: int
    active_customers: int
    conversion_rate: float
    sales_forecast: float
    pipeline_counts: dict
    source_counts: dict
    sentiment_counts: dict
