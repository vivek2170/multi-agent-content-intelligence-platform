# Multi-Agent Content Intelligence Platform

A locally runnable multi-agent AI content generation and verification platform built with FastAPI, LangGraph, and vanilla JavaScript.

## What is this?

This project is a small content intelligence platform that generates platform-specific posts through a multi-agent pipeline. Instead of calling an LLM once and hoping for the best, it splits the work into planning, research, fact checking, writing, editing, and final validation.

I built it to experiment with how multiple specialized agents can work together to produce more reliable content than a single generation pass.

## Why I built it

Most content-generation demos I saw relied on one prompt and one LLM call. I wanted to see what happens if you separate concerns:

- a planner defines the shape of the content
- a researcher gathers claims and sources
- a fact checker verifies claims
- a writer produces the actual posts
- an editor reviews quality and decides whether to accept or revise
- a final fact checker gives a last approval pass

This project is my way of exploring that idea end to end, from API design to persistence to frontend feedback.

## Features

- Multi-agent content generation pipeline: planner, researcher, fact checker, writer, editor, final fact checker
- Bounded revision loop with explicit post-count enforcement
- Provider abstraction with Mock, Ollama, and OpenAI-compatible providers
- SQLite persistence for runs, metrics, and sources
- Real-time frontend status updates with current agent, elapsed time, and workflow steps
- No frontend framework dependency

## How it works

1. User submits a request from the frontend.
2. FastAPI validates the request and starts the workflow.
3. LangGraph runs the agent pipeline:
   - Planner
   - Researcher
   - Fact Checker
   - Writer
   - Editor
   - Revision loop if needed
   - Final Fact Checker
4. Results and metrics are saved to SQLite.
5. Frontend polls for status and renders the final posts.

## Agents

### Planner
Turns the request into a structured plan with topic, audience, platform, research questions, keywords, and tone guidelines.

### Researcher
Generates claims and sources from the plan, then normalizes them into `ResearchResult` objects. Merges any user-provided URLs.

### Fact Checker
Verifies claims against sources and updates their status and confidence.

### Writer
Generates exactly the requested number of posts. If the count is wrong, it retries once. Revisions preserve the exact count.

### Editor
Evaluates drafts for quality, accuracy, and platform fit. If the score is too low and revisions remain, it sends the draft back to the writer.

### Final Fact Checker
Produces an approval verdict: `APPROVED` or `NEEDS_HUMAN_REVIEW`.

## Tech Stack

- Backend: FastAPI, LangGraph, SQLAlchemy, Pydantic
- Frontend: HTML, CSS, vanilla JavaScript
- LLM providers: Mock, Ollama, OpenAI-compatible
- Database: SQLite
- Testing: pytest, pytest-asyncio

## Project Structure

```
.
├── backend/
│   └── app/
│       ├── agents/
│       ├── providers/
│       ├── routes/
│       ├── workflow/
│       ├── models/
│       ├── services/
│       ├── config.py
│       ├── database.py
│       └── main.py
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   ├── manifest.json
│   └── assets/
├── tests/
├── docs/
├── .env.example
├── requirements.txt
├── START_PROJECT.bat
├── STOP_PROJECT.bat
├── TEST_PROJECT.bat
└── README.md
```

## Setup

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Ollama Setup

If you want to use the Ollama provider instead of Mock:

1. Install Ollama: https://ollama.com
2. Run `ollama serve`
3. Pull a model, for example:
   ```bash
   ollama pull llama3.2:3b
   ```
4. Set `LLM_PROVIDER=ollama` and `LLM_MODEL=llama3.2:3b` in `.env`

## Configuration

Copy `.env.example` to `.env` and adjust the values you need.

Key settings:

- `LLM_PROVIDER`: `mock`, `ollama`, or `openai`
- `LLM_MODEL`: model name for the selected provider
- `OLLAMA_BASE_URL`: Ollama server URL
- `OPENAI_API_KEY`: required only if using OpenAI
- `MAX_REVISIONS`: maximum editor revision cycles
- `LLM_TIMEOUT_SECONDS`: timeout for each LLM request
- `WORKFLOW_TIMEOUT_SECONDS`: overall workflow timeout

## Running the Project

```bash
START_PROJECT.bat
```

This will:
1. Check for Python
2. Create and prepare the virtual environment
3. Copy `.env.example` to `.env` if needed
4. Create `data/` and `logs/` directories
5. Start the backend
6. Wait for the health endpoint
7. Open the frontend in the default browser

To stop the backend:

```bash
STOP_PROJECT.bat
```

To run tests:

```bash
TEST_PROJECT.bat
```

## API

### `GET /health`
Returns `{"status": "ok"}`.

### `GET /api/config`
Returns current provider and model configuration.

### `POST /api/content/generate`
Starts a content generation run.

Request body:
```json
{
  "topic": "AI in healthcare",
  "platform": "LinkedIn",
  "audience": "Doctors",
  "tone": "Professional",
  "posts": 2,
  "length": "Medium",
  "keywords": ["AI", "healthcare"],
  "urls": [],
  "provider": "mock",
  "model": "mock"
}
```

### `GET /api/content/runs/{run_id}/status`
Returns the current run status.

### `GET /api/content/runs/{run_id}/trace`
Returns the full run trace, including posts, sources, metrics, and errors.

### `GET /api/content/runs/{run_id}/metrics`
Returns aggregated metrics for the run.

## Testing

Run the test suite:

```bash
pytest tests -v
```

Current test coverage focuses on:
- workflow execution
- post-count invariant
- revision loop behavior
- mock providers
- schema validation

## Screenshots

_Add screenshots of the frontend here after running the project._

## Future Improvements

- Replace the Mock search provider with a real web search integration
- Add streaming responses for long-running generations
- Add authentication and per-user run history
- Add export options for generated posts
- Improve error reporting with retry suggestions
