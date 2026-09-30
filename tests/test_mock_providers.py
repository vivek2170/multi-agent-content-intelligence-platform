import pytest
import asyncio
from backend.app.providers.mock_llm import MockLLMProvider
from backend.app.providers.mock_search import MockSearchProvider

@pytest.mark.asyncio
async def test_mock_llm_generate():
    provider = MockLLMProvider(model="mock", config={})
    response = await provider.generate("Create a plan", system="planner", json_mode=True)
    assert response.success is True
    assert response.provider == "mock"
    assert response.usage.total_tokens >= 0

@pytest.mark.asyncio
async def test_mock_search():
    provider = MockSearchProvider()
    results = await provider.search("AI")
    assert len(results) == 5
    assert results[0].url.startswith("https://")
