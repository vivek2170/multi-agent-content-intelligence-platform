# Workflow

## End-to-end flow

1. User opens the frontend and fills in the form.
2. Frontend sends a `POST /api/content/generate` request.
3. FastAPI creates a run record and starts the workflow in the background.
4. Frontend begins polling `/api/content/runs/{run_id}/status`.
5. LangGraph executes the agent pipeline.

## Generation steps

### Planning
The planner receives the request and produces a structured plan. This keeps later agents focused on the same topic, audience, and tone.

### Research
The researcher uses the plan to generate claims and sources. User-provided URLs are merged into the source list.

### Fact checking
The fact checker verifies each claim against the sources and assigns a status:
- `VERIFIED`
- `PARTIALLY_VERIFIED`
- `UNSUPPORTED`
- `CONTRADICTED`

### Writing
The writer generates exactly the requested number of posts. The prompt explicitly states the required count. If the LLM returns the wrong count, the writer retries once. If the retry still fails, the posts are padded or truncated to the requested count so the invariant holds.

### Editing
The editor scores the draft and either approves it, requests a revision, or rejects it after too many revisions.

### Revision loop
If the editor requests a revision and the revision count is below `MAX_REVISIONS`, the workflow routes back to the writer. The writer replaces the existing drafts with a new draft. The final output is always the latest approved draft.

### Final validation
The final fact checker returns either `APPROVED` or `NEEDS_HUMAN_REVIEW`.

## Post-count invariant

The number of posts returned to the frontend must equal the number requested. This invariant is enforced in the writer and verified by tests for 1, 2, 3, 5, and 10 posts, including after revision loops.

## Provider selection

The frontend can override the default provider and model per request. The backend builds the provider from the request values or falls back to `.env` settings.

- `mock`: deterministic output, useful for testing and demos
- `ollama`: local model through Ollama
- `openai`: OpenAI-compatible API

If the selected provider fails, the error is returned to the frontend. There is no silent fallback to another provider.

## Polling and completion

The frontend polls the status endpoint every 1.5 seconds. When the status reaches a terminal state (`APPROVED`, `NEEDS_HUMAN_REVIEW`, `READY_FOR_REVIEW`, or `FAILED`), polling stops and the results are rendered.
