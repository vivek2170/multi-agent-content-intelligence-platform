from abc import ABC, abstractmethod
from typing import Optional
from ..models.schemas import AgentMetrics

class BaseAgent(ABC):
    def __init__(self, llm_provider, search_provider, config: dict):
        self.llm = llm_provider
        self.search = search_provider
        self.config = config

    @abstractmethod
    async def run(self, state: dict, iteration: int = 0) -> dict:
        pass

    async def _metrics(self, name: str, iteration: int, start: float, input_tokens: int, output_tokens: int, success: bool = True, error: Optional[str] = None) -> AgentMetrics:
        import time
        latency_ms = int((time.perf_counter() - start) * 1000)
        return AgentMetrics(agent=name, iteration=iteration, latency_ms=latency_ms, input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=input_tokens + output_tokens, success=success, error=error)
