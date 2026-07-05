# app/main.py - MAIN APPLICATION
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request , Query, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
from typing import Dict, Any

from .models import OnboardRequest, CampaignResponse
from .agents import graph, AgencyState
from .storage import save_campaign_state, get_all_campaigns, get_client, get_client_campaigns, delete_client, delete_campaign
from .analytics import generate_daily_metrics, aggregate_metrics
from .scheduler import CampaignScheduler
from .analyst import PerformanceMonitor, run_immediate_optimization, fetch_real_kpis, refresh_kpis
from .auth import create_default_admin, generate_token, verify_user, get_user_by_email
from .middleware import require_role

from .analytics import generate_daily_metrics, aggregate_metrics, get_performance_trend

from .kpi_fetcher import KPIFetcher
from pydantic import BaseModel

# ================================================================
# IN-MEMORY STORAGE
# ================================================================
campaigns: Dict[str, Any] = {}
kpi_store: Dict[str, Any] = {}
monitor = PerformanceMonitor(campaigns, kpi_store)
scheduler = CampaignScheduler()

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
                'client_id': item.get('client_id'),
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

@app.get("/healthz")
def healthz():
    return {"status": "online", "service": "Agentic Marketing Agency"}

@app.get("/api/healthz")
def api_healthz():
    return {"status": "online", "service": "Agentic Marketing Agency"}

# ================================================================
# AUTHENTICATION ENDPOINTS
# ================================================================

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/api/auth/login")
async def login(
    login_data: LoginRequest | None = None,
    email: str | None = Query(None),
    password: str | None = Query(None),
):
    if login_data:
        email = login_data.email
        password = login_data.password
    if not email or not password:
        raise HTTPException(status_code=422, detail="Email and password are required")

    user = verify_user(email, password)
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




VALID_CLIENT_STATUSES = {"active", "inactive", "pending", "suspended", "archived"}

# ================================================================
# CLIENT MANAGEMENT ENDPOINTS
# ================================================================
from .storage import create_client, get_all_clients, get_client, get_users_by_client, create_user, update_client

@app.post("/api/clients")
@require_role(["admin"])
async def create_new_client(request: Request, client_data: dict):
    if not str(client_data.get("name", "")).strip():
        raise HTTPException(status_code=422, detail="Client name is required")
    if client_data.get("platform_status", "inactive") not in VALID_CLIENT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid platform_status")
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


@app.patch("/api/clients/{client_id}")
@require_role(["admin"])
async def update_client_endpoint(request: Request, client_id: str, updates: dict):
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if "platform_status" in updates and updates["platform_status"] not in VALID_CLIENT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid platform_status")
    if "name" in updates and not str(updates["name"]).strip():
        raise HTTPException(status_code=422, detail="Client name is required")
    success = update_client(client_id, updates)
    if not success:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    return {"message": "Client updated", "client": get_client(client_id)}

@app.patch("/api/clients/{client_id}/status")
@require_role(["admin", "client_manager"])
async def update_client_status_endpoint(request: Request, client_id: str, status_data: dict):
    user = request.state.user
    if user["role"] != "admin" and user.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Access denied")
    new_status = status_data.get("platform_status")
    if new_status not in VALID_CLIENT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    update_client(client_id, {"platform_status": new_status})
    return {"message": f"Status updated to {new_status}", "platform_status": new_status}

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
@require_role(["admin", "client_manager"])
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
                    "platform_status": "active",
                }
                client_id = create_client(client_data)
                print(f"[Onboard] Created default client: {client_id}")
            else:
                raise HTTPException(status_code=400, detail="client_id required for non-admin users")
        
        # Verify client exists and is allowed to create campaigns
        client = get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail=f"Client '{client_id}' not found")
        if client.get("platform_status") in {"inactive", "suspended"}:
            raise HTTPException(
                status_code=403,
                detail=f"Client platform status is {client.get('platform_status')}; campaign orchestration is disabled",
            )
        campaign_id = str(uuid.uuid4())[:8]
        initial_state = {
            "client_profile": campaign_data.model_dump(mode="json"),
            "market_intelligence": {},
            "creative_assets": {},
            "deployment_status": {},
            "human_feedback": {},
            "validation_errors": [],
            "analysis": {},
            "last_optimization": "",
            "optimization_actions": [],
        }

        config = {"configurable": {"thread_id": campaign_id}}
        final_state = graph.invoke(initial_state, config=config)
        status = "pending_review"

        campaigns[campaign_id] = {
            "state": final_state,
            "status": status,
            "thread_id": campaign_id,
            "client_id": client_id,
            "client_name": campaign_data.client_name,
            "language": campaign_data.language.value,
            "created_at": None,
        }
        save_campaign_state(campaign_id, final_state, status, client_id)

        return {
            "campaign_id": campaign_id,
            "status": status,
            "message": "Campaign created and ready for review",
        }

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
            "budget": float(client.get("daily_budget", 0) or 0),
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

@app.delete("/api/campaigns/{campaign_id}")
@require_role(["admin", "client_manager"])
async def delete_campaign_endpoint(request: Request, campaign_id: str):
    """Delete a campaign and its associated data."""
    # Check if campaign exists in memory or database
    if campaign_id not in campaigns:
        # Try to get from database
        from .storage import get_client_campaigns
        try:
            client = request.state.user
            if client['role'] != 'admin':
                raise HTTPException(status_code=403, detail="Access denied")
            
            all_campaigns = get_all_campaigns()
            db_campaign_found = any(c['campaign_id'] == campaign_id for c in all_campaigns)
            
            if not db_campaign_found:
                raise HTTPException(status_code=404, detail="Campaign not found in database")
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))
    
    # Remove from memory if it exists there
    if campaign_id in campaigns:
        del campaigns[campaign_id]
    
    # Remove from database
    from .storage import delete_campaign
    success = delete_campaign(campaign_id)
    if not success:
        raise HTTPException(status_code=404, detail="Campaign not found in database")
    
    return {"message": f"Campaign {campaign_id} deleted successfully"}

@app.get("/api/campaigns/{campaign_id}/report")
async def get_campaign_report(campaign_id: str):
    """Generate and download a PDF report for the campaign."""
    if campaign_id not in campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    data = campaigns[campaign_id]
    state = data["state"]
    client_profile = state.get("client_profile", {})
    
    # Get campaign metrics
    kpis = fetch_real_kpis(campaign_id, client_profile.get("platform", "auto"))
    if not kpis:
        kpis = {
            "impressions": 0,
            "clicks": 0,
            "ctr": 0,
            "cpc": 0.0,
            "conversions": 0,
            "roas": 0.0,
            "cost": 0.0
        }
    
    # Get analysis (use last optimization or generate default)
    from .storage import get_optimization_history
    history = get_optimization_history(campaign_id, limit=1)
    if history:
        analysis = {"summary": history[0].get("action_description", ""), "recommendations": []}
    else:
        analysis = {
            "summary": "Campaign performing within expected parameters.",
            "recommendations": [],
            "creative_feedback": None,
            "score": 75
        }
    
    # Generate PDF report
    from .reporting import ReportGenerator
    generator = ReportGenerator()
    pdf_bytes = generator.generate_report(
        campaign_data={"client_name": client_profile.get("client_name", "Unnamed Campaign")},
        metrics=kpis,
        analysis=analysis
    )
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={campaign_id}_report.pdf"}
    )

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

@app.get("/api/client-dashboard")
@require_role(["admin", "client_manager", "client_viewer"])
async def get_client_dashboard(request: Request):
    user = request.state.user
    client_id = user.get("client_id")
    if not client_id:
        raise HTTPException(status_code=403, detail="Client dashboard is only available for users linked to a client")

    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    campaigns_data = get_client_campaigns(client_id)
    campaign_rows = []
    total_spend = 0.0
    active_campaigns = 0
    pending_campaigns = 0

    for campaign in campaigns_data:
        state = campaign.get("state", {}) or {}
        profile = state.get("client_profile", {}) or {}
        creatives = state.get("creative_assets", {}) or {}
        kpis = kpi_store.get(campaign["campaign_id"], {})
        spend = float(kpis.get("cost") or kpis.get("total_spend") or 0)
        total_spend += spend

        if campaign.get("status") == "active":
            active_campaigns += 1
        if campaign.get("status") == "pending_review":
            pending_campaigns += 1

        campaign_rows.append({
            "campaign_id": campaign["campaign_id"],
            "name": profile.get("client_name") or campaign.get("campaign_id", "Unnamed"),
            "status": campaign.get("status", "unknown"),
            "budget": float(profile.get("daily_budget", 0) or 0),
            "creatives": {
                "google_ads": len(creatives.get("google_ads", [])),
                "meta_ads": len(creatives.get("meta_ads", [])),
                "images": len(creatives.get("images", [])),
            },
        })

    return {
        "client_info": client,
        "summary": {
            "total_campaigns": len(campaign_rows),
            "active_campaigns": active_campaigns,
            "pending_campaigns": pending_campaigns,
            "total_spend": round(total_spend, 2),
        },
        "campaigns": campaign_rows,
    }

@app.get("/api/status/agents")
def get_agent_status():
    return {
        "orchestrator": "idle",
        "research": "idle",
        "creative": "idle",
        "launch": "idle",
        "analyst": "idle"
    }


# ================================================================
# ANALYTICS ENDPOINTS
# ================================================================
@app.get("/api/analytics/{campaign_id}")
async def get_analytics(campaign_id: str, days: int = Query(30, ge=1, le=90)):
    """Get analytics data for a campaign."""
    if campaign_id not in campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Generate daily metrics (simulated for now, can use real API later)
    daily_data = generate_daily_metrics(campaign_id, days)
    
    # Get current KPIs from memory
    state = campaigns[campaign_id]["state"]
    deployment = state.get("deployment_status", {})
    
    return {
        "campaign_id": campaign_id,
        "daily": daily_data,
        "summary": {
            "status": campaigns[campaign_id].get("status", "unknown"),
            "created_at": campaigns[campaign_id].get("created_at"),
            "total_spend": sum(d["spend"] for d in daily_data),
            "avg_ctr": round(sum(d["ctr"] for d in daily_data) / len(daily_data), 2) if daily_data else 0,
            "trend": get_performance_trend(daily_data, "impressions")
        }
    }

@app.get("/api/analytics/all")
async def get_all_analytics():
    """Get aggregated analytics for all campaigns."""
    all_campaigns = []
    for cid, data in campaigns.items():
        state = data.get("state", {})
        creatives = state.get("creative_assets", {})
        kpis = kpi_store.get(cid, {})
        
        # Get client profile name
        client_name = ""
        try:
            client = get_client(data.get("client_id"))
            if client:
                client_name = client.get("name", "Unnamed")
        except Exception:
            pass
        
        all_campaigns.append({
            "campaign_id": cid,
            "name": client_name or state.get("client_profile", {}).get("client_name", "Unknown"),
            "status": data.get("status", "unknown"),
            "metrics": kpis,
            "creatives_count": {
                "google": len(creatives.get("google_ads", [])),
                "meta": len(creatives.get("meta_ads", []))
            }
        })
    
    aggregated = aggregate_metrics(all_campaigns)
    
    return {
        "campaigns": all_campaigns,
        "aggregated": aggregated
    }

# ================================================================
# SCHEDULING ENDPOINTS
# ================================================================
from pydantic import BaseModel

class ScheduleData(BaseModel):
    start_date: str
    end_date: str
    start_time: str = "00:00"
    end_time: str = "23:59"

@app.post("/api/campaigns/{campaign_id}/schedule")
@require_role(["admin", "client_manager"])
async def schedule_campaign_endpoint(request: Request, campaign_id: str, schedule_data: ScheduleData):
    """Schedule a campaign for specific dates/times."""
    if campaign_id not in campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    result = scheduler.schedule_campaign(
        campaign_id,
        schedule_data.start_date,
        schedule_data.end_date,
        schedule_data.start_time,
        schedule_data.end_time
    )
    return {"success": result, "campaign_id": campaign_id}

@app.delete("/api/campaigns/{campaign_id}/schedule")
@require_role(["admin", "client_manager"])
async def unschedule_campaign_endpoint(request: Request, campaign_id: str):
    """Remove schedule for a campaign."""
    result = scheduler.unschedule_campaign(campaign_id)
    return {"success": result, "campaign_id": campaign_id}

@app.get("/api/campaigns/{campaign_id}/schedule")
@require_role(["admin", "client_manager", "client_viewer"])
async def get_campaign_schedule_endpoint(request: Request, campaign_id: str):
    """Get schedule for a campaign."""
    return scheduler.get_schedule(campaign_id)

# ================================================================

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
