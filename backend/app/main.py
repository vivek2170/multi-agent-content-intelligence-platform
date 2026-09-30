from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from .config import settings
from .database import engine, Base
from .routes.content import router as content_router
from .routes import content as content_module
from .providers.llm import LLMProvider
from .providers.ollama_provider import OllamaProvider
from .providers.openai_provider import OpenAIProvider
from .providers.mock_llm import MockLLMProvider
from .providers.search import SearchProvider
from .providers.mock_search import MockSearchProvider
from .workflow.graph import ContentWorkflow

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ContentForge", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api/config")
async def app_config():
    return {
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
        "search_provider": settings.SEARCH_PROVIDER,
        "max_revisions": settings.MAX_REVISIONS,
    }

app.include_router(content_router)

frontend_path = Path(__file__).resolve().parents[2] / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


def _build_llm_provider(provider: str | None = None, model: str | None = None) -> LLMProvider:
    selected = (provider or settings.LLM_PROVIDER).lower()
    if selected == "openai":
        return OpenAIProvider(
            model=model or settings.OPENAI_MODEL,
            config={"api_key": settings.OPENAI_API_KEY, "base_url": "https://api.openai.com/v1", "timeout": settings.LLM_TIMEOUT_SECONDS},
        )
    if selected == "mock":
        return MockLLMProvider(model=model or settings.LLM_MODEL, config={"timeout": settings.LLM_TIMEOUT_SECONDS})
    return OllamaProvider(
        model=model or settings.LLM_MODEL or "llama3.2:3b",
        config={"base_url": settings.OLLAMA_BASE_URL, "timeout": settings.LLM_TIMEOUT_SECONDS},
    )


def _build_search_provider() -> SearchProvider:
    if settings.SEARCH_PROVIDER.lower() == "mock":
        return MockSearchProvider()
    return MockSearchProvider()


def create_workflow(request: dict) -> ContentWorkflow:
    llm = _build_llm_provider(request.get("provider"), request.get("model"))
    search = _build_search_provider()
    return ContentWorkflow(llm, search, {"MAX_REVISIONS": settings.MAX_REVISIONS, "WORKFLOW_TIMEOUT_SECONDS": settings.WORKFLOW_TIMEOUT_SECONDS})


content_module.provider_factory = _build_llm_provider
content_module.search_provider_factory = _build_search_provider
content_module.workflow_factory = create_workflow
