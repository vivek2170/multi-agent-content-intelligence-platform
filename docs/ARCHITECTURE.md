# Architecture

## Overview

The platform is split into a small FastAPI backend and a static frontend. The backend owns the workflow, persistence, and provider abstraction. The frontend owns the form, status polling, and results rendering.

```
Frontend
  → FastAPI
  → LangGraph StateGraph
  → Agents
  → Providers
  → SQLite
  → API response
  → Frontend
```

## Backend

### Entry point
`backend/app/main.py` mounts the API router and the frontend static files. It also builds providers and the workflow on demand.

### Configuration
`backend/app/config.py` loads settings from `.env` using `pydantic-settings`.

### Routes
`backend/app/routes/content.py` exposes:
- `/api/content/generate`
- `/api/content/runs/{run_id}/status`
- `/api/content/runs/{run_id}/trace`
- `/api/content/runs/{run_id}/metrics`
- `/api/content/provider/health`

### Workflow
`backend/app/workflow/graph.py` defines `WorkflowState` and the LangGraph graph. The graph is:
1. `planner`
2. `researcher`
3. `fact_checker`
4. `writer`
5. `editor`
6. conditional route from `editor`
7. `final_fact_checker`

## LangGraph Workflow

### WorkflowState
```python
class WorkflowState(TypedDict, total=False):
    run_id: str
    request: Dict[str, Any]
    plan: Dict[str, Any]
    research: Dict[str, Any]
    drafts: list
    editor_feedback: Dict[str, Any]
    revision_count: int
    max_revisions: int
    quality_score: float
    final_content: str
    sources: list
    metrics: list
    errors: list
    status: str
    current_agent: str
    current_iteration: int
```

### Execution
`ContentWorkflow.execute` creates the initial state, then calls `ainvoke` with a timeout. Timeouts are surfaced as `FAILED` with a clear error message.

## Agents

All agents inherit from `BaseAgent` in `backend/app/agents/base.py`.

### Agent interface
```python
class BaseAgent(ABC):
    async def run(self, state: dict, iteration: int = 0) -> dict:
        ...

    async def _metrics(self, name, iteration, start, input_tokens, output_tokens, success, error):
        ...
```

### Agent list
- `planner.py`
- `researcher.py`
- `fact_checker.py`
- `writer.py`
- `editor.py`
- `final_fact_checker.py`

Each agent updates `state` in place and returns it.

## Providers

### LLM providers
- `backend/app/providers/llm.py`: `LLMProvider`, `LLMResponse`, `TokenUsage`
- `backend/app/providers/ollama_provider.py`: Ollama
- `backend/app/providers/openai_provider.py`: OpenAI-compatible
- `backend/app/providers/mock_llm.py`: deterministic mock

### Search providers
- `backend/app/providers/search.py`: `SearchProvider`, `SearchResult`
- `backend/app/providers/mock_search.py`: deterministic mock

## Database

### Models
`backend/app/models/database.py` defines:
- `RunRecord`
- `AgentMetricRecord`
- `SourceRecord`

### Service
`backend/app/services/database.py` implements:
- `create_run`
- `complete_run`
- `get_run`
- `get_metrics`
- `get_sources`

### Schema
`backend/app/models/schemas.py` defines Pydantic models for requests, responses, and internal objects.

## Research

The researcher generates claims and sources. The fact checker verifies them. Both agents use the LLM in `json_mode` to get structured output.

## Revision Loop

The editor evaluates drafts. If `passed` is false and `revision_count < max_revisions`, the workflow routes back to the writer. The writer produces a new draft. The final output is always the latest approved draft.

## Error Handling

LLM provider errors are captured in `LLMResponse.success` and `LLMResponse.error`. Agents append errors to `state["errors"]` and set `state["status"] = "FAILED"`. Workflow timeouts are caught at the top level.

## Status / Trace / Metrics

- `StatusResponse` includes `status`, `revision_count`, `quality_score`, `current_agent`, `created_at`, `updated_at`.
- `/trace` includes `posts`, `sources`, `metrics`, `errors`, and timing fields.
- `/metrics` aggregates token usage, latency, and cost.
