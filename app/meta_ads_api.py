# app/meta_ads_api.py
"""
Meta Ads API Integration - Real API with fallback to simulation
"""
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

try:
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.adaccount import AdAccount
    from facebook_business.adobjects.campaign import Campaign
    META_AVAILABLE = True
except ImportError:
    META_AVAILABLE = False

class MetaAdsAPI:
    """Meta Ads API integration with fallback to simulation"""
    
    def __init__(self):
        self.api = None
        self.ad_account_id = os.getenv("META_AD_ACCOUNT_ID", "")
        self._init_client()
    
    def _init_client(self):
        """Initialize Meta Ads client from environment."""
        if not META_AVAILABLE:
            print("[MetaAds] ⚠️  facebook-business library not installed")
            return
        
        try:
            app_id = os.getenv("META_APP_ID")
            app_secret = os.getenv("META_APP_SECRET")
            access_token = os.getenv("META_ACCESS_TOKEN")
            
            if all([app_id, app_secret, access_token]):
                FacebookAdsApi.init(app_id, app_secret, access_token)
                self.api = FacebookAdsApi.get_default_api()
                print("[MetaAds] ✅ Client initialized from environment")
                
                if self.ad_account_id:
                    print(f"[MetaAds] ✅ Ad account configured: {self.ad_account_id}")
                else:
                    print("[MetaAds] ⚠️  META_AD_ACCOUNT_ID not set")
            else:
                missing = []
                if not app_id: missing.append("META_APP_ID")
                if not app_secret: missing.append("META_APP_SECRET")
                if not access_token: missing.append("META_ACCESS_TOKEN")
                print(f"[MetaAds] ⚠️  Missing credentials: {', '.join(missing)}")
        except Exception as e:
            print(f"[MetaAds] ❌ Initialization error: {e}")
    
    def is_available(self) -> bool:
        """Check if real API is available."""
        return self.api is not None and META_AVAILABLE and bool(self.ad_account_id)
    
    def create_campaign(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a campaign (real or simulated)."""
        if not self.is_available():
            return self._simulate_campaign_creation(campaign_data)
        
        try:
            account_id = self.ad_account_id if self.ad_account_id.startswith('act_') else f"act_{self.ad_account_id}"
            
            campaign = Campaign(account_id=account_id)
            response = campaign.create({
                Campaign.Field.name: campaign_data.get("name", "AI Generated Campaign"),
                Campaign.Field.objective: campaign_data.get("objective", "OUTCOME_AWARENESS"),
                Campaign.Field.status: Campaign.Status.paused,
                Campaign.Field.special_ad_categories: [],
            })
            
            campaign_id = response.get('id', 'unknown')
            print(f"[MetaAds] ✅ Campaign created: {campaign_id}")
            
            return {
                "status": "success",
                "campaign_id": campaign_id,
                "campaign_name": campaign_data.get("name", "AI Generated Campaign"),
                "status_text": "PAUSED",
                "platform": "meta_ads",
                "real_api": True
            }
        except Exception as e:
            print(f"[MetaAds] ❌ Campaign creation error: {e}")
            return self._simulate_campaign_creation(campaign_data)
    
    def _simulate_campaign_creation(self, campaign_data: Dict) -> Dict:
        """Simulate campaign creation."""
        import random
        return {
            "status": "success",
            "campaign_id": f"MC-{random.randint(10000, 99999)}",
            "campaign_name": campaign_data.get("name", "Simulated Campaign"),
            "status_text": "DRAFT (simulated)",
            "platform": "meta_ads",
            "real_api": False
        }
    
    def get_campaign_metrics(self, campaign_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetch campaign metrics (real or simulated)."""
        if not self.is_available():
            return self._simulate_metrics(campaign_id)
        
        try:
            account_id = self.ad_account_id if self.ad_account_id.startswith('act_') else f"act_{self.ad_account_id}"
            account = AdAccount(account_id)
            
            fields = ['campaign_id', 'campaign_name', 'campaign_status', 
                     'impressions', 'clicks', 'spend', 'conversions', 
                     'conversion_value', 'ctr', 'cpc', 'conversions_value_per_cost']
            
            params = {
                'level': 'campaign',
                'time_range': {
                    'since': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                    'until': datetime.now().strftime('%Y-%m-%d'),
                }
            }
            
            if campaign_id:
                params['filtering'] = [{'field': 'campaign.id', 'operator': 'EQUAL', 'value': campaign_id}]
            
            insights = account.get_insights(fields=fields, params=params)
            results = []
            
            for insight in insights:
                results.append({
                    "campaign_id": insight.get('campaign_id', ''),
                    "campaign_name": insight.get('campaign_name', ''),
                    "status": insight.get('campaign_status', ''),
                    "impressions": int(insight.get('impressions', 0)),
                    "clicks": int(insight.get('clicks', 0)),
                    "cost": float(insight.get('spend', 0)),
                    "conversions": float(insight.get('conversions', 0)),
                    "conversion_value": float(insight.get('conversion_value', 0)),
                    "ctr": float(insight.get('ctr', 0)),
                    "cpc": float(insight.get('cpc', 0)),
                    "roas": float(insight.get('conversions_value_per_cost', 0)),
                    "source": "meta_ads"
                })
            
            if campaign_id and results:
                return results[0]
            return {"campaigns": results} if results else self._simulate_metrics(campaign_id)
        except Exception as e:
            print(f"[MetaAds] ❌ Error fetching metrics: {e}")
            return self._simulate_metrics(campaign_id)
    
    def _simulate_metrics(self, campaign_id: Optional[str] = None) -> Dict:
        """Simulate metrics for demo/testing."""
        import random
        return {
            "campaign_id": campaign_id or "simulated_meta",
            "campaign_name": "Simulated Meta Campaign",
            "status": "ACTIVE",
            "impressions": random.randint(1000, 10000),
            "clicks": random.randint(100, 1000),
            "cost": round(random.uniform(50, 500), 2),
            "conversions": random.randint(10, 100),
            "conversion_value": round(random.uniform(100, 1000), 2),
            "ctr": round(random.uniform(1.5, 6.0), 2),
            "cpc": round(random.uniform(0.5, 3.0), 2),
            "roas": round(random.uniform(1.5, 4.0), 2),
            "source": "simulated_meta"
        }
