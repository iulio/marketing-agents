# app/google_ads_api.py
"""
Google Ads API Integration - Real API with fallback to simulation
"""
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

try:
    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException
    GOOGLE_ADS_AVAILABLE = True
except ImportError:
    GOOGLE_ADS_AVAILABLE = False

class GoogleAdsAPI:
    """Real Google Ads API integration with fallback to simulation"""
    
    def __init__(self, credentials: Optional[Dict[str, Any]] = None):
        self.client = None
        self.credentials = credentials or {}
        self.customer_id = self.credentials.get("google_ads_customer_id") or os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")
        self._init_client(self.credentials)
    
    def _init_client(self, credentials: Optional[Dict[str, Any]] = None):
        """Initialize Google Ads client from environment or credentials file."""
        if not GOOGLE_ADS_AVAILABLE:
            print("[GoogleAds] ⚠️  google-ads library not installed")
            return
        
        try:
            # Try passed credentials first, then environment variables
            creds_to_use = credentials or {}
            if all([os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
                   os.getenv("GOOGLE_ADS_CLIENT_ID"),
                   os.getenv("GOOGLE_ADS_REFRESH_TOKEN")]):
                self.client = GoogleAdsClient.load_from_env()
                print("[GoogleAds] ✅ Client initialized from environment variables")
                return
            
            if all([creds_to_use.get("google_ads_developer_token"),
                    creds_to_use.get("google_ads_client_id"),
                    creds_to_use.get("google_ads_client_secret"),
                    creds_to_use.get("google_ads_refresh_token")]):
                
                config = {
                    "developer_token": creds_to_use["google_ads_developer_token"],
                    "client_id": creds_to_use["google_ads_client_id"],
                    "client_secret": creds_to_use["google_ads_client_secret"],
                    "refresh_token": creds_to_use["google_ads_refresh_token"],
                    "login_customer_id": creds_to_use.get("google_ads_customer_id", "").replace("-", ""),
                    "use_proto_plus": True
                }
                self.client = GoogleAdsClient.load_from_dict(config)
                print("[GoogleAds] ✅ Client initialized from provided credentials")
                return

            # Try credentials file
            cred_path = os.path.join(os.path.dirname(__file__), "credentials", "google-ads.yaml")
            if os.path.exists(cred_path):
                self.client = GoogleAdsClient.load_from_storage(cred_path)
                print(f"[GoogleAds] ✅ Client initialized from {cred_path}")
                return
            
            print("[GoogleAds] ⚠️  No credentials found (env vars or yaml file)")
        except Exception as e:
            print(f"[GoogleAds] ❌ Initialization error: {e}")
    
    def is_available(self) -> bool:
        """Check if real API is available."""
        return self.client is not None and GOOGLE_ADS_AVAILABLE

    def test_credentials(self) -> Dict[str, Any]:
        """Test credentials by fetching a single campaign to verify connectivity."""
        if not self.is_available():
            return {"status": "error", "message": "Google Ads library not installed or client not initialized."}
        
        if not self.customer_id:
            return {"status": "error", "message": "Google Ads Customer ID is not configured."}

        try:
            ga_service = self.client.get_service("GoogleAdsService")
            query = """
                SELECT campaign.id, campaign.name FROM campaign
                WHERE campaign.status != 'REMOVED'
                ORDER BY campaign.id
                LIMIT 1
            """
            response_stream = ga_service.search_stream(customer_id=self.customer_id.replace("-", ""), query=query)
            
            # Iterating through the stream is what actually makes the API call
            for batch in response_stream:
                # If we get here, even with no results, the call was successful.
                pass
            return {"status": "success", "message": "Successfully connected to Google Ads."}
        except GoogleAdsException as ex:
            return {"status": "error", "message": f"Google Ads API Error: {ex.error.code().name}"}
        except Exception as e:
            return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}
    
    def create_campaign(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a campaign (real or simulated)."""
        if not self.is_available():
            return self._simulate_campaign_creation(campaign_data)
        
        try:
            client = self.client
            campaign_service = client.get_service("CampaignService")
            campaign = client.get_type("Campaign")
            campaign.name = campaign_data.get("name", "AI Generated Campaign")
            campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
            campaign.status = client.enums.CampaignStatusEnum.PAUSED
            
            # Create budget
            budget = client.get_type("Budget")
            budget.name = f"Budget for {campaign.name}"
            budget.amount_micros = int(campaign_data.get("budget", 100) * 1_000_000)
            budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
            budget_service = client.get_service("CampaignBudgetService")
            budget_response = budget_service.mutate_campaign_budgets(self.customer_id, [budget])
            campaign.campaign_budget = budget_response.results[0].resource_name
            
            # Create campaign
            response = campaign_service.mutate_campaigns(self.customer_id, [campaign])
            print(f"[GoogleAds] ✅ Campaign created: {response.results[0].resource_name}")
            
            return {
                "status": "success",
                "campaign_id": response.results[0].resource_name,
                "campaign_name": campaign.name,
                "status_text": "PAUSED",
                "platform": "google_ads",
                "real_api": True
            }
        except Exception as e:
            print(f"[GoogleAds] ❌ Campaign creation error: {e}")
            return self._simulate_campaign_creation(campaign_data)
    
    def _simulate_campaign_creation(self, campaign_data: Dict) -> Dict:
        """Simulate campaign creation."""
        import random
        return {
            "status": "success",
            "campaign_id": f"GC-{random.randint(10000, 99999)}",
            "campaign_name": campaign_data.get("name", "Simulated Campaign"),
            "status_text": "DRAFT (simulated)",
            "platform": "google_ads",
            "real_api": False
        }
    
    def get_campaign_metrics(self, campaign_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetch campaign metrics (real or simulated)."""
        if not self.is_available():
            return self._simulate_metrics(campaign_id)
        
        try:
            ga_service = self.client.get_service("GoogleAdsService")
            query = f"""
                SELECT campaign.id, campaign.name, campaign.status,
                       metrics.impressions, metrics.clicks, metrics.cost_micros,
                       metrics.conversions, metrics.conversions_value,
                       metrics.ctr, metrics.average_cpc,
                       metrics.conversions_value_per_cost
                FROM campaign
                WHERE campaign.status != 'REMOVED'
                {f"AND campaign.id = {campaign_id}" if campaign_id else ""}
                AND segments.date DURING LAST_30_DAYS
            """
            response = ga_service.search_stream(customer_id=self.customer_id, query=query)
            results = []
            
            for batch in response:
                for row in batch.results:
                    campaign = row.campaign
                    metrics = row.metrics
                    results.append({
                        "campaign_id": str(campaign.id),
                        "campaign_name": campaign.name,
                        "status": campaign.status.name,
                        "impressions": metrics.impressions,
                        "clicks": metrics.clicks,
                        "cost": metrics.cost_micros / 1_000_000,
                        "conversions": metrics.conversions,
                        "conversion_value": metrics.conversions_value,
                        "ctr": metrics.ctr * 100 if metrics.ctr else 0,
                        "cpc": metrics.average_cpc / 1_000_000 if metrics.average_cpc else 0,
                        "roas": metrics.conversions_value_per_cost if metrics.conversions_value_per_cost else 0,
                        "source": "google_ads"
                    })
            
            if campaign_id and results:
                return results[0]
            return {"campaigns": results} if results else self._simulate_metrics(campaign_id)
        except Exception as e:
            print(f"[GoogleAds] ❌ Error fetching metrics: {e}")
            return self._simulate_metrics(campaign_id)
    
    def _simulate_metrics(self, campaign_id: Optional[str] = None) -> Dict:
        """Simulate metrics for demo/testing."""
        import random
        return {
            "campaign_id": campaign_id or "simulated",
            "campaign_name": "Simulated Campaign",
            "status": "ENABLED",
            "impressions": random.randint(1000, 10000),
            "clicks": random.randint(100, 1000),
            "cost": round(random.uniform(50, 500), 2),
            "conversions": random.randint(10, 100),
            "conversion_value": round(random.uniform(100, 1000), 2),
            "ctr": round(random.uniform(1.5, 6.0), 2),
            "cpc": round(random.uniform(0.5, 3.0), 2),
            "roas": round(random.uniform(1.5, 4.0), 2),
            "source": "simulated_google"
        }
