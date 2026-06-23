from fastapi import FastAPI, HTTPException
from fastapi.routing import Mount
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
from .models import OnboardRequest, CampaignResponse
from .agents import graph, AgencyState

app = FastAPI(title="Agentic Marketing Agency API")

# CORS for UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/", StaticFiles(directory="static", html=True), name="static")

@app.get("/")
def root():
    return {"status": "online", "service": "Agentic Marketing Agency"}

@app.get("/api/status/agents")
def get_agent_status():
    """Returns current status of all 5 agents."""
    return {
        "orchestrator": "idle",
        "research": "idle",
        "creative": "idle",
        "launch": "idle",
        "analyst": "idle"
    }

@app.post("/api/campaigns/onboard", response_model=CampaignResponse)
async def onboard_campaign(request: OnboardRequest):
    """Triggers the full agentic workflow."""
    try:
        campaign_id = str(uuid.uuid4())[:8]
        
        # Initialize state
        initial_state: AgencyState = {
            "client_profile": request.dict(),
            "market_intelligence": {},
            "creative_assets": {},
            "deployment_status": {},
            "human_feedback": {},
            "validation_errors": []
        }
        
        # Run the graph (will interrupt at human_review)
        # In production, you'd run this async and return a job ID
        # For now, we return a campaign ID for tracking
        
        return CampaignResponse(
            campaign_id=campaign_id,
            status="pending_review",
            message="Campaign created. Please review creatives in the dashboard."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/campaigns/{campaign_id}/approve")
async def approve_campaign(campaign_id: str):
    """Approves the campaign and triggers launch."""
    # Resume the graph with human_feedback = {"status": "APPROVED"}
    return {"status": "approved", "campaign_id": campaign_id}

@app.patch("/api/campaigns/{campaign_id}/reject")
async def reject_campaign(campaign_id: str):
    """Rejects the campaign and triggers regeneration."""
    return {"status": "rejected", "campaign_id": campaign_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)