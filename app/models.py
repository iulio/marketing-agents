# app/models.py
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
import uuid
from enum import Enum  # <-- ADDED
from typing import List, Optional
from pydantic import BaseModel, Field, validator

# ================================================================
# SQLALCHEMY DATABASE MODELS
# ================================================================

def gen_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String, nullable=False)
    client_id = Column(String, ForeignKey("clients.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    stripe_customer_id = Column(String, nullable=True)
    subscription_status = Column(String, default="trial")
    plan = Column(String, nullable=True)  # e.g., "pro", "agency"

class Client(Base):
    __tablename__ = "clients"
    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    industry = Column(String)
    website = Column(String)
    logo_url = Column(String)
    billing_email = Column(String)
    billing_info = Column(JSON)
    settings = Column(JSON)
    platform_status = Column(String, default="inactive")
    google_ads_developer_token = Column(String, nullable=True)
    google_ads_client_id = Column(String, nullable=True)
    google_ads_client_secret = Column(String, nullable=True)
    google_ads_refresh_token = Column(String, nullable=True)
    google_ads_customer_id = Column(String, nullable=True)
    meta_app_id = Column(String, nullable=True)
    meta_app_secret = Column(String, nullable=True)
    meta_access_token = Column(String, nullable=True)
    meta_ad_account_id = Column(String, nullable=True)
    google_ads_configured = Column(Boolean, default=False)
    meta_ads_configured = Column(Boolean, default=False)
    
    # Per-Agent LLM Settings (JSON)
    agent_llm_settings = Column(JSON, nullable=True)  # e.g., {"orchestrator": "vertex", "creative": "claude"}
    
    # Additional "other" fields
    image_generation_preferences = Column(JSON, nullable=True)  # e.g., {"provider": "pollinations", "style": "professional"}
    default_budget = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    users = relationship("User", backref="client")

class Campaign(Base):
    __tablename__ = "campaigns"
    campaign_id = Column(String, primary_key=True)
    client_id = Column(String, ForeignKey("clients.id"))
    created_by = Column(String, ForeignKey("users.id"))
    state = Column(JSON, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class OptimizationHistory(Base):
    __tablename__ = "optimization_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(String, ForeignKey("campaigns.campaign_id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action_type = Column(String, nullable=False)
    action_description = Column(String)
    kpi_before = Column(JSON)
    kpi_after = Column(JSON)
    status = Column(String, default="completed")

class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(String, primary_key=True, default=gen_uuid)
    client_id = Column(String, ForeignKey("clients.id"), nullable=False)
    name = Column(String, nullable=False)
    key_hash = Column(String, nullable=False)
    last_used = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)

class Setting(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True)
    value = Column(Text)
    is_encrypted = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ABTest(Base):
    __tablename__ = "ab_tests"
    id = Column(String, primary_key=True, default=gen_uuid)
    campaign_id = Column(String, ForeignKey("campaigns.campaign_id"), nullable=False)
    name = Column(String)
    status = Column(String, default="running")
    variants = Column(JSON, nullable=False)
    results = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

class ReportTemplate(Base):
    __tablename__ = "report_templates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(String)
    sections = Column(JSON, nullable=False, default=lambda: ["kpi", "recommendations"])
    branding = Column(JSON)       # {"primary_color": "#238636", "logo_url": "..."}
    custom_message = Column(String)
    client_id = Column(String, ForeignKey("clients.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ================================================================
# PYDANTIC MODELS (API validation)
# ================================================================

class Language(str, Enum):
    RO = "ro-RO"
    EN_US = "en-US"
    EN_GB = "en-GB"
    DE = "de-DE"
    FR = "fr-FR"
    ES = "es-ES"

class ToneOfVoice(str, Enum):
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    URGENT = "urgent"
    LUXURY = "luxury"
    AUTHORITATIVE = "authoritative"
    EMPATHETIC = "empathetic"
    CASUAL = "casual"
    INSPIRATIONAL = "inspirational"
    HUMOROUS = "humorous"

class CampaignObjective(str, Enum):
    AWARENESS = "awareness"
    SALES = "sales"
    TRAFFIC = "traffic"
    ENGAGEMENT = "engagement"

class OnboardRequest(BaseModel):
    # Required fields
    client_name: str = Field(..., min_length=1, max_length=100)
    website_url: str = Field(..., pattern=r"^https?://.+")
    industry: str = Field(..., min_length=1)
    daily_budget: float = Field(..., ge=5, le=10000, description="Daily budget in Euros (€)")
    target_geo: List[str] = Field(..., min_items=1)
    
    # Optional fields with defaults
    language: Language = Language.EN_US
    tone_of_voice: ToneOfVoice = ToneOfVoice.PROFESSIONAL
    cultural_triggers: List[str] = Field(default_factory=list)
    llm_backend: str = Field(default="cloud", pattern="^(cloud)$")
    platform: str = Field(default="auto", pattern="^(auto|google|meta)$")
    objective: CampaignObjective = CampaignObjective.SALES
    special_events: List[str] = Field(default_factory=list)
    product_keywords: List[str] = Field(default_factory=list)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_days: Optional[int] = Field(default=None, ge=1, le=365)

    @validator('daily_budget')
    def validate_budget(cls, v):
        if v < 5:
            raise ValueError('Daily budget must be at least €5')
        return v

class CreativeAsset(BaseModel):
    headline: str = Field(..., max_length=30)
    description: str = Field(..., max_length=90)
    image_prompt: Optional[str] = None

class CampaignResponse(BaseModel):
    campaign_id: str
    status: str
    message: str


class ClientCreate(BaseModel):
    name: str = Field(..., min_length=1)
    industry: Optional[str] = ""
    website: Optional[str] = ""
    logo_url: Optional[str] = ""
    billing_email: Optional[str] = ""
    billing_info: Optional[dict] = Field(default_factory=dict)
    settings: Optional[dict] = Field(default_factory=dict)
    platform_status: Optional[str] = "inactive"
    google_ads_developer_token: Optional[str] = ""
    google_ads_client_id: Optional[str] = ""
    google_ads_client_secret: Optional[str] = ""
    google_ads_refresh_token: Optional[str] = ""
    google_ads_customer_id: Optional[str] = ""
    meta_app_id: Optional[str] = ""
    meta_app_secret: Optional[str] = ""
    meta_access_token: Optional[str] = ""
    meta_ad_account_id: Optional[str] = ""
    google_ads_configured: Optional[bool] = False
    meta_ads_configured: Optional[bool] = False
    agent_llm_settings: Optional[dict] = Field(default_factory=dict)
    image_generation_preferences: Optional[dict] = Field(default_factory=dict)
    default_budget: Optional[float] = None


