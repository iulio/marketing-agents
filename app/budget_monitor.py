import os
from datetime import datetime
from typing import Dict, Any, Optional
from .notifications import send_budget_alert

BUDGET_ALERT_THRESHOLD = float(os.getenv("BUDGET_ALERT_THRESHOLD", "80"))
PACING_ALERT_THRESHOLD = float(os.getenv("PACING_ALERT_THRESHOLD", "1.5"))
AUTO_PAUSE_ENABLED = os.getenv("AUTO_PAUSE_ENABLED", "false").lower() == "true"
AUTO_PAUSE_THRESHOLD = float(os.getenv("AUTO_PAUSE_THRESHOLD", "95"))


def calculate_pacing(spent: float, budget: float, hours_elapsed: int, total_hours: int = 24) -> float:
    if budget == 0:
        return 0
    expected_spend = budget * (hours_elapsed / total_hours)
    if expected_spend == 0:
        return 0
    return spent / expected_spend


def check_budget_alerts(campaign_id: str, spent: float, budget: float, campaign_name: str, client_name: str) -> Dict:
    alerts = []

    if budget == 0:
        return {"alerts": [], "status": "no_budget"}

    percentage_spent = (spent / budget) * 100

    if percentage_spent >= BUDGET_ALERT_THRESHOLD:
        alerts.append({
            "type": "spend_alert",
            "message": f"Campaign {campaign_name} has spent {percentage_spent:.1f}% of daily budget ($ {spent:.2f} / $ {budget:.2f})",
            "severity": "warning",
            "threshold": BUDGET_ALERT_THRESHOLD
        })

    hours_elapsed = datetime.now().hour
    pacing = calculate_pacing(spent, budget, hours_elapsed)
    if pacing > PACING_ALERT_THRESHOLD:
        alerts.append({
            "type": "pacing_alert",
            "message": f"Campaign {campaign_name} is pacing too fast ({pacing:.2f}x expected). Consider reducing bids.",
            "severity": "warning",
            "pacing": pacing
        })
    elif pacing < (1 / PACING_ALERT_THRESHOLD):
        alerts.append({
            "type": "pacing_alert",
            "message": f"Campaign {campaign_name} is pacing too slow ({pacing:.2f}x expected). Consider increasing bids or budget.",
            "severity": "info",
            "pacing": pacing
        })

    if percentage_spent >= AUTO_PAUSE_THRESHOLD and AUTO_PAUSE_ENABLED:
        alerts.append({
            "type": "budget_depletion",
            "message": f"Campaign {campaign_name} is at {percentage_spent:.1f}% of budget. Auto-pause triggered.",
            "severity": "critical",
            "auto_paused": True
        })

    return {
        "alerts": alerts,
        "status": "critical" if any(a.get("severity") == "critical" for a in alerts) else "warning" if any(a.get("severity") == "warning" for a in alerts) else "ok",
        "pacing": pacing,
        "percentage_spent": percentage_spent
    }
