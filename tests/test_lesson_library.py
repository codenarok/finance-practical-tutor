"""Every lesson in the library: sound structure, safe payloads, and hand-checked answers."""
import json
from decimal import Decimal
from typing import get_args

import pytest
from fastapi.testclient import TestClient

from app.controllers.chat_controller import Topic
from app.services import lessons
from app.services.lesson_library import LESSONS

ALL_QUESTIONS = [(lesson.id, step.question) for lesson in LESSONS.values() for step in lesson.steps]
QUESTION_IDS = [f"{lesson_id}:{question.id}" for lesson_id, question in ALL_QUESTIONS]

# Worked by hand from the 2026 to 2027 figures. A change here should come from a change in uk_figures.py.
EXPECTED_ANSWERS = {
    "first-budget": {"needs": "1000", "saving": "400", "needs-percent": "60", "adjusting": "adjust"},
    "income-tax-bands": {"taxable-income": "7430", "basic-rate-tax": "1486", "crossing-the-band": "slice", "two-bands": "8232"},
    "salary-to-take-home": {"ni-charged-on": "1452", "monthly-ni": "116.16", "yearly-tax": "3486", "monthly-take-home": "2093.34"},
    "compound-growth": {"year-one": "50", "year-two": "52.5", "starting-early": "asha-much", "two-year-total": "1102.5"},
    "how-isas-work": {"allowance-left": "5000", "no-relief": "nothing", "lisa-bonus": "750", "after-lisa": "16000"},
    "workplace-pension": {"qualifying-earnings": "23760", "employer-share": "712.8", "total-contribution": "1900.8", "opting-out": "lost"},
    "emergency-fund": {"fund-target": "4200", "months-to-target": "28", "where-to-keep": "easy-access", "diversification": "one-company"},
    "what-debt-costs": {"first-interest": "24", "off-the-balance": "26", "interest-only": "never", "interest-saved": "265.13"},
    "profit-is-not-cash": {"profit": "1500", "margin": "18.75", "cash-fall": "2000", "profitable-but-broke": "timing"},
}


def test_answers_match_the_hand_worked_values() -> None:
    actual = {
        lesson.id: {
            step.question.id: (
                step.question.answer
                if step.question.kind == "choice"
                else f"{Decimal(step.question.answer).normalize():f}"
            )
            for step in lesson.steps
        }
        for lesson in LESSONS.values()
    }
    assert actual == EXPECTED_ANSWERS


def test_every_topic_a_learner_can_pick_has_a_lesson() -> None:
    topics_with_lessons = {lesson.topic for lesson in LESSONS.values()}
    assert topics_with_lessons == set(get_args(Topic)) - {"General"}


def test_ids_are_unique_and_every_lesson_has_four_questions() -> None:
    for lesson_id, lesson in LESSONS.items():
        assert lesson.id == lesson_id
        question_ids = [step.question.id for step in lesson.steps]
        assert len(question_ids) == len(set(question_ids)) == 4


@pytest.mark.parametrize(("lesson_id", "question"), ALL_QUESTIONS, ids=QUESTION_IDS)
def test_each_question_is_well_formed(lesson_id: str, question: lessons.Question) -> None:
    right = lessons.mark(question, question.answer, attempt=1)
    assert right.correct, "the stored answer must mark as correct"

    if question.kind == "choice":
        keys = [key for key, _ in question.options]
        assert question.answer in keys and len(keys) == len(set(keys)) >= 3
        assert {wrong for wrong, _ in question.common_mistakes} <= set(keys) - {question.answer}
    else:
        assert not question.options
        if question.unit == "count":
            assert question.unit_label

    for wrong, feedback in question.common_mistakes:
        marked = lessons.mark(question, wrong, attempt=1)
        assert not marked.correct, f"common mistake {wrong} must not be the right answer"
        assert feedback in marked.feedback


@pytest.mark.parametrize(("lesson_id", "question"), ALL_QUESTIONS, ids=QUESTION_IDS)
def test_a_hint_never_gives_the_answer_away(lesson_id: str, question: lessons.Question) -> None:
    if question.kind != "number":
        return
    answer = lessons.format_answer(question, Decimal(question.answer))
    assert answer not in question.hint
    for _, feedback in question.common_mistakes:
        assert answer not in feedback


def test_no_lesson_sends_answers_hints_or_working_to_the_browser(client: TestClient, auth_headers) -> None:
    for lesson in LESSONS.values():
        body = client.get(f"/api/lessons/{lesson.id}", headers=auth_headers).json()
        sent = json.dumps(body, ensure_ascii=False)
        for step in lesson.steps:
            assert step.question.working not in sent
            assert step.question.hint not in sent
            for _, feedback in step.question.common_mistakes:
                assert feedback not in sent


def test_percent_and_count_answers_are_read_and_recorded_in_their_own_units(client: TestClient, auth_headers) -> None:
    percent = client.post(
        "/api/lessons/first-budget/answer", json={"question_id": "needs-percent", "answer": "60%"}, headers=auth_headers
    ).json()
    assert percent["correct"] and "The learner answered 60%," in percent["record"]["text"]
    months = client.post(
        "/api/lessons/emergency-fund/answer", json={"question_id": "months-to-target", "answer": "28"}, headers=auth_headers
    ).json()
    assert months["correct"] and "The learner answered 28 months," in months["record"]["text"]
    near_miss = client.post(
        "/api/lessons/emergency-fund/answer", json={"question_id": "months-to-target", "answer": "27"}, headers=auth_headers
    ).json()
    assert not near_miss["correct"]
