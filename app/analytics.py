# app/analytics.py
"""
Advanced Analytics Module for Campaign Performance Visualization.
Provides data aggregation and metrics calculation for charts and reports.
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
import random
from .storage import get_all_campaigns


def generate_daily_metrics(campaign_id: str, days: int = 30) -> List[Dict]:
    """
    Generate daily metrics for a campaign.
    
    Can use simulated data or fetch from real API sources (Google Ads/Meta).
    
    Args:
        campaign_id: Unique campaign identifier
        days: Number of days of historical data to generate
    
    Returns:
        List of daily metric dictionaries
    """
    data = []
    now = datetime.now()
    
    for i in range(days - 1, -1, -1):
        date = now - timedelta(days=i)
        base_impressions = random.randint(500, 5000)
        base_clicks = int(base_impressions * random.uniform(0.01, 0.05))
        data.append({
            "date": date.strftime("%Y-%m-%d"),
            "impressions": base_impressions,
            "clicks": base_clicks,
            "ctr": round(base_clicks / base_impressions * 100, 2) if base_impressions > 0 else 0,
            "spend": round(random.uniform(5, 150), 2)
        })
    
    return data


def aggregate_metrics(campaigns_data: List[Dict]) -> Dict:
    """
    Aggregate metrics across all campaigns.
    
    Args:
        campaigns_data: List of campaign dictionaries with metrics
    
    Returns:
        Dictionary with aggregated totals and averages
    """
    total_impressions = 0
    total_clicks = 0
    total_spend = 0
    
    for campaign in campaigns_data:
        metrics = campaign.get("metrics", {})
        total_impressions += metrics.get("impressions", 0)
        total_clicks += metrics.get("clicks", 0)
        total_spend += metrics.get("cost", 0)
    
    return {
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "total_spend": total_spend,
        "avg_ctr": round(total_clicks / total_impressions * 100, 2) if total_impressions > 0 else 0,
        "campaign_count": len(campaigns_data)
    }


def calculate_campaign_roi(spend: float, revenue: float = None) -> float:
    """
    Calculate Return on Investment for a campaign.
    
    Args:
        spend: Total campaign cost
        revenue: Estimated revenue (optional)
    
    Returns:
        ROI percentage
    """
    if not revenue or spend == 0:
        return 0.0
    return round(((revenue - spend) / spend) * 100, 2)


def calculate_conversion_rate(conversions: int, clicks: int) -> float:
    """
    Calculate conversion rate.
    
    Args:
        conversions: Number of conversions
        clicks: Number of clicks
    
    Returns:
        Conversion rate percentage
    """
    if clicks == 0:
        return 0.0
    return round((conversions / clicks) * 100, 2)


def get_performance_trend(daily_data: List[Dict], metric_key: str, window: int = 7) -> str:
    """
    Calculate performance trend over recent days.
    
    Args:
        daily_data: List of daily metrics
        metric_key: Metric key (impressions, clicks, ctr, etc.)
        window: Number of days to compare (default 7)
    
    Returns:
        Trend string: 'increasing', 'decreasing', or 'stable'
    """
    if len(daily_data) < window * 2:
        return "stable"
    
    recent = [d.get(metric_key, 0) for d in daily_data[-window*2:]]
    older = [d.get(metric_key, 0) for d in daily_data[-window*3:-window]]
    
    if sum(recent) > sum(older) * 1.05:
        return "increasing"
    elif sum(recent) < sum(older) * 0.95:
        return "decreasing"
    else:
        return "stable"
