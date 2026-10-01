# Changelog

Newest first. Each entry: intent, action, validation, context for the next session.

## 2026-10-01 – Debt advice closed off, and plainer wording

**Intent.** A review found the advice boundary held for investments but not for debt: "Which debt do I pay first, my car loan or my card?" was not treated as an advice request, and a reply of "You should pay off your credit card first." passed the check. Advising a particular person about their own debts is debt counselling, a regulated activity with no exemption for being free (Regulated Activities Order article 39E; FCA PERG 17).

**Action.**
- `advice_boundary.py`: `asks_about_own_debt` recognises questions about the learner's own debts (which to pay first, pay off or save, prioritise, consolidate) and signs of difficulty (cannot pay, behind on payments, missed payments, debt collectors). The reply checks now also catch instructions about paying debts ("you should pay off…", "Clear the card first", "…your loan first").
- Chat: such a message is never sent to the model. It gets `DEBT_FALLBACK`, fixed text that says what the tutor can explain instead and points to free debt advice through MoneyHelper. A sum in the same message is still calculated and shown first.
- Wording: the page now says "Education only. It cannot tell you what to do with your money." in place of "Educational guidance only — not professional financial advice" ("guidance" has a specific meaning in UK finance), and "an exercise to try" in place of "something practical to try". The README disclaimer matches.
- Rule for anything public about this project: never describe it as safe, compliant, guaranteed or personal.

**Validation.** `python -m pytest`: 311 passed, with 12 own-debt phrasings that must be caught and 11 how-debt-works or non-debt questions that must not be.

**Context for next session.** Explaining how debt works, for an invented person or in general, stays allowed: the debt lesson and the payoff calculator are unchanged. This is still pattern matching and still not a legal review.

## 2026-10-01 – The advice boundary, in code

**Intent.** "Never recommend a product" was only a line in the prompt. Enforce it in code, the same way amounts are.

**Action.**
- `app/services/advice_boundary.py`: `asks_for_recommendation` (patterns for "should I buy", "which … is best", "recommend", "is X a good investment" and similar), `reads_like_a_recommendation` (directive phrases in a reply) and `names_a_product` (a list of well-known platform, bank, fund-house, company and coin names the learner did not raise).
- Chat: for an advice request the rule goes beside the question, the reply is held and checked, and `BOUNDARY_FALLBACK` replaces it if it recommends or names a product. A model outage also yields the fixed answer, so these questions never return a 503. In ordinary streamed replies a recommendation triggers a `note` event shown under the reply. The explanation of a calculation is now also replaced if it contains advice.
- Prompt: exercises must be learning tasks, never steps that open an account, buy anything or move money. This followed a real reply whose "exercise" was to open an account with a platform.

**Validation.** `python -m pytest`: 272 passed, with 20 advice-seeking phrasings that must be spotted and 15 how-it-works questions that must not be. Against the real model: "Which fund should I buy for my ISA?", "Should I buy Bitcoin?", "What's the best platform for a beginner?" and "Should I pay off my credit card or save first?" each got a no-recommendation answer about what to weigh up; "How do index funds work?" and "What is an ISA?" were answered normally with a paper exercise. The `note` under a streamed reply is covered by tests but was not seen in the browser.

**Context for next session.** The patterns were narrowed after the first draft treated "How do I open an ISA?" as an advice request. General-principle questions such as "should I pay off debt or save first?" do count as advice requests; the tutor still answers them, in terms of what to compare. This is not a compliance review.

## 2026-10-01 – Sums in chat are done by the calculators

**Intent.** "How much tax on 45000?" was still answered by the model doing arithmetic, sometimes wrongly. Route such questions to the calculators in code.

**Action.**
- `app/services/intents.py`: pattern matching over the message (no model call) for three questions: tax or take-home pay on a salary, savings growth, and debt payoff. It fires only when the wording and the numbers are unambiguous, and has an explicit list of things the calculators do not cover (Scotland, self-employment, bonuses, dividends, capital gains, weekly or hourly pay, and more).
- Chat stream: a `calculation` event (summary plus app signature) is sent first. The model is then asked to explain it, with the result placed beside the question. In this case the explanation is not streamed: it is held, checked with `amount_check`, and replaced by a fixed sentence if it contains any amount the app did not supply. If the model is down the calculation still arrives, followed by an `error` event.
- `amount_check` now accepts a trusted amount rounded to the nearest pound (£1,233.96 quoted as £1,234).
- UI: the calculation card appears above the tutor's reply and joins the conversation.

**Validation.** `python -m pytest`: 207 passed, including 21 phrasings that must not trigger a calculation. Against the real model: tax on 45000, take-home on 28k, a savings question and a debt question each produced the exact card and an explanation using only its amounts. Before the check was added, the same tax question produced "£15,080 at 40%" next to the correct card; that reply can no longer reach the learner. Seen working in the browser.

**Context for next session.** Placing the calculation in the system message was not enough for the tax question; beside the question it worked. Whole-pound rounding by the model was the first cause of false replacements, hence the rounding rule. The fixed replacement sentence is `EXPLANATION_FALLBACK` in `chat_controller.py`.

## 2026-10-01 – Eight more lessons

**Intent.** The first lesson's shape was accepted. Give every topic at least one.

**Action.**
- Lesson content moved to `app/services/lesson_library.py`; `lessons.py` is now only the engine.
- Eight new lessons (nine in total): 50/30/20 budget, salary to take-home pay, compound growth, ISAs, workplace pensions, emergency fund and diversification, what a debt costs, profit versus cash. All amounts are computed from the figures table and calculators.
- Number questions gained a unit (pounds, percent, or a count such as months) and a per-question tolerance; the answer box and the signed record use the unit.
- UI: lessons are listed by topic; after a miss the old answer is selected so retyping replaces it.
- `tests/test_lesson_library.py`: hand-worked expected answers for all 36 questions, plus checks on every question that the stored answer marks correct, no "common mistake" is the right answer, no hint or mistake feedback contains the answer, and nothing leaks into the browser payload. These caught one real slip while writing (a "mistake" value equal to the correct answer).

**Validation.** `python -m pytest`: 168 passed. In the browser: the list shows nine lessons grouped by topic, and the budget lesson was worked through including a percentage answer.

**Context for next session.** Lesson facts beyond the figures table (automatic enrolment rules, Lifetime ISA withdrawal charge) were taken from the gov.uk pages read on 2026-10-01. The three-month emergency fund and 50/30/20 are presented as rules of thumb, not official guidance. All lessons are beginner level.

## 2026-10-01 – First checked lesson

**Intent.** The tutor suggested exercises but nothing checked the answers. Build one lesson end to end, marked in code, before writing more.

**Action.**
- `app/services/lessons.py`: lesson "How Income Tax bands work" (four parts, three number questions and one multiple choice). All amounts are computed from `uk_figures` and `calculators`. Marking: amounts accepted in any common format and within £1; first miss gets a hint (or feedback specific to a known mistake); second miss shows the working; unreadable input does not use up a try.
- `app/controllers/lesson_controller.py`: `GET /api/lessons`, `GET /api/lessons/{id}` (no answers, hints or working in the payload), `POST /api/lessons/{id}/answer`. Explanations and finished-question records are signed so they join the conversation as trusted turns; records use the server's reading of the answer, not the learner's text.
- UI: a "Lessons" panel; the lesson runs inside the chat window with the question form in the explanation card, and ends with a "right first time" count.

- Found while testing the lesson: asked why an answer was wrong, the model redid the sum itself and reached £10,746 where the lesson's working says £8,232. Three changes followed.
  - App-written text (lesson parts, marked answers, calculation results) now goes into the system message as material the app showed the learner, instead of posing as earlier tutor turns. A reminder placed as a trailing system message was tried first and made the model recite the whole lesson back; it was removed.
  - Signatures now carry a source, `tutor` or `app` (`app/services/signing.py`).
  - `app/services/amount_check.py`: after each reply, any £ amount that does not appear in the figures, the app's own texts or the learner's messages is sent as a `caution` event and shown under the reply as "not checked by the app". Earlier model replies do not vouch for their own numbers.
- The reason for a model-server failure is now logged (never conversation content).

**Validation.** `python -m pytest`: 91 passed. In the browser the whole lesson was worked through: a known mistake got its specific hint, a second miss showed the working. Against the real model with the lesson in context: "why isn't all of her salary taxed at 40%?" got a short explanation with no invented amounts; "how much tax on 45000?" got a sum the model did itself (correct this time) and the note listed £32,430 and £6,486 as unchecked.

**Context for next session.** This is the demo lesson; its shape should be agreed before more are written. Lesson progress lives in the tab only, in keeping with storing nothing server-side beyond the account. One 503 from the model server appeared during testing and could not be reproduced; the new log line will show the cause if it recurs. The real fix for "how much tax on X?" is to answer it from the calculator rather than the model (needs a tool-calling model such as `llama3.1`, or an intent check in code).

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
