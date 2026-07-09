import json
import os
from typing import Dict, Any, Optional

BENCHMARK_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "benchmarks.json")

def load_benchmarks() -> Dict[str, Dict]:
    if os.path.exists(BENCHMARK_FILE):
        with open(BENCHMARK_FILE, "r") as f:
            return json.load(f)
    return {}

def get_benchmarks_for_industry(industry: str) -> Optional[Dict]:
    benchmarks = load_benchmarks()
    industry_key = industry.lower().replace(" ", "_")
    if industry_key in benchmarks:
        return benchmarks[industry_key]
    for key, value in benchmarks.items():
        if value.get("name", "").lower() == industry.lower():
            return value
    return benchmarks.get("general")

def compare_campaign_to_benchmark(campaign_metrics: Dict, industry: str) -> Dict:
    benchmark = get_benchmarks_for_industry(industry)
    if not benchmark:
        return {
            "industry": industry,
            "available": False,
            "message": "No benchmark data available for this industry"
        }

    comparison = {
        "industry": industry,
        "benchmark": benchmark,
        "campaign": {},
        "comparison": {},
        "available": True
    }

    metrics = ["ctr", "cpc", "roas", "conversion_rate"]
    for metric in metrics:
        campaign_value = campaign_metrics.get(metric, 0)
        benchmark_value = benchmark.get(metric, 0)

        comparison["campaign"][metric] = campaign_value
        comparison["comparison"][metric] = {
            "value": campaign_value,
            "benchmark": benchmark_value,
            "diff": campaign_value - benchmark_value,
            "percentage_diff": (campaign_value - benchmark_value) / benchmark_value * 100 if benchmark_value > 0 else 0,
            "status": (
                "excellent" if (campaign_value > benchmark_value * 1.2 if metric != "cpc" else campaign_value < benchmark_value * 0.8) else
                "good" if (campaign_value > benchmark_value * 1.05 if metric != "cpc" else campaign_value < benchmark_value * 0.95) else
                "average"
            )
        }

    return comparison
