import httpx
import time
from typing import Optional
from .llm import LLMProvider, LLMResponse, TokenUsage

class OpenAIProvider(LLMProvider):
    def __init__(self, model: str, config: dict):
        super().__init__(model, config)
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")

    async def generate(self, prompt: str, system: Optional[str] = None, json_mode: bool = False) -> LLMResponse:
        start = time.perf_counter()
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": self.model, "messages": messages, "temperature": 0.7, "max_tokens": 2000}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            async with httpx.AsyncClient(timeout=self.config.get("timeout", 60)) as client:
                response = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                latency_ms = (time.perf_counter() - start) * 1000
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = data.get("usage", {})
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)
                cost = (input_tokens * 0.00001) + (output_tokens * 0.00003)
                return LLMResponse(
                    content=content,
                    usage=TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens, estimated_cost=cost),
                    model=self.model,
                    provider="openai",
                    latency_ms=latency_ms,
                    success=True,
                )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            return LLMResponse(content="", usage=TokenUsage(), model=self.model, provider="openai", latency_ms=latency_ms, success=False, error=str(e))

    async def health_check(self) -> bool:
        return bool(self.api_key)
