# app/social_generator.py
import json
from typing import Any, Dict, List, Optional

from .agents import get_llm_for_agent


async def generate_social_posts(
    campaign_description: str,
    platforms: List[str],
    tone: str = "professional",
    target_audience: str = "",
    post_count: int = 3,
    include_hashtags: bool = True,
    include_cta: bool = True,
) -> Dict[str, Any]:
    """Generate social media posts for specified platforms."""
    llm = get_llm_for_agent("creative")
    prompt = f"""
    Generate {post_count} social media post(s) for each of these platforms: {platforms}.
    Campaign description: "{campaign_description}"
    Tone: {tone}
    Target audience: {target_audience or "general"}
    Include hashtags: {include_hashtags}
    Include call-to-action: {include_cta}

    Return a JSON object with platform names as keys:
    {{
        "facebook": [
            {{"post_text": "...", "hashtags": ["#tag"], "cta": "..."}}
        ],
        "linkedin": [...],
        "twitter": [...],
        "instagram": [
            {{"post_text": "...", "hashtags": ["#tag"], "cta": "...", "image_description": "..."}}
        ]
    }}
    Include only the platforms that were requested. For instagram include an image_description field.
    """
    result = await llm.ainvoke(prompt)
    content = result.content if hasattr(result, "content") else str(result)
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        content = content.rsplit("```", 1)[0]
    return json.loads(content.strip())


async def generate_post_variants(
    base_post: str,
    platform: str,
    variations: int = 3,
) -> List[Dict[str, str]]:
    """Generate A/B test variants of a social post."""
    llm = get_llm_for_agent("creative")
    prompt = f"""
    Take this social media post for {platform} and generate {variations} distinct A/B test variants:

    "{base_post}"

    Return a JSON array of objects:
    [
        {{"variant": "A", "post_text": "...", "hook": "...", "cta": "...", "reasoning": "why this variant works"}},
        ...
    ]
    """
    result = await llm.ainvoke(prompt)
    content = result.content if hasattr(result, "content") else str(result)
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        content = content.rsplit("```", 1)[0]
    return json.loads(content.strip())
