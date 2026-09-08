import os
import re
import json
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

def clean_text(text: str) -> str:
    """Step: Text cleaning / data preparation"""
    if not text:
        return ""
    # Strip unnecessary whitespaces and clean up line breaks
    cleaned = re.sub(r'[ \t]+', ' ', text)
    cleaned = re.sub(r'\n+', '\n', cleaned).strip()
    return cleaned

def analyze_lead_ai(lead_data: dict, interactions: list = None) -> dict:
    """
    AI Lead Analysis:
    - Analyzes requirements, budget, customer interest, and past notes/messages
    - Computes Lead Score (0-100), Sentiment, Priority, Suggested Action, Summary & Draft Reply
    """
    req = clean_text(lead_data.get("requirement", ""))
    company = clean_text(lead_data.get("company", "Individual"))
    name = clean_text(lead_data.get("name", "Valued Client"))
    budget = float(lead_data.get("budget", 0) or 0)
    source = lead_data.get("source", "Website")
    status = lead_data.get("status", "New")

    notes_history = []
    if interactions:
        for it in interactions:
            notes_history.append(f"[{it.type} - {it.direction}]: {clean_text(it.content)}")
    history_text = "\n".join(notes_history) if notes_history else "No previous interactions yet."

    # Try Gemini LLM if API Key is configured
    if GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)

            prompt = f"""
You are an expert Enterprise CRM Sales & AI Analyst. Analyze the following sales lead thoroughly.

Lead Details:
- Customer Name: {name}
- Company: {company}
- Source: {source}
- Budget: INR {budget:,.0f}
- Current Pipeline Stage: {status}
- Requirement:
{req}

Interactions & Notes History:
{history_text}

Provide output strictly in valid JSON format without markdown code fences. Structure:
{{
  "lead_score": (integer 0-100),
  "score_category": ("High" | "Medium" | "Low"),
  "sentiment": ("Positive" | "Neutral" | "Negative"),
  "priority": ("Urgent" | "High" | "Medium" | "Low"),
  "suggested_action": "Clear actionable next step for the salesperson",
  "key_insights": "2-3 bullet points regarding requirement, budget match, and readiness",
  "summary": "Concise 2-3 sentence overview of this lead and conversation progress",
  "draft_reply": "Professional, personalized email/WhatsApp message draft for the salesperson to review and send to {name}"
}}
"""
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            raw_text = response.text.strip()
            # Clean possible markdown wrap
            if raw_text.startswith("`"):
                raw_text = re.sub(r'^`(?:json)?\s*', '', raw_text)
                raw_text = re.sub(r'\s*`$', '', raw_text)
            parsed = json.loads(raw_text)
            return parsed
        except Exception as e:
            print(f"[AI Service] Gemini call fallback to local engine: {e}")

    # Built-in Intelligent Rule & NLP Engine (Works 100% offline out-of-the-box)
    return fallback_rule_nlp_engine(name, company, req, budget, source, status, interactions, history_text)

def fallback_rule_nlp_engine(name: str, company: str, req: str, budget: float, source: str, status: str, interactions: list, history_text: str) -> dict:
    full_corpus = f"{req} {history_text}".lower()

    positive_tokens = [
        "urgent", "interested", "demo", "buy", "purchase", "pricing", "quote",
        "ready", "start immediately", "decision", "soon", "looking forward", "excited",
        "budget approved", "meeting", "call", "proposal"
    ]
    negative_tokens = [
        "expensive", "too high", "not now", "delay", "postpone", "cancel", "competitor",
        "no budget", "unhappy", "not interested", "issue", "problem", "disappointed"
    ]

    pos_score = sum(1 for token in positive_tokens if token in full_corpus)
    neg_score = sum(1 for token in negative_tokens if token in full_corpus)

    if pos_score > neg_score:
        sentiment = "Positive"
    elif neg_score > pos_score:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"

    # Base Score calculation (0 - 100)
    score = 40

    # Budget weighting
    if budget >= 200000:
        score += 25
    elif budget >= 50000:
        score += 18
    elif budget >= 15000:
        score += 10
    elif budget > 0:
        score += 5

    # Requirement clarity
    if len(req) > 80:
        score += 15
    elif len(req) > 20:
        score += 10

    # Source credibility
    if source in ["Referral", "Website"]:
        score += 10
    elif source in ["LinkedIn", "WhatsApp"]:
        score += 7
    elif source in ["Instagram"]:
        score += 5

    # Sentiment influence
    if sentiment == "Positive":
        score += 15
    elif sentiment == "Negative":
        score -= 20

    # Pipeline progression
    if status in ["Qualified", "Demo", "Proposal"]:
        score += 10

    score = max(5, min(99, score))

    if score >= 75:
        score_category = "High"
        priority = "Urgent" if sentiment == "Positive" else "High"
    elif score >= 45:
        score_category = "Medium"
        priority = "Medium"
    else:
        score_category = "Low"
        priority = "Low"

    # Suggested Next Action
    if status == "New":
        suggested_action = f"Initiate initial discovery call with {name} and qualify budget requirements."
    elif status == "Contacted":
        suggested_action = f"Schedule a 20-minute live product demo focused on: '{req[:50]}...'."
    elif status == "Qualified":
        suggested_action = "Prepare and share tailored proposal with ROI breakdown based on approved budget."
    elif status == "Demo":
        suggested_action = "Follow up regarding demo feedback and address any technical/feature questions."
    elif status == "Proposal":
        suggested_action = "Reach out to close deal or offer strategic incentive to finalize contract."
    elif status == "Won":
        suggested_action = "Begin customer onboarding and introduce implementation manager."
    else:
        suggested_action = "Archive lead and set automated 60-day re-engagement nurture campaign."

    # Summary
    summary = f"{name} from {company} is seeking solutions for '{req if req else 'CRM implementation'}'. Budget indicated is INR {budget:,.0f}. Overall sentiment is {sentiment} with {len(interactions or [])} recorded interaction(s)."

    # Draft Reply (Editable by salesperson)
    draft_reply = (
        f"Hi {name},\n\n"
        f"Thank you for connecting with us regarding {company}'s requirements for {req if req else 'business automation'}. "
        f"Based on your timeline and needs, we have crafted a tailored solution within your targeted scope.\n\n"
        f"Would you be available for a brief 15-minute walkthrough this week to review the implementation and answer any questions?\n\n"
        f"Looking forward to partnering with {company}.\n\n"
        f"Best regards,\n"
        f"Sales Team"
    )

    return {
        "lead_score": score,
        "score_category": score_category,
        "sentiment": sentiment,
        "priority": priority,
        "suggested_action": suggested_action,
        "key_insights": f"• Budget indicated: INR {budget:,.0f} ({'Strong budget match' if budget >= 50000 else 'Standard tier'})\n• Customer engagement sentiment: {sentiment}\n• Source channel: {source}",
        "summary": summary,
        "draft_reply": draft_reply
    }
