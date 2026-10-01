# Finance Practical Tutor – entry point for any AI assistant

Read this first, then `NEXT_SESSION_PROMPT.md`, then the top of `CHANGELOG.md`.

## What this is
A portfolio piece: a FastAPI app that tutors UK personal finance through a locally hosted Ollama model. Public repo `codenarok/finance-practical-tutor`. Not deployed anywhere.

## Real tech stack
- Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2.0 (held below 2.1), PostgreSQL (SQLite for local runs and tests)
- PyJWT + bcrypt (no passlib, no python-jose)
- httpx to Ollama's `/api/chat`, streamed
- Plain HTML/CSS/JS in `app/static`, no framework and no build step
- pytest; GitHub Actions runs it on push

## Code preferences
- Keep the layout: `controllers/` (routes), `managers/` (user logic), `services/` (database, model, rate limiter), `models/`.
- Facts and arithmetic belong in code; the model only explains. Never let the model be the source of a tax figure.
- Every model call path keeps its hard caps: bounded input, bounded output, bounded time, no retries loop.
- The learner's free text goes to the model only as a user message. Anything placed in the system prompt must come from a fixed list.
- Conversations are never stored or logged server-side.
- No new external services or accounts without a cost reason.
- Every change ships with tests; `python -m pytest` must pass before a commit.

## Session protocol
- Work on `main`.
- Before ending a session: append to `CHANGELOG.md` (newest first) and refresh `NEXT_SESSION_PROMPT.md`.
