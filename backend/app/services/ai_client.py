import json
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("AIClient")


class AIClient:
    """OpenAI-compatible client with structured JSON outputs."""

    def __init__(self) -> None:
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url.rstrip("/")
        self.model = settings.openai_model

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not self.enabled:
            return {}

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception as exc:
            logger.log("ai_error", f"AI request failed: {exc}")
            return {}


ai_client = AIClient()
