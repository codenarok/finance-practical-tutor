"""Chat controller that interacts with the finance tutor model."""
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.controllers.auth_controller import get_current_user
from app.services.llama_model import llama_model


router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    """Payload for chat interactions."""

    message: str = Field(..., description="User question or statement")
    topic: str = Field("general", description="Finance topic user is interested in")
    knowledge_level: str = Field("Beginner", description="User self-assessed finance knowledge")


class ChatResponse(BaseModel):
    """Response containing the tutor output."""

    reply: str


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, user=Depends(get_current_user)) -> ChatResponse:  # noqa: B008 - dependency injection
    """Return a finance tutor reply without storing conversation logs."""

    del user  # user is only validated for authentication; conversation is not persisted
    try:
        data: Dict[str, str] = llama_model.generate(
            knowledge_level=payload.knowledge_level,
            topic=payload.topic,
            user_message=payload.message,
        )
    except Exception as exc:  # surfacing model/server issues politely
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tutor is temporarily unavailable. Please try again shortly.",
        ) from exc
    reply_text = data.get("response", "") or (
        "I couldn't retrieve a tutor reply. This is educational only — not professional financial advice."
    )
    return ChatResponse(reply=reply_text)
