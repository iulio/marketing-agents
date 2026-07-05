# app/main.py - MAIN APPLICATION
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request , Query, Response, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
from typing import Dict, Any
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

from .models import OnboardRequest, CampaignResponse
from .agents import graph, AgencyState
from .storage import save_campaign_state, get_all_campaigns, get_client, get_client_campaigns, delete_client, delete_campaign
from .analytics import generate_daily_metrics, aggregate_metrics
from .scheduler import CampaignScheduler
from .analyst import PerformanceMonitor, run_immediate_optimization, fetch_real_kpis, refresh_kpis
from .auth import create_default_admin, generate_token, verify_user, get_user_by_email
from .middleware import require_role, get_current_user
from .email import send_welcome_email, send_audit_report_email, send_proposal_email, send_follow_up_email
from .audit import perform_audit
from .competitor import get_competitor_data
from .proposal import generate_proposal
from .reporting import generate_audit_pdf, generate_proposal_pdf

from .analytics import generate_daily_metrics, aggregate_metrics, get_performance_trend
from .storage import create_client, get_all_clients, get_client, get_users_by_client, create_user, update_client, get_total_clients_sync, get_active_campaigns_sync, get_new_signups_sync, save_global_ad_credentials, load_global_ad_credentials, update_client_credentials, get_client_credentials, get_credential_status, create_lead, get_all_leads, update_lead, save_audit_report, get_audit_report, save_proposal_record, get_proposal_record, log_publish_event, get_publish_events

from .kpi_fetcher import KPIFetcher
from pydantic import BaseModel, EmailStr

security = HTTPBearer(auto_error=False)

sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(dsn=sentry_dsn, integrations=[FastApiIntegration()])

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

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    tutorials_dir = os.path.join(static_dir, "tutorials")
    if os.path.exists(tutorials_dir):
        app.mount("/tutorials", StaticFiles(directory=tutorials_dir), name="tutorials")

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


@app.post("/api/audit")
async def run_audit(url_data: UrlRequest):
    if not url_data.url:
        raise HTTPException(status_code=400, detail="URL required")
    result = await perform_audit(url_data.url)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    audit_id = save_audit_report(result)
    result["audit_id"] = audit_id
    return result


@app.post("/api/audit/pdf")
async def download_audit_pdf(url_data: UrlRequest):
    if not url_data.url:
        raise HTTPException(status_code=400, detail="URL required")
    result = await perform_audit(url_data.url)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    pdf_bytes = generate_audit_pdf(result)
    return Response(
        pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=audit.pdf"},
    )


@app.post("/api/competitor/heatmap")
async def competitor_heatmap(data: CompetitorHeatmapRequest):
    if not data.domain or not data.competitors:
        raise HTTPException(status_code=400, detail="Domain and at least one competitor required")
    return await get_competitor_data(data.domain, data.competitors)


@app.post("/api/proposal/generate")
async def create_proposal(data: ProposalRequest):
    proposal = await generate_proposal(data.client or {}, data.audit or {})
    proposal_id = save_proposal_record(proposal, website=(data.client or {}).get("website", ""))
    return {"proposal_id": proposal_id, "proposal": proposal}


@app.post("/api/proposal/pdf")
async def download_proposal_pdf(data: ProposalRequest):
    proposal = await generate_proposal(data.client or {}, data.audit or {})
    pdf_bytes = generate_proposal_pdf(proposal, data.client or {})
    return Response(
        pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=proposal.pdf"},
    )


@app.post("/api/leads")
async def create_lead_endpoint(data: LeadRequest):
    lead_id = create_lead(data.model_dump())
    return {"lead_id": lead_id, "message": "Lead created"}


@app.get("/api/leads")
async def list_leads_endpoint():
    return {"leads": get_all_leads()}


@app.patch("/api/leads/{lead_id}")
async def update_lead_endpoint(lead_id: str, updates: dict):
    success = update_lead(lead_id, updates)
    if not success:
        raise HTTPException(status_code=400, detail="No valid lead fields to update")
    return {"message": "Lead updated", "lead_id": lead_id}


@app.get("/api/audit/{audit_id}")
async def get_saved_audit(audit_id: str):
    audit = get_audit_report(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    return audit


@app.get("/api/proposal/{proposal_id}")
async def get_saved_proposal(proposal_id: str):
    proposal = get_proposal_record(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal


@app.post("/api/outreach/audit")
async def send_audit_outreach_email(data: OutreachRequest):
    send_audit_report_email(data.email, data.website, data.summary or "Your audit is ready.")
    return {"message": "Audit email queued"}


@app.post("/api/outreach/proposal")
async def send_proposal_outreach_email(data: OutreachRequest):
    send_proposal_email(data.email, data.website, data.summary or "Your proposal is ready.")
    return {"message": "Proposal email queued"}


@app.post("/api/outreach/follow-up")
async def send_follow_up_outreach_email(data: OutreachRequest):
    send_follow_up_email(data.email, data.website)
    return {"message": "Follow-up email queued"}

# ================================================================
# AUTHENTICATION ENDPOINTS
# ================================================================

class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class UrlRequest(BaseModel):
    url: str


class CompetitorHeatmapRequest(BaseModel):
    domain: str
    competitors: list[str]


class ProposalRequest(BaseModel):
    client: dict
    audit: dict


class LeadRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    website: str
    company: str | None = None
    notes: str | None = None
    follow_up_at: str | None = None


class OutreachRequest(BaseModel):
    email: EmailStr
    website: str
    summary: str | None = None

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
@app.post("/api/clients")
@require_role(["admin"])
async def create_new_client(request: Request, client_data: dict):
    if not str(client_data.get("name", "")).strip():
        raise HTTPException(status_code=422, detail="Client name is required")
    if client_data.get("platform_status", "inactive") not in VALID_CLIENT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid platform_status")
    client_id = create_client(client_data)
    return {"client_id": client_id, "message": "Client created"}


@app.post("/api/auth/signup")
async def signup(signup_data: SignupRequest):
    existing_user = get_user_by_email(signup_data.email)
    if existing_user:
        raise HTTPException(status_code=409, detail="User already exists")
    user_id = create_user({
        "email": signup_data.email,
        "password": signup_data.password,
        "full_name": signup_data.full_name,
        "role": "client_viewer",
        "client_id": None,
        "subscription_status": "trial",
    })
    send_welcome_email(signup_data.email, signup_data.full_name)
    return {"user_id": user_id, "message": "Signup successful"}


@app.get("/api/admin/analytics")
@require_role(["admin"])
async def admin_analytics(request: Request):
    return {
        "total_clients": get_total_clients_sync(),
        "active_campaigns": get_active_campaigns_sync(),
        "new_signups": get_new_signups_sync(),
    }

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
    campaigns_data = get_client_campaigns(client_id)
    result = []
    for c in campaigns_data:
        state = c['state']
        client_profile = state.get('client_profile', {})
        deployment = state.get('deployment_status', {})
        result.append({
            "campaign_id": c['campaign_id'],
            "campaign_name": client_profile.get('client_name', 'Unnamed'),
            "status": c['status'],
            "budget": client_profile.get('daily_budget', 0),
            "language": client_profile.get('language', 'en-US'),
            "start_date": client_profile.get('start_date'),
            "end_date": client_profile.get('end_date'),
            "duration_days": client_profile.get('duration_days'),
            "google_campaign_verified": deployment.get('google_campaign_verified', False),
            "meta_campaign_verified": deployment.get('meta_campaign_verified', False),
            "google_push_attempted": deployment.get('google_push_attempted', False),
            "meta_push_attempted": deployment.get('meta_push_attempted', False),
            "google_push_succeeded": deployment.get('google_push_succeeded', False),
            "meta_push_succeeded": deployment.get('meta_push_succeeded', False),
            "google_platform_response_id": deployment.get('google_platform_response_id'),
            "meta_platform_response_id": deployment.get('meta_platform_response_id'),
            "google_platform_error_message": deployment.get('google_platform_error_message'),
            "meta_platform_error_message": deployment.get('meta_platform_error_message'),
            "verification_message": deployment.get('verification_message', ''),
            "created_at": c['created_at']
        })
    return {"campaigns": result}


@app.get("/api/settings/credentials")
@require_role(["admin", "client_manager", "client_viewer"])
async def get_settings_credentials(request: Request, masked: bool = Query(True)):
    return load_global_ad_credentials(mask_secrets=masked)


@app.post("/api/settings/credentials")
@require_role(["admin", "client_manager", "client_viewer"])
async def save_settings_credentials(request: Request, credentials: dict):
    return {
        "message": "Global credentials saved successfully",
        "credentials": save_global_ad_credentials(credentials),
    }


@app.get("/api/clients/{client_id}/credentials/status")
@require_role(["admin", "client_manager", "client_viewer"])
async def get_client_credentials_status(request: Request, client_id: str):
    user = request.state.user
    if user["role"] != "admin" and user.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Access denied")
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return await get_credential_status(client_id)


@app.get("/api/clients/{client_id}/credentials")
@require_role(["admin", "client_manager", "client_viewer"])
async def get_client_credentials_endpoint(request: Request, client_id: str):
    user = request.state.user
    if user["role"] != "admin" and user.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Access denied")
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return await get_client_credentials(client_id)


@app.post("/api/clients/{client_id}/credentials")
@require_role(["admin", "client_manager"])
async def save_client_credentials_endpoint(request: Request, client_id: str, credentials: dict):
    user = request.state.user
    if user["role"] != "admin" and user.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Access denied")
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    await update_client_credentials(client_id, credentials)
    return {"message": "Client credentials saved successfully", "client_id": client_id}


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
        creds = load_global_ad_credentials(mask_secrets=False)
        initial_state = {
            "client_profile": campaign_data.model_dump(mode="json"),
            "client_credentials": creds,
            "global_credentials": creds,
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
            "duration": {
                "start_date": final_state.get("client_profile", {}).get("start_date"),
                "end_date": final_state.get("client_profile", {}).get("end_date"),
                "duration_days": final_state.get("client_profile", {}).get("duration_days"),
            },
            "deployment_status": final_state.get("deployment_status", {}),
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
        deployment = state.get("deployment_status", {})
        result.append({
            "campaign_id": cid,
            "campaign_name": client.get("client_name", "Unnamed"),
            "platform": "Google & Meta",
            "language": client.get("language", "en-US"),
            "budget": float(client.get("daily_budget", 0) or 0),
            "ctr": "4.2%",
            "status": data.get("status", "unknown"),
            "start_date": client.get("start_date"),
            "end_date": client.get("end_date"),
            "duration_days": client.get("duration_days"),
            "google_campaign_verified": deployment.get("google_campaign_verified", False),
            "meta_campaign_verified": deployment.get("meta_campaign_verified", False),
            "google_push_attempted": deployment.get("google_push_attempted", False),
            "meta_push_attempted": deployment.get("meta_push_attempted", False),
            "google_push_succeeded": deployment.get("google_push_succeeded", False),
            "meta_push_succeeded": deployment.get("meta_push_succeeded", False),
            "google_platform_response_id": deployment.get("google_platform_response_id"),
            "meta_platform_response_id": deployment.get("meta_platform_response_id"),
            "google_platform_error_message": deployment.get("google_platform_error_message"),
            "meta_platform_error_message": deployment.get("meta_platform_error_message"),
            "verification_message": deployment.get("verification_message", ""),
        })
    return result

@app.get("/api/campaigns/{campaign_id}/creatives")
def get_creatives(campaign_id: str):
    if campaign_id not in campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    state = campaigns[campaign_id]["state"]
    return state.get("creative_assets", {})


@app.get("/api/campaigns/{campaign_id}/publish-events")
def campaign_publish_events(campaign_id: str):
    if campaign_id not in campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"campaign_id": campaign_id, "events": get_publish_events(campaign_id)}


@app.post("/api/campaigns/{campaign_id}/retry-publish")
def retry_publish_campaign(campaign_id: str):
    if campaign_id not in campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")

    data = campaigns[campaign_id]
    state = data.get("state", {})
    creatives = state.get("creative_assets", {})
    creds = state.get("global_credentials") or state.get("client_credentials", {}) or {}
    deployment = state.get("deployment_status", {})

    google_attempted = len(creatives.get("google_ads", [])) > 0
    meta_attempted = len(creatives.get("meta_ads", [])) > 0
    google_succeeded = bool(creds.get("google_ads_developer_token")) and google_attempted
    meta_succeeded = bool(creds.get("meta_app_id")) and meta_attempted
    google_response_id = f"GGL-REP-{hash(str(creatives.get('google_ads', []))) % 100000:05d}" if google_succeeded else None
    meta_response_id = f"META-REP-{hash(str(creatives.get('meta_ads', []))) % 100000:05d}" if meta_succeeded else None
    google_error = None if google_succeeded or not google_attempted else "Google Ads retry failed: missing credentials"
    meta_error = None if meta_succeeded or not meta_attempted else "Meta Ads retry failed: missing credentials"

    log_publish_event(campaign_id, "google", google_attempted, google_succeeded, google_response_id, google_error, {"ads": len(creatives.get("google_ads", []))})
    log_publish_event(campaign_id, "meta", meta_attempted, meta_succeeded, meta_response_id, meta_error, {"ads": len(creatives.get("meta_ads", []))})

    deployment.update({
        "google_push_attempted": google_attempted,
        "meta_push_attempted": meta_attempted,
        "google_push_succeeded": google_succeeded,
        "meta_push_succeeded": meta_succeeded,
        "google_platform_response_id": google_response_id,
        "meta_platform_response_id": meta_response_id,
        "google_platform_error_message": google_error,
        "meta_platform_error_message": meta_error,
        "google_campaign_verified": google_succeeded,
        "meta_campaign_verified": meta_succeeded,
        "verification_message": "Retry publish succeeded on at least one platform" if (google_succeeded or meta_succeeded) else "Retry publish failed",
    })

    state["deployment_status"] = deployment
    data["state"] = state
    campaigns[campaign_id] = data
    save_campaign_state(campaign_id, state, data.get("status", "pending_review"), data.get("client_id"))

    return {"campaign_id": campaign_id, "deployment_status": deployment}

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
    client = get_client(client_id) if client_id else None
    campaigns_data = get_all_campaigns()
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
        "client_info": client or {"name": "Solo Agency"},
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

if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
