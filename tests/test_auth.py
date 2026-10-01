"""Registration, login and token checks."""
from datetime import timedelta

from fastapi.testclient import TestClient

from app.controllers.auth_controller import create_access_token

LEARNER = {"email": "learner@example.com", "password": "correct-horse"}


def login(client: TestClient, email: str, password: str):
    return client.post("/api/login", data={"username": email, "password": password, "grant_type": "password"})


def test_register_returns_a_working_token(client: TestClient, fake_ollama) -> None:
    res = client.post("/api/register", json=LEARNER)
    assert res.status_code == 200
    token = res.json()["access_token"]
    chat = client.post("/api/chat", json={"message": "What is a budget?"}, headers={"Authorization": f"Bearer {token}"})
    assert chat.status_code == 200


def test_register_rejects_a_duplicate_email_in_any_case(client: TestClient) -> None:
    assert client.post("/api/register", json=LEARNER).status_code == 200
    res = client.post("/api/register", json={**LEARNER, "email": "Learner@Example.com"})
    assert res.status_code == 400
    assert res.json()["detail"] == "Email already registered"


def test_register_rejects_a_short_password(client: TestClient) -> None:
    res = client.post("/api/register", json={**LEARNER, "password": "short"})
    assert res.status_code == 422


def test_register_rejects_a_password_over_the_bcrypt_limit(client: TestClient) -> None:
    res = client.post("/api/register", json={**LEARNER, "password": "x" * 73})
    assert res.status_code == 422


def test_register_rejects_an_invalid_email(client: TestClient) -> None:
    res = client.post("/api/register", json={**LEARNER, "email": "not-an-email"})
    assert res.status_code == 422


def test_login_succeeds_with_the_right_password_and_any_email_case(client: TestClient) -> None:
    client.post("/api/register", json=LEARNER)
    res = login(client, "LEARNER@example.com", LEARNER["password"])
    assert res.status_code == 200
    assert res.json()["token_type"] == "bearer"


def test_login_fails_the_same_way_for_wrong_password_and_unknown_email(client: TestClient) -> None:
    client.post("/api/register", json=LEARNER)
    wrong_password = login(client, LEARNER["email"], "not-the-password")
    unknown_email = login(client, "nobody@example.com", LEARNER["password"])
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_login_with_an_overlong_password_is_a_plain_failure(client: TestClient) -> None:
    client.post("/api/register", json=LEARNER)
    assert login(client, LEARNER["email"], "x" * 500).status_code == 401


def test_login_is_rate_limited(client: TestClient) -> None:
    client.post("/api/register", json=LEARNER)  # counts as one of the five attempts
    statuses = [login(client, LEARNER["email"], "not-the-password").status_code for _ in range(5)]
    assert statuses == [401, 401, 401, 401, 429]


def test_chat_requires_a_token(client: TestClient) -> None:
    assert client.post("/api/chat", json={"message": "hello"}).status_code == 401


def test_chat_rejects_a_forged_token(client: TestClient) -> None:
    res = client.post("/api/chat", json={"message": "hello"}, headers={"Authorization": "Bearer not.a.token"})
    assert res.status_code == 401


def test_chat_rejects_an_expired_token(client: TestClient, auth_headers) -> None:
    expired = create_access_token({"sub": "1"}, expires_delta=timedelta(minutes=-1))
    res = client.post("/api/chat", json={"message": "hello"}, headers={"Authorization": f"Bearer {expired}"})
    assert res.status_code == 401


def test_chat_rejects_a_token_for_a_user_that_does_not_exist(client: TestClient) -> None:
    token = create_access_token({"sub": "999"})
    res = client.post("/api/chat", json={"message": "hello"}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
