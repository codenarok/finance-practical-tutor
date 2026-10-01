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
   |-- UK figures (dated tax-year table from gov.uk) + calculators (pure Python)
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
- Tutor replies are signed by the server, so a tutor turn the browser sends back is only trusted if this server wrote it. The signature also records whether the model or the app wrote the text, so only app-computed numbers count as checked
- Level and topic are fixed choices; the learner's text only ever reaches the model as a user message, never as part of the instructions
- UK rates and allowances come from a dated table in code (each with its gov.uk source), not from the model's memory
- Calculators for take-home pay, savings growth and debt payoff: the app does the sums, and the signed result joins the chat for the tutor to explain
- Lessons with questions marked in code: a hint on the first miss (specific to common mistakes), the working on the second, and the tutor can discuss any of it
- Sums asked for in chat are done in code: "how much tax on £45,000?", "£200 a month at 5% for 10 years?" and "£1,200 at 24% APR paying £50 a month?" are spotted by pattern matching, answered by the calculators as a card, and only then explained by the tutor. That explanation is checked before it is shown and replaced if it contains any amount the app did not supply
- An advice boundary held in code: a message asking what to buy, choose or do ("which fund should I buy?") is spotted by pattern matching, the tutor is told to explain how to weigh the choice instead, and its reply is checked before it is shown. A reply that recommends something, or names a well-known product the learner did not raise, is replaced with a fixed answer
- A code-side check on every reply: any £ amount the app did not supply (from the figures, a calculator, a lesson or the learner's own message) is listed under the reply as "not checked by the app"
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
- Tells the tutor to teach concepts and never recommend specific products or tell learners what to do with their money, and to set exercises that are learning tasks, never steps that open an account or move money
- Lists the official figures for the chosen topic and the tax year they belong to, and tells the tutor to send learners to gov.uk for anything not listed rather than guess a number
- Tells the tutor not to work out tax, pay, growth or repayment figures itself, and to use calculator results from the conversation exactly

The disclaimer ("Education only. It cannot tell you what to do with your money.") is part of the page itself, so it does not depend on the model remembering to say it.

## UK Figures and Calculators
`app/services/uk_figures.py` holds the figures for one tax year (currently 2026 to 2027, checked against gov.uk on 1 October 2026): Income Tax bands and Personal Allowance, employee and employer National Insurance, ISA and Lifetime ISA limits, pension allowances and automatic enrolment, the new State Pension, and the savings, dividend and capital gains allowances. Income Tax bands are for England, Wales and Northern Ireland.

Once that tax year ends, the tutor is told the figures may have changed and says so to the learner. To roll over, re-check each source page, update the numbers and dates, and run the tests, which include gov.uk's own worked examples.

`app/services/calculators.py` does the arithmetic with `Decimal`:
- **Take-home pay** – Income Tax (including the allowance taper above £100,000) and category A National Insurance on equal monthly pay.
- **Savings growth** – a starting amount plus monthly payments at a steady rate, compounded monthly.
- **Debt payoff** – months to clear and total interest for a fixed payment; a payment that never clears the debt is reported, not looped on.

These are estimates with their assumptions stated in every result. They are not a payroll or a lender's figures.

`app/services/intents.py` connects the chat to the calculators. It reads a message with regular expressions (no model call) and runs a calculator only when both the question and the numbers are clear. It stays quiet for anything ambiguous or outside what the calculators cover: two salaries in one message, weekly or hourly pay, Scottish bands, self-employment, bonuses, dividends, capital gains and so on. Those go to the tutor to answer in words.

## Lessons
`app/services/lesson_library.py` holds short lessons: four explanations, each followed by a question. `app/services/lessons.py` is the engine that marks them. Marking is done in code, never by the model, and the answers are not sent to the browser until the question is finished. Every number in a lesson is computed from the figures table and the calculators, so lessons move with the tax year.

A first wrong answer gets a hint, with specific feedback when it matches a known mistake (for example, taxing the whole salary at 20%). A second shows the working. Each explanation and each finished question joins the conversation as a signed turn, so the learner can ask the tutor "why was I wrong?" and get an answer about that exact question. The record is built from the server's reading of the answer, never the learner's raw text.

There are nine lessons, at least one for every topic:

| Topic | Lesson |
| --- | --- |
| Budgeting | A first budget: 50/30/20 |
| UK taxes | How Income Tax bands work |
| UK taxes | From salary to take-home pay |
| Investing basics | How compound growth works |
| Investing basics | How ISAs work |
| Retirement | Workplace pensions: your employer pays in too |
| Risk management | An emergency fund, and why to spread risk |
| Debt management | What a debt really costs |
| Business finance | Profit is not cash |

Answers can be pounds, percentages or counts (such as months). To add a lesson, write a builder function in `lesson_library.py` and add it to `_BUILDERS`; the library tests then check its structure, that no hint gives the answer away, and that nothing leaks to the browser. Progress is kept in the browser tab only.

## The Advice Boundary
The tutor teaches how money works. Telling someone what to buy or choose is a personal recommendation, which in the UK is regulated financial advice, so the app does not do it. `app/services/advice_boundary.py` enforces that in four places:

1. **On the way in.** "Should I buy…", "which … is best", "can you recommend…" and similar are recognised. The instruction not to recommend is placed right beside the question, and the tutor is asked for what to weigh up instead.
2. **Before an answer to such a question is shown.** The reply is held and checked. If it tells the learner what to do, or brings up a well-known platform, bank, fund house, company or coin the learner did not mention, a fixed answer is sent instead. If the model is down, the same fixed answer is sent, so these questions never fail.
3. **After an ordinary streamed reply.** Text already sent cannot be taken back, so if it reads like a recommendation a reminder is shown under it.

4. **Debt, always.** Advising a particular person what to do about their own debts is a separate regulated activity (debt counselling), and being free does not exempt it. A message asking which debt to pay first, whether to pay debt or save, or saying the learner is struggling to pay, is never sent to the model: it gets a fixed answer that points to free debt advice. A sum in the same message is still worked out and shown. The reply checks also catch instructions about paying debts.

Questions about how things work ("how do I open an ISA?", "which ISAs count towards the allowance?", "how does credit card interest work?") are not treated as advice requests. The product-name list is a backstop for common names, not a complete register.

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
- The model can still get a concept wrong. When the app has done the sum, the tutor's amounts are guaranteed to match it; in ordinary conversation a small model can still do a sum of its own, and the unchecked-amounts note flags those numbers rather than stopping them.
- Calculation questions and advice requests are recognised by pattern, so unusual phrasings are missed and fall back to the ordinary tutor, where the prompt rules and the after-the-fact notes are the only guard.
- This is a teaching tool with guard rails, not a compliance system. It has not been reviewed against FCA rules.
- The take-home calculator covers a single salaried job with the standard allowance: no pension contributions, student loans, Scottish bands or benefits in kind.
- Lesson progress is not saved between visits, and all nine lessons are beginner level.
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
The tutor is for education only. It does not give financial advice and cannot tell you what to do with your money. For a personal recommendation, speak to a regulated financial adviser. For help with debts, free debt advice is available; MoneyHelper lists where to find it.
