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
