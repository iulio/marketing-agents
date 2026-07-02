# app/main.py - MAIN APPLICATION
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request , Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
from typing import Dict, Any

from .models import OnboardRequest, CampaignResponse
from .agents import graph, AgencyState
from .storage import save_campaign_state, get_all_campaigns, get_client, get_client_campaigns, delete_client
from .analyst import PerformanceMonitor, run_immediate_optimization, fetch_real_kpis, refresh_kpis
from .auth import create_default_admin, generate_token, verify_user, get_user_by_email
from .middleware import require_role
from .kpi_fetcher import KPIFetcher
from pydantic import BaseModel

# ================================================================
# IN-MEMORY STORAGE
# ================================================================
campaigns: Dict[str, Any] = {}
kpi_store: Dict[str, Any] = {}
monitor = PerformanceMonitor(campaigns, kpi_store)

# ================================================================
# LIFESPAN MANAGER
# ================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Startup] Initializing application...")
    
    try:
        create_default_admin()
        print("[Startup] Admin user check completed")
    except Exception as e:
        print(f"[Startup] Admin creation warning: {e}")
    
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
    
    monitor.start()
    print("[Startup] Performance monitoring started")
    
    yield
    
    print("[Shutdown] Shutting down...")
    monitor.stop()
    print("[Shutdown] Performance monitoring stopped")

# ================================================================
# FASTAPI APP
# ================================================================
app = FastAPI(
    title="Agentic Marketing Agency API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static UI

# ================================================================
# ROOT ENDPOINT
# ================================================================
# @app.get("/")
# def root():
#     return {"status": "online", "service": "Agentic Marketing Agency"}

# ================================================================
# AUTHENTICATION ENDPOINTS
# ================================================================

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/api/auth/login")
async def login(login_data: LoginRequest):
    user = verify_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = generate_token(user['id'], user['email'], user['role'], user.get('client_id'))
    return {
        "token": token,
        "user": {
            "id": user['id'],
            "email": user['email'],
            "full_name": user['full_name'],
            "role": user['role'],
            "client_id": user.get('client_id')
        }
    }




# ================================================================
# CLIENT MANAGEMENT ENDPOINTS
# ================================================================
from .storage import create_client, get_all_clients, get_client, get_users_by_client, create_user

@app.post("/api/clients")
@require_role(["admin"])
async def create_new_client(request: Request, client_data: dict):
    client_id = create_client(client_data)
    return {"client_id": client_id, "message": "Client created"}

@app.get("/api/clients")
@require_role(["admin"])
async def list_clients(request: Request):
    return {"clients": get_all_clients()}

@app.get("/api/clients/{client_id}")
@require_role(["admin", "client_manager", "client_viewer"])
async def get_client_details(request: Request, client_id: str):
    user = request.state.user
    if user['role'] != 'admin' and user.get('client_id') != client_id:
        raise HTTPException(status_code=403, detail="Access denied")
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"client": client}

@app.get("/api/clients/{client_id}/campaigns")
@require_role(["admin", "client_manager", "client_viewer"])
async def list_client_campaigns(request: Request, client_id: str):
    user = request.state.user
    if user['role'] != 'admin' and user.get('client_id') != client_id:
        raise HTTPException(status_code=403, detail="Access denied")
    campaigns_data = get_client_campaigns(client_id)
    result = []
    for c in campaigns_data:
        state = c['state']
        client_profile = state.get('client_profile', {})
        result.append({
            "campaign_id": c['campaign_id'],
            "campaign_name": client_profile.get('client_name', 'Unnamed'),
            "status": c['status'],
            "budget": client_profile.get('daily_budget', 0),
            "language": client_profile.get('language', 'en-US'),
            "created_at": c['created_at']
        })
    return {"campaigns": result}

@app.delete("/api/clients/{client_id}")
@require_role(["admin"])
async def delete_client_endpoint(request: Request, client_id: str):
    """Delete a client and all their associated campaigns."""
    user = request.state.user
    if user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Access denied")
    
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    success = delete_client(client_id)
    if success:
        return {"message": f"Client '{client_id}' deleted successfully", "client_id": client_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete client")

# ================================================================
# CAMPAIGN ENDPOINTS
# ================================================================
@app.post("/api/campaigns/onboard")
async def onboard_campaign(
    request: Request,
    campaign_data: OnboardRequest,
    client_id: str = Query(None, description="Client ID (optional, creates default if not provided)")
):
    """
    Create a new campaign.
    - If client_id is provided, use that client.
    - If not, create a default client automatically.
    """
    try:
        # If no client_id, create a default client
        if not client_id:
            # Check if user is authenticated
            user = getattr(request.state, 'user', None)
            if user and user.get('role') in ['admin', 'client_manager']:
                # Create a default client for the admin
                client_data = {
                    "name": campaign_data.client_name or "Default Client",
                    "industry": campaign_data.industry or "General",
                    "website": campaign_data.website_url or "",
                }
                client_id = create_client(client_data)
                print(f"[Onboard] Created default client: {client_id}")
            else:
                raise HTTPException(status_code=400, detail="client_id required for non-admin users")
        
        # Verify client exists
        if not get_client(client_id):
            raise HTTPException(status_code=404, detail=f"Client '{client_id}' not found")
        
        # ... rest of your existing code (create campaign, run agents, etc.)
        # (Keep the rest of the function exactly as you have it)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Onboard] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/campaigns")
def list_campaigns():
    result = []
    for cid, data in campaigns.items():
        state = data.get("state", {})
        client = state.get("client_profile", {})
        result.append({
            "campaign_id": cid,
            "campaign_name": client.get("client_name", "Unnamed"),
            "platform": "Google & Meta",
            "language": client.get("language", "en-US"),
            "budget": f"${client.get('daily_budget', 0)} / day",
            "ctr": "4.2%",
            "status": data.get("status", "unknown")
        })
    return result

@app.get("/api/campaigns/{campaign_id}/creatives")
def get_creatives(campaign_id: str):
    if campaign_id not in campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    state = campaigns[campaign_id]["state"]
    return state.get("creative_assets", {})

@app.post("/api/campaigns/{campaign_id}/approve")
async def approve_campaign(campaign_id: str):
    if campaign_id not in campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    data = campaigns[campaign_id]
    thread_id = data["thread_id"]
    data["state"]["human_feedback"] = {"status": "APPROVED"}
    
    config = {"configurable": {"thread_id": thread_id}}
    final_state = graph.invoke(None, config=config)
    
    data["state"] = final_state
    data["status"] = "active"
    campaigns[campaign_id] = data
    
    save_campaign_state(campaign_id, final_state, "active", data.get("client_id"))
    
    return {"status": "approved", "campaign_id": campaign_id}

@app.post("/api/campaigns/{campaign_id}/reject")
async def reject_campaign(campaign_id: str):
    if campaign_id not in campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    data = campaigns[campaign_id]
    thread_id = data["thread_id"]
    data["state"]["human_feedback"] = {"status": "REJECTED"}
    
    config = {"configurable": {"thread_id": thread_id}}
    final_state = graph.invoke(None, config=config)
    
    data["state"] = final_state
    data["status"] = "pending_review"
    campaigns[campaign_id] = data
    
    save_campaign_state(campaign_id, final_state, "pending_review", data.get("client_id"))
    
    return {"status": "rejected", "campaign_id": campaign_id}

# ================================================================
# OPTIMIZATION ENDPOINTS
# ================================================================
@app.post("/api/campaigns/{campaign_id}/optimize")
async def optimize_campaign(campaign_id: str):
    if campaign_id not in campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    data = campaigns[campaign_id]
    state = data["state"]
    platform = state.get("client_profile", {}).get("platform", "auto")
    
    try:
        new_state = run_immediate_optimization(campaign_id, state, platform)
        data["state"] = new_state
        campaigns[campaign_id] = data
        return {
            "campaign_id": campaign_id,
            "analysis": new_state.get("analysis", {}),
            "actions": new_state.get("optimization_actions", []),
            "message": "Optimization completed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/campaigns/{campaign_id}/optimization-history")
async def get_optimization_history_endpoint(campaign_id: str):
    if campaign_id not in campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    from .storage import get_optimization_history
    history = get_optimization_history(campaign_id)
    return {"campaign_id": campaign_id, "history": history}

@app.get("/api/campaigns/{campaign_id}/kpis")
async def get_kpis(campaign_id: str):
    if campaign_id not in campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign_id in kpi_store:
        return kpi_store[campaign_id]
    
    platform = campaigns[campaign_id]["state"].get("client_profile", {}).get("platform", "auto")
    kpis = fetch_real_kpis(campaign_id, platform)
    if kpis:
        kpi_store[campaign_id] = kpis
    return kpis

@app.get("/api/platforms/status")
async def get_platform_status():
    from .kpi_fetcher import KPIFetcher
    fetcher = KPIFetcher()
    return {
        "google_ads": {
            "available": fetcher.google.is_available(),
            "configured": bool(os.getenv("GOOGLE_ADS_CUSTOMER_ID"))
        },
        "meta_ads": {
            "available": fetcher.meta.is_available(),
            "configured": bool(os.getenv("META_AD_ACCOUNT_ID"))
        }
    }

# ================================================================
# AGENT STATUS
# ================================================================
@app.get("/api/status/agents")
def get_agent_status():
    return {
        "orchestrator": "idle",
        "research": "idle",
        "creative": "idle",
        "launch": "idle",
        "analyst": "idle"
    }

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
