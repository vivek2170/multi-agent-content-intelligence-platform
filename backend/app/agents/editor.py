import json
import time
from typing import Dict, Any
from .base import BaseAgent
from ..models.schemas import AgentMetrics, EditorFeedback

class EditorAgent(BaseAgent):
    async def run(self, state: Dict[str, Any], iteration: int = 0) -> Dict[str, Any]:
        start = time.perf_counter()
        request = state["request"]
        drafts = state.get("drafts") or []
        research = state.get("research") or {}
        system = (
            "You are an editor. Return ONLY valid JSON with keys: quality_score (0-100), passed (bool), issues (array of strings), revision_instructions (string or null)."
        )
        claims = getattr(research, "claims", None)
        if claims is None and isinstance(research, dict):
            claims = research.get("claims", [])
        claims_text = "\n".join(f"- {c.claim} [{c.status}]" for c in (claims or []))
        drafts_text = "\n\n".join(f"Post {d.get('post_index', i+1)}:\n{d.get('content','')}" for i, d in enumerate(drafts))
        prompt = (
            f"Evaluate {len(drafts)} post(s) for platform {request['platform']} and audience {request['audience']}.\n"
            f"Tone: {request['tone']}\nDrafts:\n{drafts_text}\n\nResearch claims:\n{claims_text}\n"
            "Assess accuracy, clarity, structure, readability, engagement, platform fit, evidence, and instruction compliance."
        )
        response = await self.llm.generate(prompt=prompt, system=system, json_mode=True)
        metrics = await self._metrics("editor", iteration, start, response.usage.input_tokens, response.usage.output_tokens, response.success, response.error)
        state.setdefault("metrics", []).append(metrics)
        if not response.success:
            state["errors"].append(response.error or "Editor failed")
            state["status"] = "FAILED"
            return state
        try:
            data = json.loads(response.content)
            feedback = EditorFeedback(
                quality_score=float(data.get("quality_score", 0)),
                passed=bool(data.get("passed", False)),
                issues=data.get("issues", []),
                revision_instructions=data.get("revision_instructions"),
            )
            state["editor_feedback"] = feedback.model_dump()
            state["quality_score"] = feedback.quality_score
            state["revision_count"] = state.get("revision_count", 0) + 1
            if feedback.passed:
                state["status"] = "READY_FOR_REVIEW"
                state["current_agent"] = "final_fact_checker"
            elif state.get("revision_count", 0) < state.get("max_revisions", 3):
                state["status"] = "REVISION_REQUIRED"
                state["current_agent"] = "writer"
            else:
                state["status"] = "NEEDS_HUMAN_REVIEW"
                state["current_agent"] = "final_fact_checker"
            return state
        except Exception as e:
            state["errors"].append(f"Editor JSON parse failed: {e}")
            state["status"] = "FAILED"
            return state
