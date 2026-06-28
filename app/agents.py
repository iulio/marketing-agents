# app/agents.py
import os
import json
import warnings
from typing import TypedDict, Literal, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_community.chat_models import ChatOllama

from .industry_prompts import get_industry_template
warnings.filterwarnings("ignore", category=DeprecationWarning)

# ================================================================
# STATE DEFINITION
# ================================================================
class AgencyState(TypedDict):
    client_profile: Dict[str, Any]
    market_intelligence: Dict[str, Any]
    creative_assets: Dict[str, Any]
    deployment_status: Dict[str, Any]
    human_feedback: Dict[str, Any]
    validation_errors: list
    analysis: Dict[str, Any]
    last_optimization: str
    optimization_actions: list

# ================================================================
# LLM INITIALIZATION
# ================================================================
llm = ChatOllama(
    model="llama3.2:3b",
    base_url="http://localhost:11434",
    temperature=0.7,
)

# ================================================================
# AGENT 1: MASTER ORCHESTRATOR
# ================================================================
def orchestrator_node(state: AgencyState) -> AgencyState:
    """Breaks down client brief into sub-tasks and coordinates the workflow."""
    client = state.get("client_profile", {})
    
    prompt = f"""
    You are the Master Orchestrator of a digital marketing agency.
    Analyze this client brief and create a structured execution plan.
    
    Client: {client.get('client_name', 'Unknown')}
    Industry: {client.get('industry', 'Unknown')}
    Website: {client.get('website_url', 'Unknown')}
    Budget: ${client.get('daily_budget', 0)}/day
    Target Locations: {client.get('target_geo', [])}
    Tone: {client.get('tone_of_voice', 'Professional')}
    
    Output a JSON with:
    1. "strategy_summary": Brief 1-sentence strategy
    2. "target_audience": Primary audience description
    3. "key_benefits": 3 key selling points
    4. "recommended_channels": ["Google", "Meta", "Both"]
    """
    
    response = llm.invoke(prompt)
    print(f"[Orchestrator] LLM Response: {response.content[:100]}...")
    
    try:
        content = response.content
        start = content.find('{')
        end = content.rfind('}') + 1
        if start != -1 and end != 0:
            json_str = content[start:end]
            plan = json.loads(json_str)
        else:
            plan = self._fallback_plan()
    except:
        plan = self._fallback_plan()
    
    state["market_intelligence"] = plan
    return state

def _fallback_plan():
    return {
        "strategy_summary": "Build awareness through targeted campaigns.",
        "target_audience": "Professionals interested in technology",
        "key_benefits": ["Efficiency", "Innovation", "Scalability"],
        "recommended_channels": ["Google", "Meta"]
    }

# ================================================================
# AGENT 2: STRATEGIC MARKET RESEARCHER
# ================================================================
def researcher_node(state: AgencyState) -> AgencyState:
    """Analyzes the target market, competitors, and customer personas."""
    client = state.get("client_profile", {})
    plan = state.get("market_intelligence", {})
    
    prompt = f"""
    You are a Strategic Market Researcher. Analyze this client and provide detailed market intelligence.
    
    Client: {client.get('client_name', 'Unknown')}
    Industry: {client.get('industry', 'Unknown')}
    Strategy: {plan.get('strategy_summary', 'Unknown')}
    Target Audience: {plan.get('target_audience', 'Unknown')}
    
    Output a JSON with:
    1. "buyer_personas": Array of 2 personas with (name, age, job, pain_points, goals)
    2. "competitor_insights": Array of 2 competitors with (name, strengths, weaknesses)
    3. "keyword_clusters": Array of 5-8 high-intent keywords
    4. "market_opportunities": 3 opportunities or gaps
    """
    
    response = llm.invoke(prompt)
    print(f"[Researcher] LLM Response: {response.content[:100]}...")
    
    try:
        content = response.content
        start = content.find('{')
        end = content.rfind('}') + 1
        if start != -1 and end != 0:
            json_str = content[start:end]
            research = json.loads(json_str)
        else:
            research = _fallback_research()
    except:
        research = _fallback_research()
    
    existing = state.get("market_intelligence", {})
    existing["research"] = research
    state["market_intelligence"] = existing
    return state

def _fallback_research():
    return {
        "buyer_personas": [
            {"name": "Professional", "age": 30, "job": "Manager", "pain_points": "Time", "goals": "Results"}
        ],
        "competitor_insights": [
            {"name": "Competitor", "strengths": "Brand", "weaknesses": "Price"}
        ],
        "keyword_clusters": ["automation", "SaaS"],
        "market_opportunities": ["Organic growth"]
    }

# ================================================================
# AGENT 3: CREATIVE COPYWRITER & ASSET GENERATOR
# ================================================================
def creative_node(state: AgencyState) -> AgencyState:
    client = state.get("client_profile", {})
    market = state.get("market_intelligence", {})
    website_data = market.get("website_data", {})

    # Extract industry and objective
    industry = client.get("industry", "general")
    objective = client.get("objective", "sales")
    special_events = client.get("special_events", [])
    product_keywords = client.get("product_keywords", [])

    # Get industry template
    template = get_industry_template(industry)
    strategy_focus = template.get("strategy_focus", "")
    target_audience = template.get("target_audience", "")
    creative_angles = template.get("creative_angles", [])

    # If products were scraped, use them
    products = website_data.get("products", [])
    if products:
        product_names = ", ".join([p.get("name", "") for p in products if p.get("name")])
    else:
        product_names = ", ".join(product_keywords) if product_keywords else "our products"

    # Build the prompt
    prompt = f"""
    You are a Direct-Response Creative Director specializing in the {industry} industry.
    
    INDUSTRY TEMPLATE:
    - Strategy Focus: {strategy_focus}
    - Target Audience: {target_audience}
    - Suggested Tone: {template.get('tone_suggestions', ['Professional'])}
    - Creative Angles: {', '.join(creative_angles[:3])}
    
    CLIENT DATA:
    Client: {client.get('client_name', 'Unknown')}
    Website: {client.get('website_url', '')}
    Products: {product_names}
    Campaign Objective: {objective}
    Special Events: {', '.join(special_events) if special_events else 'None'}
    
    Generate 3 Google RSA ad variations (Headlines: max 30 chars, Descriptions: max 90 chars).
    Also generate 3 Meta ad variations (Primary Text: max 125 chars).
    Ensure the copy resonates with the target audience and highlights the unique selling points of this business.
    If special events are provided, incorporate them into the messaging.
    
    Output JSON:
    {{
        "google_ads": [
            {{"headline": "...", "description": "..."}},
            ...
        ],
        "meta_ads": [
            {{"primary_text": "..."}},
            ...
        ]
    }}
    """
    response = llm.invoke(prompt)
    print(f"[Creative] LLM Response: {response.content[:100]}...")
    
    try:
        content = response.content
        start = content.find('{')
        end = content.rfind('}') + 1
        if start != -1 and end != 0:
            json_str = content[start:end]
            creatives = json.loads(json_str)
        else:
            creatives = _fallback_creatives()
    except:
        creatives = _fallback_creatives()
    
    # Try to generate images
    try:
        from .image_gen import generate_campaign_images
        image_prompt = f"Create a professional marketing image for a {client.get('industry', 'business')} company. Target audience: {plan}."
        images = generate_campaign_images(image_prompt, num_images=2)
        creatives["images"] = images
    except Exception as e:
        print(f"[Creative] Image generation skipped: {e}")
        creatives["images"] = []
    
    state["creative_assets"] = creatives
    return state

def _fallback_creatives():
    return {
        "google_ads": [
            {"headline": "Innovative SaaS Solution", "description": "Scale your business with AI."}
        ],
        "meta_ads": [
            {"primary_text": "Join thousands of happy customers."}
        ],
        "images": []
    }

# ================================================================
# AGENT 4: HUMAN REVIEW GATE
# ================================================================
def human_review_node(state: AgencyState) -> AgencyState:
    """Human-in-the-loop gate. Pauses execution for approval."""
    feedback = state.get("human_feedback", {})
    status = feedback.get("status", "pending")
    
    if status == "APPROVED":
        print("[HumanReview] ✅ Approved! Proceeding to launch.")
    elif status == "REJECTED":
        print("[HumanReview] ❌ Rejected. Routing back to creative.")
    else:
        print("[HumanReview] ⏳ Waiting for human approval...")
        state["human_feedback"] = {"status": "APPROVED"}
    
    return state

# ================================================================
# AGENT 5: CAMPAIGN LAUNCH ENGINEER
# ================================================================
def launch_node(state: AgencyState) -> AgencyState:
    """Simulates campaign launch (or integrates with real APIs)."""
    client = state.get("client_profile", {})
    creatives = state.get("creative_assets", {})
    
    print(f"[Launch] Deploying campaign for {client.get('client_name', 'Unknown')}")
    print(f"[Launch] Google Ads: {len(creatives.get('google_ads', []))} variations")
    print(f"[Launch] Meta Ads: {len(creatives.get('meta_ads', []))} variations")
    
    state["deployment_status"] = {
        "status": "draft",
        "google_campaign_id": f"GC-{hash(str(creatives)) % 100000:05d}",
        "meta_campaign_id": f"MC-{hash(str(creatives)) % 100000:05d}",
        "message": "Campaign deployed in DRAFT mode (simulated)"
    }
    
    return state

# ================================================================
# ROUTING LOGIC
# ================================================================
def should_continue(state: AgencyState) -> Literal["launch", "creative"]:
    """Conditional routing based on human feedback."""
    feedback = state.get("human_feedback", {})
    if feedback.get("status") == "APPROVED":
        return "launch"
    return "creative"

# ================================================================
# BUILD THE GRAPH WITH CHECKPOINTER
# ================================================================
workflow = StateGraph(AgencyState)
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("researcher", researcher_node)
workflow.add_node("creative", creative_node)
workflow.add_node("human_review", human_review_node)
workflow.add_node("launch", launch_node)

workflow.set_entry_point("orchestrator")
workflow.add_edge("orchestrator", "researcher")
workflow.add_edge("researcher", "creative")
workflow.add_edge("creative", "human_review")
workflow.add_conditional_edges("human_review", should_continue, {
    "launch": "launch",
    "creative": "creative"
})
workflow.add_edge("launch", END)

# Add checkpointing for human-in-the-loop
memory = MemorySaver()
graph = workflow.compile(interrupt_before=["human_review"], checkpointer=memory)