from typing import List, Optional
from .search import SearchProvider, SearchResult

class MockSearchProvider(SearchProvider):
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        return [
            SearchResult(title=f"Result {i+1} for {query}", url=f"https://example.com/{i+1}", snippet=f"Mock snippet for {query}", source_type="web")
            for i in range(max_results)
        ]

    async def health_check(self) -> bool:
        return True
