import json
import time
from typing import Dict, Any
from .base import BaseAgent
from ..models.schemas import AgentMetrics

class FinalFactCheckerAgent(BaseAgent):
    async def run(self, state: Dict[str, Any], iteration: int = 0) -> Dict[str, Any]:
        start = time.perf_counter()
        system = (
            "You are a final validator. Return ONLY valid JSON with keys: final_verdict (APPROVED|NEEDS_REVISION), remaining_issues (array of strings), confidence (0-1)."
        )
        drafts = state.get("drafts") or []
        text = "\n\n".join(d.get("content", "") for d in drafts)
        prompt = f"Final validation for:\n{text}\nReturn approval verdict."
        response = await self.llm.generate(prompt=prompt, system=system, json_mode=True)
        metrics = await self._metrics("final_fact_checker", iteration, start, response.usage.input_tokens, response.usage.output_tokens, response.success, response.error)
        state.setdefault("metrics", []).append(metrics)
        if not response.success:
            state["errors"].append(response.error or "Final fact checker failed")
            state["status"] = "FAILED"
            return state
        try:
            data = json.loads(response.content)
            verdict = data.get("final_verdict", "NEEDS_REVISION")
            if verdict == "APPROVED":
                state["status"] = "APPROVED"
            else:
                state["status"] = "NEEDS_HUMAN_REVIEW"
            state["final_verdict"] = data
            state["current_agent"] = None
            state["completed_at"] = time.time()
            return state
        except Exception as e:
            state["errors"].append(f"Final fact checker JSON parse failed: {e}")
            state["status"] = "FAILED"
            return state
