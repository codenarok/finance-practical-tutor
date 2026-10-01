# Changelog

Newest first. Each entry: intent, action, validation, context for the next session.

## 2026-10-01 – UK figures from code, and calculators

**Intent.** A finance tutor must not recall tax figures from memory or do sums in its head. Move both into code.

**Action.**
- `app/services/uk_figures.py`: the 2026 to 2027 figures, each read from its gov.uk page on 2026-10-01 (via the gov.uk content API, not a search summary) and recorded with its source. The tutor's system prompt now lists the figures for the chosen topic, names the tax year, and forbids stating any number that is not listed. After 5 April 2027 the prompt switches to "these may have changed" wording on its own.
- `app/services/calculators.py`: take-home pay, savings growth and debt payoff, in `Decimal`. `POST /api/calculate/{take-home,savings-growth,debt-payoff}` return a text summary plus the same signature used for tutor replies, so the browser can add the result to the conversation as a trusted turn. The prompt tells the tutor to use those numbers exactly and not to work them out itself.
- Signing moved to `app/services/signing.py` (shared by chat and calculators).
- UI: a "Calculators" panel above the message box; results appear in the chat with a highlighted border.

**Validation.** `python -m pytest`: 62 passed. Tests include gov.uk's worked examples (20% of £22,430 = £4,486; £58.66 NI on £1,000 a week). In the browser: a £60,000 take-home calculation showed £11,432.00 tax and £3,210.00 NI, and the tutor then explained the result.

**Context for next session.** Dividend rates changed for 2026 to 2027 (10.75% / 35.75% / 39.35%), a good example of why the table must be re-read from gov.uk each April rather than remembered. Capital gains rates are not in the table (only the £3,000 allowance); add them only from the gov.uk rates page.

## 2026-10-01 – Hygiene pass and a real conversation

**Intent.** The app was a login page in front of a one-shot prompt, on dependencies with known vulnerabilities, with no tests. Make it sound, then make the chat an actual conversation.

**Action.**
- Dependencies: Python 3.12; all pins refreshed. python-jose replaced by PyJWT, passlib by direct bcrypt (existing `$2b$` hashes still verify), requests by httpx. Unused `ollama` package removed.
- Auth: 8-character minimum password, 72-byte maximum (bcrypt's limit), emails matched without regard to case, login/register rate limited per client address, unknown-email logins take as long as wrong-password ones. `SECRET_KEY` must be 32+ characters or the app will not start.
- Chat: moved from Ollama `/api/generate` to `/api/chat` with a system message. Level and topic are fixed lists. The browser holds the conversation and sends it with each message; the server signs each tutor reply (HMAC with `SECRET_KEY`, bound to the user id) and drops tutor turns without a valid signature. Replies stream as NDJSON (`token`, `done`, `error` events).
- Caps on every model call: 2,000-character message, 8,000 characters of history, 700 reply tokens, 120 seconds, one attempt, 20 messages per user per minute.
- Prompt: no longer forces a three-part format on every reply; tells the tutor not to recommend products and to point to gov.uk rather than guess a figure. The disclaimer is fixed text in the page.
- CORS middleware removed (the UI is same-origin).
- UI: level and topic dropdowns with labels, one message box, "Thinking…" state, send disabled while a reply streams, inline errors instead of `alert()`, bullets rendered, dark scrollbars.
- Docker: non-root user, Python 3.12, no build tools. Compose: `SECRET_KEY` required from the environment, Postgres bound to localhost only, Ollama not published, a one-shot service pulls the model, the app waits for a healthy database.
- `.gitignore` now covers `.venv/`, `*.db`, `*.log`.
- Added `tests/` (25 tests), `requirements-dev.txt`, `.github/workflows/ci.yml`, and the three session docs.

**Validation.** `python -m pytest`: 25 passed. Run in the browser against local Ollama `llama3`: sign-in error shown inline, account created, a budgeting question streamed in, and a follow-up ("show me that with 2000 pounds a month") was answered in context. `docker compose config` accepts the compose file; the full Docker stack was not started.

**Context for next session.** UK figures still come from the model's memory. On a laptop without a discrete GPU a reply takes roughly 30–50 seconds end to end.
