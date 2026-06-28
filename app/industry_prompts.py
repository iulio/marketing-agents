# app/industry_prompts.py

INDUSTRY_TEMPLATES = {
    "flower_shop": {
        "strategy_focus": "Emphasize the beauty, freshness, and emotional impact of flowers. Highlight special occasions, gifting, and local delivery.",
        "target_audience": "Adults 25-55, gift-givers, event planners, and couples.",
        "tone_suggestions": ["Romantic", "Warm", "Elegant", "Urgent (for holidays)"],
        "visual_style": "Vibrant colors, high-contrast floral arrangements, soft lighting, lifestyle shots of happy recipients.",
        "creative_angles": [
            "Surprise your loved one with a beautiful bouquet.",
            "Fresh flowers for every occasion – delivered today.",
            "Create unforgettable moments with our curated arrangements.",
            "Valentine’s Day special – order now for early delivery."
        ]
    },
    "restaurant": {
        "strategy_focus": "Focus on the dining experience, taste, ambiance, and special offers. Highlight cuisine type and location.",
        "target_audience": "Local foodies, families, couples, and tourists.",
        "tone_suggestions": ["Appetizing", "Warm", "Inviting", "Exclusive"],
        "visual_style": "Close-up shots of dishes, warm lighting, cozy interior, happy diners.",
        "creative_angles": [
            "Experience the taste of [Cuisine] at our table.",
            "Book your table now and enjoy a free appetizer.",
            "Family dinner special – 20% off for groups of 4+."
        ]
    },
    "dentist": {
        "strategy_focus": "Build trust, highlight technology, and offer pain-free solutions. Emphasize professionalism and results.",
        "target_audience": "Adults 25-65, families, people with dental anxiety.",
        "tone_suggestions": ["Professional", "Caring", "Reassuring"],
        "visual_style": "Clean, bright, professional clinic images, smiling patients.",
        "creative_angles": [
            "State-of-the-art dentistry – comfortable and gentle.",
            "Your smile is our priority. Book a free consultation.",
            "Invisalign offers – transform your smile without braces."
        ]
    },
    # Add more industries: salon, gym, real estate, etc.
}

DEFAULT_TEMPLATE = {
    "strategy_focus": "Drive awareness and sales through targeted digital campaigns.",
    "target_audience": "General audience based on location and demographics.",
    "tone_suggestions": ["Professional", "Friendly"],
    "visual_style": "High-quality professional imagery.",
    "creative_angles": [
        "Discover our products – designed for you.",
        "Limited time offer – shop now.",
        "Join thousands of happy customers."
    ]
}

def get_industry_template(industry: str):
    """Return the template for a given industry, or default if not found."""
    return INDUSTRY_TEMPLATES.get(industry.lower().replace(" ", "_"), DEFAULT_TEMPLATE)