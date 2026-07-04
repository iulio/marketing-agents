# app/cloud_llm.py
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List

from anthropic import AnthropicVertex


@dataclass
class LLMResponse:
    content: str


class CloudLLM:
    """Small adapter that exposes the invoke() shape used by the agents."""

    def __init__(self, temperature: float = 0.7):
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.region = os.getenv("GCP_AGENT_PLATFORM_REGION", os.getenv("GCP_LOCATION", "global"))
        self.model = os.getenv("AGENT_PLATFORM_MODEL", "claude-fable-5")
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "4096"))
        self.temperature = temperature

        if not self.project_id:
            raise RuntimeError("GCP_PROJECT_ID is required for Agent Platform LLM calls")

        self.client = AnthropicVertex(project_id=self.project_id, region=self.region)

    def invoke(self, prompt: str) -> LLMResponse:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return LLMResponse(content=self._content_to_text(message.content))

    @staticmethod
    def _content_to_text(content: List[Any]) -> str:
        parts = []
        for block in content:
            text = getattr(block, "text", None)
            if text is not None:
                parts.append(text)
                continue
            if isinstance(block, Dict) and block.get("text"):
                parts.append(block["text"])
                continue
            parts.append(str(block))
        return "\n".join(parts)


def extract_json_object(text: str) -> Dict[str, Any] | None:
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        return None
    return json.loads(text[start:end])


def get_cloud_llm(temperature: float = 0.7) -> CloudLLM:
    return CloudLLM(temperature=temperature)
