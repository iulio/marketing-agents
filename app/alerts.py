# app/alerts.py
"""
Performance Alerts Module.
Sends email notifications when campaign KPIs drop below configurable thresholds.
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any


def should_send_alert(kpis: Dict[str, Any], thresholds: Dict[str, float]) -> bool:
    """
    Check if any KPI has crossed the alert threshold.
    
    Args:
        kpis: Current campaign KPI metrics
        thresholds: Dictionary of threshold keys and values
        
    Returns:
        True if any threshold has been breached
    """
    for key, threshold in thresholds.items():
        current_value = kpis.get(key, 0)
        
        # CTR below threshold
        if key == "ctr" and isinstance(current_value, (int, float)) and current_value < threshold:
            return True
        
        # ROAS below threshold  
        if key == "roas" and isinstance(current_value, (int, float)) and current_value < threshold:
            return True
        
        # CPC above threshold (higher cost is bad)
        if key == "cpc" and isinstance(current_value, (int, float)) and current_value > threshold:
            return True
    
    return False


def send_email_alert(campaign_id: str, kpis: Dict, recipients: list):
    """
    Send an email alert when KPIs drop below thresholds.
    
    Args:
        campaign_id: Unique campaign identifier
        kpis: Current campaign KPI metrics
        recipients: List of email addresses to send alerts to
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    
    if not all([smtp_host, smtp_user, smtp_password]):
        print("[Alerts] SMTP not configured - alerts disabled")
        return
    
    subject = f"🚨 Campaign Alert: {campaign_id}"
    
    # Get current values for the alert message
    ctr = kpis.get('ctr', 0)
    roas = kpis.get('roas', 0)
    cpc = kpis.get('cpc', 0.0)
    
    body = f"""
Campaign {campaign_id} has crossed a performance threshold.

Current KPIs:
- CTR: {ctr:.2f}%
- ROAS: {roas:.2f}x  
- CPC: ${cpc:.2f}

Please review the campaign dashboard at:
{os.getenv("APP_URL", "http://localhost:8000")}/campaigns/{campaign_id}

This is an automated notification from Marketing Agents.
"""
    
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = ", ".join(recipients)
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            
            for recipient in recipients:
                server.send_message(msg, from_addr=smtp_user, to_addrs=[recipient])
        
        print(f"[Alerts] ✅ Alert sent for campaign {campaign_id}")
    except Exception as e:
        print(f"[Alerts] ❌ Failed to send alert: {e}")


def send_slack_alert(webhook_url: str, campaign_id: str, kpis: Dict):
    """
    Send a Slack notification when KPIs drop below thresholds.
    
    Args:
        webhook_url: Slack incoming webhook URL
        campaign_id: Unique campaign identifier
        kpis: Current campaign KPI metrics
    """
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook or webhook != webhook_url:
        return
    
    body = f"""{{
        "text": "🚨 Campaign Alert: {campaign_id}",
        "attachments": [
            {{
                "color": "danger",
                "fields": [
                    {{ "title": "CTR", "value": f"{kpis.get('ctr', 0):.2f}%", "short": true }},
                    {{ "title": "ROAS", "value": f"{kpis.get('roas', 0):.2f}x", "short": true }},
                    {{ "title": "CPC", "value": f"${{kpis.get('cpc', 0.0):.2f}", "short": true }}
                ]
            }}
        ]
    }}"""
    
    try:
        import urllib.request
        req = urllib.request.Request(webhook, data=body.encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as response:
            print(f"[Alerts] ✅ Slack alert sent for campaign {campaign_id}")
    except Exception as e:
        print(f"[Alerts] ❌ Failed to send Slack alert: {e}")


def format_alert_message(campaign_id: str, kpis: Dict, action_type: str = "alert") -> str:
    """
    Format a standardized alert message for logging.
    
    Args:
        campaign_id: Unique campaign identifier
        kpis: Current KPI metrics
        action_type: Type of alert (alert, optimization_complete, etc.)
    
    Returns:
        Formatted alert message string
    """
    return f"[{action_type.upper()}] Campaign {campaign_id}: CTR={kpis.get('ctr', 0):.2f}%, ROAS={kpis.get('roas', 0):.2f}x, CPC=${kpis.get('cpc', 0.0):.2f}"
