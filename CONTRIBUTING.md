# Contributing

## Setup

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` if you want to change defaults.

## Running tests

```bash
pytest tests -v
```

Or on Windows:

```bash
TEST_PROJECT.bat
```

## Making changes

- Keep the frontend in plain HTML, CSS, and JavaScript.
- Keep the backend in `backend/app/`.
- Follow the existing agent pattern if you add a new agent.
- Run the tests before pushing.

## Pull requests

- Describe what changed and why.
- Include tests if the change affects behavior.
- Make sure `pytest tests -v` passes.
