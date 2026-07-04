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
    daily_budget: float = Field(..., gt=0, le=10000)
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

    @validator('daily_budget')
    def validate_budget(cls, v):
        if v < 5:
            raise ValueError('Daily budget must be at least $5')
        return v

class CreativeAsset(BaseModel):
    headline: str = Field(..., max_length=30)
    description: str = Field(..., max_length=90)
    image_prompt: Optional[str] = None

class CampaignResponse(BaseModel):
    campaign_id: str
    status: str
    message: str
