# app/competitor_intel.py
import json
from typing import Any, Dict, List

from .agents import get_llm_for_agent


async def fetch_competitor_ads(
    domain: str,
    competitors: List[str],
    industry: str,
    location: str = "US",
) -> Dict[str, Any]:
    """Use the LLM to simulate competitor ad intelligence — ad copy, landing pages, estimated spend."""
    llm = get_llm_for_agent("analyst")
    prompt = f"""
    Act as a competitive intelligence analyst for "{domain}" in the "{industry}" industry.
    Analyze the following competitors: {competitors}.
    Target location: {location}.

    Return a JSON object:
    {{
        "client": {{
            "domain": "{domain}",
            "estimated_monthly_spend": 5000,
            "top_ad_copy": [],
            "primary_keywords": []
        }},
        "competitors": [
            {{
                "domain": "...",
                "estimated_monthly_spend": 7000,
                "top_ad_headlines": ["headline1", "headline2"],
                "top_ad_descriptions": ["desc1"],
                "landing_page_strategy": "description of their LP approach",
                "primary_keywords": ["kw1", "kw2"],
                "estimated_ctr": 2.5,
                "strengths": ["fast checkout", "social proof"],
                "weaknesses": ["slow page load", "no retargeting"]
            }}
        ],
        "market_positioning": {{
            "pricing": "premium/mid/budget",
            "unique_selling_points": ["usp1"],
            "differentiation_opportunities": ["opportunity1"]
        }},
        "recommended_actions": ["action1", "action2"]
    }}
    """
    result = await llm.ainvoke(prompt)
    content = result.content if hasattr(result, "content") else str(result)
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        content = content.rsplit("```", 1)[0]
    return json.loads(content.strip())


async def analyze_ad_creative(ad_copy: str, competitor_ad_copy: str) -> Dict[str, Any]:
    """Compare two ad copies and provide improvement suggestions."""
    llm = get_llm_for_agent("creative")
    prompt = f"""
    Compare this ad copy:
    --- OUR AD ---
    {ad_copy}
    --- COMPETITOR AD ---
    {competitor_ad_copy}

    Return JSON:
    {{
        "our_strengths": [list],
        "competitor_strengths": [list],
        "improvement_suggestions": [list],
        "recommended_headlines": [list],
        "recommended_descriptions": [list],
        "angle_differentiation": "string"
    }}
    """
    result = await llm.ainvoke(prompt)
    content = result.content if hasattr(result, "content") else str(result)
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        content = content.rsplit("```", 1)[0]
    return json.loads(content.strip())
