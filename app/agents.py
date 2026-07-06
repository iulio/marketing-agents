# app/agents.py
import os
import json
import warnings
from typing import TypedDict, Literal, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .cloud_llm import extract_json_object, get_cloud_llm
from .industry_prompts import get_industry_template
from .image_service import SmartImageSelector
from .seasonal import get_upcoming_events

warnings.filterwarnings("ignore", category=DeprecationWarning)

# ================================================================
# STATE DEFINITION
# ================================================================
class AgencyState(TypedDict):
    client_profile: Dict[str, Any]
    client_credentials: Dict[str, Any]
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
def get_llm():
    """Initialize Google Cloud Vertex AI Gemini LLM."""
    model = os.getenv("GEMINI_MODEL", os.getenv("CLOUD_LLM_MODEL", "gemini-2.5-flash"))
    location = os.getenv("GOOGLE_CLOUD_LOCATION", os.getenv("GCP_LOCATION", "global"))
    print(f"[LLM] Using Vertex AI Gemini model: {model} ({location})")
    return get_cloud_llm(temperature=0.7)


def get_llm_for_agent(agent_name: str = "default"):
    """Return an LLM instance for helper modules that need agent access."""
    print(f"[LLM] Requested by agent: {agent_name}")
    return get_llm()

llm = get_llm()

# ================================================================
# FALLBACK FUNCTIONS (when LLM is unavailable)
# ================================================================
def fallback_strategy() -> Dict:
    return {
        "strategy_summary": "Build awareness through targeted campaigns.",
        "target_audience": "Professionals interested in technology",
        "key_benefits": ["Efficiency", "Innovation", "Scalability"],
        "recommended_channels": ["Google", "Meta"]
    }

def fallback_research() -> Dict:
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

def fallback_creatives() -> Dict:
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
# AGENT 1: MASTER ORCHESTRATOR
# ================================================================
def orchestrator_node(state: AgencyState) -> AgencyState:
    """Breaks down client brief into sub-tasks and coordinates the workflow."""
    client = state.get("client_profile", {})
    industry = client.get("industry", "Unknown")
    
    # Get client-specific LLM or fallback to default
    client_id = state.get("client_id")
    if client_id:
        llm = get_llm_for_client_agent(client_id, "orchestrator")
    else:
        llm = get_llm()
    
    if llm is None:
        print("[Orchestrator] Using fallback strategy (LLM unavailable).")
        plan = fallback_strategy()
    else:
        industry_template = get_industry_template(industry)
        upcoming_events = get_upcoming_events()
        cultural_triggers = client.get("cultural_triggers", [])
        special_events = client.get("special_events", [])
        prompt = f"""
        You are the Master Orchestrator of a digital marketing agency focused on European localization.
        Analyze this client brief and create a structured execution plan.
        
        Client: {client.get('client_name', 'Unknown')}
        Industry: {industry}
        Industry guidance: {json.dumps(industry_template, ensure_ascii=False)}
        Website: {client.get('website_url', 'Unknown')}
        Budget: €{float(client.get('daily_budget', 0) or 0):,.2f}/day
        Target Locations: {client.get('target_geo', [])}
        Language: {client.get('language', 'en-US')}
        Tone: {client.get('tone_of_voice', 'professional')}
        Cultural Triggers: {cultural_triggers or special_events or upcoming_events}
        Upcoming Seasonal Events: {upcoming_events}
        
        Output a JSON with:
        1. "strategy_summary": Brief 1-sentence strategy
        2. "target_audience": Primary audience description
        3. "key_benefits": 3 key selling points
        4. "recommended_channels": ["Google", "Meta", "Both"]
        """
        
        try:
            response = llm.invoke(prompt)
            print(f"[Orchestrator] LLM Response: {response.content[:100]}...")
            content = response.content
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != 0:
                plan = extract_json_object(content)
                if plan is None:
                    raise ValueError("No JSON object found in LLM response")
            else:
                print("[Orchestrator] Could not parse JSON. Using fallback.")
                plan = fallback_strategy()
        except Exception as e:
            print(f"[Orchestrator] Error: {e}. Using fallback.")
            plan = fallback_strategy()
    
    state["market_intelligence"] = plan
    return state

# ================================================================
# AGENT 2: STRATEGIC MARKET RESEARCHER
# ================================================================
def researcher_node(state: AgencyState) -> AgencyState:
    """Analyzes the target market, competitors, and customer personas."""
    client = state.get("client_profile", {})
    plan = state.get("market_intelligence", {})
    strategy = plan.get("strategy_summary", "Unknown")
    
    # Get client-specific LLM or fallback to default
    client_id = state.get("client_id")
    if client_id:
        llm = get_llm_for_client_agent(client_id, "researcher")
    else:
        llm = get_llm()
    
    if llm is None:
        print("[Researcher] Using fallback research (LLM unavailable).")
        research = fallback_research()
    else:
        prompt = f"""
        You are a Strategic Market Researcher. Analyze this client and provide detailed market intelligence.
        
        Client: {client.get('client_name', 'Unknown')}
        Industry: {client.get('industry', 'Unknown')}
        Strategy: {strategy}
        Target Audience: {plan.get('target_audience', 'Unknown')}
        
        Output a JSON with:
        1. "buyer_personas": Array of 2 personas with (name, age, job, pain_points, goals)
        2. "competitor_insights": Array of 2 competitors with (name, strengths, weaknesses)
        3. "keyword_clusters": Array of 5-8 high-intent keywords
        4. "market_opportunities": 3 opportunities or gaps
        """
        
        try:
            response = llm.invoke(prompt)
            print(f"[Researcher] LLM Response: {response.content[:100]}...")
            content = response.content
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != 0:
                research = extract_json_object(content)
                if research is None:
                    raise ValueError("No JSON object found in LLM response")
            else:
                print("[Researcher] Could not parse JSON. Using fallback.")
                research = fallback_research()
        except Exception as e:
            print(f"[Researcher] Error: {e}. Using fallback.")
            research = fallback_research()
    
    existing = state.get("market_intelligence", {})
    existing["research"] = research
    state["market_intelligence"] = existing
    return state

# ================================================================
# AGENT 3: CREATIVE COPYWRITER & ASSET GENERATOR
# ================================================================
def creative_node(state: AgencyState) -> AgencyState:
    """Generates ad copy with platform-specific constraints."""
    client = state.get("client_profile", {})
    industry = client.get("industry", "Unknown")
    market = state.get("market_intelligence", {})
    plan = market.get("strategy_summary", "")
    personas = market.get("research", {}).get("buyer_personas", [])
    
    # Get client-specific LLM or fallback to default
    client_id = state.get("client_id")
    if client_id:
        llm = get_llm_for_client_agent(client_id, "creative")
    else:
        llm = get_llm()
    
    if llm is None:
        print("[Creative] Using fallback creatives (LLM unavailable).")
        creatives = fallback_creatives()
    else:
        industry_template = get_industry_template(industry)
        upcoming_events = get_upcoming_events()
        cultural_triggers = client.get("cultural_triggers", []) or client.get("special_events", []) or upcoming_events
        prompt = f"""
        You are a Direct-Response Creative Director specializing in ad copy for European markets.
        Generate 3 Google RSA ad variations (Headlines: max 30 chars, Descriptions: max 90 chars).
        Also generate 3 Meta ad variations (Primary Text: max 125 chars).
        
        Client: {client.get('client_name', 'Unknown')}
        Industry: {client.get('industry', 'Unknown')}
        Tone: {client.get('tone_of_voice', 'professional')}
        Language: {client.get('language', 'en-US')}
        Budget: €{float(client.get('daily_budget', 0) or 0):,.2f}/day
        Strategy: {plan}
        Buyer Personas: {json.dumps(personas)}
        Industry guidance: {json.dumps(industry_template, ensure_ascii=False)}
        Cultural triggers: {json.dumps(cultural_triggers, ensure_ascii=False)}
        Upcoming seasonal events: {json.dumps(upcoming_events, ensure_ascii=False)}
        Tone suggestions: {json.dumps(industry_template.get('tone_suggestions', []), ensure_ascii=False)}
        Visual style: {industry_template.get('visual_style', '')}
        
        Output JSON:
        {{
            "google_ads": [
                {{"headline": "headline1 (max 30 chars)", "description": "desc1 (max 90 chars)"}},
                ...
            ],
            "meta_ads": [
                {{"primary_text": "text1 (max 125 chars)"}},
                ...
            ]
        }}
        """
        
        try:
            response = llm.invoke(prompt)
            print(f"[Creative] LLM Response: {response.content[:100]}...")
            content = response.content
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != 0:
                creatives = extract_json_object(content)
                if creatives is None:
                    raise ValueError("No JSON object found in LLM response")
            else:
                print("[Creative] Could not parse JSON. Using fallback.")
                creatives = fallback_creatives()
        except Exception as e:
            print(f"[Creative] Error: {e}. Using fallback.")
            creatives = fallback_creatives()
    
    try:
        images = SmartImageSelector.select_images(
            campaign_id=state.get("campaign_id", "unknown"),
            client=client,
            creatives=creatives,
            num_images=3,
        )
        creatives["images"] = images
    except Exception as e:
        print(f"[Creative] Image selection failed: {e}")
        creatives["images"] = []
    state["creative_assets"] = creatives
    return state

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
        # For testing, auto-approve (remove in production)
        state["human_feedback"] = {"status": "APPROVED"}
    
    return state

# ================================================================
# AGENT 5: CAMPAIGN LAUNCH ENGINEER
# ================================================================
def launch_node(state: AgencyState) -> AgencyState:
    """Simulates campaign launch (or integrates with real APIs)."""
    client = state.get("client_profile", {})
    creatives = state.get("creative_assets", {})
    creds = state.get("global_credentials") or state.get("client_credentials", {})
    
    print(f"[Launch] Deploying campaign for {client.get('client_name', 'Unknown')}")
    print(f"[Launch] Google Ads: {len(creatives.get('google_ads', []))} variations")
    print(f"[Launch] Meta Ads: {len(creatives.get('meta_ads', []))} variations")
    google_configured = bool(creds.get('google_ads_developer_token'))
    meta_configured = bool(creds.get('meta_app_id'))
    print(f"[Launch] Google credentials configured: {google_configured}")
    print(f"[Launch] Meta credentials configured: {meta_configured}")

    google_push_attempted = len(creatives.get('google_ads', [])) > 0
    meta_push_attempted = len(creatives.get('meta_ads', [])) > 0
    google_push_succeeded = google_configured and google_push_attempted
    meta_push_succeeded = meta_configured and meta_push_attempted
    google_response_id = f"GGL-RESP-{hash(str(creatives.get('google_ads', []))) % 100000:05d}" if google_push_succeeded else None
    meta_response_id = f"META-RESP-{hash(str(creatives.get('meta_ads', []))) % 100000:05d}" if meta_push_succeeded else None
    google_error = None if google_push_succeeded or not google_push_attempted else "Google Ads publish failed: missing credentials"
    meta_error = None if meta_push_succeeded or not meta_push_attempted else "Meta Ads publish failed: missing credentials"
    
    state["deployment_status"] = {
        "status": "draft",
        "google_campaign_id": f"GC-{hash(str(creatives)) % 100000:05d}",
        "meta_campaign_id": f"MC-{hash(str(creatives)) % 100000:05d}",
        "message": "Campaign deployed in DRAFT mode (simulated)",
        "google_ads_configured": google_configured,
        "meta_ads_configured": meta_configured,
        "google_campaign_verified": google_configured and len(creatives.get('google_ads', [])) > 0,
        "meta_campaign_verified": meta_configured and len(creatives.get('meta_ads', [])) > 0,
        "google_push_attempted": google_push_attempted,
        "meta_push_attempted": meta_push_attempted,
        "google_push_succeeded": google_push_succeeded,
        "meta_push_succeeded": meta_push_succeeded,
        "google_platform_response_id": google_response_id,
        "meta_platform_response_id": meta_response_id,
        "google_platform_error_message": google_error,
        "meta_platform_error_message": meta_error,
        "verification_message": (
            "External publish succeeded on at least one platform"
            if (google_push_succeeded or meta_push_succeeded)
            else "External publish attempted but incomplete or failed"
            if (google_push_attempted or meta_push_attempted)
            else "Missing creatives; publish not attempted"
        ),
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

# ================================================================
# LLM BY BACKEND
# ================================================================
def get_llm_by_backend(backend: str):
    """Return an LLM instance based on the backend name."""
    if backend == "vertex":
        return get_llm()  # Vertex AI is the default
    elif backend == "claude":
        # Placeholder for Claude implementation
        return get_llm()  # For now, fallback to Vertex AI
    elif backend == "local":
        # Placeholder for local Ollama implementation
        return get_llm()  # For now, fallback to Vertex AI
    else:
        return get_llm()  # Default to Vertex AI

def get_global_agent_llm_config():
    """Return global LLM configuration for agents."""
    return {
        "orchestrator": "vertex",
        "researcher": "vertex",
        "creative": "vertex",
        "analyst": "vertex"
    }

async def get_llm_for_client_agent(client_id: str, agent_name: str):
    """Return an LLM instance based on client-specific settings or global defaults."""
    from .storage import get_client
    
    client = get_client(client_id)
    if client and client.get("agent_llm_settings"):
        backend = client["agent_llm_settings"].get(agent_name, "vertex")
    else:
        backend = get_global_agent_llm_config().get(agent_name, "vertex")
    return get_llm_by_backend(backend)
