import os
from datetime import datetime, timedelta
from backend.database import engine, SessionLocal, Base
from backend import models, ai_service

# Ensure tables are created
Base.metadata.create_all(bind=engine)

def seed():
    db = SessionLocal()
    # Check if leads already exist
    if db.query(models.Lead).count() > 0:
        print("Database already contains data. Skipping seeding.")
        db.close()
        return

    print("Populating Smart CRM AI with sample leads...")

    sample_leads = [
        {
            "name": "Rajeshbhai Patel",
            "company": "Patel Textiles LLP (Surat)",
            "email": "rajesh@pateltextiles.in",
            "phone": "+919825012345",
            "source": "Website",
            "status": "Qualified",
            "budget": 120000.0,
            "deal_value": 120000.0,
            "requirement": "Urgent requirement for multi-agent sales CRM with direct WhatsApp notification and inventory sync for textile wholesale team.",
            "interactions": [
                ("Call", "Outbound", "Called Rajeshbhai. Explained cloud CRM features, he is eager for live demo with his 6 sales reps."),
                ("WhatsApp", "Inbound", "We are very interested! Can you share demo slot for tomorrow 3 PM? Budget is approved.")
            ],
            "follow_up": (datetime.utcnow() + timedelta(days=1), "Conduct live Zoom product demo with sales directors.")
        },
        {
            "name": "Pooja Shah",
            "company": "Shah Digital Marketing",
            "email": "pooja@shahmarketing.com",
            "phone": "+919879023456",
            "source": "Instagram",
            "status": "Proposal",
            "budget": 65000.0,
            "deal_value": 65000.0,
            "requirement": "Needs AI-driven lead scoring and automated email/WhatsApp follow-up drafts for agency client inquiries.",
            "interactions": [
                ("Email", "Outbound", "Shared proposal with commercial details for 10 user licenses."),
                ("WhatsApp", "Inbound", "Looks good. Can we discuss a 5% discount for annual upfront payment?")
            ],
            "follow_up": (datetime.utcnow() - timedelta(hours=2), "Review requested discount with sales manager and send final contract.") # Overdue to show alert!
        },
        {
            "name": "Amit Varma",
            "company": "Varma Logistics Pvt Ltd",
            "email": "amit@varmalogistics.com",
            "phone": "+919909034567",
            "source": "Referral",
            "status": "Won",
            "is_customer": True,
            "budget": 180000.0,
            "deal_value": 180000.0,
            "requirement": "Enterprise CRM deployment across Ahmedabad and Mumbai offices with dispatch tracking and CRM analytics.",
            "interactions": [
                ("Meeting", "Outbound", "Contract signed and initial payment received. Account onboarded.")
            ],
            "follow_up": None
        },
        {
            "name": "Deepak Mehta",
            "company": "Mehta Electronics",
            "email": "deepak@mehtaelec.com",
            "phone": "+919712045678",
            "source": "Cold Call",
            "status": "New",
            "budget": 35000.0,
            "deal_value": 35000.0,
            "requirement": "Basic customer management for showroom walk-in inquiries and quote follow-ups.",
            "interactions": [],
            "follow_up": (datetime.utcnow() + timedelta(days=2), "Initial introduction call.")
        }
    ]

    for data in sample_leads:
        lead = models.Lead(
            name=data["name"],
            company=data["company"],
            email=data["email"],
            phone=data["phone"],
            source=data["source"],
            status=data["status"],
            is_customer=data.get("is_customer", False),
            budget=data["budget"],
            deal_value=data["deal_value"],
            requirement=data["requirement"]
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)

        # Add interactions
        for it_type, direction, content in data["interactions"]:
            it = models.Interaction(
                lead_id=lead.id,
                type=it_type,
                direction=direction,
                content=content
            )
            db.add(it)
        db.commit()

        # Run AI analysis
        interactions = db.query(models.Interaction).filter(models.Interaction.lead_id == lead.id).all()
        ai_res = ai_service.analyze_lead_ai({
            "name": lead.name,
            "company": lead.company,
            "requirement": lead.requirement,
            "budget": lead.budget,
            "source": lead.source,
            "status": lead.status
        }, interactions=interactions)

        analysis = models.AIAnalysis(
            lead_id=lead.id,
            lead_score=ai_res.get("lead_score", 60),
            score_category=ai_res.get("score_category", "Medium"),
            sentiment=ai_res.get("sentiment", "Neutral"),
            priority=ai_res.get("priority", "Medium"),
            suggested_action=ai_res.get("suggested_action", ""),
            key_insights=ai_res.get("key_insights", ""),
            summary=ai_res.get("summary", ""),
            draft_reply=ai_res.get("draft_reply", "")
        )
        db.add(analysis)

        # Follow up
        if data.get("follow_up"):
            due_dt, note = data["follow_up"]
            fu = models.FollowUp(
                lead_id=lead.id,
                due_date=due_dt,
                reminder_note=note,
                is_completed=False
            )
            db.add(fu)

        db.commit()

    print("Seed data successfully added!")
    db.close()

if __name__ == "__main__":
    seed()
