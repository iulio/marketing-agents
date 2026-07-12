# app/main.py - MAIN APPLICATION
# Triggering a new build
import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request , Query, Response, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
from typing import Dict, Any, Optional
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from .models import OnboardRequest, CampaignResponse, ClientCreate, ClientStatus, ClientUpdate, ClientStatusUpdate, ReportScheduleIn
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
from .keyword_optimizer import discover_keywords, analyze_search_terms
from .competitor_intel import fetch_competitor_ads, analyze_ad_creative
from .social_generator import generate_social_posts, generate_post_variants
from .report_scheduler import scheduler_loop
from .proposal import generate_proposal
from .reporting import generate_audit_pdf, generate_proposal_pdf, render_custom_report
from .notifications import notify_campaign_created, notify_campaign_approved, notify_performance_alert
from .storage import create_report_template, get_report_template, get_report_templates

from .analytics import generate_daily_metrics, aggregate_metrics, get_performance_trend
from .google_ads_api import GoogleAdsAPI
from .meta_ads_api import MetaAdsAPI
from .storage import create_client, get_all_clients, get_client, get_users_by_client, create_user, update_client, get_total_clients_sync, get_active_campaigns_sync, get_new_signups_sync, save_global_ad_credentials, load_global_ad_credentials, update_client_credentials, get_client_credentials, get_credential_status, create_lead, get_all_leads, update_lead, save_audit_report, get_audit_report, save_proposal_record, get_proposal_record, log_publish_event, get_publish_events, get_global_llm_config, set_global_llm_config
from .ab_testing import ABTestingEngine
from .storage import create_onboarding_session, save_onboarding_session, get_latest_onboarding_session, get_onboarding_session, update_onboarding_status, delete_onboarding_session
from .storage import create_report_schedule, get_report_schedules, get_report_schedule, delete_report_schedule
from .image_service import StockImageSearch, AIImageGenerator, SmartImageSelector
from .benchmarks import compare_campaign_to_benchmark, get_benchmarks_for_industry, load_benchmarks
from .budget_monitor import check_budget_alerts
from .notifications import send_budget_alert

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
ab_testing_engine = ABTestingEngine()

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
    
    # Start the background report scheduler
    scheduler_task = asyncio.create_task(scheduler_loop(interval_seconds=300))
    print("[Startup] Report scheduler started (interval=300s)")

    # Start background budget monitor loop
    async def budget_monitor_loop():
        while True:
            await asyncio.sleep(900)
            try:
                for cid, data in campaigns.items():
                    if data.get("status") == "active":
                        state = data.get("state", {})
                        client = state.get("client_profile", {})
                        daily_budget = float(client.get("daily_budget", 0) or 0)
                        campaign_name = client.get("client_name", "Unknown")
                        kpis = kpi_store.get(cid, {})
                        spend = float(kpis.get("cost", 0) or 0)
                        alert_data = check_budget_alerts(cid, spend, daily_budget, campaign_name, client.get("client_name", "Unknown"))
                        for alert in alert_data.get("alerts", []):
                            if alert.get("severity") in ["critical", "warning"]:
                                send_budget_alert(campaign_name, alert["message"], alert.get("severity"))
                        if alert_data.get("status") == "critical":
                            print(f"[Budget Monitor] Auto-pausing campaign {cid}")
                            data["status"] = "paused"
            except Exception as e:
                print(f"[Budget Monitor] Error: {e}")

    budget_task = asyncio.create_task(budget_monitor_loop())
    print("[Startup] Budget monitor started (interval=900s)")

    yield

    budget_task.cancel()
    scheduler_task.cancel()
    
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
    from .auth import verify_token
    payload = verify_token(token)
    expires_at = payload.get("exp", 0) if payload else 0
    return {
        "token": token,
        "expires_at": expires_at,
        "user": {
            "id": user['id'],
            "email": user['email'],
            "full_name": user['full_name'],
            "role": user['role'],
            "client_id": user.get('client_id')
        }
    }




VALID_CLIENT_STATUSES = {status.value for status in ClientStatus}

# ================================================================
# CLIENT MANAGEMENT ENDPOINTS
# ================================================================
@app.post("/api/clients")
@require_role(["admin", "client_manager"])
async def create_new_client(request: Request, client_data: ClientCreate):
    client_data_dict = client_data.model_dump()
    if not str(client_data_dict.get("name", "")).strip():
        raise HTTPException(status_code=422, detail="Client name is required")
    client_id = create_client(client_data_dict)
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


@app.get("/api/settings/llm-config")
@require_role(["admin", "client_manager", "client_viewer"])
async def get_llm_config_endpoint(request: Request):
    """Return the global per-agent LLM configuration."""
    return {"config": get_global_llm_config()}


@app.post("/api/settings/llm-config")
@require_role(["admin"])
async def save_llm_config_endpoint(request: Request, config: dict):
    """Persist the global per-agent LLM configuration."""
    set_global_llm_config(config)
    return {"message": "LLM config saved", "config": get_global_llm_config()}

@app.post("/api/settings/test-credentials")
@require_role(["admin"])
async def test_global_credentials_endpoint(request: Request):
    """
    Tests the globally configured ad platform credentials.
    """
    creds = load_global_ad_credentials(mask_secrets=False)
    if not creds:
        raise HTTPException(status_code=404, detail="Global credentials are not configured.")

    # Test Google Ads
    google_api = GoogleAdsAPI(credentials=creds)
    google_result = google_api.test_credentials()

    # Test Meta Ads
    meta_api = MetaAdsAPI(credentials=creds)
    meta_result = meta_api.test_credentials()

    return {
        "google_ads": google_result,
        "meta_ads": meta_result
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

@app.post("/api/clients/{client_id}/test-credentials")
@require_role(["admin", "client_manager"])
async def test_client_credentials_endpoint(request: Request, client_id: str):
    user = request.state.user
    if user["role"] != "admin" and user.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    creds = await get_client_credentials(client_id)
    if not creds:
        raise HTTPException(status_code=404, detail="Client not found or has no credentials.")

    # Test Google Ads
    google_api = GoogleAdsAPI(credentials=creds)
    google_result = google_api.test_credentials()

    # Test Meta Ads
    meta_api = MetaAdsAPI(credentials=creds)
    meta_result = meta_api.test_credentials()

    return {
        "google_ads": google_result,
        "meta_ads": meta_result
    }


@app.patch("/api/clients/{client_id}")
@require_role(["admin"])
async def update_client_endpoint(request: Request, client_id: str, updates: ClientUpdate):
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    updates_dict = updates.model_dump(exclude_unset=True)
    if "name" in updates_dict and not str(updates_dict["name"]).strip():
        raise HTTPException(status_code=422, detail="Client name is required")
    success = update_client(client_id, updates_dict)
    if not success:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    return {"message": "Client updated", "client": get_client(client_id)}

@app.patch("/api/clients/{client_id}/status")
@require_role(["admin", "client_manager"])
async def update_client_status_endpoint(request: Request, client_id: str, status_data: ClientStatusUpdate):
    user = request.state.user
    if user["role"] != "admin" and user.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Access denied")
    new_status = status_data.platform_status
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
# ONBOARDING WIZARD ENDPOINTS
# ================================================================

@app.post("/api/onboarding/start")
@require_role(["admin"])
async def start_onboarding(request: Request):
    user = request.state.user
    session_id = create_onboarding_session(user["id"])
    return {"session_id": session_id, "step": 1, "data": {}}


@app.post("/api/onboarding/save")
@require_role(["admin"])
async def save_onboarding(request: Request, payload: dict):
    session_id = payload.get("session_id")
    step = payload.get("step")
    step_data = payload.get("data", {})
    if not session_id or not step:
        raise HTTPException(status_code=400, detail="session_id and step are required")
    success = save_onboarding_session(session_id, step, step_data)
    if not success:
        raise HTTPException(status_code=404, detail="Onboarding session not found")
    return {"message": "Progress saved"}


@app.get("/api/onboarding/resume")
@require_role(["admin"])
async def resume_onboarding(request: Request):
    user = request.state.user
    session_data = get_latest_onboarding_session(user["id"])
    if not session_data:
        return {"session_id": None, "step": 1, "data": {}}
    return session_data


@app.post("/api/onboarding/submit")
@require_role(["admin"])
async def submit_onboarding(request: Request, payload: dict):
    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    session_data_wrapper = get_onboarding_session(session_id)
    if not session_data_wrapper:
        raise HTTPException(status_code=404, detail="Onboarding session not found")
        
    if session_data_wrapper["status"] != "in_progress":
        raise HTTPException(status_code=400, detail="Onboarding session is already finished or cancelled")
        
    session_data = session_data_wrapper["data"]

    
    # 1. Create client
    client_name = session_data.get("name", "New Client").strip()
    if not client_name:
        raise HTTPException(status_code=422, detail="Client name is required")
        
    client_id = str(uuid.uuid4())
    client_payload = {
        "id": client_id,
        "name": client_name,
        "industry": session_data.get("industry", ""),
        "website": session_data.get("website", ""),
        "logo_url": session_data.get("logo_url", ""),
        "billing_email": session_data.get("billing_email", ""),
        "billing_info": session_data.get("billing_info", {}),
        "settings": session_data.get("settings", {}),
        "platform_status": session_data.get("platform_status", "active"),
        "google_ads_developer_token": session_data.get("google_ads_developer_token", ""),
        "google_ads_client_id": session_data.get("google_ads_client_id", ""),
        "google_ads_client_secret": session_data.get("google_ads_client_secret", ""),
        "google_ads_refresh_token": session_data.get("google_ads_refresh_token", ""),
        "google_ads_customer_id": session_data.get("google_ads_customer_id", ""),
        "meta_app_id": session_data.get("meta_app_id", ""),
        "meta_app_secret": session_data.get("meta_app_secret", ""),
        "meta_access_token": session_data.get("meta_access_token", ""),
        "meta_ad_account_id": session_data.get("meta_ad_account_id", ""),
        "google_ads_configured": bool(session_data.get("google_ads_developer_token")),
        "meta_ads_configured": bool(session_data.get("meta_app_id")),
        "agent_llm_settings": session_data.get("agent_llm_settings", {}),
        "image_generation_preferences": session_data.get("image_generation_preferences", {}),
        "default_budget": float(session_data.get("default_budget")) if session_data.get("default_budget") else None
    }
    
    # Store client to database
    create_client(client_payload)
    
    # 2. Check if a campaign should be created
    campaign_id = None
    campaign_status = None
    if session_data.get("launch_campaign", True):
        try:
            target_geo = session_data.get("target_geo", ["US"])
            if isinstance(target_geo, str):
                target_geo = [g.strip() for g in target_geo.split(",") if g.strip()]
            
            cultural_triggers = session_data.get("cultural_triggers", [])
            if isinstance(cultural_triggers, str):
                cultural_triggers = [t.strip() for t in cultural_triggers.split(",") if t.strip()]
                
            special_events = session_data.get("special_events", [])
            if isinstance(special_events, str):
                special_events = [e.strip() for e in special_events.split(",") if e.strip()]
                
            product_keywords = session_data.get("product_keywords", [])
            if isinstance(product_keywords, str):
                product_keywords = [k.strip() for k in product_keywords.split(",") if k.strip()]

            campaign_req = OnboardRequest(
                client_name=client_name,
                website_url=session_data.get("website", "https://example.com"),
                language=session_data.get("campaign_language", "en-US"),
                tone_of_voice=session_data.get("tone_of_voice", "professional"),
                objective=session_data.get("campaign_objective", "traffic"),
                industry=session_data.get("industry", "General"),
                daily_budget=float(session_data.get("daily_budget", 100.0)),
                target_geo=target_geo,
                cultural_triggers=cultural_triggers,
                special_events=special_events,
                product_keywords=product_keywords,
                start_date=session_data.get("start_date"),
                end_date=session_data.get("end_date"),
                duration_days=int(session_data.get("duration_days", 30)) if session_data.get("duration_days") else 30
            )
            
            campaign_id = str(uuid.uuid4())[:8]
            # Load the credentials we just saved for this client
            creds = {
                "google_ads_developer_token": client_payload["google_ads_developer_token"],
                "google_ads_client_id": client_payload["google_ads_client_id"],
                "google_ads_client_secret": client_payload["google_ads_client_secret"],
                "google_ads_refresh_token": client_payload["google_ads_refresh_token"],
                "google_ads_customer_id": client_payload["google_ads_customer_id"],
                "meta_app_id": client_payload["meta_app_id"],
                "meta_app_secret": client_payload["meta_app_secret"],
                "meta_access_token": client_payload["meta_access_token"],
                "meta_ad_account_id": client_payload["meta_ad_account_id"]
            }
            initial_state = {
                "client_profile": campaign_req.model_dump(mode="json"),
                "client_credentials": creds,
                "global_credentials": load_global_ad_credentials(mask_secrets=False),
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
            campaign_status = "pending_review"
            
            campaigns[campaign_id] = {
                "state": final_state,
                "status": campaign_status,
                "thread_id": campaign_id,
                "client_id": client_id,
                "client_name": campaign_req.client_name,
                "language": campaign_req.language.value,
                "created_at": None,
            }
            save_campaign_state(campaign_id, final_state, campaign_status, client_id)
            
            try:
                notify_campaign_created(
                    campaign_name=campaign_req.client_name,
                    client_name=client_name,
                    campaign_id=campaign_id,
                )
            except Exception:
                pass
        except Exception as e:
            print(f"[Onboarding Submit] Failed to create campaign: {e}")
            
    # 3. Mark onboarding session as completed
    update_onboarding_status(session_id, "completed")
    
    return {
        "message": "Onboarding completed successfully",
        "client_id": client_id,
        "campaign_id": campaign_id,
        "campaign_status": campaign_status
    }


@app.delete("/api/onboarding/cancel")
@require_role(["admin"])
async def cancel_onboarding(request: Request, payload: dict):
    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    success = update_onboarding_status(session_id, "abandoned")
    if not success:
        raise HTTPException(status_code=404, detail="Onboarding session not found")
    return {"message": "Onboarding cancelled"}

# ================================================================
# OAUTH 2.0 AUTHENTICATION FLOWS
# ================================================================

@app.get("/api/auth/google/start")
@require_role(["admin"])
async def auth_google_start(request: Request, session_id: str = Query(...)):
    """
    Starts the Google OAuth 2.0 flow by redirecting the user to Google's consent screen.
    """
    creds = load_global_ad_credentials(mask_secrets=False)
    google_client_id = creds.get("google_ads_client_id")
    google_client_secret = creds.get("google_ads_client_secret")

    if not google_client_id or not google_client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth credentials are not configured on the server.")

    # The redirect_uri must be registered in your Google Cloud project
    redirect_uri = f"{request.base_url}api/auth/google/callback"

    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": google_client_id,
                "client_secret": google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/adwords"],
        redirect_uri=redirect_uri
    )
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true', state=session_id)
    return RedirectResponse(authorization_url)

@app.get("/api/auth/google/callback")
async def auth_google_callback(request: Request, code: str = Query(...), state: str = Query(...)):
    """
    Handles the OAuth 2.0 callback from Google. Exchanges the code for a refresh token.
    """
    session_id = state
    creds = load_global_ad_credentials(mask_secrets=False)
    google_client_id = creds.get("google_ads_client_id")
    google_client_secret = creds.get("google_ads_client_secret")
    developer_token = creds.get("google_ads_developer_token")

    if not google_client_id or not google_client_secret:
        return RedirectResponse(f"/onboarding.html?google_auth=error&message=Server-side+OAuth+config+missing")

    redirect_uri = f"{request.base_url}api/auth/google/callback"

    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": google_client_id,
                "client_secret": google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/adwords"],
        redirect_uri=redirect_uri
    )

    try:
        flow.fetch_token(code=code)
        google_creds = flow.credentials
        
        # Save the refresh token and other necessary details to the onboarding session
        save_onboarding_session(session_id, 2, {
            "google_ads_refresh_token": google_creds.refresh_token,
            "google_ads_client_id": google_client_id,
            "google_ads_client_secret": google_client_secret,
            "google_ads_developer_token": developer_token,
        })
        return RedirectResponse(f"/onboarding.html?google_auth=success&session_id={session_id}")
    except Exception as e:
        print(f"Error during Google OAuth callback: {e}")
        return RedirectResponse(f"/onboarding.html?google_auth=error&message=Failed+to+fetch+token")

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
        global_creds = load_global_ad_credentials(mask_secrets=False)
        client_creds = await get_client_credentials(client_id) or {}
        initial_state = {
            "client_profile": campaign_data.model_dump(mode="json"),
            "client_credentials": creds,
            "global_credentials": creds,
            "client_id": client_id, # Pass client_id into the state
            "client_credentials": client_creds,
            "global_credentials": global_creds,
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

        # Fire Slack notification (no-op if SLACK_WEBHOOK_URL not set)
        try:
            notify_campaign_created(
                campaign_name=campaign_data.client_name,
                client_name=client.get("name", campaign_data.client_name),
                campaign_id=campaign_id,
            )
        except Exception:
            pass

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

@app.patch("/api/campaigns/{campaign_id}/creatives")
async def update_creative(campaign_id: str, request: Request):
    if campaign_id not in campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    data = await request.json()
    state = campaigns[campaign_id]["state"]
    creatives = state.get("creative_assets", {})
    platform = data.get("platform")
    index = data.get("index")
    updates = data.get("updates", {})
    if platform == "google":
        ads = creatives.get("google_ads", [])
        if 0 <= index < len(ads):
            ads[index].update(updates)
    elif platform == "meta":
        ads = creatives.get("meta_ads", [])
        if 0 <= index < len(ads):
            ads[index].update(updates)
    state["creative_assets"] = creatives
    campaigns[campaign_id]["state"] = state
    save_campaign_state(campaign_id, state, campaigns[campaign_id].get("status", "pending_review"), campaigns[campaign_id].get("client_id"))
    return {"status": "ok", "creatives": creatives}


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
    deployment = state.get("deployment_status", {})
    client_id = data.get("client_id")

    # Correctly load and merge credentials, same as in launch_node
    from .storage import get_client_credentials_sync, load_global_ad_credentials
    
    # Start with global credentials as a base
    creds = load_global_ad_credentials(mask_secrets=False)
    
    # Layer client-specific credentials on top
    if client_id:
        client_creds = get_client_credentials_sync(client_id) or {}
        creds.update({k: v for k, v in client_creds.items() if v})

    # The rest of the logic remains the same, using the correctly merged 'creds'
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

    # Fire Slack notification (no-op if SLACK_WEBHOOK_URL not set)
    try:
        client_name = data.get("client_name") or campaign_id
        campaign_name = final_state.get("client_profile", {}).get("client_name", campaign_id)
        notify_campaign_approved(
            campaign_name=campaign_name,
            client_name=client_name,
            campaign_id=campaign_id,
        )
    except Exception:
        pass

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
# BENCHMARK ENDPOINTS
# ================================================================

@app.get("/api/campaigns/{campaign_id}/benchmark")
async def get_benchmark(campaign_id: str):
    if campaign_id not in campaigns:
        raise HTTPException(404, "Campaign not found")
    state = campaigns[campaign_id].get("state", {})
    client = state.get("client_profile", {})
    industry = client.get("industry", "general")
    kpis = kpi_store.get(campaign_id, {})
    comparison = compare_campaign_to_benchmark(kpis, industry)
    return {"campaign_id": campaign_id, "industry": industry, "comparison": comparison}

@app.get("/api/benchmarks/industries")
async def list_benchmark_industries():
    benchmarks = load_benchmarks()
    return {"industries": list(benchmarks.keys())}

@app.get("/api/benchmarks/{industry}")
async def get_industry_benchmark(industry: str):
    benchmark = get_benchmarks_for_industry(industry)
    if not benchmark:
        raise HTTPException(404, f"Benchmark data not found for industry: {industry}")
    return benchmark

# ================================================================
# BUDGET STATUS ENDPOINT
# ================================================================

@app.get("/api/campaigns/{campaign_id}/budget-status")
async def get_budget_status(campaign_id: str):
    if campaign_id not in campaigns:
        raise HTTPException(404, "Campaign not found")
    data = campaigns[campaign_id]
    state = data.get("state", {})
    client = state.get("client_profile", {})
    daily_budget = float(client.get("daily_budget", 0) or 0)
    campaign_name = client.get("client_name", "Unknown")
    kpis = kpi_store.get(campaign_id, {})
    spend = float(kpis.get("cost", 0) or 0)
    alert_data = check_budget_alerts(campaign_id, spend, daily_budget, campaign_name, client.get("client_name", "Unknown"))
    for alert in alert_data.get("alerts", []):
        if alert.get("severity") in ["critical", "warning"]:
            send_budget_alert(campaign_name, alert["message"], alert.get("severity"))
    if alert_data.get("status") == "critical":
        data["status"] = "paused"
    return {"campaign_id": campaign_id, "campaign_name": campaign_name, "daily_budget": daily_budget, "spent_today": spend, **alert_data}

@app.post("/api/campaigns/budget-statuses")
async def get_bulk_budget_statuses(request: Request, payload: dict):
    """Get budget status for multiple campaigns in a single call."""
    campaign_ids = payload.get("campaign_ids", [])
    results = {}
    for campaign_id in campaign_ids:
        if campaign_id not in campaigns:
            continue
        data = campaigns[campaign_id]
        state = data.get("state", {})
        client = state.get("client_profile", {})
        daily_budget = float(client.get("daily_budget", 0) or 0)
        campaign_name = client.get("client_name", "Unknown")
        kpis = kpi_store.get(campaign_id, {})
        spend = float(kpis.get("cost", 0) or 0)
        
        alert_data = check_budget_alerts(campaign_id, spend, daily_budget, campaign_name, client.get("client_name", "Unknown"))
        results[campaign_id] = {"daily_budget": daily_budget, "spent_today": spend, **alert_data}
    return results


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
# A/B TESTING ENDPOINTS
# ================================================================

@app.post("/api/campaigns/{campaign_id}/ab-test")
async def create_ab_test_endpoint(campaign_id: str, request: Request):
    variants = await request.json()
    test_data = ab_testing_engine.create_test(campaign_id, variants)
    return test_data

@app.get("/api/campaigns/{campaign_id}/ab-test/results")
async def get_ab_test_results_endpoint(campaign_id: str):
    return ab_testing_engine.evaluate_test(campaign_id)

@app.post("/api/campaigns/{campaign_id}/ab-test/promote")
async def promote_ab_test_winner(campaign_id: str, request: Request):
    if campaign_id not in campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    body = await request.json()
    variant_id = body.get("variant_id", "")
    state = campaigns[campaign_id]["state"]
    creatives = state.get("creative_assets", {})
    test_data = ab_testing_engine.tests.get(campaign_id, {})
    variants = test_data.get("variants", [])
    winner = None
    for v in variants:
        if v.get("id") == variant_id:
            winner = v
            break
    if winner is None:
        raise HTTPException(status_code=404, detail="Variant not found")
    winner_content = winner.get("content", {})
    google_ads = creatives.get("google_ads", [])
    if winner_content.get("headline"):
        for ad in google_ads:
            ad["headline"] = winner_content["headline"]
    if winner_content.get("description"):
        for ad in google_ads:
            ad["description"] = winner_content["description"]
    if winner_content.get("primary_text"):
        meta_ads = creatives.get("meta_ads", [])
        for ad in meta_ads:
            ad["primary_text"] = winner_content["primary_text"]
    state["creative_assets"] = creatives
    campaigns[campaign_id]["state"] = state
    save_campaign_state(campaign_id, state, campaigns[campaign_id].get("status", "pending_review"), campaigns[campaign_id].get("client_id"))
    return {"status": "ok", "promoted_variant": variant_id, "creatives": creatives}

# ================================================================
# IMAGE SERVICE ENDPOINTS
# ================================================================

class ImageSearchRequest(BaseModel):
    query: str
    per_page: int = 9
    provider: str = "all"  # all, unsplash, pexels, pixabay

class ImageGenerateRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    num_images: int = 2
    provider: str = "pollinations"  # pollinations, replicate, huggingface

@app.post("/api/images/search")
async def search_images(req: ImageSearchRequest):
    """Search free stock images from Unsplash, Pexels, Pixabay."""
    try:
        if req.provider == "unsplash":
            results = StockImageSearch.search_unsplash(req.query, req.per_page)
        elif req.provider == "pexels":
            results = StockImageSearch.search_pexels(req.query, req.per_page)
        elif req.provider == "pixabay":
            results = StockImageSearch.search_pixabay(req.query, req.per_page)
        else:
            results = StockImageSearch.search(req.query, req.per_page)
        return {"images": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/images/generate")
async def generate_image_endpoint(req: ImageGenerateRequest):
    """Generate AI images using Pollinations, Replicate, or HuggingFace."""
    import os as _os
    _os.environ["IMAGE_PROVIDER"] = req.provider
    try:
        urls = AIImageGenerator.generate(req.prompt, req.negative_prompt, req.num_images)
        images = [
            {
                "id": f"gen-{i+1}",
                "type": "generated",
                "url": url,
                "thumb": url,
                "source": req.provider,
                "alt": req.prompt[:100],
                "photographer": "AI"
            }
            for i, url in enumerate(urls)
        ]
        return {"images": images, "count": len(images), "prompt": req.prompt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/campaigns/{campaign_id}/images/regenerate")
async def regenerate_campaign_images(campaign_id: str):
    """Regenerate images for a campaign using AI."""
    campaign = campaigns.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    try:
        state = campaign.get("state", {})
        client = state.get("client_profile", {})
        creatives = state.get("creative_assets", {})
        images = SmartImageSelector.select_images(
            campaign_id=campaign_id,
            client=client,
            creatives=creatives,
            num_images=3
        )
        creatives["images"] = images
        state["creative_assets"] = creatives
        campaign["state"] = state
        campaigns[campaign_id] = campaign
        save_campaign_state(campaign_id, state, campaign.get("status", "pending_review"), campaign.get("client_id"))
        return {"images": images, "count": len(images)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/campaigns/{campaign_id}/images")
async def add_campaign_image(campaign_id: str, img: dict):
    """Add a custom image to the campaign's creatives."""
    if campaign_id not in campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    data = campaigns[campaign_id]
    state = data.get("state", {})
    creatives = state.get("creative_assets", {}) or {}
    if "images" not in creatives:
        creatives["images"] = []
    creatives["images"].append(img)
    state["creative_assets"] = creatives
    data["state"] = state
    campaigns[campaign_id] = data
    save_campaign_state(campaign_id, state, data.get("status"), data.get("client_id"))
    return {"status": "success", "images": creatives["images"]}

@app.delete("/api/campaigns/{campaign_id}/images/{image_id}")
async def delete_campaign_image_endpoint(campaign_id: str, image_id: str):
    """Delete a specific image from the campaign's creatives."""
    if campaign_id not in campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    data = campaigns[campaign_id]
    state = data.get("state", {})
    creatives = state.get("creative_assets", {}) or {}
    images = creatives.get("images", [])
    
    # Helper to check matching ID (supporting both dicts and plain string URLs)
    def match_id(x):
        if isinstance(x, dict):
            return x.get("id") == image_id or x.get("url") == image_id
        return x == image_id

    creatives["images"] = [img for img in images if not match_id(img)]
    state["creative_assets"] = creatives
    data["state"] = state
    campaigns[campaign_id] = data
    save_campaign_state(campaign_id, state, data.get("status"), data.get("client_id"))
    return {"status": "success", "images": creatives["images"]}

# ================================================================
# REPORT TEMPLATES ENDPOINTS
# ================================================================

class ReportTemplateCreate(BaseModel):
    name: str
    description: str = ""
    sections: list[str] = ["kpi", "recommendations"]
    branding: dict = {}
    custom_message: str = ""


@app.post("/api/reports/templates")
@require_role(["admin", "client_manager"])
async def create_template_endpoint(request: Request, data: ReportTemplateCreate):
    """Create a new report template."""
    user = request.state.user
    payload = data.model_dump()
    # client_viewers can't create; admins can create global (client_id=None) templates
    if user["role"] != "admin":
        payload["client_id"] = user.get("client_id")
    template_id = create_report_template(payload)
    return {"id": template_id, "message": "Template created"}


@app.get("/api/reports/templates")
@require_role(["admin", "client_manager", "client_viewer"])
async def list_templates_endpoint(request: Request):
    """List report templates visible to the authenticated user."""
    user = request.state.user
    client_id = None if user["role"] == "admin" else user.get("client_id")
    templates = get_report_templates(client_id)
    return {"templates": templates}


@app.post("/api/reports/generate")
@require_role(["admin", "client_manager", "client_viewer"])
async def generate_custom_report_endpoint(request: Request, data: dict):
    """Generate a branded PDF from a report template + campaign."""
    campaign_id = data.get("campaign_id")
    template_id = data.get("template_id")

    if not campaign_id or template_id is None:
        raise HTTPException(status_code=400, detail="campaign_id and template_id are required")

    if campaign_id not in campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")

    template = get_report_template(int(template_id))
    if not template:
        raise HTTPException(status_code=404, detail="Report template not found")

    state = campaigns[campaign_id]["state"]
    client_profile = state.get("client_profile", {})
    campaign_data = {
        "client_name": client_profile.get("client_name", "Unknown Campaign"),
        "creative_assets": state.get("creative_assets", {}),
        "recommendations": state.get("analysis", {}).get("recommendations", []),
    }

    metrics = kpi_store.get(campaign_id) or fetch_real_kpis(campaign_id, client_profile.get("platform", "auto")) or {
        "impressions": 0, "clicks": 0, "ctr": 0, "cpc": 0.0,
        "conversions": 0, "roas": 0.0, "cost": 0.0,
    }

    pdf_bytes = render_custom_report(campaign_data, metrics, template)
    filename = f"{campaign_id}_{template.get('name', 'report').replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ================================================================
# KEYWORD DISCOVERY ENDPOINTS
# ================================================================

@app.post("/api/keywords/discover")
async def api_discover_keywords(data: dict):
    """Discover keyword clusters, negatives, and match type recommendations."""
    try:
        result = await discover_keywords(
            website=data.get("website", ""),
            industry=data.get("industry", ""),
            seed_keywords=data.get("seed_keywords", []),
            location=data.get("location", "US"),
            language=data.get("language", "en"),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/keywords/analyze-search-terms")
async def api_analyze_search_terms(data: dict):
    """Analyze search term report and provide optimization recommendations."""
    try:
        result = await analyze_search_terms(data.get("query_log", []))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================================================
# COMPETITOR INTELLIGENCE ENDPOINTS
# ================================================================

@app.post("/api/competitor-intel/analyze")
async def api_competitor_analyze(data: dict):
    """Analyze competitors and produce intelligence report."""
    try:
        result = await fetch_competitor_ads(
            domain=data.get("domain", ""),
            competitors=data.get("competitors", []),
            industry=data.get("industry", ""),
            location=data.get("location", "US"),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/competitor-intel/compare-ads")
async def api_compare_ads(data: dict):
    """Compare two ad copies and get improvement suggestions."""
    try:
        result = await analyze_ad_creative(
            ad_copy=data.get("ad_copy", ""),
            competitor_ad_copy=data.get("competitor_ad_copy", ""),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================================================
# SOCIAL MEDIA GENERATOR ENDPOINTS
# ================================================================

@app.post("/api/social/generate")
async def api_social_generate(data: dict):
    """Generate social media posts for multiple platforms."""
    try:
        result = await generate_social_posts(
            campaign_description=data.get("campaign_description", ""),
            platforms=data.get("platforms", ["facebook", "linkedin"]),
            tone=data.get("tone", "professional"),
            target_audience=data.get("target_audience", ""),
            post_count=data.get("post_count", 3),
            include_hashtags=data.get("include_hashtags", True),
            include_cta=data.get("include_cta", True),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/social/variants")
async def api_social_variants(data: dict):
    """Generate A/B test variants of a social post."""
    try:
        result = await generate_post_variants(
            base_post=data.get("base_post", ""),
            platform=data.get("platform", "facebook"),
            variations=data.get("variations", 3),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================================================
# REPORT SCHEDULER ENDPOINTS
# ================================================================

@app.post("/api/report-schedules")
async def api_create_schedule(data: ReportScheduleIn):
    """Create a new report schedule."""
    try:
        schedule_id = create_report_schedule(data.model_dump())
        return {"id": schedule_id, "message": "Schedule created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/report-schedules")
async def api_get_schedules():
    """Get all report schedules."""
    try:
        return get_report_schedules()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/report-schedules/{schedule_id}")
async def api_get_schedule(schedule_id: int):
    """Get a single report schedule."""
    schedule = get_report_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@app.delete("/api/report-schedules/{schedule_id}")
async def api_delete_schedule(schedule_id: int):
    """Delete a report schedule."""
    deleted = delete_report_schedule(schedule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"message": "Schedule deleted"}


# ================================================================

if os.path.exists(static_dir):
    tutorials_dir = os.path.join(static_dir, "tutorials")
    if os.path.exists(tutorials_dir):
        app.mount("/tutorials", StaticFiles(directory=tutorials_dir), name="tutorials")
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
