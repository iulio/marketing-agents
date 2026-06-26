# app/analyst.py
"""
Performance Analyst Agent – Real-time Optimization with Real KPI Integration
Monitors campaigns, fetches real KPIs from Google Ads/Meta Ads, analyzes performance,
and applies automatic optimizations including creative regeneration.
"""
import os
import json
import random
import threading
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from langchain_community.chat_models import ChatOllama

from .storage import save_optimization_action, save_campaign_state
from .kpi_fetcher import KPIFetcher
from .agents import creative_node

# ================================================================
# CONFIGURATION
# ================================================================
AUTO_OPTIMIZE = os.getenv("AUTO_OPTIMIZE", "true").lower() == "true"
OPTIMIZATION_INTERVAL = int(os.getenv("OPTIMIZATION_INTERVAL", "60"))
MIN_CTR = float(os.getenv("MIN_CTR", "1.5"))
MAX_CPC = float(os.getenv("MAX_CPC", "2.0"))
MIN_ROAS = float(os.getenv("MIN_ROAS", "1.5"))

# ================================================================
# LLM INITIALIZATION
# ================================================================
llm = ChatOllama(
    model="llama3.2:3b",
    base_url="http://localhost:11434",
    temperature=0.3,
)

# ================================================================
# KPI FETCHER
# ================================================================
kpi_fetcher = KPIFetcher()

def fetch_real_kpis(campaign_id: str, platform: str = "auto") -> Dict[str, Any]:
    """Fetch real KPIs from the platform, with automatic fallback to simulation."""
    return kpi_fetcher.fetch_campaign_kpis(campaign_id, platform)

def refresh_kpis(campaign_id: str, platform: str = "auto") -> Dict[str, Any]:
    """Force a fresh fetch (bypass cache)."""
    return kpi_fetcher.refresh_kpis(campaign_id, platform)

# ================================================================
# PERFORMANCE ANALYSIS ENGINE
# ================================================================
def analyze_performance(campaign_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze campaign performance using an LLM."""
    prompt = f"""
    You are a Senior Performance Marketing Analyst. Analyze this campaign data and provide optimization recommendations.
    
    CAMPAIGN DATA:
    {json.dumps(campaign_data, indent=2)}
    
    Output JSON:
    {{
        "summary": "Overall performance assessment",
        "score": 0-100,
        "issues": ["issue1", "issue2"],
        "recommendations": [
            {{
                "priority": "high|medium|low",
                "category": "creative|bidding|targeting|budget",
                "action": "Description of what to do",
                "expected_impact": "Expected improvement"
            }}
        ],
        "creative_feedback": "Specific feedback on creatives if needed"
    }}
    """
    response = llm.invoke(prompt)
    print(f"[Analyst] Analysis: {response.content[:100]}...")
    
    try:
        content = response.content
        start = content.find('{')
        end = content.rfind('}') + 1
        if start != -1 and end != 0:
            json_str = content[start:end]
            return json.loads(json_str)
    except:
        pass
    
    # Fallback
    metrics = campaign_data.get("metrics", {})
    ctr = metrics.get("ctr", 2.0)
    cpc = metrics.get("cpc", 1.5)
    roas = metrics.get("roas", 2.0)
    
    issues = []
    if ctr < MIN_CTR:
        issues.append(f"CTR ({ctr}%) is below target")
    if cpc > MAX_CPC:
        issues.append(f"CPC (${cpc}) is above target")
    if roas < MIN_ROAS:
        issues.append(f"ROAS ({roas}x) is below target")
    
    recommendations = []
    if "CTR" in str(issues):
        recommendations.append({
            "priority": "high",
            "category": "creative",
            "action": "Refresh headlines and descriptions",
            "expected_impact": "Potential +20% CTR"
        })
    if "CPC" in str(issues):
        recommendations.append({
            "priority": "medium",
            "category": "bidding",
            "action": "Reduce bids on low-performing keywords",
            "expected_impact": "Potential -15% CPC"
        })
    if not recommendations:
        recommendations.append({
            "priority": "low",
            "category": "optimization",
            "action": "Continue current strategy",
            "expected_impact": "Maintain performance"
        })
    
    return {
        "summary": f"Campaign is {'performing well' if not issues else 'underperforming'}.",
        "score": max(0, 100 - len(issues) * 15),
        "issues": issues,
        "recommendations": recommendations,
        "creative_feedback": "Consider A/B testing new variants."
    }

# ================================================================
# OPTIMIZATION EXECUTOR
# ================================================================
def perform_optimization(campaign_id: str, state: Dict[str, Any], kpis: Dict[str, Any]) -> Dict[str, Any]:
    """Execute optimization actions based on analysis."""
    client = state.get("client_profile", {})
    creatives = state.get("creative_assets", {})
    analysis_data = {
        "campaign_name": client.get("client_name", "Unknown"),
        "industry": client.get("industry", "Unknown"),
        "budget": client.get("daily_budget", 0),
        "metrics": kpis,
        "creative_assets": {
            "headlines": [ad.get("headline", "") for ad in creatives.get("google_ads", [])],
            "descriptions": [ad.get("description", "") for ad in creatives.get("google_ads", [])],
            "primary_texts": [ad.get("primary_text", "") for ad in creatives.get("meta_ads", [])]
        }
    }
    
    analysis = analyze_performance(analysis_data)
    kpi_before = kpis.copy()
    actions_taken = []
    needs_refresh = False
    
    for rec in analysis.get("recommendations", []):
        category = rec.get("category", "")
        action = rec.get("action", "")
        priority = rec.get("priority", "low")
        
        if category == "creative" and priority in ["high", "medium"] and AUTO_OPTIMIZE:
            needs_refresh = True
            actions_taken.append({
                "type": "creative_refresh_triggered",
                "message": f"Creative refresh triggered due to: {action}"
            })
        else:
            actions_taken.append({
                "type": "suggestion",
                "message": f"[{priority}] {action}"
            })
    
    if needs_refresh:
        print(f"[Optimizer] Refreshing creatives for campaign {campaign_id}")
        try:
            new_state = creative_node(state.copy())
            state['creative_assets'] = new_state['creative_assets']
            state['creative_assets']['needs_refresh'] = False
            state['last_creative_refresh'] = datetime.now().isoformat()
            
            save_optimization_action(
                campaign_id,
                'creative_refresh',
                f'Regenerated creatives',
                kpi_before,
                None
            )
            save_campaign_state(campaign_id, state, state.get('status', 'active'))
            actions_taken.append({
                "type": "creative_refresh_completed",
                "message": "Successfully regenerated creatives"
            })
        except Exception as e:
            print(f"[Optimizer] Creative regeneration failed: {e}")
            actions_taken.append({
                "type": "creative_refresh_failed",
                "message": f"Failed to regenerate creatives: {str(e)}"
            })
    
    state["analysis"] = analysis
    state["last_optimization"] = datetime.now().isoformat()
    state["optimization_actions"] = actions_taken
    state["last_kpis"] = kpis
    
    save_campaign_state(campaign_id, state, state.get('status', 'active'))
    return state

# ================================================================
# BACKGROUND MONITOR
# ================================================================
class PerformanceMonitor:
    """Background thread that monitors all active campaigns and runs optimization."""
    def __init__(self, campaigns_store: Dict, kpi_store: Dict):
        self.campaigns_store = campaigns_store
        self.kpi_store = kpi_store
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print(f"[Monitor] Performance monitoring started (interval: {OPTIMIZATION_INTERVAL}s)")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("[Monitor] Performance monitoring stopped")

    def _run(self):
        while self.running:
            try:
                self._optimize_all_campaigns()
            except Exception as e:
                print(f"[Monitor] Error in optimization loop: {e}")
            time.sleep(OPTIMIZATION_INTERVAL)

    def _optimize_all_campaigns(self):
        for campaign_id, data in list(self.campaigns_store.items()):
            state = data.get("state", {})
            status = data.get("status", "unknown")
            
            if status != "active":
                continue
            
            platform = state.get("client_profile", {}).get("platform", "auto")
            
            try:
                kpis = fetch_real_kpis(campaign_id, platform)
                if kpis:
                    self.kpi_store[campaign_id] = kpis
            except Exception as e:
                print(f"[Monitor] Failed to fetch KPIs for {campaign_id}: {e}")
                if campaign_id not in self.kpi_store:
                    continue
            
            kpis = self.kpi_store.get(campaign_id)
            if not kpis:
                continue
            
            try:
                new_state = perform_optimization(campaign_id, state, kpis)
                data["state"] = new_state
                self.campaigns_store[campaign_id] = data
                print(f"[Monitor] Optimization executed for campaign {campaign_id}")
            except Exception as e:
                print(f"[Monitor] Optimization failed for {campaign_id}: {e}")

def run_immediate_optimization(campaign_id: str, state: Dict, platform: str = "auto") -> Dict[str, Any]:
    """Manually trigger optimization for a campaign."""
    kpis = refresh_kpis(campaign_id, platform)
    if not kpis:
        raise ValueError("Failed to fetch KPIs for optimization")
    return perform_optimization(campaign_id, state, kpis)