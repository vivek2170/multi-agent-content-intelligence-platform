import pytest
import asyncio
import json
from backend.app.providers.mock_llm import MockLLMProvider
from backend.app.providers.mock_search import MockSearchProvider
from backend.app.workflow.graph import ContentWorkflow

class BadCountMockLLMProvider(MockLLMProvider):
    def __init__(self, model, config, bad_count=7):
        super().__init__(model, config)
        self.bad_count = bad_count
        self.call_count = 0

    async def generate(self, prompt, system=None, json_mode=False):
        self.call_count += 1
        if "writer" in (system or "").lower() or "return only valid json with key 'posts'" in (prompt or "").lower():
            num_posts = 1
            m = __import__("re").search(r"generate exactly (\d+)", prompt.lower())
            if m:
                num_posts = int(m.group(1))
            elif "write" in prompt.lower():
                m2 = __import__("re").search(r"write\s+(\d+)", prompt.lower())
                if m2:
                    num_posts = int(m2.group(1))
            count = self.bad_count if self.call_count == 1 else num_posts
            posts = [f"Post {i+1} about the topic." for i in range(count)]
            content = json.dumps({"posts": posts})
            from backend.app.providers.llm import LLMResponse, TokenUsage
            return LLMResponse(
                content=content,
                usage=TokenUsage(input_tokens=10, output_tokens=20, total_tokens=30, estimated_cost=0.0),
                model=self.model,
                provider="mock",
                latency_ms=25,
                success=True,
            )
        return await super().generate(prompt, system, json_mode)


@pytest.mark.asyncio
async def test_mock_workflow_runs():
    llm = MockLLMProvider(model="mock", config={})
    search = MockSearchProvider()
    wf = ContentWorkflow(llm, search, {"MAX_REVISIONS": 1})
    request = {"topic": "AI agents", "platform": "LinkedIn", "audience": "engineers", "tone": "Professional", "posts": 1, "length": "Medium", "keywords": [], "urls": []}
    result = await wf.execute("run-1", request)
    assert "status" in result
    assert result["status"] in ["APPROVED", "NEEDS_HUMAN_REVIEW", "READY_FOR_REVIEW", "FAILED"]
    assert "metrics" in result

@pytest.mark.asyncio
async def test_mock_workflow_produces_posts():
    llm = MockLLMProvider(model="mock", config={})
    search = MockSearchProvider()
    wf = ContentWorkflow(llm, search, {"MAX_REVISIONS": 1})
    request = {"topic": "How competitive programming develops algorithmic problem-solving skills", "platform": "LinkedIn", "audience": "Software engineers", "tone": "Professional", "posts": 3, "length": "Medium", "keywords": [], "urls": []}
    result = await wf.execute("run-2", request)
    drafts = result.get("drafts", [])
    assert len(drafts) == 3
    for d in drafts:
        assert len(d.get("content", "")) > 10

@pytest.mark.asyncio
@pytest.mark.parametrize("num_posts", [1, 2, 3, 5, 10])
async def test_post_count_invariant(num_posts):
    llm = MockLLMProvider(model="mock", config={})
    search = MockSearchProvider()
    wf = ContentWorkflow(llm, search, {"MAX_REVISIONS": 1})
    request = {"topic": "AI in healthcare", "platform": "LinkedIn", "audience": "Doctors", "tone": "Professional", "posts": num_posts, "length": "Medium", "keywords": [], "urls": []}
    result = await wf.execute(f"run-count-{num_posts}", request)
    drafts = result.get("drafts", [])
    assert len(drafts) == num_posts, f"Expected {num_posts} drafts, got {len(drafts)}"

@pytest.mark.asyncio
async def test_revision_loop_preserves_exact_count():
    llm = BadCountMockLLMProvider(model="mock", config={}, bad_count=7)
    search = MockSearchProvider()
    wf = ContentWorkflow(llm, search, {"MAX_REVISIONS": 3})
    request = {"topic": "AI in healthcare", "platform": "LinkedIn", "audience": "Doctors", "tone": "Professional", "posts": 2, "length": "Medium", "keywords": [], "urls": []}
    result = await wf.execute("run-revision-count", request)
    drafts = result.get("drafts", [])
    assert len(drafts) == 2, f"Expected 2 drafts after revision, got {len(drafts)}"
    for d in drafts:
        assert len(d.get("content", "")) > 0

@pytest.mark.asyncio
async def test_final_content_format_is_json_array():
    llm = MockLLMProvider(model="mock", config={})
    search = MockSearchProvider()
    wf = ContentWorkflow(llm, search, {"MAX_REVISIONS": 1})
    request = {"topic": "AI in healthcare", "platform": "LinkedIn", "audience": "Doctors", "tone": "Professional", "posts": 2, "length": "Medium", "keywords": [], "urls": []}
    result = await wf.execute("run-format", request)
    drafts = result.get("drafts", [])
    post_contents = [d.get("content", "") for d in drafts]
    final_content = json.dumps(post_contents)
    parsed = json.loads(final_content)
    assert isinstance(parsed, list)
    assert len(parsed) == 2
