# app/kpi_fetcher.py
"""
Unified KPI Fetcher - Aggregates data from Google Ads and Meta Ads
"""
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

from .google_ads_client import GoogleAdsClientWrapper
from .meta_ads_client import MetaAdsClientWrapper

class KPIFetcher:
    """Unified interface for fetching KPIs from multiple ad platforms."""
    
    def __init__(self):
        self.google = GoogleAdsClientWrapper()
        self.meta = MetaAdsClientWrapper()
        self._cache = {}
    
    def fetch_campaign_kpis(self, campaign_id: str, platform: str = "auto") -> Dict[str, Any]:
        """Fetch KPIs for a specific campaign."""
        if platform == "auto":
            platform = self._detect_platform(campaign_id)
        
        if platform == "google":
            return self.google.get_campaign_metrics(campaign_id)
        elif platform == "meta":
            return self.meta.get_campaign_metrics(campaign_id)
        else:
            return self._simulate(campaign_id)
    
    def refresh_kpis(self, campaign_id: str, platform: str = "auto") -> Dict[str, Any]:
        """Force refresh KPIs (bypass cache)."""
        cache_key = f"{platform}:{campaign_id}"
        if cache_key in self._cache:
            del self._cache[cache_key]
        return self.fetch_campaign_kpis(campaign_id, platform)
    
    def fetch_all_campaigns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch all campaigns from all available platforms."""
        all_campaigns = []
        
        google_data = self.google.get_campaign_metrics()
        if isinstance(google_data, dict) and "campaigns" in google_data:
            for c in google_data["campaigns"]:
                c["platform"] = "google"
                all_campaigns.append(c)
        
        meta_data = self.meta.get_campaign_metrics()
        if isinstance(meta_data, dict) and "campaigns" in meta_data:
            for c in meta_data["campaigns"]:
                c["platform"] = "meta"
                all_campaigns.append(c)
        
        return {"campaigns": all_campaigns}
    
    def _detect_platform(self, campaign_id: str) -> str:
        """Detect platform from campaign ID format."""
        if campaign_id and campaign_id.isdigit():
            return "google"
        return "meta"
    
    def _simulate(self, campaign_id: str) -> Dict[str, Any]:
        """Fallback simulation."""
        import random
        return {
            "campaign_id": campaign_id,
            "campaign_name": f"Campaign {campaign_id[:8]}",
            "status": "ACTIVE",
            "impressions": random.randint(1000, 10000),
            "clicks": random.randint(100, 1000),
            "cost": round(random.uniform(50, 500), 2),
            "conversions": random.randint(10, 100),
            "conversion_value": round(random.uniform(100, 1000), 2),
            "ctr": round(random.uniform(1.5, 6.0), 2),
            "cpc": round(random.uniform(0.5, 3.0), 2),
            "cost_per_conversion": round(random.uniform(5, 20), 2),
            "roas": round(random.uniform(1.5, 4.0), 2),
            "source": "simulated",
            "platform": "unknown",
            "updated_at": datetime.now().isoformat()
        }