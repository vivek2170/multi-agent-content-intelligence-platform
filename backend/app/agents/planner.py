import json
import time
from typing import Dict, Any
from .base import BaseAgent
from ..models.schemas import AgentMetrics, Platform

class PlannerAgent(BaseAgent):
    async def run(self, state: Dict[str, Any], iteration: int = 0) -> Dict[str, Any]:
        start = time.perf_counter()
        request = state["request"]
        system = (
            "You are a content planner. Return ONLY valid JSON with keys: "
            "topic, audience, platform, content_goal, research_questions (array of strings), "
            "required_sections (array of strings), keywords (array of strings), estimated_length (int), tone_guidelines (string)."
        )
        prompt = (
            f"Topic: {request['topic']}\nAudience: {request['audience']}\nPlatform: {request['platform']}\n"
            f"Tone: {request['tone']}\nLength: {request['length']}\nPosts: {request['posts']}\nKeywords: {request['keywords']}\n"
            "Create a concise plan for the requested output."
        )
        response = await self.llm.generate(prompt=prompt, system=system, json_mode=True)
        metrics = await self._metrics("planner", iteration, start, response.usage.input_tokens, response.usage.output_tokens, response.success, response.error)
        state.setdefault("metrics", []).append(metrics)
        if not response.success:
            state["errors"].append(response.error or "Planner failed")
            state["status"] = "FAILED"
            return state
        try:
            plan = json.loads(response.content)
        except Exception as e:
            state["errors"].append(f"Planner JSON parse failed: {e}")
            state["status"] = "FAILED"
            return state
        state["plan"] = plan
        state["status"] = "RESEARCHING"
        state["current_agent"] = "researcher"
        return state
