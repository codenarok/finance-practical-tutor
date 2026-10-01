"""Signatures for text the server wrote, so it can be trusted when the browser sends it back.

A signature also records who wrote the text: the tutor (the model, which can be wrong)
or the app (figures, calculators and lessons, which are computed in code).
"""
import hashlib
import hmac
from typing import Literal, Optional

from app.config import get_settings

Source = Literal["tutor", "app"]
SOURCES: tuple[Source, ...] = ("tutor", "app")


def sign_reply(user_id: int, content: str, source: Source = "tutor") -> str:
    """Sign a tutor reply, calculation result or lesson text for one learner."""

    secret = get_settings().secret_key.encode("utf-8")
    return hmac.new(secret, f"{source}:{user_id}:{content}".encode("utf-8"), hashlib.sha256).hexdigest()


def signed_source(user_id: int, content: str, sig: str) -> Optional[Source]:
    """Who wrote `content` according to `sig`, or None if this server did not sign it for this learner."""

    for source in SOURCES:
        if hmac.compare_digest(sig, sign_reply(user_id, content, source)):
            return source
    return None
