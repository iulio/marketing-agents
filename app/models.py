from pydantic import BaseModel, Field, validator
from typing import List, Optional
from enum import Enum

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

class OnboardRequest(BaseModel):
    client_name: str = Field(..., min_length=1, max_length=100)
    website_url: str = Field(..., pattern=r"^https?://.+")
    language: Language = Language.RO
    industry: str = Field(..., min_length=1)
    daily_budget: float = Field(..., gt=0, le=10000)
    target_geo: List[str] = Field(..., min_items=1)
    tone_of_voice: ToneOfVoice = ToneOfVoice.FRIENDLY
    cultural_triggers: List[str] = Field(default_factory=list)
    llm_backend: str = Field(default="foundry", pattern="^(foundry|local)$")

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