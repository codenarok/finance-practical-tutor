"""The line between teaching and advising, held in code."""
import pytest

from app.services.advice_boundary import asks_for_recommendation, names_a_product, reads_like_a_recommendation


@pytest.mark.parametrize(
    "message",
    [
        "What should I buy?",
        "Should I buy Bitcoin?",
        "should i invest in index funds or individual shares",
        "Should I put my savings into a stocks and shares ISA?",
        "Should I pay off my credit card or save first?",
        "Should we overpay the mortgage?",
        "Which fund should I choose for my pension?",
        "Which ISA provider is best?",
        "which is better, a cash ISA or a stocks and shares ISA for me",
        "What's the best savings account right now?",
        "best stocks to buy in 2026",
        "Can you recommend a platform?",
        "What do you suggest I do with £10,000?",
        "Is Tesla a good investment?",
        "Is gold worth buying?",
        "Is now a good time to invest?",
        "Tell me what to do with my bonus",
        "What would you do with £5,000?",
        "Where should I put my emergency fund money?",
        "Would it be better to cash in my pension?",
    ],
)
def test_requests_for_a_personal_recommendation_are_spotted(message: str) -> None:
    assert asks_for_recommendation(message)


@pytest.mark.parametrize(
    "message",
    [
        "What is an ISA?",
        "How do I open an ISA?",
        "Can I put more than £20,000 into ISAs in a year?",
        "Which ISAs count towards the allowance?",
        "How do index funds work?",
        "What is the difference between a share and a fund?",
        "How should I think about risk?",
        "Why do people say to pay off expensive debt first?",
        "What does diversification mean?",
        "How much tax on £45,000?",
        "Should I start a budget?",
        "Do I pay tax on savings interest?",
        "What happens if I withdraw from a Lifetime ISA early?",
        "I got the last one wrong. Why isn't all of the salary taxed at 40%?",
        "What are the risks of buying shares?",
    ],
)
def test_questions_about_how_things_work_are_not_treated_as_advice_requests(message: str) -> None:
    assert not asks_for_recommendation(message)


@pytest.mark.parametrize(
    "reply",
    [
        "I recommend buying a global index fund.",
        "I'd suggest you open a stocks and shares ISA.",
        "I would strongly advise that you sell those shares.",
        "You should invest in a tracker fund.",
        "You should definitely put your money into property.",
        "You should go with the cheaper platform.",
        "My recommendation is a cash ISA.",
        "The best option for you is a Lifetime ISA.",
        "The best fund is one that tracks the whole market.",
        "Just buy the index and forget about it.",
        "If I were you, I'd wait.",
        "Consider opening an account with a low-cost platform and starting small.",
    ],
)
def test_replies_that_tell_the_learner_what_to_do_are_caught(reply: str) -> None:
    assert reads_like_a_recommendation(reply)


@pytest.mark.parametrize(
    "reply",
    [
        "I can't recommend what to buy, but here is how to compare funds.",
        "People who invest usually think about cost, risk and timescale.",
        "You should check gov.uk for the current allowance.",
        "A common rule of thumb is to build an emergency fund first.",
        "You should only invest money you will not need for at least five years.",
        "I recommend checking the fees before choosing anything.",
        "Some investors choose index funds because the fees are low.",
        "The best way to learn this is to try the exercise.",
    ],
)
def test_general_teaching_is_not_mistaken_for_a_recommendation(reply: str) -> None:
    assert not reads_like_a_recommendation(reply)


def test_product_names_the_learner_did_not_raise_are_caught() -> None:
    assert names_a_product("Many people use Vanguard for this.", "Which platform should I use?")
    assert names_a_product("Bitcoin and Ethereum are the largest.", "Should I buy crypto?")
    assert not names_a_product("Bitcoin is a cryptoasset whose price swings sharply.", "Should I buy bitcoin?")
    assert not names_a_product("An index such as the FTSE 100 tracks large companies.", "What should I buy?")
    assert not names_a_product("Eating an apple a day is cheaper.", "What should I buy?")


# --- in the chat endpoint ---

from fastapi.testclient import TestClient  # noqa: E402

from app.services.advice_boundary import ADVICE_NOTE, BOUNDARY_FALLBACK, BOUNDARY_INSTRUCTION  # noqa: E402
from app.services.signing import signed_source  # noqa: E402


def ask(client: TestClient, headers: dict, read_events, message: str) -> list[dict]:
    res = client.post("/api/chat", json={"message": message, "topic": "Investing basics"}, headers=headers)
    assert res.status_code == 200
    return read_events(res)


def test_an_advice_request_gets_the_rule_beside_the_question_and_a_checked_reply(
    client: TestClient, auth_headers, fake_ollama, read_events
) -> None:
    fake_ollama.reply_pieces = ["I can't recommend what to choose. ", "Compare the fees, the risk and how long you can leave the money."]
    events = ask(client, auth_headers, read_events, "Which fund should I buy?")
    # Held and sent whole, not streamed piece by piece.
    assert [e["type"] for e in events] == ["token", "done"]
    assert events[0]["text"].startswith("I can't recommend what to choose.")
    asked = fake_ollama.requests[0]["messages"][-1]["content"]
    assert asked == f"Which fund should I buy?\n\n{BOUNDARY_INSTRUCTION}"


@pytest.mark.parametrize(
    "model_reply",
    [
        "I recommend buying a global index fund.",
        "You should invest in a tracker fund with low fees.",
        "Many beginners start with Vanguard because it is cheap.",
    ],
)
def test_a_reply_that_recommends_or_names_a_product_never_reaches_the_learner(
    client: TestClient, auth_headers, fake_ollama, read_events, model_reply: str
) -> None:
    fake_ollama.reply_pieces = [model_reply]
    res = client.post("/api/chat", json={"message": "Which fund should I buy?"}, headers=auth_headers)
    events = read_events(res)
    assert [e["type"] for e in events] == ["token", "done"]
    assert events[0]["text"] == BOUNDARY_FALLBACK
    assert model_reply not in res.text
    # What is signed, and so can return as history, is the fixed answer.
    assert signed_source(1, BOUNDARY_FALLBACK, events[1]["sig"]) == "tutor"


def test_an_advice_request_is_still_answered_when_the_model_is_down(
    client: TestClient, auth_headers, fake_ollama, read_events
) -> None:
    fake_ollama.status_code = 500
    events = ask(client, auth_headers, read_events, "Should I buy Bitcoin?")
    assert [e["type"] for e in events] == ["token", "done"]
    assert events[0]["text"] == BOUNDARY_FALLBACK


def test_the_learner_may_name_a_product_and_have_it_explained(client: TestClient, auth_headers, fake_ollama, read_events) -> None:
    fake_ollama.reply_pieces = ["I can't say whether to buy it. Bitcoin is a cryptoasset whose price swings sharply."]
    events = ask(client, auth_headers, read_events, "Should I buy bitcoin?")
    assert "Bitcoin is a cryptoasset" in events[0]["text"]


def test_advice_slipping_into_an_ordinary_streamed_reply_is_followed_by_a_note(
    client: TestClient, auth_headers, fake_ollama, read_events
) -> None:
    fake_ollama.reply_pieces = ["An index fund holds many companies. ", "You should invest in a tracker fund."]
    events = ask(client, auth_headers, read_events, "How do index funds work?")
    assert [e["type"] for e in events] == ["token", "token", "note", "done"]
    assert events[2]["text"] == ADVICE_NOTE


def test_an_ordinary_teaching_reply_gets_no_note_and_no_boundary_instruction(
    client: TestClient, auth_headers, fake_ollama, read_events
) -> None:
    fake_ollama.reply_pieces = ["An index fund holds many companies, ", "which spreads the risk."]
    events = ask(client, auth_headers, read_events, "How do index funds work?")
    assert [e["type"] for e in events] == ["token", "token", "done"]
    assert BOUNDARY_INSTRUCTION not in fake_ollama.requests[0]["messages"][-1]["content"]


def test_advice_inside_the_explanation_of_a_calculation_is_replaced_too(
    client: TestClient, auth_headers, fake_ollama, read_events
) -> None:
    from app.controllers.chat_controller import EXPLANATION_FALLBACK

    fake_ollama.reply_pieces = ["The debt takes 34 months to clear. You should take out a cheaper loan instead."]
    events = ask(client, auth_headers, read_events, "I owe £1,200 on a credit card at 24% APR and pay £50 a month. How long?")
    assert [e["type"] for e in events] == ["calculation", "token", "done"]
    assert events[1]["text"] == EXPLANATION_FALLBACK


# --- debt: a learner's own debts get a fixed answer and never reach the model ---

from app.services.advice_boundary import DEBT_FALLBACK, asks_about_own_debt  # noqa: E402


@pytest.mark.parametrize(
    "message",
    [
        "Which debt do I pay first, my car loan or my card?",
        "I owe 3000 on two cards, what do I do?",
        "Should I pay off my credit card or save first?",
        "Is it better to clear my overdraft or my loan?",
        "Should we overpay the mortgage?",
        "How should I prioritise my debts?",
        "Should I consolidate my loans?",
        "What would you do about my credit card debt?",
        "I can't afford my repayments this month",
        "I'm behind on my credit card payments",
        "I've missed a payment and a debt collector wrote to me",
        "I'm struggling to keep up with my loan",
    ],
)
def test_questions_about_the_learners_own_debts_are_spotted(message: str) -> None:
    assert asks_about_own_debt(message)


@pytest.mark.parametrize(
    "message",
    [
        "How does credit card interest work?",
        "What is APR?",
        "What is the difference between a loan and an overdraft?",
        "Why do people say to pay off expensive debt first?",
        "What happens if someone misses a payment?",
        "What is an IVA?",
        "How does a minimum payment work?",
        "I owe £1,200 on a credit card at 24% APR and pay £50 a month. How long to clear it?",
        "Which fund should I buy?",
        "What should I do with £5,000?",
        "How do I open an ISA?",
    ],
)
def test_how_debt_works_and_non_debt_questions_are_not_treated_as_own_debt(message: str) -> None:
    assert not asks_about_own_debt(message)


@pytest.mark.parametrize(
    "reply",
    [
        "I recommend you pay off the card.",
        "You should pay off your credit card first.",
        "Clear the card first, then build savings.",
        "You should prioritise the loan with the highest rate.",
        "Here is a plan:\n- Pay off your overdraft\n- Then save",
        "It makes sense to deal with your loan first.",
        "I'd suggest consolidating your debts.",
    ],
)
def test_replies_that_tell_the_learner_which_debt_to_pay_are_caught(reply: str) -> None:
    assert reads_like_a_recommendation(reply)


@pytest.mark.parametrize(
    "reply",
    [
        "Interest is charged each month on what is still owed.",
        "A larger payment clears a debt sooner and costs less interest.",
        "People often pay the most expensive debt first because it costs the most to keep.",
        "In the lesson, Dan pays off the card in 34 months.",
        "A minimum payment mostly covers interest, so the balance falls slowly.",
    ],
)
def test_explaining_how_debt_works_is_not_mistaken_for_debt_advice(reply: str) -> None:
    assert not reads_like_a_recommendation(reply)


def test_an_own_debt_question_gets_the_fixed_answer_without_calling_the_model(
    client: TestClient, auth_headers, fake_ollama, read_events
) -> None:
    events = ask(client, auth_headers, read_events, "Which debt do I pay first, my car loan or my card?")
    assert [e["type"] for e in events] == ["token", "done"]
    assert events[0]["text"] == DEBT_FALLBACK
    assert "free debt adviser" in DEBT_FALLBACK and "MoneyHelper" in DEBT_FALLBACK
    assert fake_ollama.requests == []
    assert signed_source(1, DEBT_FALLBACK, events[1]["sig"]) == "tutor"


def test_a_sum_in_a_debt_worry_is_still_worked_out_but_not_explained_by_the_model(
    client: TestClient, auth_headers, fake_ollama, read_events
) -> None:
    events = ask(
        client, auth_headers, read_events,
        "I owe £1,200 on a credit card at 24% APR and pay £50 a month. I'm struggling to keep up, what do I do?",
    )
    assert [e["type"] for e in events] == ["calculation", "token", "done"]
    assert "Time to clear: 34 months" in events[0]["summary"]
    assert events[1]["text"] == DEBT_FALLBACK
    assert fake_ollama.requests == []


def test_a_how_debt_works_question_still_goes_to_the_tutor(client: TestClient, auth_headers, fake_ollama, read_events) -> None:
    fake_ollama.reply_pieces = ["Interest is charged each month on what is still owed."]
    events = ask(client, auth_headers, read_events, "How does credit card interest work?")
    assert [e["type"] for e in events] == ["token", "done"]
    assert len(fake_ollama.requests) == 1


def test_debt_advice_slipping_into_a_streamed_reply_is_followed_by_the_note(
    client: TestClient, auth_headers, fake_ollama, read_events
) -> None:
    fake_ollama.reply_pieces = ["Interest adds up quickly. ", "You should pay off your credit card first."]
    events = ask(client, auth_headers, read_events, "How does credit card interest work?")
    assert [e["type"] for e in events] == ["token", "token", "note", "done"]
