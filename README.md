# Smart CRM AI - Sales Automation

A complete fullstack AI-powered Customer Relationship Management (CRM) system designed to automate lead qualification, sentiment analysis, personalized follow-ups, and sales pipeline tracking.

## Complete 17-Step Workflow Supported
1. Open CRM Web Dashboard
2. Add New Lead (Name, Email, Phone, Company, Requirement, Budget, Source)
3. Instant Database persistence (SQLite)
4. AI Lead Analysis (requirement understanding, budget matching, intent recognition)
5. AI Output badge (Lead Score 0-100, Sentiment, Priority, Suggested Action)
6. Interactive Pipeline Stages (New -> Contacted -> Qualified -> Demo -> Proposal -> Won/Lost)
7. Quick Action triggers (Direct WhatsApp chat, Send Email, Log Calls)
8. Log customer notes and conversation updates
9. AI Conversation Summary & Auto-generated follow-up draft
10. Human-in-the-Loop review and draft editing before dispatch
11. Approved communication send via WhatsApp / Email
12. Follow-up scheduling with date & time reminders
13. Overdue & Due today visual notification alerts
14. Real-time lead score and sentiment updates on new interactions
15. Deal Closing (Won -> Customer Account Conversion, Lost -> Reason capture)
16. KPI Metrics & Visual Reports (Total Leads, High-Priority, Win Rate, Sales Forecast)
17. Edit saved lead details to correct spelling or contact information

## How to Run in VS Code

1. Create a local environment file from the example:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Update `.env` with your own settings. Keep real credentials in `.env` only; do not commit that file.
3. In your VS Code terminal, activate the environment if you use one, then run:
   ```powershell
   .\venv\Scripts\activate
   python main.py
   ```
4. Open the dashboard at http://127.0.0.1:8000.

The server host and port, SMTP settings, and automatic follow-up delay can be configured in `.env`.