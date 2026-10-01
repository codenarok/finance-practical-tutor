"""Shared test setup: a throwaway SQLite database and a stand-in for the Ollama server."""
import json
import os
import tempfile
from pathlib import Path
from typing import Callable, Iterator

import httpx
import pytest

# Settings are read at import time, so the environment must be set before the app is imported.
_db_dir = tempfile.mkdtemp(prefix="fintutor-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_db_dir) / 'test.db'}"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256"
os.environ["OLLAMA_BASE_URL"] = "http://ollama.test"
os.environ["OLLAMA_MODEL"] = "test-model"
os.environ["AUTH_RATE_LIMIT_PER_MINUTE"] = "5"
os.environ["CHAT_RATE_LIMIT_PER_MINUTE"] = "5"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services.database import db_manager  # noqa: E402
from app.services.llama_model import llama_model  # noqa: E402
from app.services.rate_limiter import auth_limiter, chat_limiter  # noqa: E402


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A client against a fresh database with rate limits cleared."""

    db_manager.Base.metadata.drop_all(bind=db_manager.engine)
    auth_limiter.reset()
    chat_limiter.reset()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    """Bearer headers for a newly registered learner."""

    res = client.post("/api/register", json={"email": "learner@example.com", "password": "correct-horse"})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


class FakeOllama:
    """Stands in for the Ollama server and records what the app sent it."""

    def __init__(self) -> None:
        self.requests: list[dict] = []
        self.reply_pieces = ["A budget ", "is a plan."]
        self.status_code = 200
        self.fail_after_first_piece = False

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        if self.status_code != 200:
            return httpx.Response(self.status_code, json={"error": "model not found"})
        lines = [json.dumps({"message": {"role": "assistant", "content": piece}, "done": False}) for piece in self.reply_pieces]
        if self.fail_after_first_piece:
            lines = lines[:1] + [json.dumps({"error": "model crashed"})]
        else:
            lines.append(json.dumps({"message": {"role": "assistant", "content": ""}, "done": True}))
        return httpx.Response(200, content="\n".join(lines) + "\n")


@pytest.fixture
def fake_ollama(monkeypatch: pytest.MonkeyPatch) -> FakeOllama:
    fake = FakeOllama()
    monkeypatch.setattr(llama_model, "client", httpx.Client(transport=httpx.MockTransport(fake.handle)))
    return fake


@pytest.fixture
def read_events() -> Callable[[httpx.Response], list[dict]]:
    """Parse a chat response body into its list of stream events."""

    def _read(response: httpx.Response) -> list[dict]:
        return [json.loads(line) for line in response.text.splitlines() if line]

    return _read
