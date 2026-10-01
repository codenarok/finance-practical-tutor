"""The figures table and how it reaches the tutor's instructions."""
from datetime import date

from fastapi.testclient import TestClient

from app.services import uk_figures as uk

IN_YEAR = date(2026, 10, 1)
AFTER_YEAR = date(2027, 4, 6)


def test_every_figure_cites_a_gov_uk_page_and_a_known_group() -> None:
    for figure in uk.FIGURES:
        assert figure.source.startswith("https://www.gov.uk/")
        assert figure.group in uk.ALL_GROUPS


def test_figures_are_current_only_inside_their_tax_year() -> None:
    assert uk.figures_are_current(uk.TAX_YEAR_START)
    assert uk.figures_are_current(uk.TAX_YEAR_END)
    assert not uk.figures_are_current(date(2026, 4, 5))
    assert not uk.figures_are_current(AFTER_YEAR)


def test_prompt_block_states_the_tax_year_and_the_figures() -> None:
    block = uk.prompt_block("UK taxes", today=IN_YEAR)
    assert "Official UK figures for the 2026 to 2027 tax year" in block
    assert "£12,570" in block
    assert "£20,000" in block
    assert "10.75%" in block
    assert "do not state a number" in block


def test_prompt_block_warns_once_the_tax_year_has_ended() -> None:
    block = uk.prompt_block("UK taxes", today=AFTER_YEAR)
    assert "no longer the current one" in block
    assert "Official UK figures" not in block
    assert "£12,570" in block


def test_topics_only_get_their_own_figures() -> None:
    budgeting = uk.prompt_block("Budgeting", today=IN_YEAR)
    assert "National Insurance" in budgeting
    assert "Lifetime ISA" not in budgeting
    retirement = uk.prompt_block("Retirement", today=IN_YEAR)
    assert "State Pension" in retirement
    assert "Dividends" not in retirement


def test_a_topic_without_figures_still_forbids_guessing() -> None:
    block = uk.prompt_block("Debt management", today=IN_YEAR)
    assert "no official UK figures" in block
    assert "do not state a number" in block


def test_every_chat_topic_has_a_figures_mapping() -> None:
    from typing import get_args

    from app.controllers.chat_controller import Topic

    assert set(get_args(Topic)) == set(uk.GROUPS_BY_TOPIC)


def test_the_tutor_is_given_the_figures_and_told_not_to_do_the_sums(client: TestClient, auth_headers, fake_ollama) -> None:
    client.post("/api/chat", json={"message": "How much can I put in an ISA?", "topic": "UK taxes"}, headers=auth_headers)
    system = fake_ollama.requests[0]["messages"][0]["content"]
    assert "up to £20,000 can be paid into ISAs" in system
    assert "Do not work out Income Tax" in system
