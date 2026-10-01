"""Signatures for text the server wrote, so it can be trusted when the browser sends it back."""
import hashlib
import hmac

from app.config import get_settings


def sign_reply(user_id: int, content: str) -> str:
    """Sign a tutor reply or calculation result for one learner."""

    secret = get_settings().secret_key.encode("utf-8")
    return hmac.new(secret, f"{user_id}:{content}".encode("utf-8"), hashlib.sha256).hexdigest()


def is_signed_by_server(user_id: int, content: str, sig: str) -> bool:
    """True when `sig` is this server's signature for `content` and this learner."""

    return hmac.compare_digest(sig, sign_reply(user_id, content))
