import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@yourapp.com")


def send_welcome_email(to_email: str, name: str):
    subject = "Welcome to AI Marketing Agency!"
    content = f"Hi {name}, welcome! Start your free trial now."
    _send_email(to_email, subject, content)


def send_payment_confirmation(to_email: str, plan: str):
    subject = "Payment Confirmed"
    content = f"Thanks for subscribing to {plan}. You now have full access."
    _send_email(to_email, subject, content)


def send_audit_report_email(to_email: str, website: str, summary: str):
    subject = f"Your free marketing audit for {website}"
    content = f"<p>Here is your audit summary for <strong>{website}</strong>.</p><p>{summary}</p><p>Reply to discuss next steps.</p>"
    _send_email(to_email, subject, content)


def send_proposal_email(to_email: str, website: str, summary: str):
    subject = f"Your marketing proposal for {website}"
    content = f"<p>We prepared a proposal for <strong>{website}</strong>.</p><p>{summary}</p><p>Reply to schedule a strategy call.</p>"
    _send_email(to_email, subject, content)


def send_follow_up_email(to_email: str, website: str):
    subject = f"Following up on your audit for {website}"
    content = f"<p>Checking in on your audit for <strong>{website}</strong>.</p><p>If you want, we can walk through the findings and next steps.</p>"
    _send_email(to_email, subject, content)


def send_bug_report_email(to_email: str, bug_data: dict):
    subject = "New Bug Report Received"
    content = f"""
    <h2>New Bug Report</h2>
    <p><strong>Description:</strong> {bug_data.get('description')}</p>
    <p><strong>URL:</strong> {bug_data.get('url')}</p>
    <p><strong>User Agent:</strong> {bug_data.get('userAgent')}</p>
    <p><strong>Screen Resolution:</strong> {bug_data.get('screenResolution')}</p>
    <p><strong>Timestamp:</strong> {bug_data.get('timestamp')}</p>
    """
    _send_email(to_email, subject, content)


def _send_email(to: str, subject: str, html: str):
    if not SENDGRID_API_KEY:
        print("[Email] No API key, skipping send.")
        return
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to,
        subject=subject,
        html_content=html
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
    except Exception as e:
        print(f"[Email] Error: {e}")
