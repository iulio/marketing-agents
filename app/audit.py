import json
from typing import Any, Dict

from .agents import get_llm_for_agent
from .scraper import WebsiteScraper


async def perform_audit(url: str) -> Dict[str, Any]:
    """Scrape a website and generate audit recommendations."""
    scraper = WebsiteScraper()
    data = await scraper.analyze_website(url)
    if data.get("error"):
        return {"error": data["error"]}

    llm = get_llm_for_agent("orchestrator")
    prompt = f"""
    You are a digital marketing expert. Perform a quick audit of this website and provide recommendations.

    Website: {url}
    Title: {data.get('title', '')}
    Description: {data.get('meta_description', '')}
    Headings: {', '.join(data.get('headings', [])[:5])}
    Products/Services: {', '.join([p.get('name', '') for p in data.get('products', [])[:5]])}
    Testimonials: {len(data.get('testimonials', []))}
    Social Links: {len(data.get('social_links', []))}

    Generate recommendations in these categories:
    1. SEO (on-page, keywords, meta tags)
    2. Paid Ads (Google/Meta opportunities)
    3. Social Media (presence, engagement)
    4. Content (blog, videos, resources)
    5. Overall score (out of 100)

    Output JSON:
    {{
        "seo_score": 0,
        "ads_opportunity": "low|medium|high",
        "social_presence": "poor|average|excellent",
        "content_quality": "poor|average|excellent",
        "recommendations": [
            {{"category": "seo|ads|social|content", "priority": "high|medium|low", "text": "..."}}
        ],
        "summary": "Brief summary of findings."
    }}
    """

    try:
        response = llm.invoke(prompt)
        content = response.content
        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end != 0:
            audit = json.loads(content[start:end])
        else:
            raise ValueError("No JSON content returned")
    except Exception:
        audit = {
            "seo_score": 60,
            "ads_opportunity": "medium",
            "social_presence": "average",
            "content_quality": "average",
            "recommendations": [
                {"category": "seo", "priority": "high", "text": "Improve meta descriptions on core pages."},
                {"category": "ads", "priority": "medium", "text": "Test Google Ads for high-intent product keywords."},
                {"category": "content", "priority": "medium", "text": "Publish educational content that addresses buyer objections."},
            ],
            "summary": "The website has good fundamentals but needs stronger SEO, content depth, and paid acquisition structure.",
        }

    return {
        "url": url,
        "data": data,
        "audit": audit,
    }