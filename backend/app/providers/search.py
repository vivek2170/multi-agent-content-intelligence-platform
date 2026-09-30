from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    source_type: str = "web"

class SearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass
