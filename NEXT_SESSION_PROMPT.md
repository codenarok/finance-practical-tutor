# Next session – Finance Practical Tutor

Refreshed 2026-10-01.

## State
- Hygiene pass and the conversation rewrite are done on `main`. See `CHANGELOG.md`.
- 25 tests pass. Verified by hand in the browser against local Ollama.
- Open question: is this a portfolio piece or a product? Steps 3–5 below suit either; anything beyond them waits for that answer.

## What is next (in order)
3. **Facts from code.** One dated file of UK tax-year figures (ISA allowance, personal allowance, PAYE bands, NI thresholds, pension annual allowance), each with its gov.uk source and the tax year it applies to; verify every figure on gov.uk, never from model memory. Inject the relevant ones into the system prompt. Add Python calculators (take-home pay, compound growth, debt payoff) so the model explains numbers and never does the arithmetic.
4. **Checked exercises.** Two or three short lessons per topic where the learner's answer is marked in code. Build one, review it, then scale out.
5. **Advice boundary tests.** The prompt already says not to recommend products; add tests and a server-side check for "what should I buy" questions.

## Where things live
- Routes: `app/controllers/` (auth, chat). Model call and system prompt: `app/services/llama_model.py`. Caps and limits: `app/config.py` and the constants at the top of `chat_controller.py`. Rate limiter: `app/services/rate_limiter.py`.
- UI: `app/static/` (plain HTML/CSS/JS).
- Tests: `tests/`; `conftest.py` has the stand-in Ollama server.

## Running it
- Tests: `.venv/bin/python -m pytest`
- Quick run without Postgres: `DATABASE_URL=sqlite:///./preview.db .venv/bin/uvicorn app.main:app --port 8745` (`*.db` is ignored by git).

## Gotchas
- Settings are read at import time; tests set the environment in `conftest.py` before importing the app.
- `.env` points at Postgres on localhost, which only exists while `docker compose up db` is running. Override `DATABASE_URL` with SQLite for a quick run.
- The email validator rejects reserved domains such as `.test`; use `example.com` in tests.
- Rate limits are in memory, per process.
- pytest prints one Starlette deprecation warning about httpx in the test client; it is upstream and harmless.

## Blockers
None.
