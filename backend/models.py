from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(120), nullable=True)
    phone = Column(String(50), nullable=True)
    company = Column(String(120), nullable=True)
    requirement = Column(Text, nullable=True)
    budget = Column(Float, default=0.0)
    source = Column(String(50), default="Website")
    status = Column(String(50), default="New")  # New, Contacted, Qualified, Demo, Proposal, Won, Lost
    is_customer = Column(Boolean, default=False)
    lost_reason = Column(String(255), nullable=True)
    deal_value = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    analyses = relationship("AIAnalysis", back_populates="lead", cascade="all, delete-orphan", order_by="desc(AIAnalysis.created_at)")
    interactions = relationship("Interaction", back_populates="lead", cascade="all, delete-orphan", order_by="desc(Interaction.created_at)")
    follow_ups = relationship("FollowUp", back_populates="lead", cascade="all, delete-orphan", order_by="FollowUp.due_date")

class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    lead_score = Column(Integer, default=50) # 0-100
    score_category = Column(String(20), default="Medium") # High, Medium, Low
    sentiment = Column(String(20), default="Neutral") # Positive, Neutral, Negative
    priority = Column(String(20), default="Medium") # Urgent, High, Medium, Low
    suggested_action = Column(Text, nullable=True)
    key_insights = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    draft_reply = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="analyses")

class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), default="Note") # Call, Email, WhatsApp, Meeting, Note
    direction = Column(String(20), default="Outbound") # Inbound, Outbound
    content = Column(Text, nullable=False)
    sentiment_detected = Column(String(20), default="Neutral")
    created_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="interactions")

class FollowUp(Base):
    __tablename__ = "follow_ups"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    due_date = Column(DateTime, nullable=False)
    reminder_note = Column(String(255), nullable=True)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="follow_ups")
