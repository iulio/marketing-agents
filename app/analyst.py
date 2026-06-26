"""
Performance Analyst Agent - Real-time Optimization
Monitors campaigns, analyzes KPIs, and applies automatic optimizations.
"""
import os
import json
import random
import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_community.chat_models import ChatOllama

# ================================================================
# CONFIGURATION
# ================================================================
AUTO_OPTIMIZE = os.getenv("AUTO_OPTIMIZE", "true").lower() == "true"
OPTIMIZATION_INTERVAL = int(os.getenv("OPTIMIZATION_INTERVAL", "60"))  # seconds
MIN_CTR = float(os.getenv("MIN_CTR", "1.5"))  # %
MAX_CPC = float(os.getenv("MAX_CPC", "2.0"))   # $
MIN_ROAS = float(os.getenv("MIN_ROAS", "1.5"))  # multiplier

# ================================================================
# LLM INITIALIZATION
# ================================================================
llm = ChatOllama(
    model="llama3.2:3b",
    base_url="http://localhost:11434",
    temperature=0.3,
)


# ================================================================
# DATA SIMULATION (Replace with real API calls later)
# ================================================================
def simulate_kpi_update(campaign_id: str) -> Dict[str, Any]:
    """Simulate real-time KPI data"""
    return {
        "campaign_id": campaign_id,
        "impressions": random.randint(1000, 10000),
        "clicks": random.randint(100, 1000),
        "conversions": random.randint(10, 100),
        "spend": random.randint(50, 500),
        "ctr": round(random.uniform(0.5, 8.0), 2),
        "cpc": round(random.uniform(0.3, 3.5), 2),
        "roas": round(random.uniform(0.8, 5.0), 2),
        "status": "active",
        "updated_at": datetime.now().isoformat()
    }


# ================================================================
# ANALYSIS ENGINE
# ================================================================
def analyze_performance(campaign_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze campaign performance and generate optimization recommendations.
    """
    prompt = f"""
    You are a Senior Performance Marketing Analyst. Analyze this campaign data and provide optimization recommendations.
    
    CAMPAIGN DATA:
    {json.dumps(campaign_data, indent=2)}
    
    Analyze the following aspects:
    1. Current performance (strengths and weaknesses)
    2. 3 actionable recommendations to improve performance
    3. Specific creative suggestions (if CTR is low)
    4. Bid/budget recommendations (if CPC is high or budget is under/over-spent)
    
    Output JSON:
    {{
        "summary": "Overall performance assessment (2-3 sentences)",
        "score": 0-100 (performance score),
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
    
    # Parse response
    try:
        content = response.content
        start = content.find('{')
        end = content.rfind('}') + 1
        if start != -1 and end != 0:
            json_str = content[start:end]
            return json.loads(json_str)
    except:
        pass
    
    # Fallback analysis
    metrics = campaign_data.get("metrics", {})
    ctr = metrics.get("ctr", 2.0)
    cpc = metrics.get("cpc", 1.5)
    roas = metrics.get("roas", 2.0)
    
    issues = []
    if ctr < MIN_CTR:
        issues.append(f"CTR ({ctr}%) is below target ({MIN_CTR}%)")
    if cpc > MAX_CPC:
        issues.append(f"CPC (${cpc}) is above target (${MAX_CPC})")
    if roas < MIN_ROAS:
        issues.append(f"ROAS ({roas}x) is below target ({MIN_ROAS}x)")
    
    recommendations = []
    if "CTR" in str(issues):
        recommendations.append({
            "priority": "high",
            "category": "creative",
            "action": "Refresh headlines and descriptions with more emotional appeals",
            "expected_impact": f"Potential +20% CTR"
        })
    if "CPC" in str(issues):
        recommendations.append({
            "priority": "medium",
            "category": "bidding",
            "action": "Reduce bids by 10% on low-performing keywords",
            "expected_impact": f"Potential -15% CPC"
        })
    if "ROAS" in str(issues):
        recommendations.append({
            "priority": "high",
            "category": "budget",
            "action": "Reallocate budget to top-performing ad groups",
            "expected_impact": f"Potential +30% ROAS"
        })
    
    if not recommendations:
        recommendations.append({
            "priority": "low",
            "category": "optimization",
            "action": "Continue current strategy; all KPIs within targets",
            "expected_impact": "Maintain performance"
        })
    
    return {
        "summary": f"Campaign is {'performing well' if not issues else 'underperforming'}.",
        "score": max(0, 100 - len(issues) * 15),
        "issues": issues,
        "recommendations": recommendations,
        "creative_feedback": "Current creatives are adequate; consider A/B testing new variants."
    }


# ================================================================
# OPTIMIZATION EXECUTOR
# ================================================================
def perform_optimization(campaign_id: str, state: Dict[str, Any], kpis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute optimization actions based on analysis.
    Returns updated state and log of actions taken.
    """
    # Prepare analysis data
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
    
    # Run analysis
    analysis = analyze_performance(analysis_data)
    
    # Apply actions
    actions_taken = []
    for rec in analysis.get("recommendations", []):
        category = rec.get("category", "")
        action = rec.get("action", "")
        priority = rec.get("priority", "low")
        
        if priority == "high" and AUTO_OPTIMIZE:
            if category == "creative":
                # Trigger creative regeneration
                actions_taken.append({
                    "type": "regenerate_creatives",
                    "message": "Triggered creative refresh due to low CTR"
                })
                # In a real system, you'd call the creative agent to generate new ads
                # For now, we'll just flag it
                state["creative_assets"]["needs_refresh"] = True
            elif category == "bidding":
                # Adjust bids (simulate)
                actions_taken.append({
                    "type": "adjust_bids",
                    "message": action,
                    "adjustment": "-10%"
                })
            elif category == "budget":
                # Reallocate budget (simulate)
                actions_taken.append({
                    "type": "reallocate_budget",
                    "message": action
                })
        else:
            # Log suggestion for human review
            actions_taken.append({
                "type": "suggestion",
                "message": f"[{priority}] {action} (auto-optimization disabled or priority not high)"
            })
    
    # Update state with analysis results
    state["analysis"] = analysis
    state["last_optimization"] = datetime.now().isoformat()
    state["optimization_actions"] = actions_taken
    
    return state


# ================================================================
# BACKGROUND MONITORING
# ================================================================
class PerformanceMonitor:
    """
    Background thread that monitors all active campaigns and runs optimization.
    """
    def __init__(self, campaigns_store, kpi_store):
        self.campaigns_store = campaigns_store  # Reference to in-memory campaigns dict
        self.kpi_store = kpi_store              # Reference to in-memory KPIs dict
        self.running = False
        self.thread = None
        
    def start(self):
        """Start the monitoring thread"""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print(f"[Monitor] Performance monitoring started (interval: {OPTIMIZATION_INTERVAL}s)")
    
    def stop(self):
        """Stop the monitoring thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("[Monitor] Performance monitoring stopped")
    
    def _run(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._optimize_all_campaigns()
            except Exception as e:
                print(f"[Monitor] Error in optimization loop: {e}")
            time.sleep(OPTIMIZATION_INTERVAL)
    
    def _optimize_all_campaigns(self):
        """Iterate over all campaigns and optimize those that are active"""
        # Acquire lock if using threading (not needed for simple dict)
        for campaign_id, data in list(self.campaigns_store.items()):
            state = data.get("state", {})
            status = data.get("status", "unknown")
            
            # Only optimize active campaigns
            if status != "active":
                continue
            
            # Get or simulate KPIs
            if campaign_id not in self.kpi_store:
                self.kpi_store[campaign_id] = simulate_kpi_update(campaign_id)
            
            kpis = self.kpi_store[campaign_id]
            
            # Run optimization (this modifies state)
            try:
                new_state = perform_optimization(campaign_id, state, kpis)
                data["state"] = new_state
                self.campaigns_store[campaign_id] = data
                print(f"[Monitor] Optimization executed for campaign {campaign_id}")
            except Exception as e:
                print(f"[Monitor] Optimization failed for {campaign_id}: {e}")