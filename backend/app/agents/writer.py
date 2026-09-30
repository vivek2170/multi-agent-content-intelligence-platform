import json
import time
from typing import Dict, Any
from .base import BaseAgent
from ..models.schemas import AgentMetrics, Platform, Draft

class WriterAgent(BaseAgent):
    async def run(self, state: Dict[str, Any], iteration: int = 0) -> Dict[str, Any]:
        start = time.perf_counter()
        request = state["request"]
        plan = state.get("plan") or {}
        research = state.get("research") or {}
        platform = Platform(request.get("platform", "LinkedIn"))
        posts = int(request.get("posts", 1))
        claims = getattr(research, "claims", None)
        if claims is None and isinstance(research, dict):
            claims = research.get("claims", [])
        claims_text = "\n".join(f"- {c.claim}" for c in (claims or []))

        for attempt in range(2):
            system = (
                "You are a platform-aware content writer. Return ONLY valid JSON with key 'posts' as an array of strings. "
                "Each item should be a complete, original post tailored to the platform, tone, and evidence."
            )
            if attempt == 0:
                prompt = (
                    f"Generate exactly {posts} independent {platform.value} posts about {request['topic']} for {request['audience']}. Tone: {request['tone']}. Length: {request['length']}. "
                    f"Keywords: {request['keywords']}. Use research:\n{claims_text}\n"
                    "Return exactly {num_posts} items in the posts array. Never return more or fewer items. "
                    "Do not split one post into multiple posts. Do not create additional variations.".replace("{num_posts}", str(posts))
                )
            else:
                feedback = state.get("editor_feedback") or {}
                revision_instructions = feedback.get("revision_instructions") or "Improve the posts while maintaining the same count and structure."
                prompt = (
                    f"Revise the {posts} posts. Keep exactly {posts} posts. "
                    f"Topic: {request['topic']}. Platform: {platform.value}. Audience: {request['audience']}. Tone: {request['tone']}. Length: {request['length']}. "
                    f"Keywords: {request['keywords']}. Instructions: {revision_instructions}\n"
                    "Return exactly {num_posts} items in the posts array. Do not add or remove posts.".replace("{num_posts}", str(posts))
                )
            response = await self.llm.generate(prompt=prompt, system=system, json_mode=True)
            metrics = await self._metrics("writer", iteration, start, response.usage.input_tokens, response.usage.output_tokens, response.success, response.error)
            state.setdefault("metrics", []).append(metrics)
            if not response.success:
                state["errors"].append(response.error or "Writer failed")
                state["status"] = "FAILED"
                return state
            try:
                data = json.loads(response.content)
                post_texts = data.get("posts", [])
                if not isinstance(post_texts, list):
                    post_texts = [str(post_texts)]
                if len(post_texts) != posts:
                    if attempt == 0:
                        continue
                    post_texts = (post_texts + [""] * posts)[:posts]
                state["drafts"] = [Draft(content=text, platform=platform, post_index=i + 1).model_dump() for i, text in enumerate(post_texts[:posts])]
                state["status"] = "EDITING"
                state["current_agent"] = "editor"
                return state
            except Exception as e:
                if attempt == 0:
                    continue
                state["errors"].append(f"Writer JSON parse failed: {e}")
                state["status"] = "FAILED"
                return state
        state["errors"].append("Writer failed after retry")
        state["status"] = "FAILED"
        return state
