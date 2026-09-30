from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel
import time

class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0

class LLMResponse(BaseModel):
    content: str
    usage: TokenUsage
    model: str
    provider: str
    latency_ms: float
    success: bool = True
    error: Optional[str] = None

class LLMProvider(ABC):
    def __init__(self, model: str, config: dict):
        self.model = model
        self.config = config

    @abstractmethod
    async def generate(self, prompt: str, system: Optional[str] = None, json_mode: bool = False) -> LLMResponse:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass
