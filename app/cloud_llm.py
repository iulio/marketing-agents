# app/cloud_llm.py
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from google import genai
from google.genai import types


@dataclass
class LLMResponse:
    content: str


class CloudLLM:
    """Small adapter that exposes the invoke() shape used by the agents."""

    def __init__(self, temperature: float = 0.7, model: Optional[str] = None):
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", os.getenv("GCP_LOCATION", "global"))
        # model param takes precedence over env var
        self.model = model or os.getenv("GEMINI_MODEL", os.getenv("CLOUD_LLM_MODEL", "gemini-2.5-flash"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "4096"))
        self.temperature = temperature

        if not self.project_id:
            raise RuntimeError("GCP_PROJECT_ID is required for Vertex AI Gemini calls")

        self.client = genai.Client(
            vertexai=True,
            project=self.project_id,
            location=self.location,
        )

    def invoke(self, prompt: str) -> LLMResponse:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=self.max_tokens,
                temperature=self.temperature,
                response_mime_type="application/json",
            ),
        )
        return LLMResponse(content=response.text or "")


def extract_json_object(text: str) -> Dict[str, Any] | None:
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        return None
    return json.loads(text[start:end])


def get_cloud_llm(temperature: float = 0.7, model: Optional[str] = None) -> CloudLLM:
    return CloudLLM(temperature=temperature, model=model)
