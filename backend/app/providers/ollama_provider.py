import httpx
import json
import time
from typing import Optional
from .llm import LLMProvider, LLMResponse, TokenUsage

class OllamaProvider(LLMProvider):
    def __init__(self, model: str, config: dict):
        super().__init__(model, config)
        self.base_url = config.get("base_url", "http://localhost:11434").rstrip("/")

    async def generate(self, prompt: str, system: Optional[str] = None, json_mode: bool = False) -> LLMResponse:
        start = time.perf_counter()
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 2000},
        }
        if system:
            payload["system"] = system
        if json_mode:
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=self.config.get("timeout", 180)) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                latency_ms = (time.perf_counter() - start) * 1000

                if response.status_code == 404:
                    return LLMResponse(
                        content="",
                        usage=TokenUsage(),
                        model=self.model,
                        provider="ollama",
                        latency_ms=latency_ms,
                        success=False,
                        error=f"Ollama endpoint or model not found: {self.model}",
                    )

                response.raise_for_status()
                data = response.json()
                content = data.get("response", "")
                input_tokens = len(prompt.split()) // 4
                output_tokens = len(content.split()) // 4
                return LLMResponse(
                    content=content,
                    usage=TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=input_tokens + output_tokens, estimated_cost=0.0),
                    model=self.model,
                    provider="ollama",
                    latency_ms=latency_ms,
                    success=True,
                )
        except httpx.HTTPStatusError as e:
            latency_ms = (time.perf_counter() - start) * 1000
            status = e.response.status_code if e.response is not None else "unknown"
            return LLMResponse(
                content="",
                usage=TokenUsage(),
                model=self.model,
                provider="ollama",
                latency_ms=latency_ms,
                success=False,
                error=f"Ollama HTTP {status}: {e.response.text[:200] if e.response is not None else 'no body'}",
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            return LLMResponse(
                content="",
                usage=TokenUsage(),
                model=self.model,
                provider="ollama",
                latency_ms=latency_ms,
                success=False,
                error=f"Ollama request failed: {type(e).__name__}: {e}",
            )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
