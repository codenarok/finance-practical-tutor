"""Chat controller that interacts with the finance tutor model."""
import hashlib
import hmac
import json
from typing import Iterator, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.controllers.auth_controller import get_current_user
from app.models.user import User
from app.services.llama_model import TutorUnavailable, llama_model
from app.services.rate_limiter import chat_limiter


settings = get_settings()
router = APIRouter(prefix="/api", tags=["chat"])

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


def sign_reply(user_id: int, content: str) -> str:
    """Sign a tutor reply so it can be trusted when the browser sends it back as history."""

    return hmac.new(settings.secret_key.encode("utf-8"), f"{user_id}:{content}".encode("utf-8"), hashlib.sha256).hexdigest()


def trusted_history(user_id: int, history: list[HistoryItem]) -> list[dict[str, str]]:
    """Keep the newest turns that fit the budget, dropping tutor turns this server did not write."""

    kept: list[dict[str, str]] = []
    used_chars = 0
    for item in reversed(history):
        if item.role == "assistant" and not (
            item.sig and hmac.compare_digest(item.sig, sign_reply(user_id, item.content))
        ):
            continue
        used_chars += len(item.content)
        if used_chars > settings.max_history_chars:
            break
        kept.append({"role": item.role, "content": item.content})
    kept.reverse()
    return kept


def _event(**fields: str) -> str:
    return json.dumps(fields) + "\n"


@router.post("/chat")
def chat(payload: ChatRequest, user: User = Depends(get_current_user)) -> StreamingResponse:
    """Stream a finance tutor reply without storing conversation logs.

    The response is newline-delimited JSON: `token` events carrying text, then one
    `done` event with the signature for the full reply (or an `error` event).
    """

    user_id = user.id
    chat_limiter.check(str(user_id))
    messages = llama_model.build_messages(
        knowledge_level=payload.knowledge_level,
        topic=payload.topic,
        history=trusted_history(user_id, payload.history),
        user_message=payload.message,
    )
    tokens = llama_model.stream(messages)
    # Wait for the first piece so a model that is down fails as a clean 503, not a broken stream.
    try:
        first = next(tokens)
    except (TutorUnavailable, StopIteration) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=UNAVAILABLE_DETAIL) from exc

    def events() -> Iterator[str]:
        parts = [first]
        yield _event(type="token", text=first)
        try:
            for text in tokens:
                parts.append(text)
                yield _event(type="token", text=text)
        except TutorUnavailable:
            yield _event(type="error", detail=UNAVAILABLE_DETAIL)
            return
        finally:
            tokens.close()  # stops the model call if the browser went away mid-reply
        yield _event(type="done", sig=sign_reply(user_id, "".join(parts)))

    return StreamingResponse(events(), media_type="application/x-ndjson", headers={"Cache-Control": "no-store"})
