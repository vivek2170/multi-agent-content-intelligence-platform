import uuid
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from ..models.schemas import ContentRequest, CreateResponse, StatusResponse, MetricsResponse, ErrorResponse, WorkflowStatus
from ..database import get_db, SessionLocal
from ..services.database import DatabaseService
from ..workflow.graph import ContentWorkflow
from ..config import settings

logger = logging.getLogger("content")

router = APIRouter(prefix="/api/content", tags=["content"])


def get_workflow():
    raise HTTPException(status_code=503, detail="Workflow not initialized")


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/provider/health")
async def provider_health():
    provider_name = settings.LLM_PROVIDER.lower()
    provider_info = {"provider": provider_name, "model": settings.LLM_MODEL, "base_url": settings.OLLAMA_BASE_URL}

    if provider_name == "ollama":
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                provider_info["server_reachable"] = resp.status_code == 200
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m["name"] for m in data.get("models", [])]
                    provider_info["installed_models"] = models
                    provider_info["model_installed"] = settings.LLM_MODEL in models
                else:
                    provider_info["installed_models"] = []
                    provider_info["model_installed"] = False
        except Exception as e:
            provider_info["server_reachable"] = False
            provider_info["installed_models"] = []
            provider_info["model_installed"] = False
            provider_info["error"] = str(e)
    else:
        provider_info["server_reachable"] = True
        provider_info["installed_models"] = [settings.LLM_MODEL]
        provider_info["model_installed"] = True

    return provider_info


@router.post("/generate", response_model=CreateResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def generate(request: ContentRequest, background_tasks: BackgroundTasks):
    run_id = str(uuid.uuid4())
    wf = workflow_factory(request.model_dump())
    background_tasks.add_task(run_workflow, run_id, request.model_dump(), wf)
    return CreateResponse(run_id=run_id, status=WorkflowStatus.CREATED)


@router.get("/runs/{run_id}/status", response_model=StatusResponse, responses={404: {"model": ErrorResponse}})
async def run_status(run_id: str, db: Session = Depends(get_db)):
    db_service = DatabaseService(db)
    run = db_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return StatusResponse(run_id=run.run_id, status=WorkflowStatus(run.status), current_agent=None, revision_count=run.revision_count, quality_score=run.quality_score, created_at=run.created_at, updated_at=run.updated_at)


@router.get("/runs/{run_id}/trace", responses={404: {"model": ErrorResponse}})
async def run_trace(run_id: str, db: Session = Depends(get_db)):
    db_service = DatabaseService(db)
    run = db_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "run_id": run.run_id,
        "status": run.status,
        "request": json.loads(run.request) if run.request else {},
        "final_content": run.final_content,
        "posts": json.loads(run.final_content) if run.final_content else [],
        "quality_score": run.quality_score,
        "sources": db_service.get_sources(run_id),
        "metrics": db_service.get_metrics(run_id).get("agent_metrics", []),
        "errors": json.loads(run.errors) if run.errors else [],
        "created_at": run.created_at.isoformat(),
        "updated_at": run.updated_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "llm_provider": run.llm_provider,
        "llm_model": run.llm_model,
    }


@router.get("/runs/{run_id}/metrics", response_model=MetricsResponse, responses={404: {"model": ErrorResponse}})
async def run_metrics(run_id: str, db: Session = Depends(get_db)):
    db_service = DatabaseService(db)
    data = db_service.get_metrics(run_id)
    if not data:
        raise HTTPException(status_code=404, detail="Run not found")
    return MetricsResponse(**data)


async def run_workflow(run_id: str, request: dict, wf: ContentWorkflow):
    db = None
    try:
        logger.info("run_workflow start run_id=%s", run_id)
        db = SessionLocal()
        db_service = DatabaseService(db)
        db_service.create_run(run_id, request, WorkflowStatus.CREATED.value)
        logger.info("run_workflow executing run_id=%s", run_id)
        try:
            result = await wf.execute(run_id, request)
            logger.info("run_workflow completed run_id=%s status=%s", run_id, result.get("status"))
            status = result.get("status", "FAILED")
            drafts = result.get("drafts", [])
            post_contents = [d.get("content", "") for d in drafts]
            final_content = json.dumps(post_contents)
            research = result.get("research")
            if research is not None:
                sources = getattr(research, "sources", None)
                if sources is None and isinstance(research, dict):
                    sources = research.get("sources", [])
                else:
                    sources = list(sources or [])
            else:
                sources = []
            metrics = result.get("metrics", [])
            errors = result.get("errors", [])
            db_service.complete_run(run_id, status, final_content, result.get("quality_score", 0.0), metrics, errors, sources)
            logger.info("run_workflow saved run_id=%s posts=%s", run_id, len(post_contents))
        except Exception as e:
            logger.exception("run_workflow workflow error run_id=%s: %s", run_id, e)
            db_service.complete_run(run_id, "FAILED", "", 0.0, [], [str(e)], [])
    except Exception as e:
        logger.exception("run_workflow outer error run_id=%s: %s", run_id, e)
    finally:
        if db is not None:
            db.close()
