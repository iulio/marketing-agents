# app/industry_prompts.py

INDUSTRY_TEMPLATES = {
    "flower_shop": {
        "strategy_focus": "Emphasize beauty, freshness, and emotional impact.",
        "target_audience": "Adults 25-55, gift-givers, event planners.",
        "tone_suggestions": ["Romantic", "Warm", "Elegant"],
        "visual_style": "Vibrant colors, floral arrangements, lifestyle shots.",
        "creative_angles": [
            "Surprise your loved one with a beautiful bouquet.",
            "Fresh flowers delivered today.",
            "Valentine's Day special – order now."
        ]
    },
    "restaurant": {
        "strategy_focus": "Focus on dining experience, taste, and ambiance.",
        "target_audience": "Local foodies, families, couples.",
        "tone_suggestions": ["Appetizing", "Warm", "Inviting"],
        "visual_style": "Close-up shots of dishes, warm lighting.",
        "creative_angles": [
            "Experience the taste of [Cuisine].",
            "Book your table now and enjoy a free appetizer.",
            "Family dinner special – 20% off for groups of 4+."
        ]
    },
    "dentist": {
        "strategy_focus": "Build trust, highlight technology, and offer pain-free solutions.",
        "target_audience": "Adults 25-65, families, people with dental anxiety.",
        "tone_suggestions": ["Professional", "Caring", "Reassuring"],
        "visual_style": "Clean, bright, professional clinic images.",
        "creative_angles": [
            "State-of-the-art dentistry – comfortable and gentle.",
            "Your smile is our priority. Book a free consultation.",
            "Invisalign offers – transform your smile without braces."
        ]
    },
}

DEFAULT_TEMPLATE = {
    "strategy_focus": "Drive awareness and sales through targeted campaigns.",
    "target_audience": "General audience based on location.",
    "tone_suggestions": ["Professional", "Friendly"],
    "visual_style": "High-quality professional imagery.",
    "creative_angles": [
        "Discover our products – designed for you.",
        "Limited time offer – shop now.",
        "Join thousands of happy customers."
    ]
}

def get_industry_template(industry: str):
    if not industry:
        return DEFAULT_TEMPLATE
    return INDUSTRY_TEMPLATES.get(industry.lower().replace(" ", "_"), DEFAULT_TEMPLATE)