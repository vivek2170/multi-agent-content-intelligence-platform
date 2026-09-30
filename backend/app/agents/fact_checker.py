import json
import time
from typing import Dict, Any
from .base import BaseAgent
from ..models.schemas import AgentMetrics, Claim, ClaimStatus, ResearchResult

class FactCheckerAgent(BaseAgent):
    async def run(self, state: Dict[str, Any], iteration: int = 0) -> Dict[str, Any]:
        start = time.perf_counter()
        research: ResearchResult = state.get("research") or ResearchResult()
        system = (
            "You are a fact checker. Return ONLY valid JSON with keys: fact_check_results (array of {claim, status: VERIFIED|PARTIALLY_VERIFIED|UNSUPPORTED|CONTRADICTED, evidence, confidence})."
        )
        claims_text = "\n".join(f"- {c.claim}" for c in research.claims)
        prompt = f"Verify these claims:\n{claims_text}\nSources:\n" + "\n".join(f"- {s.url}: {s.title}" for s in research.sources)
        response = await self.llm.generate(prompt=prompt, system=system, json_mode=True)
        metrics = await self._metrics("fact_checker", iteration, start, response.usage.input_tokens, response.usage.output_tokens, response.success, response.error)
        state.setdefault("metrics", []).append(metrics)
        if not response.success:
            state["errors"].append(response.error or "Fact checker failed")
            state["status"] = "FAILED"
            return state
        try:
            data = json.loads(response.content)
            updated_claims = []
            claim_map = {c.claim: c for c in research.claims}
            for item in data.get("fact_check_results", []):
                original = claim_map.get(item.get("claim"))
                if original:
                    original.status = ClaimStatus(item.get("status", original.status))
                    original.confidence = float(item.get("confidence", original.confidence))
                    original.evidence = item.get("evidence", original.evidence)
                    updated_claims.append(original)
            state["research"] = ResearchResult(claims=updated_claims, sources=research.sources)
            state["verified_claims"] = [c for c in updated_claims if c.status == ClaimStatus.VERIFIED]
            state["status"] = "WRITING"
            state["current_agent"] = "writer"
            return state
        except Exception as e:
            state["errors"].append(f"Fact checker JSON parse failed: {e}")
            state["status"] = "FAILED"
            return state
