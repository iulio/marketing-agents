# app/report_scheduler.py
import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .email import _send_email
from .reporting import render_custom_report
from .storage import (
    create_report_schedule,
    get_due_report_schedules,
    get_report_template,
    get_report_schedule,
    get_all_campaigns,
    mark_report_schedule_sent,
)


async def check_and_send_due_reports():
    """Background task: check for due scheduled reports and send them."""
    due_schedules = get_due_report_schedules()
    for schedule in due_schedules:
        try:
            _send_scheduled_report(schedule)
            mark_report_schedule_sent(schedule["id"])
        except Exception as e:
            print(f"[Scheduler] Failed to send report {schedule['id']}: {e}")


def _send_scheduled_report(schedule: Dict[str, Any]):
    """Build and send a single scheduled report email."""
    template = get_report_template(schedule["template_id"])
    if not template:
        print(f"[Scheduler] Template {schedule['template_id']} not found for schedule {schedule['id']}")
        return

    campaign_data = {
        "client_name": schedule.get("client_name", "Client"),
        "creative_assets": {},
        "recommendations": [],
    }
    metrics = {
        "impressions": 0, "clicks": 0, "ctr": 0, "cpc": 0.0,
        "conversions": 0, "roas": 0.0, "cost": 0.0,
    }

    pdf_bytes = render_custom_report(campaign_data, metrics, template)
    to_email = schedule.get("recipient_email") or schedule.get("email", "")

    if to_email and pdf_bytes:
        _send_email_with_attachment(to_email, schedule, pdf_bytes)


def _send_email_with_attachment(to_email: str, schedule: Dict[str, Any], pdf_bytes: bytes):
    """Send the PDF report as an email attachment using SendGrid."""
    subject = f"Scheduled Report: {schedule.get('name', 'Marketing Report')}"
    html = f"""
    <p>Hi,</p>
    <p>Attached is your scheduled marketing report: <strong>{schedule.get('name', '')}</strong></p>
    <p>Generated at: {datetime.utcnow().isoformat()}</p>
    """

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
        import base64
        import os

        api_key = os.getenv("SENDGRID_API_KEY")
        if not api_key:
            print("[Scheduler] No SENDGRID_API_KEY, skipping email")
            return

        encoded = base64.b64encode(pdf_bytes).decode()
        attachment = Attachment(
            FileContent(encoded),
            FileName(f"report_{schedule['id']}.pdf"),
            FileType("application/pdf"),
            Disposition("attachment"),
        )

        message = Mail(
            from_email=os.getenv("FROM_EMAIL", "noreply@yourapp.com"),
            to_emails=to_email,
            subject=subject,
            html_content=html,
        )
        message.add_attachment(attachment)

        sg = SendGridAPIClient(api_key)
        sg.send(message)
        print(f"[Scheduler] Report {schedule['id']} sent to {to_email}")
    except Exception as e:
        print(f"[Scheduler] Email send error: {e}")


async def scheduler_loop(interval_seconds: int = 60):
    """Run the due-report checker periodically."""
    while True:
        try:
            await check_and_send_due_reports()
        except Exception as e:
            print(f"[Scheduler] Loop error: {e}")
        await asyncio.sleep(interval_seconds)
