import os
import smtplib
from datetime import datetime, date, timedelta
from email.message import EmailMessage
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from backend.database import engine, get_db, Base
from backend import models, schemas, ai_service

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart CRM AI", version="1.0.0", description="Intelligent AI-powered CRM System")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)
if not os.path.exists(TEMPLATES_DIR):
    os.makedirs(TEMPLATES_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.get("/")
def home():
    """Serve the main CRM Web Dashboard"""
    return FileResponse(os.path.join(TEMPLATES_DIR, "index.html"))

# ==================== LEAD ENDPOINTS ====================

@app.post("/api/leads", response_model=schemas.LeadResponse)
def create_lead(lead_in: schemas.LeadCreate, db: Session = Depends(get_db)):
    """
    Step 2 & 3: New customer/lead added, saved to database.
    Step 4 & 5: AI analyzes lead automatically and produces Lead Score, Sentiment, Priority, Suggested Action.
    """
    # Block accidental duplicates while allowing records without email/phone.
    if lead_in.email:
        duplicate = db.query(models.Lead).filter(func.lower(models.Lead.email) == lead_in.email.strip().lower()).first()
        if duplicate:
            raise HTTPException(status_code=409, detail=f"Duplicate lead: email already belongs to {duplicate.name}.")
    if lead_in.phone:
        duplicate = db.query(models.Lead).filter(models.Lead.phone == lead_in.phone.strip()).first()
        if duplicate:
            raise HTTPException(status_code=409, detail=f"Duplicate lead: phone already belongs to {duplicate.name}.")

    lead = models.Lead(
        name=lead_in.name,
        email=lead_in.email,
        phone=lead_in.phone,
        company=lead_in.company,
        requirement=lead_in.requirement,
        budget=lead_in.budget or 0.0,
        source=lead_in.source or "Website",
        status="New",
        deal_value=lead_in.budget or 0.0
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    # Trigger AI analysis
    ai_output = ai_service.analyze_lead_ai({
        "name": lead.name,
        "company": lead.company,
        "requirement": lead.requirement,
        "budget": lead.budget,
        "source": lead.source,
        "status": lead.status
    })
    valid_sentiments = {"Positive", "Neutral", "Negative"}
    valid_priorities = {"Urgent", "High", "Medium", "Low"}
    if lead_in.sentiment in valid_sentiments:
        ai_output["sentiment"] = lead_in.sentiment
    if lead_in.priority in valid_priorities:
        ai_output["priority"] = lead_in.priority

    analysis = models.AIAnalysis(
        lead_id=lead.id,
        lead_score=ai_output.get("lead_score", 50),
        score_category=ai_output.get("score_category", "Medium"),
        sentiment=ai_output.get("sentiment", "Neutral"),
        priority=ai_output.get("priority", "Medium"),
        suggested_action=ai_output.get("suggested_action", ""),
        key_insights=ai_output.get("key_insights", ""),
        summary=ai_output.get("summary", ""),
        draft_reply=ai_output.get("draft_reply", "")
    )
    db.add(analysis)
    db.commit()

    # Automatic follow-up rule: every new open lead receives one reminder.
    # It can be completed or rescheduled from the dashboard.
    follow_up_days = max(1, int(os.getenv("AUTO_FOLLOWUP_DAYS", "2")))
    auto_follow_up = models.FollowUp(
        lead_id=lead.id,
        due_date=datetime.utcnow() + timedelta(days=follow_up_days),
        reminder_note=f"Automatic follow-up: {ai_output.get('suggested_action', 'Contact this lead.')}"
    )
    db.add(auto_follow_up)
    db.commit()
    db.refresh(lead)

    return build_lead_response(lead)

@app.post("/api/leads/{lead_id}/send-email")
def send_lead_email(lead_id: int, email_in: schemas.EmailSendRequest, db: Session = Depends(get_db)):
    """Send an approved lead email through the configured SMTP provider."""
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not lead.email:
        raise HTTPException(status_code=400, detail="This lead has no email address")

    host = os.getenv("SMTP_HOST", "").strip()
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    sender = os.getenv("SMTP_FROM", username).strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    if not all([host, username, password, sender]):
        raise HTTPException(status_code=503, detail="Email is not configured. Add SMTP settings to .env and restart the server.")

    message = EmailMessage()
    message["Subject"] = email_in.subject.strip() or "Following up from Smart CRM"
    message["From"] = sender
    message["To"] = lead.email
    message.set_content(email_in.body)
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=20) as smtp:
                smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=20) as smtp:
                smtp.starttls()
                smtp.login(username, password)
                smtp.send_message(message)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Email delivery failed: {str(exc)}")
    return {"status": "sent", "recipient": lead.email}

@app.get("/api/leads", response_model=List[schemas.LeadResponse])
def get_leads(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List leads with optional filtering"""
    query = db.query(models.Lead)
    if status and status != "All":
        query = query.filter(models.Lead.status == status)
    if search:
        s = f"%{search}%"
        query = query.filter(
            (models.Lead.name.ilike(s)) |
            (models.Lead.company.ilike(s)) |
            (models.Lead.email.ilike(s)) |
            (models.Lead.phone.ilike(s))
        )
    leads = query.order_by(desc(models.Lead.created_at)).all()
    
    results = [build_lead_response(lead) for lead in leads]
    if priority and priority != "All":
        results = [r for r in results if r.latest_analysis and r.latest_analysis.priority == priority]
    return results

@app.get("/api/leads/{lead_id}", response_model=schemas.LeadResponse)
def get_lead_by_id(lead_id: int, db: Session = Depends(get_db)):
    """Retrieve full lead details, interactions, and AI analyses"""
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return build_lead_response(lead)

@app.patch("/api/leads/{lead_id}/status", response_model=schemas.LeadResponse)
def update_lead_status(lead_id: int, status_update: schemas.LeadStatusUpdate, db: Session = Depends(get_db)):
    """
    Step 6: Move lead across CRM pipeline
    New -> Contacted -> Qualified -> Demo -> Proposal -> Won/Lost
    """
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    new_status = status_update.status
    lead.status = new_status
    if new_status == "Won":
        lead.is_customer = True
    elif new_status == "Lost":
        lead.is_customer = False

    lead.updated_at = datetime.utcnow()
    db.commit()

    # Re-run AI analysis on status progression to update suggested action
    refresh_ai_for_lead(lead, db)
    db.refresh(lead)
    return build_lead_response(lead)

@app.post("/api/leads/{lead_id}/interactions", response_model=schemas.LeadResponse)
def add_interaction(lead_id: int, it_in: schemas.InteractionCreate, db: Session = Depends(get_db)):
    """
    Step 8 & 9: Salesperson adds conversation note or customer message.
    AI creates conversation summary & drafts reply/follow-up message.
    Step 14: Updates sentiment and lead score dynamically.
    """
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Save interaction
    interaction = models.Interaction(
        lead_id=lead.id,
        type=it_in.type,
        direction=it_in.direction,
        content=it_in.content
    )
    db.add(interaction)
    db.commit()

    # Re-analyze with updated interaction history
    refresh_ai_for_lead(lead, db)
    db.refresh(lead)
    return build_lead_response(lead)

@app.post("/api/leads/{lead_id}/analyze", response_model=schemas.LeadResponse)
def trigger_analysis(lead_id: int, db: Session = Depends(get_db)):
    """Explicitly trigger AI analysis"""
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    refresh_ai_for_lead(lead, db)
    db.refresh(lead)
    return build_lead_response(lead)

# ==================== FOLLOW-UP & ALERTS ====================

@app.post("/api/leads/{lead_id}/follow-ups", response_model=schemas.FollowUpResponse)
def create_follow_up(lead_id: int, fu_in: schemas.FollowUpCreate, db: Session = Depends(get_db)):
    """
    Step 12: Set follow-up date and reminder note.
    """
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    follow_up = models.FollowUp(
        lead_id=lead.id,
        due_date=fu_in.due_date,
        reminder_note=fu_in.reminder_note,
        is_completed=False
    )
    db.add(follow_up)
    db.commit()
    db.refresh(follow_up)

    return schemas.FollowUpResponse(
        id=follow_up.id,
        lead_id=follow_up.lead_id,
        due_date=follow_up.due_date,
        reminder_note=follow_up.reminder_note,
        is_completed=follow_up.is_completed,
        created_at=follow_up.created_at,
        lead_name=lead.name,
        company=lead.company
    )

@app.patch("/api/follow-ups/{follow_up_id}/complete")
def complete_follow_up(follow_up_id: int, db: Session = Depends(get_db)):
    """Mark reminder as completed"""
    fu = db.query(models.FollowUp).filter(models.FollowUp.id == follow_up_id).first()
    if not fu:
        raise HTTPException(status_code=404, detail="Follow up not found")
    fu.is_completed = True
    db.commit()
    return {"status": "success", "message": "Follow-up marked completed"}

@app.get("/api/follow-ups/pending", response_model=List[schemas.FollowUpResponse])
def get_pending_follow_ups(db: Session = Depends(get_db)):
    """
    Step 13: Dashboard alert for due/overdue reminders
    """
    fus = db.query(models.FollowUp).filter(models.FollowUp.is_completed == False).order_by(models.FollowUp.due_date).all()
    results = []
    for fu in fus:
        lead = db.query(models.Lead).filter(models.Lead.id == fu.lead_id).first()
        results.append(schemas.FollowUpResponse(
            id=fu.id,
            lead_id=fu.lead_id,
            due_date=fu.due_date,
            reminder_note=fu.reminder_note,
            is_completed=fu.is_completed,
            created_at=fu.created_at,
            lead_name=lead.name if lead else "Unknown",
            company=lead.company if lead else "N/A"
        ))
    return results

# ==================== CLOSE DEAL (WON / LOST) ====================

@app.post("/api/leads/{lead_id}/close-deal", response_model=schemas.LeadResponse)
def close_deal(lead_id: int, close_in: schemas.LeadCloseDeal, db: Session = Depends(get_db)):
    """
    Step 15: Close deal
    Won -> Customer account convert
    Lost -> Save reason
    """
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.status = close_in.status
    if close_in.status == "Won":
        lead.is_customer = True
        lead.lost_reason = None
        if close_in.deal_value and close_in.deal_value > 0:
            lead.deal_value = close_in.deal_value
    else:
        lead.is_customer = False
        lead.lost_reason = close_in.lost_reason or "Unspecified"

    lead.updated_at = datetime.utcnow()
    db.commit()
    refresh_ai_for_lead(lead, db)
    db.refresh(lead)
    return build_lead_response(lead)

# ==================== DASHBOARD & REPORTING ====================

@app.get("/api/dashboard/stats", response_model=schemas.DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Step 16: Dashboard & Reports:
    - Total leads
    - High-priority leads
    - Pending follow-ups
    - Won / Lost deals
    - Conversion rate %
    - Sales forecast
    """
    total_leads = db.query(models.Lead).count()
    won_deals = db.query(models.Lead).filter(models.Lead.status == "Won").count()
    lost_deals = db.query(models.Lead).filter(models.Lead.status == "Lost").count()
    active_customers = db.query(models.Lead).filter(models.Lead.is_customer == True).count()
    pending_followups = db.query(models.FollowUp).filter(models.FollowUp.is_completed == False).count()

    # High priority leads count
    high_priority_leads = 0
    leads = db.query(models.Lead).all()
    for l in leads:
        if l.analyses and l.analyses[0].priority in ["Urgent", "High"]:
            high_priority_leads += 1

    # Conversion rate: Won / (Total closed or Total Leads)
    conversion_rate = 0.0
    if total_leads > 0:
        conversion_rate = round((won_deals / total_leads) * 100, 1)

    # Sales forecast: Pipeline weighted value
    # Proposal: 80%, Demo: 60%, Qualified: 40%, Contacted: 20%, New: 10%
    pipeline_weights = {
        "New": 0.10,
        "Contacted": 0.20,
        "Qualified": 0.40,
        "Demo": 0.60,
        "Proposal": 0.80,
        "Won": 1.0,
        "Lost": 0.0
    }
    sales_forecast = 0.0
    pipeline_counts = {"New": 0, "Contacted": 0, "Qualified": 0, "Demo": 0, "Proposal": 0, "Won": 0, "Lost": 0}
    source_counts = {}
    sentiment_counts = {"Positive": 0, "Neutral": 0, "Negative": 0}

    for l in leads:
        st = l.status if l.status in pipeline_counts else "New"
        pipeline_counts[st] += 1
        src = l.source or "Website"
        source_counts[src] = source_counts.get(src, 0) + 1

        val = l.deal_value or l.budget or 0.0
        weight = pipeline_weights.get(st, 0.1)
        sales_forecast += val * weight

        if l.analyses:
            sent = l.analyses[0].sentiment or "Neutral"
            sentiment_counts[sent] = sentiment_counts.get(sent, 0) + 1

    return schemas.DashboardStats(
        total_leads=total_leads,
        high_priority_leads=high_priority_leads,
        pending_followups=pending_followups,
        won_deals=won_deals,
        lost_deals=lost_deals,
        active_customers=active_customers,
        conversion_rate=conversion_rate,
        sales_forecast=round(sales_forecast, 2),
        pipeline_counts=pipeline_counts,
        source_counts=source_counts,
        sentiment_counts=sentiment_counts
    )

# ==================== HELPER FUNCTIONS ====================

def refresh_ai_for_lead(lead: models.Lead, db: Session):
    """Executes AI Analysis and inserts fresh AI analysis record"""
    interactions = db.query(models.Interaction).filter(models.Interaction.lead_id == lead.id).order_by(models.Interaction.created_at).all()
    ai_output = ai_service.analyze_lead_ai({
        "name": lead.name,
        "company": lead.company,
        "requirement": lead.requirement,
        "budget": lead.budget,
        "source": lead.source,
        "status": lead.status
    }, interactions=interactions)

    analysis = models.AIAnalysis(
        lead_id=lead.id,
        lead_score=ai_output.get("lead_score", 50),
        score_category=ai_output.get("score_category", "Medium"),
        sentiment=ai_output.get("sentiment", "Neutral"),
        priority=ai_output.get("priority", "Medium"),
        suggested_action=ai_output.get("suggested_action", ""),
        key_insights=ai_output.get("key_insights", ""),
        summary=ai_output.get("summary", ""),
        draft_reply=ai_output.get("draft_reply", "")
    )
    db.add(analysis)
    db.commit()

def build_lead_response(lead: models.Lead) -> schemas.LeadResponse:
    latest_analysis = None
    if lead.analyses:
        la = lead.analyses[0]
        latest_analysis = schemas.AIAnalysisResponse(
            id=la.id,
            lead_id=la.lead_id,
            lead_score=la.lead_score,
            score_category=la.score_category,
            sentiment=la.sentiment,
            priority=la.priority,
            suggested_action=la.suggested_action,
            key_insights=la.key_insights,
            summary=la.summary,
            draft_reply=la.draft_reply,
            created_at=la.created_at
        )

    interactions_resp = [
        schemas.InteractionResponse(
            id=it.id,
            lead_id=it.lead_id,
            type=it.type,
            direction=it.direction,
            content=it.content,
            sentiment_detected=it.sentiment_detected,
            created_at=it.created_at
        ) for it in lead.interactions
    ]

    follow_ups_resp = [
        schemas.FollowUpResponse(
            id=fu.id,
            lead_id=fu.lead_id,
            due_date=fu.due_date,
            reminder_note=fu.reminder_note,
            is_completed=fu.is_completed,
            created_at=fu.created_at,
            lead_name=lead.name,
            company=lead.company
        ) for fu in lead.follow_ups
    ]

    return schemas.LeadResponse(
        id=lead.id,
        name=lead.name,
        email=lead.email,
        phone=lead.phone,
        company=lead.company,
        requirement=lead.requirement,
        budget=lead.budget or 0.0,
        source=lead.source or "Website",
        status=lead.status,
        is_customer=lead.is_customer,
        lost_reason=lead.lost_reason,
        deal_value=lead.deal_value or 0.0,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
        latest_analysis=latest_analysis,
        interactions=interactions_resp,
        follow_ups=follow_ups_resp
    )

if __name__ == "__main__":
    import uvicorn
    print("Starting Smart CRM AI server on http://127.0.0.1:8000 ...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
