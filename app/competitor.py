import json
import random
from typing import Any, Dict, List

from .agents import get_llm_for_agent


async def get_competitor_data(domain: str, competitor_domains: List[str]) -> Dict[str, Any]:
    """Generate or simulate competitor comparison data."""
    llm = get_llm_for_agent("analyst")
    prompt = f"""
    Generate realistic marketing competitor data for {domain} and these competitors: {', '.join(competitor_domains)}.
    Include estimated monthly ad spend, CTR, keyword count, social followers, and SEO score.
    Output JSON with structure:
    {{
        "client": {{
            "domain": "{domain}",
            "ad_spend": 5000,
            "ctr": 3.2,
            "keywords": 450,
            "social_followers": 15000,
            "seo_score": 68
        }},
        "competitors": [
            {{
                "domain": "...",
                "ad_spend": 7000,
                "ctr": 2.8,
                "keywords": 600,
                "social_followers": 22000,
                "seo_score": 74
            }}
        ]
    }}
    """

    try:
        response = llm.invoke(prompt)
        content = response.content
        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end != 0:
            return json.loads(content[start:end])
        raise ValueError("No JSON returned")
    except Exception:
        return {
            "client": {
                "domain": domain,
                "ad_spend": random.randint(2000, 10000),
                "ctr": round(random.uniform(1.5, 5.0), 1),
                "keywords": random.randint(100, 800),
                "social_followers": random.randint(1000, 50000),
                "seo_score": random.randint(40, 90),
            },
            "competitors": [
                {
                    "domain": comp,
                    "ad_spend": random.randint(3000, 12000),
                    "ctr": round(random.uniform(1.0, 4.5), 1),
                    "keywords": random.randint(200, 1000),
                    "social_followers": random.randint(5000, 100000),
                    "seo_score": random.randint(50, 95),
                }
                for comp in competitor_domains
            ],
        }