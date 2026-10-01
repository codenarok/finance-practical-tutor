"""The backstop that reports amounts the tutor made up or worked out itself."""
from fastapi.testclient import TestClient

from app.services.amount_check import unchecked_amounts
from app.services.signing import sign_reply

WORKING = "Working: 20% of £37,700 is £7,540. 40% of £1,730 is £692. Together that is £8,232."


def test_amounts_found_in_trusted_text_pass_however_they_are_written() -> None:
    reply = "You pay £7,540.00 plus £692, so £8232 in total. On 2000 pounds that is different."
    assert unchecked_amounts(reply, [WORKING]) == []


def test_amounts_the_app_never_supplied_are_reported_once_each_in_order() -> None:
    reply = "20% on the first £50,270 (£10,054) and £692 more. Total: £10,054 + £692 = £10,746."
    assert unchecked_amounts(reply, [WORKING, "bands end at £50,270"]) == ["£10,054", "£10,746"]


def test_the_learners_own_numbers_count_even_without_a_pound_sign() -> None:
    assert unchecked_amounts("With £2,000 a month you could...", ["Show me that with 2000 pounds a month"]) == []


def test_percentages_and_plain_numbers_in_a_reply_are_not_amounts() -> None:
    assert unchecked_amounts("The rate is 20% for 35 years.", []) == []


def chat_events(client: TestClient, headers: dict, read_events, **body) -> list[dict]:
    return read_events(client.post("/api/chat", json=body, headers=headers))


def test_a_reply_with_its_own_sums_ends_with_a_caution(client: TestClient, auth_headers, fake_ollama, read_events) -> None:
    fake_ollama.reply_pieces = ["Total Income Tax: £10,054 + £692 ", "= £10,746."]
    record = f"Lesson question: tax on £52,000?\n{WORKING}"
    history = [{"role": "assistant", "content": record, "sig": sign_reply(1, record, source="app")}]
    events = chat_events(client, auth_headers, read_events, message="Why?", topic="UK taxes", history=history)
    assert [e["type"] for e in events] == ["token", "token", "caution", "done"]
    assert events[2]["amounts"] == ["£10,054", "£10,746"]


def test_no_caution_when_every_amount_comes_from_the_app_the_figures_or_the_learner(
    client: TestClient, auth_headers, fake_ollama, read_events
) -> None:
    fake_ollama.reply_pieces = ["The allowance is £12,570, the tax is £8,232, and you asked about £300."]
    record = f"Lesson question: tax on £52,000?\n{WORKING}"
    history = [{"role": "assistant", "content": record, "sig": sign_reply(1, record, source="app")}]
    events = chat_events(client, auth_headers, read_events, message="What about 300?", topic="UK taxes", history=history)
    assert [e["type"] for e in events] == ["token", "done"]


def test_an_earlier_model_reply_does_not_vouch_for_its_own_numbers(
    client: TestClient, auth_headers, fake_ollama, read_events
) -> None:
    fake_ollama.reply_pieces = ["As I said, the total is £10,746."]
    earlier = "Total Income Tax: £10,746."
    history = [
        {"role": "user", "content": "How much tax?"},
        {"role": "assistant", "content": earlier, "sig": sign_reply(1, earlier)},
    ]
    events = chat_events(client, auth_headers, read_events, message="Say that again", history=history)
    assert events[-2] == {"type": "caution", "amounts": ["£10,746"]}
    # The earlier reply is still given to the model as conversation; it just is not a source of truth.
    assert fake_ollama.requests[0]["messages"][2] == {"role": "assistant", "content": earlier}
