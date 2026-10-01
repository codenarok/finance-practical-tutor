"""Spotting sums in chat messages: fire when clear, stay quiet when not."""
import pytest
from fastapi.testclient import TestClient

from app.controllers.chat_controller import EXPLANATION_FALLBACK
from app.services.intents import detect_calculation
from app.services.signing import signed_source


@pytest.mark.parametrize(
    "message",
    [
        "How much Income Tax would someone on 45000 pay?",
        "how much tax on £45,000",
        "What's the take-home pay on a 45k salary?",
        "I earn £45,000 a year, what do I get after tax?",
        "What is my net pay if I earn £3,750 a month?",
        "how much national insurance on 45000 in 2026",
    ],
)
def test_salary_questions_get_the_take_home_calculation(message: str) -> None:
    summary = detect_calculation(message)
    assert summary is not None
    assert "salary of £45,000.00 a year" in summary
    assert "Income Tax: £6,486.00 a year" in summary


@pytest.mark.parametrize(
    "message",
    [
        "If I save £200 a month at 5% for 10 years, what will I have?",
        "what would 200 a month grow to over 10 years at 5 percent",
        "investing £200 per month for 10 years with 5% growth",
    ],
)
def test_savings_questions_get_the_growth_calculation(message: str) -> None:
    summary = detect_calculation(message)
    assert summary is not None
    assert "Savings growth over 10 years at 5% a year" in summary
    assert "Total paid in: £24,000.00" in summary


def test_savings_with_a_starting_amount_and_monthly_payments() -> None:
    summary = detect_calculation("I have £1,000 saved and put in £100 a month. What is it worth after 2 years at 4%?")
    assert "Starting amount: £1,000.00" in summary and "Paid in each month: £100.00" in summary


@pytest.mark.parametrize(
    "message",
    [
        "I owe £1,200 on a credit card at 24% APR and pay £50 a month. How long to clear it?",
        "how long to pay off a 1200 debt at 24% paying 50 a month",
    ],
)
def test_debt_questions_get_the_payoff_calculation(message: str) -> None:
    summary = detect_calculation(message)
    assert summary is not None
    assert "Time to clear: 34 months" in summary and "Total interest: £451.11" in summary


def test_a_debt_payment_that_never_clears_is_answered_in_code_too() -> None:
    summary = detect_calculation("I owe £1,200 at 24% APR and can pay £20 a month")
    assert "never be cleared" in summary


@pytest.mark.parametrize(
    "message",
    [
        # no numbers, or not a sum
        "What is Income Tax?",
        "How do tax bands work?",
        "Why is my tax that much?",
        # more than one candidate salary: ambiguous
        "How much more tax on 52000 than on 50000?",
        # kinds of tax or pay the calculator does not cover
        "How much capital gains tax on £45,000?",
        "How much tax on £5,000 of dividends?",
        "How much tax on a £5,000 bonus?",
        "How much income tax on 45000 in Scotland?",
        "I'm self-employed and earn 45000, how much tax?",
        "How much tax on a pension of 45000?",
        "tax on rental income of 12000",
        # pay periods the calculator does not handle
        "How much tax if I earn £600 a week?",
        "take-home pay on £15 an hour",
        # too small to be a salary, or not money at all
        "How much tax on 500?",
        "I'm 30, how much tax will I pay?",
        "how much tax did people pay in 2026",
        # savings or debt questions missing a number
        "How much will £200 a month grow to?",
        "If I save £200 a month for 10 years what will I have?",
        "I owe £1,200 at 24% APR, how long to clear it?",
        # not asking about pay at all
        "Show me that with 2000 pounds a month",
        "Is 45000 a good salary?",
    ],
)
def test_unclear_or_uncovered_messages_are_left_to_the_tutor(message: str) -> None:
    assert detect_calculation(message) is None


def test_chat_sends_the_calculation_first_and_gives_it_to_the_tutor(
    client: TestClient, auth_headers, fake_ollama, read_events
) -> None:
    fake_ollama.reply_pieces = ["On £45,000 the Income Tax is £6,486.00 ", "and you take home £35,920.08."]
    res = client.post("/api/chat", json={"message": "How much tax on £45,000?", "topic": "UK taxes"}, headers=auth_headers)
    events = read_events(res)
    # The explanation is checked and sent whole; every amount in it came from the app's calculation.
    assert [e["type"] for e in events] == ["calculation", "token", "done"]
    calculation = events[0]
    assert "Income Tax: £6,486.00 a year" in calculation["summary"]
    assert signed_source(1, calculation["summary"], calculation["sig"]) == "app"
    assert events[1]["text"] == "On £45,000 the Income Tax is £6,486.00 and you take home £35,920.08."
    assert signed_source(1, events[1]["text"], events[2]["sig"]) == "tutor"
    # The result sits right beside the question the model is asked.
    asked = fake_ollama.requests[0]["messages"][-1]["content"]
    assert asked.startswith("How much tax on £45,000?")
    assert calculation["summary"] in asked and "using only the amounts shown" in asked


def test_an_explanation_with_its_own_sums_is_never_shown(client: TestClient, auth_headers, fake_ollama, read_events) -> None:
    fake_ollama.reply_pieces = ["You are in the 40% band, so the tax is ", "£15,080.40 a year."]
    res = client.post("/api/chat", json={"message": "How much tax on £45,000?"}, headers=auth_headers)
    events = read_events(res)
    assert [e["type"] for e in events] == ["calculation", "token", "done"]
    assert events[1]["text"] == EXPLANATION_FALLBACK
    assert "15,080" not in res.text
    # What gets signed, and so can come back as history, is the replacement and not the wrong sum.
    assert signed_source(1, EXPLANATION_FALLBACK, events[2]["sig"]) == "tutor"


def test_the_calculation_still_arrives_when_the_model_is_down(client: TestClient, auth_headers, fake_ollama, read_events) -> None:
    fake_ollama.status_code = 500
    res = client.post("/api/chat", json={"message": "How much tax on £45,000?"}, headers=auth_headers)
    assert res.status_code == 200
    events = read_events(res)
    assert [e["type"] for e in events] == ["calculation", "error"]
    assert "calculation above is exact" in events[1]["detail"]


def test_an_ordinary_question_gets_no_calculation(client: TestClient, auth_headers, fake_ollama, read_events) -> None:
    res = client.post("/api/chat", json={"message": "What is a budget?"}, headers=auth_headers)
    assert [e["type"] for e in read_events(res)] == ["token", "token", "done"]
