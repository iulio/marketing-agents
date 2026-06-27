# app/ab_testing.py
import json
import random
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict

class ABTestingEngine:
    """A/B Testing and creative optimization engine"""
    
    def __init__(self):
        self.tests = {}
    
    def create_test(self, campaign_id: str, variants: List[Dict], test_duration_hours: int = 24) -> Dict:
        test_id = f"AB-{random.randint(10000, 99999)}"
        test_data = {
            "test_id": test_id,
            "campaign_id": campaign_id,
            "created_at": datetime.now().isoformat(),
            "duration_hours": test_duration_hours,
            "status": "running",
            "variants": variants,
            "results": {"winners": [], "losers": [], "statistics": {}}
        }
        self.tests[campaign_id] = test_data
        return test_data
    
    def track_performance(self, campaign_id: str, variant_id: str, metrics: Dict) -> None:
        if campaign_id not in self.tests:
            return
        test = self.tests[campaign_id]
        if "performance_history" not in test:
            test["performance_history"] = {}
        if variant_id not in test["performance_history"]:
            test["performance_history"][variant_id] = []
        test["performance_history"][variant_id].append({
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics
        })
    
    def evaluate_test(self, campaign_id: str) -> Dict:
        if campaign_id not in self.tests:
            return {"error": "No test found for this campaign"}
        test = self.tests[campaign_id]
        if test["status"] != "running":
            return {"error": "Test is not running"}
        
        start_time = datetime.fromisoformat(test["created_at"])
        elapsed = (datetime.now() - start_time).total_seconds() / 3600
        if elapsed < test["duration_hours"]:
            return {
                "status": "running",
                "remaining_hours": test["duration_hours"] - elapsed,
                "message": "Test still in progress"
            }
        
        results = []
        for idx, variant in enumerate(test["variants"]):
            variant_id = variant.get("id", f"variant_{idx}")
            history = test.get("performance_history", {}).get(variant_id, [])
            if not history:
                results.append({
                    "variant_id": variant_id,
                    "data": variant,
                    "score": 0,
                    "confidence": "low",
                    "status": "insufficient_data"
                })
                continue
            
            total_clicks = sum(h["metrics"].get("clicks", 0) for h in history)
            total_impressions = sum(h["metrics"].get("impressions", 0) for h in history)
            if total_impressions == 0:
                score = 0
                confidence = "low"
            else:
                ctr = total_clicks / total_impressions
                score = ctr * 100
                confidence = "high" if total_impressions > 1000 else "medium" if total_impressions > 100 else "low"
            
            results.append({
                "variant_id": variant_id,
                "data": variant,
                "score": score,
                "ctr": round(score, 2),
                "confidence": confidence,
                "status": "success" if confidence in ["high", "medium"] else "needs_more_data"
            })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        winners = [r for r in results if r["score"] > 0 and r["confidence"] in ["high", "medium"]][:2]
        losers = [r for r in results if r["score"] > 0 and r["confidence"] in ["high", "medium"]][2:]
        
        test["results"]["winners"] = winners
        test["results"]["losers"] = losers
        test["results"]["all_variants"] = results
        test["status"] = "completed"
        test["completed_at"] = datetime.now().isoformat()
        
        return {
            "status": "completed",
            "winners": winners,
            "losers": losers,
            "all_variants": results,
            "recommendation": self._generate_recommendation(winners, losers)
        }
    
    def _generate_recommendation(self, winners: List, losers: List) -> str:
        if not winners:
            return "Insufficient data. Continue running the test."
        if len(winners) == 1:
            return f"Promote variant '{winners[0]['data'].get('name', 'Variant')}' as the winner. It performed best with {winners[0]['ctr']:.2f}% CTR."
        return "Both variants performed well. Consider A/B testing against a new challenger variant."