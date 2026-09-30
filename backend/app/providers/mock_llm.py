import time
import json
import re
from typing import Optional
from .llm import LLMProvider, LLMResponse, TokenUsage

class MockLLMProvider(LLMProvider):
    def __init__(self, model: str, config: dict):
        super().__init__(model, config)

    async def generate(self, prompt: str, system: Optional[str] = None, json_mode: bool = False) -> LLMResponse:
        start = time.perf_counter()
        latency_ms = (time.perf_counter() - start) * 1000 + 25
        prompt_lower = prompt.lower()
        system_lower = (system or "").lower()

        if "planner" in system_lower or "content plan" in prompt_lower:
            topic_match = re.search(r"topic[:\s]+(.+?)(?:\n|$)", prompt, re.IGNORECASE)
            topic = topic_match.group(1).strip() if topic_match else "the requested topic"
            content = json.dumps({
                "topic": topic,
                "audience": "General",
                "platform": "LinkedIn",
                "content_goal": "Inform",
                "research_questions": [f"What is {topic}?", f"Why does {topic} matter?"],
                "required_sections": ["Introduction", "Body", "Conclusion"],
                "keywords": [topic],
                "estimated_length": 500,
                "tone_guidelines": "Professional"
            })
        elif "writer" in system_lower or "return only valid json with key 'posts'" in prompt_lower:
            topic_match = re.search(r"about\s+(.+?)\s+for", prompt_lower)
            topic = topic_match.group(1).strip() if topic_match else "the topic"
            platform_match = re.search(r"write\s+\d+\s+(.+?)\s+post", prompt_lower)
            platform = platform_match.group(1).strip() if platform_match else "social media"
            num_posts = 1
            m = re.search(r"write\s+(\d+)", prompt_lower)
            if not m:
                m = re.search(r"generate exactly (\d+)", prompt_lower)
            if m:
                num_posts = int(m.group(1))
            tone_match = re.search(r"tone[:\s]+(.+?)(?:\.|$)", prompt, re.IGNORECASE)
            tone = tone_match.group(1).strip() if tone_match else "professional"
            posts = []
            for i in range(num_posts):
                posts.append(
                    f"{tone.capitalize()} {platform} post {i+1} about {topic}. "
                    f"This post explores key insights and actionable takeaways for the target audience. "
                    f"#{topic.replace(' ', '')} #Content #Professional"
                )
            content = json.dumps({"posts": posts})
        elif "researcher" in system_lower or "research" in prompt_lower:
            topic_match = re.search(r"topic[:\s]+(.+?)(?:\n|$)", prompt, re.IGNORECASE)
            topic = topic_match.group(1).strip() if topic_match else "the topic"
            content = json.dumps({
                "claims": [
                    {"claim": f"{topic} is increasingly relevant", "evidence": "Industry analysis shows growing impact", "source": {"url": "https://example.com/1", "title": "Industry Study", "source_type": "web"}, "confidence": 0.9},
                    {"claim": f"Organizations are investing in {topic}", "evidence": "Survey data indicates increased adoption", "source": {"url": "https://example.com/2", "title": "Market Survey", "source_type": "web"}, "confidence": 0.85}
                ],
                "sources": [
                    {"url": "https://example.com/1", "title": "Industry Study", "source_type": "web"},
                    {"url": "https://example.com/2", "title": "Market Survey", "source_type": "web"}
                ]
            })
        elif "fact" in system_lower or "fact" in prompt_lower:
            content = json.dumps({
                "fact_check_results": [
                    {"claim": "Industry impact verified", "status": "VERIFIED", "evidence": "Found in source", "source": {"url": "https://example.com/1", "title": "Industry Study"}, "confidence": 0.9},
                    {"claim": "Adoption trend confirmed", "status": "PARTIALLY_VERIFIED", "evidence": "Partially supported", "source": {"url": "https://example.com/2", "title": "Market Survey"}, "confidence": 0.7}
                ],
                "total_claims": 2,
                "supported_claims": 1,
                "partially_supported": 1,
                "unsupported_claims": 0,
                "contradicted": 0,
                "overall_confidence": 0.8,
                "critical_issues": []
            })
        elif "editor" in system_lower or "evaluat" in prompt_lower:
            content = json.dumps({
                "score": 85.0,
                "passed": True,
                "issues": ["Minor wording tweak"],
                "revision_instructions": None
            })
        elif "final fact" in system_lower or "final validator" in system_lower:
            content = json.dumps({
                "final_verdict": "APPROVED",
                "remaining_issues": [],
                "confidence": 0.9
            })
        else:
            content = "Mock generated content for: " + prompt[:100]
        input_tokens = len(prompt.split()) // 4
        output_tokens = len(content.split()) // 4
        return LLMResponse(
            content=content,
            usage=TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=input_tokens + output_tokens, estimated_cost=0.0),
            model=self.model,
            provider="mock",
            latency_ms=latency_ms,
            success=True,
        )

    async def health_check(self) -> bool:
        return True
