# Next session – Finance Practical Tutor

Refreshed 2026-10-01.

## State
- Done on `main`: hygiene pass, conversation rewrite, UK figures from code, calculators, nine checked lessons (one or two per topic), and the unchecked-amounts note. See `CHANGELOG.md`.
- Sums asked for in chat are done by the calculators in code (`app/services/intents.py`).
- 207 tests pass. Verified by hand in the browser against local Ollama.
- Open question: is this a portfolio piece or a product? Steps 4–5 below suit either; anything beyond them waits for that answer.

## What is next (in order)
4. **Lessons, next level.** A second lesson for the topics that have one, and intermediate lessons. Add builders to `app/services/lesson_library.py`; add hand-worked answers to `tests/test_lesson_library.py`.
5. **Advice boundary tests.** The prompt already says not to recommend products; add tests and a server-side check for "what should I buy" questions.

## Where things live
- Routes: `app/controllers/` (auth, chat, calculators, lessons). Lesson engine and marking: `app/services/lessons.py`. Lesson content: `app/services/lesson_library.py`. UK figures: `app/services/uk_figures.py`. Sums: `app/services/calculators.py`. Model call and system prompt: `app/services/llama_model.py`. Caps and limits: `app/config.py` and the constants at the top of `chat_controller.py`. Rate limiter: `app/services/rate_limiter.py`.
- UI: `app/static/` (plain HTML/CSS/JS).
- Tests: `tests/`; `conftest.py` has the stand-in Ollama server.

## Running it
- Tests: `.venv/bin/python -m pytest`
- Quick run without Postgres: `DATABASE_URL=sqlite:///./preview.db .venv/bin/uvicorn app.main:app --port 8745` (`*.db` is ignored by git).

## Gotchas
- App-written text (lessons, calculator results) is signed with source `app` and reaches the model inside the system message. Do not send it as assistant turns: a run of assistant turns made the small model redo sums or recite the lesson.
- After a `calculation` event the tutor's explanation is held and checked, not streamed. In ordinary conversation the unchecked-amounts note is still only a warning.
- New calculator phrasings go in `app/services/intents.py` with a test on both sides: messages that must fire and messages that must not.
- The figures table is for the 2026 to 2027 tax year. After 5 April 2027 re-read every source page on gov.uk and update `uk_figures.py`; never fill a figure from memory.
- Chat tests must not assert the "Official UK figures" heading without passing a date, or they will fail when the tax year ends.
- Settings are read at import time; tests set the environment in `conftest.py` before importing the app.
- `.env` points at Postgres on localhost, which only exists while `docker compose up db` is running. Override `DATABASE_URL` with SQLite for a quick run.
- The email validator rejects reserved domains such as `.test`; use `example.com` in tests.
- Rate limits are in memory, per process.
- pytest prints one Starlette deprecation warning about httpx in the test client; it is upstream and harmless.

## Blockers
None.
