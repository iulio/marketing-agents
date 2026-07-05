import json
from typing import Any, Dict

from .agents import get_llm_for_agent


async def generate_proposal(client_info: Dict[str, Any], audit_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a proposal from audit and client context."""
    llm = get_llm_for_agent("orchestrator")
    prompt = f"""
    You are a marketing consultant. Generate a professional proposal for the following client.

    Client: {client_info.get('name', 'Unknown')}
    Website: {client_info.get('website', '')}
    Industry: {client_info.get('industry', '')}

    Audit Summary:
    - SEO Score: {audit_data.get('seo_score', 'N/A')}/100
    - Ads Opportunity: {audit_data.get('ads_opportunity', 'N/A')}
    - Social Presence: {audit_data.get('social_presence', 'N/A')}
    - Top Recommendations: {', '.join([r.get('text', '') for r in audit_data.get('recommendations', [])[:3]])}

    Generate a structured proposal with:
    1. Executive Summary
    2. Current Situation
    3. Proposed Strategy
    4. Package Options (Starter, Pro, Enterprise with pricing)
    5. Timeline
    6. Expected Results

    Output JSON with fields: summary, current_situation, strategy, packages, timeline, expected_results
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
            "summary": "We can help you grow through AI-driven marketing.",
            "current_situation": "Your website has good fundamentals but lacks a fully structured acquisition strategy.",
            "strategy": "We will improve SEO, launch targeted Google and Meta campaigns, and strengthen content conversion paths.",
            "packages": [
                {"name": "Starter", "price": 499, "features": ["1 campaign", "basic reporting"]},
                {"name": "Pro", "price": 999, "features": ["3 campaigns", "advanced analytics"]},
                {"name": "Enterprise", "price": 2499, "features": ["Unlimited campaigns", "white-label support"]},
            ],
            "timeline": "30 days",
            "expected_results": "20% increase in leads within 3 months.",
        }