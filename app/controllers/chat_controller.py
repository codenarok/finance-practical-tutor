"""Chat controller that interacts with the finance tutor model."""
import json
import logging
from typing import Iterator, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.controllers.auth_controller import get_current_user
from app.models.user import User
from app.services.llama_model import TutorUnavailable, llama_model
from app.services.rate_limiter import chat_limiter
from app.services.amount_check import unchecked_amounts
from app.services.intents import detect_calculation
from app.services.signing import sign_reply, signed_source


settings = get_settings()
router = APIRouter(prefix="/api", tags=["chat"])
logger = logging.getLogger("uvicorn.error")

KnowledgeLevel = Literal["Beginner", "Intermediate", "Advanced"]
Topic = Literal[
    "General",
    "Budgeting",
    "Investing basics",
    "UK taxes",
    "Retirement",
    "Risk management",
    "Debt management",
    "Business finance",
]

MAX_MESSAGE_CHARS = 2000
MAX_HISTORY_ITEMS = 40
MAX_HISTORY_ITEM_CHARS = 8000

UNAVAILABLE_DETAIL = "Tutor is temporarily unavailable. Please try again shortly."
EXPLANATION_FALLBACK = (
    "The figures above are exact, worked out by the app rather than by me. "
    "Ask me about any line and I will explain what it means."
)
CALCULATED_BUT_UNAVAILABLE_DETAIL = (
    "The calculation above is exact, but the tutor is temporarily unavailable to explain it. Please try again shortly."
)


class HistoryItem(BaseModel):
    """One earlier turn, held by the browser and sent back with each message."""

    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=MAX_HISTORY_ITEM_CHARS)
    sig: Optional[str] = Field(None, max_length=64, description="Signature the server issued for a tutor reply")


class ChatRequest(BaseModel):
    """Payload for chat interactions."""

    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_CHARS, description="User question or statement")
    topic: Topic = Field("General", description="Finance topic user is interested in")
    knowledge_level: KnowledgeLevel = Field("Beginner", description="User self-assessed finance knowledge")
    history: list[HistoryItem] = Field(default_factory=list, max_length=MAX_HISTORY_ITEMS)


def trusted_history(user_id: int, history: list[HistoryItem]) -> tuple[list[dict[str, str]], list[str], list[str]]:
    """Keep the newest turns that fit the budget, dropping tutor turns this server did not write.

    Returns three things: the learner/tutor dialogue for the model; the texts the app
    itself wrote (lessons, calculations), oldest first; and every text whose numbers can
    be relied on, which is what the learner typed and what the app computed but not
    earlier model replies.
    """

    kept: list[dict[str, str]] = []
    app_notes: list[str] = []
    reliable: list[str] = []
    used_chars = 0
    for item in reversed(history):
        source = signed_source(user_id, item.content, item.sig) if item.role == "assistant" and item.sig else None
        if item.role == "assistant" and source is None:
            continue
        used_chars += len(item.content)
        if used_chars > settings.max_history_chars:
            break
        if source == "app":
            app_notes.append(item.content)
        else:
            kept.append({"role": item.role, "content": item.content})
        if item.role == "user" or source == "app":
            reliable.append(item.content)
    kept.reverse()
    app_notes.reverse()
    return kept, app_notes, reliable


def _event(**fields: object) -> str:
    return json.dumps(fields) + "\n"


@router.post("/chat")
def chat(payload: ChatRequest, user: User = Depends(get_current_user)) -> StreamingResponse:
    """Stream a finance tutor reply without storing conversation logs.

    The response is newline-delimited JSON: an optional `calculation` event when the
    message asked for a sum the app can do itself, `token` events carrying the tutor's
    text, an optional `caution` event listing amounts the app did not supply, then one
    `done` event with the signature for the full reply (or an `error` event).

    After a `calculation`, the tutor's explanation is not streamed piece by piece: it is
    checked first and sent whole, or replaced if it contains amounts of its own.
    """

    user_id = user.id
    chat_limiter.check(str(user_id))
    history, app_notes, reliable_texts = trusted_history(user_id, payload.history)
    # A sum the calculators can do is done here, in code; the model is only asked to explain it.
    calculation = detect_calculation(payload.message)
    if calculation:
        reliable_texts.append(calculation)
    messages = llama_model.build_messages(
        knowledge_level=payload.knowledge_level,
        topic=payload.topic,
        history=history,
        user_message=payload.message,
        app_notes=tuple(app_notes),
        calculation=calculation,
    )
    # Numbers the reply may quote: the official figures, what the learner typed, what the app computed.
    reliable_texts += [messages[0]["content"], payload.message]
    tokens = llama_model.stream(messages)
    first: Optional[str] = None
    if calculation is None:
        # Wait for the first piece so a model that is down fails as a clean 503, not a broken stream.
        try:
            first = next(tokens)
        except (TutorUnavailable, StopIteration) as exc:
            # The reason comes from the model server, never from the conversation.
            logger.warning("Tutor unavailable: %s", exc or "empty reply")
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=UNAVAILABLE_DETAIL) from exc

    def events() -> Iterator[str]:
        parts: list[str] = []
        if calculation:
            # Sent first and on its own, so the learner has the exact answer even if the model is down.
            yield _event(type="calculation", summary=calculation, sig=sign_reply(user_id, calculation, source="app"))
        try:
            if first is not None:
                parts.append(first)
                yield _event(type="token", text=first)
            for text in tokens:
                parts.append(text)
                if not calculation:
                    yield _event(type="token", text=text)
        except TutorUnavailable as exc:
            logger.warning("Tutor unavailable mid-reply: %s", exc)
            yield _event(type="error", detail=CALCULATED_BUT_UNAVAILABLE_DETAIL if calculation else UNAVAILABLE_DETAIL)
            return
        finally:
            tokens.close()  # stops the model call if the browser went away mid-reply
        if not parts:
            yield _event(type="error", detail=CALCULATED_BUT_UNAVAILABLE_DETAIL)
            return
        reply = "".join(parts)
        unchecked = unchecked_amounts(reply, reliable_texts)
        if calculation:
            # The explanation of an exact result was held back until it could be checked.
            # If the model added amounts of its own, the learner never sees them.
            if unchecked:
                logger.warning("Tutor explanation replaced: it contained %d amounts the app did not supply", len(unchecked))
                reply = EXPLANATION_FALLBACK
            yield _event(type="token", text=reply)
        elif unchecked:
            yield _event(type="caution", amounts=unchecked)
        yield _event(type="done", sig=sign_reply(user_id, reply))

    return StreamingResponse(events(), media_type="application/x-ndjson", headers={"Cache-Control": "no-store"})
