# app/notifications.py
"""
Slack Notification Module.
Sends structured Block Kit messages to a Slack channel via incoming webhook
for key campaign lifecycle events.

Setup:
    Set SLACK_WEBHOOK_URL in your .env file.
    Leave it empty to disable notifications without any error.
"""
import os
import json
import urllib.request
import urllib.error
from typing import Optional

SLACK_WEBHOOK_URL: Optional[str] = os.getenv("SLACK_WEBHOOK_URL")
APP_URL: str = os.getenv("APP_URL", "http://localhost:8000")


def _post(payload: dict) -> None:
    """Internal: POST a JSON payload to the configured Slack webhook."""
    webhook = os.getenv("SLACK_WEBHOOK_URL") or SLACK_WEBHOOK_URL
    if not webhook:
        return
    try:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5):
            pass
    except Exception as exc:
        # Never let a Slack failure crash the main application.
        print(f"[Notifications] ⚠️  Slack delivery failed: {exc}")


def notify_campaign_created(
    campaign_name: str,
    client_name: str,
    campaign_id: str,
) -> None:
    """Send a Slack notification when a new campaign is created."""
    _post({
        "text": f"🚀 New campaign created: {campaign_name}",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🚀 New Campaign Created", "emoji": True},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Client:*\n{client_name}"},
                    {"type": "mrkdwn", "text": f"*Campaign:*\n{campaign_name}"},
                    {"type": "mrkdwn", "text": f"*Campaign ID:*\n`{campaign_id}`"},
                    {"type": "mrkdwn", "text": f"*Status:*\n⏳ Pending Review"},
                ],
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View in Dashboard"},
                        "url": f"{APP_URL}",
                        "style": "primary",
                    }
                ],
            },
        ],
    })


def notify_campaign_approved(
    campaign_name: str,
    client_name: str,
    campaign_id: str,
) -> None:
    """Send a Slack notification when a campaign is approved and goes live."""
    _post({
        "text": f"✅ Campaign approved: {campaign_name}",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "✅ Campaign Approved & Live", "emoji": True},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Client:*\n{client_name}"},
                    {"type": "mrkdwn", "text": f"*Campaign:*\n{campaign_name}"},
                    {"type": "mrkdwn", "text": f"*Campaign ID:*\n`{campaign_id}`"},
                    {"type": "mrkdwn", "text": f"*Status:*\n🟢 Active"},
                ],
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View in Dashboard"},
                        "url": f"{APP_URL}",
                        "style": "primary",
                    }
                ],
            },
        ],
    })


def notify_performance_alert(
    campaign_name: str,
    metric: str,
    value: float,
    threshold: float,
) -> None:
    """Send a Slack notification when a KPI drops below its threshold."""
    _post({
        "text": f"⚠️ Performance alert for {campaign_name}: {metric} = {value} (threshold: {threshold})",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "⚠️ Performance Alert", "emoji": True},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Campaign:*\n{campaign_name}"},
                    {"type": "mrkdwn", "text": f"*Metric:*\n{metric}"},
                    {"type": "mrkdwn", "text": f"*Current Value:*\n{value}"},
                    {"type": "mrkdwn", "text": f"*Threshold:*\n{threshold}"},
                ],
            },
        ],
    })
