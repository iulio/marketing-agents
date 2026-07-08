# app/keyword_optimizer.py
import json
from typing import Any, Dict, List

from .agents import get_llm_for_agent


async def discover_keywords(
    website: str,
    industry: str,
    seed_keywords: List[str],
    location: str = "US",
    language: str = "en",
) -> Dict[str, Any]:
    """Use the LLM to discover keyword clusters, search volume estimates, and negative keyword suggestions."""
    llm = get_llm_for_agent("analyst")
    prompt = f"""
    Act as a Google Ads keyword researcher. For the website "{website}" in the "{industry}" industry,
    seed keywords: {seed_keywords}, target location: {location}, language: {language}.

    Return a JSON object with exactly these keys:
    - "keyword_clusters": a list of objects each with "theme" (str), "keywords" (list of str), "avg_monthly_searches" (int)
    - "negative_keywords": a list of strings that should be excluded
    - "match_type_recommendations": a dict with keys "broad", "phrase", "exact" each being a list of strings
    - "estimated_traffic_potential": a string like "High / Medium / Low"
    - "total_estimated_keywords": int
    """
    result = await llm.ainvoke(prompt)
    content = result.content if hasattr(result, "content") else str(result)
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        content = content.rsplit("```", 1)[0]
    return json.loads(content.strip())


async def analyze_search_terms(query_log: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze a list of search queries (each with 'query' and 'clicks') and provide optimization recommendations."""
    llm = get_llm_for_agent("analyst")
    prompt = f"""
    Analyze the following Google Ads search term report and provide optimization recommendations.
    Search terms: {json.dumps(query_log)}

    Return JSON:
    {{
        "high_performing_terms": [list of queries that perform well and should be added as keywords],
        "low_performing_terms": [list of queries that waste spend and should be added as negatives],
        "opportunities": [suggestions for new keywords based on search patterns],
        "estimated_savings": "string describing potential cost savings",
        "action_items": [list of recommended actions]
    }}
    """
    result = await llm.ainvoke(prompt)
    content = result.content if hasattr(result, "content") else str(result)
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        content = content.rsplit("```", 1)[0]
    return json.loads(content.strip())
