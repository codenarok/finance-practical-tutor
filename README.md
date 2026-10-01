# Finance Practical Tutor

Finance Practical Tutor is a FastAPI web app that delivers beginner-friendly finance tutoring powered by a locally hosted Ollama model. It includes secure registration/login, a streaming chat UI that holds a real conversation, and Docker assets for running the full stack.

## Architecture Overview
```
Browser (HTML/CSS/JS, holds the conversation in the tab)
   |
   | fetch() + streamed NDJSON reply
   v
FastAPI (AuthController, ChatController)
   |-- UserManager (bcrypt hashing)
   |-- RateLimiter (login, register, chat)
   |-- LLaMAModel (Ollama chat endpoint, fixed system prompt, hard caps)
   |-- DatabaseManager (PostgreSQL, or SQLite locally)
```

## Tech Stack
- FastAPI + Uvicorn (Python 3.12)
- PostgreSQL + SQLAlchemy (SQLite works for local runs)
- JWT auth (PyJWT) with bcrypt password hashing
- Ollama for model replies, called over HTTP with httpx
- Docker + docker compose
- pytest, with GitHub Actions running the suite on every push

## Features
- Registration and login with hashed passwords, a minimum password length and rate-limited attempts
- JWT-protected chat endpoint; conversations are never stored server-side
- A real conversation: the browser keeps the history in the tab and sends it with each message, and the reply streams in as it is written
- Tutor replies are signed by the server, so a tutor turn the browser sends back is only trusted if this server wrote it
- Level and topic are fixed choices; the learner's text only ever reaches the model as a user message, never as part of the instructions
- Hard caps on every model call: message length, history size, reply tokens, total time, one attempt, per-user rate limit
- Simple responsive UI without front-end frameworks

## Local Development
1. Create a virtual environment and install dependencies:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements-dev.txt
   ```
2. Copy `.env.example` to `.env` and fill in `SECRET_KEY` (the file shows how to generate one). For a run without Postgres, set `DATABASE_URL=sqlite:///./dev.db`.
3. Start Ollama and pull the model:
   ```bash
   ollama serve
   ollama pull llama3
   ```
4. Start the API:
   ```bash
   uvicorn app.main:app --reload
   ```
5. Open `http://localhost:8000/static/index.html` for the UI.

`LOCAL_SETUP.txt` has the same steps in more detail.

## Tests
```bash
python -m pytest
```
The suite uses a throwaway SQLite database and a stand-in for the Ollama server, so it needs neither Postgres nor a model.

## Docker
Build and run the full stack (API, Postgres, Ollama):
```bash
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))") docker compose up --build
```
The first run downloads the model (several GB) before the app starts. The API is then available at `http://localhost:8000`. Postgres is reachable from this machine only, and Ollama is not exposed outside the Docker network.

## Environment Variables
- `SECRET_KEY` – JWT signing secret, 32 characters or more. Required.
- `DATABASE_URL` – PostgreSQL (or SQLite) connection string. Required.
- `ALGORITHM` – JWT algorithm (default `HS256`).
- `ACCESS_TOKEN_EXPIRE_MINUTES` – Token lifetime (default 60).
- `OLLAMA_BASE_URL` – Ollama server URL (default `http://localhost:11434`).
- `OLLAMA_MODEL` – Model name for the tutor (default `llama3`).
- `MAX_REPLY_TOKENS` – Most tokens the model may write per reply (default 700).
- `MAX_HISTORY_CHARS` – Most earlier conversation text sent to the model (default 8000).
- `MODEL_CONTEXT_TOKENS` – Context window requested from Ollama (default 4096).
- `MODEL_TIMEOUT_SECONDS` – Longest a single reply may take (default 120).
- `AUTH_RATE_LIMIT_PER_MINUTE` – Login/register attempts per client address (default 10).
- `CHAT_RATE_LIMIT_PER_MINUTE` – Chat messages per user (default 20).

## Model Prompting
The backend sends a fixed system prompt that:
- States the learner's level and topic (both chosen from fixed lists)
- Restricts scope to finance topics: investing basics, budgeting, UK taxes (PAYE/NI/ISA), retirement (ISA/SIPP/pensions), risk, debt, and business finance
- Asks for a simplified explanation followed by a safe, practical exercise, and for follow-ups to be answered in context
- Tells the tutor to teach concepts and never recommend specific products or tell learners what to do with their money
- Tells the tutor to send learners to gov.uk rather than guess a current rate or allowance

The disclaimer ("Educational guidance only — not professional financial advice") is part of the page itself, so it does not depend on the model remembering to say it.

## Example Prompts
- Topic: Budgeting — "How should I split my monthly salary?"
- Topic: Investing basics — "What's the difference between a share and a fund?"
- Topic: UK taxes — "What makes an ISA different from a normal savings account?"

## Security and Privacy Notes
- Passwords are hashed with bcrypt; 8 characters minimum.
- Login, registration and chat are rate limited (in memory, per process).
- JWT tokens secure API access; keep `SECRET_KEY` private.
- Chat messages are **not** stored or logged server-side. The conversation lives in the browser tab and is gone when it closes.
- No sensitive data other than login credentials is stored.

## Known Limits
- UK tax figures still come from the model's memory, so they can be wrong or out of date. Supplying them from a dated table in code is the next planned step.
- Exercises are suggested but not marked.
- Rate limits are per process; several workers or replicas would need a shared store.

## Azure Deployment
You can deploy the app container with a managed PostgreSQL instance. A hosted deployment also needs a model host the app can reach; a CPU-only container is too slow for `llama3`.

### Azure Container Apps
1. Push the app image to Azure Container Registry.
2. Create an ACA environment and app pointing to the image.
3. Supply environment variables for `DATABASE_URL`, `SECRET_KEY`, and model settings.
4. Expose port 8000 and connect the app to Azure Database for PostgreSQL.

### Azure App Service (Docker)
1. Create a Web App for Containers.
2. Configure the container image and environment variables above.
3. Add a connection string for PostgreSQL; reference it in `DATABASE_URL`.

### Azure Kubernetes Service (optional)
- Create deployments for the app and (optionally) Ollama if not using a managed model host.
- Use Kubernetes Secrets for `SECRET_KEY` and database credentials.
- Expose the FastAPI service on port 8000 via an ingress.

Behind any proxy or ingress, run uvicorn with `--proxy-headers` so rate limiting sees the real client address.

## Financial Disclaimer
The tutor is for educational purposes only and does not provide professional financial advice. Users should consult qualified advisors for personal finance decisions.
