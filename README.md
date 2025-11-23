# Finance Practical Tutor

Finance Practical Tutor is a FastAPI web app that delivers beginner-friendly finance tutoring powered by an Ollama LLaMA model. It includes secure registration/login, a minimal chat UI, and deployment assets for local Docker and Azure.

## Architecture Overview
```
Browser (HTML/CSS/JS)
   |
   | fetch()
   v
FastAPI (AuthController, ChatController)
   |-- UserManager (bcrypt hashing)
   |-- LLaMAModel (Ollama prompt template)
   |-- DatabaseManager (PostgreSQL)
```

## Tech Stack
- FastAPI + Uvicorn
- PostgreSQL + SQLAlchemy
- JWT auth (python-jose) with bcrypt hashing (passlib)
- Ollama (default) for LLaMA responses
- Docker + docker-compose

## Features
- Secure registration and login with hashed passwords
- JWT-protected chat endpoint (no chat storage for privacy)
- Consistent tutor prompt that always includes simplified explanations, practical exercises, and a disclaimer
- Simple responsive UI without front-end frameworks

## Local Development
1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Set environment variables (example):
   ```bash
   export DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/fintutor
   export SECRET_KEY=change-me
   export OLLAMA_BASE_URL=http://localhost:11434
   export OLLAMA_MODEL=llama3
   ```
3. Start the API:
   ```bash
   uvicorn app.main:app --reload
   ```
4. Open `http://localhost:8000/static/index.html` for the UI.

## Docker
Build and run the full stack (API, Postgres, Ollama):
```bash
docker-compose up --build
```
The API will be available at `http://localhost:8000` and the Ollama daemon at `http://localhost:11434`.

## Environment Variables
- `DATABASE_URL` – PostgreSQL connection string.
- `SECRET_KEY` – JWT signing secret.
- `ALGORITHM` – JWT algorithm (default `HS256`).
- `ACCESS_TOKEN_EXPIRE_MINUTES` – Token lifetime (default 60).
- `OLLAMA_BASE_URL` – Ollama server URL (default `http://localhost:11434`).
- `OLLAMA_MODEL` – Model name for the tutor (default `llama3`).

## Model Prompting
The backend enforces a prompt template that:
- References the learner’s stated knowledge level
- Restricts scope to finance topics: investing basics, budgeting, UK taxes (PAYE/NI/ISA), retirement (ISA/SIPP/pensions), risk, debt, and business finance
- Always returns: (1) simplified explanation, (2) actionable safe exercise, (3) disclaimer: “This is educational only — not professional financial advice.”

## Example Prompts
- Topic: budgeting — “How should I split my monthly salary?”
- Topic: investing basics — “What’s a simple way to start with index funds?”
- Topic: UK taxes — “How does ISA tax relief work?”

## Security and Privacy Notes
- Passwords are hashed with bcrypt via Passlib.
- JWT tokens secure API access; keep `SECRET_KEY` private.
- Chat messages are **not** stored or logged server-side.
- No sensitive data other than login credentials is stored.

## Azure Deployment
You can deploy the app container with a managed PostgreSQL instance:

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

## Financial Disclaimer
The tutor is for educational purposes only and does not provide professional financial advice. Users should consult qualified advisors for personal finance decisions.
