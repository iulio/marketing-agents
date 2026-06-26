# app/main.py - COMPLETE FIX

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
from .models import OnboardRequest, CampaignResponse
from .agents import graph, AgencyState
from .storage import save_campaign_state, get_all_campaigns, get_client
from .analyst import PerformanceMonitor
from .auth import create_default_admin

# ================================================================
# IN-MEMORY STORAGE
# ================================================================
campaigns = {}
kpi_store = {}

# ================================================================
# PERFORMANCE MONITOR
# ================================================================
monitor = PerformanceMonitor(campaigns, kpi_store)

# ================================================================
# LIFESPAN MANAGER (Replaces on_event)
# ================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP LOGIC ---
    print("[Startup] Initializing application...")
    
    # Create default admin if none exists
    try:
        create_default_admin()
        print("[Startup] Admin user check completed")
    except Exception as e:
        print(f"[Startup] Admin creation warning: {e}")
    
    # Load campaigns from database
    try:
        db_campaigns = get_all_campaigns()
        for item in db_campaigns:
            campaign_id = item['campaign_id']
            campaigns[campaign_id] = {
                'state': item['state'],
                'status': item['status'],
                'thread_id': campaign_id,
                'client_name': item['state'].get('client_profile', {}).get('client_name', 'Unknown'),
                'language': item['state'].get('client_profile', {}).get('language', 'en-US'),
                'created_at': item['created_at']
            }
        print(f"[Startup] Loaded {len(db_campaigns)} campaigns from database")
    except Exception as e:
        print(f"[Startup] Campaign load warning: {e}")
    
    # Start the background performance monitor
    monitor.start()
    print("[Startup] Performance monitoring started")
    
    # --- APPLICATION RUNS HERE ---
    yield
    
    # --- SHUTDOWN LOGIC ---
    print("[Shutdown] Shutting down application...")
    monitor.stop()
    print("[Shutdown] Performance monitoring stopped")

# ================================================================
# CREATE FASTAPI APP WITH LIFESPAN
# ================================================================
app = FastAPI(
    title="Agentic Marketing Agency API",
    version="1.0.0",
    lifespan=lifespan,  # <-- This replaces @app.on_event
)

# ================================================================
# MIDDLEWARE
# ================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static UI
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

# ================================================================
# REMOVE THESE OLD DECORATORS (they're now replaced by lifespan)
# ================================================================
# @app.on_event("startup")  # <-- DELETE THIS
# async def startup_event():
#     ...

# @app.on_event("shutdown")  # <-- DELETE THIS
# async def shutdown_event():
#     ...

# ================================================================
# REST OF YOUR ENDPOINTS...
# ================================================================

@app.get("/")
def root():
    return {"status": "online", "service": "Agentic Marketing Agency"}

# ... (keep all your other endpoints unchanged)
@app.get("/api/status/agents")
def get_agent_status():
    return {
        "orchestrator": "idle",
        "research": "idle",
        "creative": "idle",
        "launch": "idle",
        "analyst": "idle"
    }

@app.post("/api/campaigns/onboard", response_model=CampaignResponse)
async def onboard_campaign(request: OnboardRequest):
    try:
        campaign_id = str(uuid.uuid4())[:8]
        thread_id = campaign_id  # use campaign_id as thread_id
        
        # Initialize state
        initial_state: AgencyState = {
            "client_profile": request.dict(),
            "market_intelligence": {},
            "creative_assets": {},
            "deployment_status": {},
            "human_feedback": {"status": "pending"},  # Start with pending
            "validation_errors": []
        }
        
        # Run the graph with checkpointer
        config = {"configurable": {"thread_id": thread_id}}
        final_state = graph.invoke(initial_state, config=config)
        
        # The graph will stop before human_review due to interrupt.
        # We store the campaign with current state.
        campaigns[campaign_id] = {
            "state": final_state,
            "thread_id": thread_id,
            "status": "pending_review",
            "client_name": request.client_name,
            "language": request.language,
            "created_at": str(uuid.uuid4())
        }
        
        # Get creative assets for response
        creatives = final_state.get("creative_assets", {})
        google_count = len(creatives.get("google_ads", []))
        meta_count = len(creatives.get("meta_ads", []))
        
        return CampaignResponse(
            campaign_id=campaign_id,
            status="pending_review",
            message=f"Campaign created. Generated {google_count} Google ads and {meta_count} Meta ads. Please review in the dashboard."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/campaigns")
def list_campaigns():
    # Return a list of campaigns for the table
    result = []
    for cid, data in campaigns.items():
        state = data["state"]
        client = state.get("client_profile", {})
        deployment = state.get("deployment_status", {})
        # Simulate CTR and other metrics for demo
        result.append({
            "campaign_id": cid,
            "campaign_name": client.get("client_name", "Unnamed"),
            "platform": "Google & Meta",
            "language": client.get("language", "en-US"),
            "budget": f"${client.get('daily_budget', 0)} / day",
            "ctr": "4.2%",  # placeholder
            "status": data.get("status", "unknown"),
            "actions": ["pause", "clone"]
        })
    return result

@app.get("/api/campaigns/{campaign_id}/creatives")
def get_creatives(campaign_id: str):
    if campaign_id not in campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    state = campaigns[campaign_id]["state"]
    creatives = state.get("creative_assets", {})
    return creatives

@app.post("/api/campaigns/{campaign_id}/approve")
async def approve_campaign(campaign_id: str):
    if campaign_id not in campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Get the stored data
    data = campaigns[campaign_id]
    thread_id = data["thread_id"]
    
    # Update human_feedback to APPROVED
    data["state"]["human_feedback"] = {"status": "APPROVED"}
    
    # Resume the graph
    config = {"configurable": {"thread_id": thread_id}}
    final_state = graph.invoke(None, config=config)  # Continue from interrupt
    
    # Update storage with final state
    data["state"] = final_state
    data["status"] = "active"
    campaigns[campaign_id] = data
    
    return {"status": "approved", "campaign_id": campaign_id, "deployment": final_state.get("deployment_status", {})}

@app.post("/api/campaigns/{campaign_id}/reject")
async def reject_campaign(campaign_id: str):
    if campaign_id not in campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Get the stored data
    data = campaigns[campaign_id]
    thread_id = data["thread_id"]
    
    # Update human_feedback to REJECTED
    data["state"]["human_feedback"] = {"status": "REJECTED"}
    
    # Resume the graph (should go back to creative)
    config = {"configurable": {"thread_id": thread_id}}
    final_state = graph.invoke(None, config=config)
    
    # Update storage with new state (creatives regenerated)
    data["state"] = final_state
    data["status"] = "pending_review"
    campaigns[campaign_id] = data
    
    return {"status": "rejected", "campaign_id": campaign_id, "message": "Regenerating creatives..."}

from .analyst import analyze_performance, simulate_kpi_update

# In-memory storage for KPIs (in production, use a database)
kpi_store = {}

@app.post("/api/campaigns/{campaign_id}/analyze")
async def analyze_campaign(campaign_id: str):
    """Triggers performance analysis for a campaign"""
    if campaign_id not in campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Get campaign data
    data = campaigns[campaign_id]
    state = data["state"]
    client = state.get("client_profile", {})
    creatives = state.get("creative_assets", {})
    
    # Get or simulate KPIs
    if campaign_id not in kpi_store:
        kpi_store[campaign_id] = simulate_kpi_update(campaign_id)
    
    kpis = kpi_store[campaign_id]
    
    # Prepare data for analysis
    analysis_data = {
        "campaign_name": client.get("client_name", "Unknown"),
        "industry": client.get("industry", "Unknown"),
        "budget": client.get("daily_budget", 0),
        "metrics": kpis,
        "creative_assets": {
            "headlines": [ad.get("headline", "") for ad in creatives.get("google_ads", [])],
            "descriptions": [ad.get("description", "") for ad in creatives.get("google_ads", [])],
            "primary_texts": [ad.get("primary_text", "") for ad in creatives.get("meta_ads", [])]
        }
    }
    
    # Run analysis
    analysis = analyze_performance(analysis_data)
    
    return {
        "campaign_id": campaign_id,
        "kpis": kpis,
        "analysis": analysis
    }

@app.get("/api/campaigns/{campaign_id}/kpis")
async def get_kpis(campaign_id: str):
    """Get current KPIs for a campaign"""
    if campaign_id not in kpi_store:
        kpi_store[campaign_id] = simulate_kpi_update(campaign_id)
    return kpi_store[campaign_id]