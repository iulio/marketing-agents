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
            "Valentine's Day special - order now."
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
            "Family dinner special - 20% off for groups of 4+."
        ]
    },
    "dentist": {
        "strategy_focus": "Build trust, highlight technology, and offer pain-free solutions.",
        "target_audience": "Adults 25-65, families, people with dental anxiety.",
        "tone_suggestions": ["Professional", "Caring", "Reassuring"],
        "visual_style": "Clean, bright, professional clinic images.",
        "creative_angles": [
            "State-of-the-art dentistry - comfortable and gentle.",
            "Your smile is our priority. Book a free consultation.",
            "Invisalign offers - transform your smile without braces."
        ]
    },
    "credit_brokering": {
        "strategy_focus": "Build trust, highlight competitive rates, and emphasize quick approval. Focus on financial expertise and transparency.",
        "target_audience": "Adults 25-65, homeowners, business owners, and individuals seeking loans or mortgages.",
        "tone_suggestions": ["Trustworthy", "Professional", "Reassuring", "Transparent", "Authoritative"],
        "visual_style": "Clean, professional imagery. Financial charts, happy customers holding keys or documents.",
        "creative_angles": [
            "Get approved in 24 hours - competitive rates guaranteed.",
            "Your trusted credit partner. We find the best loan for you.",
            "Mortgage, car, or personal loan. We handle the paperwork.",
            "No hidden fees - transparent lending since 2010."
        ]
    },
    "insurance": {
        "strategy_focus": "Emphasize protection, peace of mind, and value for money. Highlight coverage options and claims support.",
        "target_audience": "Adults 25-65, homeowners, drivers, and families.",
        "tone_suggestions": ["Caring", "Reassuring", "Professional", "Straightforward", "Empathetic"],
        "visual_style": "Warm, reassuring imagery. Families, homes, and cars.",
        "creative_angles": [
            "Protect what matters most. Get a free quote today.",
            "Insurance that cares. 24/7 claims support.",
            "Bundle your home and car - save up to 25%.",
            "Peace of mind starts here. Coverage you can trust."
        ]
    },
    "real_estate": {
        "strategy_focus": "Highlight prime properties, expertise, and market knowledge. Emphasize local knowledge and customer satisfaction.",
        "target_audience": "Home buyers, sellers, and investors aged 25-65.",
        "tone_suggestions": ["Professional", "Knowledgeable", "Trustworthy", "Luxury", "Inspirational"],
        "visual_style": "High-quality property photos, modern interiors, local landmarks.",
        "creative_angles": [
            "Find your dream home with local experts.",
            "Sell your property fast - market your home today.",
            "Investment properties with high ROI.",
            "Luxury living starts here. Exclusive listings available."
        ]
    },
    "financial_advisory": {
        "strategy_focus": "Build trust, highlight expertise, and emphasize personalized financial planning.",
        "target_audience": "Adults 30-65, business owners, retirees, and high-net-worth individuals.",
        "tone_suggestions": ["Professional", "Trustworthy", "Authoritative", "Empathetic"],
        "visual_style": "Clean, professional imagery. Financial charts, handshake shots.",
        "creative_angles": [
            "Plan your future with confidence. Book a free consultation.",
            "Expert financial advice tailored to your goals.",
            "Retirement planning - secure your tomorrow today.",
            "We make complex finances simple."
        ]
    },
}

DEFAULT_TEMPLATE = {
    "strategy_focus": "Drive awareness and sales through targeted campaigns.",
    "target_audience": "General audience based on location.",
    "tone_suggestions": ["Professional", "Friendly"],
    "visual_style": "High-quality professional imagery.",
    "creative_angles": [
        "Discover our products - designed for you.",
        "Limited time offer - shop now.",
        "Join thousands of happy customers."
    ]
}

def get_industry_template(industry: str):
    if not industry:
        return DEFAULT_TEMPLATE
    return INDUSTRY_TEMPLATES.get(industry.lower().replace(" ", "_"), DEFAULT_TEMPLATE)