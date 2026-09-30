import json
from datetime import datetime
from sqlalchemy.orm import Session
from ..models.database import RunRecord, AgentMetricRecord, SourceRecord
from ..models.schemas import Source

class DatabaseService:
    def __init__(self, db: Session):
        self.db = db

    def create_run(self, run_id: str, request: dict, status: str, current_agent: str = None):
        provider = request.get("provider") if isinstance(request, dict) else None
        model = request.get("model") if isinstance(request, dict) else None
        if not model and provider == "ollama":
            model = "llama3.2:3b"
        run = RunRecord(run_id=run_id, status=status, request=json.dumps(request), llm_provider=provider, llm_model=model, current_agent=current_agent)
        self.db.add(run)
        self.db.commit()
        return run

    def complete_run(self, run_id: str, status: str, final_content: str, quality_score: float, metrics: list, errors: list, sources: list, current_agent: str = None):
        run = self.db.query(RunRecord).filter(RunRecord.run_id == run_id).first()
        if not run:
            return
        run.status = status
        run.final_content = final_content
        run.quality_score = quality_score
        run.errors = json.dumps(errors)
        run.completed_at = datetime.utcnow()
        run.current_agent = current_agent
        total_tokens = sum(getattr(m, 'total_tokens', 0) for m in metrics)
        total_cost = sum(getattr(m, 'estimated_cost', 0.0) for m in metrics)
        total_latency = sum(getattr(m, 'latency_ms', 0) for m in metrics)
        run.total_tokens = total_tokens
        run.total_cost = total_cost
        run.total_latency_ms = total_latency
        run.revision_count = sum(1 for m in metrics if getattr(m, 'agent', None) == 'editor' and getattr(m, 'iteration', 0) > 0)
        for m in metrics:
            self.db.add(AgentMetricRecord(run_id=run_id, agent=getattr(m, 'agent', ''), iteration=getattr(m, 'iteration', 0), latency_ms=getattr(m, 'latency_ms', 0), input_tokens=getattr(m, 'input_tokens', 0), output_tokens=getattr(m, 'output_tokens', 0), total_tokens=getattr(m, 'total_tokens', 0), estimated_cost=getattr(m, 'estimated_cost', 0.0), success=1 if getattr(m, 'success', True) else 0, error=getattr(m, 'error', None)))
        for s in sources:
            if isinstance(s, Source):
                self.db.add(SourceRecord(run_id=run_id, url=s.url, title=s.title, source_type=s.source_type, content=s.content))
        self.db.commit()

    def get_run(self, run_id: str):
        return self.db.query(RunRecord).filter(RunRecord.run_id == run_id).first()

    def get_metrics(self, run_id: str):
        run = self.get_run(run_id)
        if not run:
            return None
        return {
            "run_id": run_id,
            "total_latency_ms": run.total_latency_ms,
            "total_tokens": run.total_tokens,
            "total_cost": run.total_cost,
            "agent_metrics": [
                {
                    "agent": m.agent,
                    "iteration": m.iteration,
                    "latency_ms": m.latency_ms,
                    "input_tokens": m.input_tokens,
                    "output_tokens": m.output_tokens,
                    "total_tokens": m.total_tokens,
                    "estimated_cost": m.estimated_cost,
                    "success": bool(m.success),
                    "error": m.error,
                }
                for m in run.agent_metrics
            ],
        }

    def get_sources(self, run_id: str):
        run = self.get_run(run_id)
        if not run:
            return []
        return [{"url": s.url, "title": s.title, "source_type": s.source_type, "content": s.content} for s in run.sources]
