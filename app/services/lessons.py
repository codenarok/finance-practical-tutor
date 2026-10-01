"""Short lessons whose answers are marked in code, not by the model.

This module is the engine: what a lesson is and how an answer is marked. The lessons
themselves are in `lesson_library.py`. The browser never receives an answer until the
learner gets it right or has used their attempts.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal, Optional

ATTEMPTS_BEFORE_REVEAL = 2
DEFAULT_TOLERANCE = "1"  # answers within £1 count, so rounding is never the reason for a miss
MAX_AMOUNT = Decimal("1000000000")  # anything larger is not a serious answer and is not echoed back


@dataclass(frozen=True)
class Question:
    id: str
    prompt: str
    kind: Literal["number", "choice"]
    answer: str  # a number, or the key of the right option
    hint: str
    working: str
    options: tuple[tuple[str, str], ...] = ()
    # For number questions: what the number measures, and how close counts as right.
    unit: Literal["pounds", "percent", "count"] = "pounds"
    unit_label: str = ""  # for counts, the thing counted: "months", "years"
    tolerance: str = DEFAULT_TOLERANCE
    # Wrong answers that reveal a specific misunderstanding, each with its own feedback.
    common_mistakes: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Step:
    text: str
    question: Question


@dataclass(frozen=True)
class Lesson:
    id: str
    title: str
    topic: str
    level: str
    summary: str
    steps: tuple[Step, ...]
    closing: str

    def question(self, question_id: str) -> Optional[Question]:
        return next((step.question for step in self.steps if step.question.id == question_id), None)


@dataclass(frozen=True)
class Marked:
    correct: bool
    revealed: bool  # true once the learner has been shown the working, right or wrong
    feedback: str
    answer_given: Optional[str] = None  # the learner's answer as the server read it, never their raw text


def pounds(amount: Decimal | int) -> str:
    amount = Decimal(amount)
    return f"£{amount:,.0f}" if amount == amount.to_integral_value() else f"£{amount:,.2f}"


def format_answer(question: Question, value: Decimal) -> str:
    """A number answer written the way the question means it: £1,250, 60% or 28 months."""

    if question.unit == "pounds":
        return pounds(value)
    plain = f"{value.normalize():f}"
    return f"{plain}%" if question.unit == "percent" else f"{plain} {question.unit_label}".strip()


def parse_amount(raw: str) -> Optional[Decimal]:
    """Read a number typed by a learner: '£7,430', '7430.00', ' 7 430 ' and '60%' all work."""

    cleaned = raw.replace("£", "").replace("%", "").replace(",", "").replace(" ", "")
    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        return None
    return amount if amount.is_finite() and 0 <= amount <= MAX_AMOUNT else None


def mark(question: Question, raw_answer: str, attempt: int) -> Marked:
    """Mark one answer. A miss gets a hint first; the working is shown once attempts run out."""

    if question.kind == "number":
        given = parse_amount(raw_answer)
        if given is None:
            return Marked(False, False, "Type your answer as a number, for example 1,250.")
        tolerance = Decimal(question.tolerance)
        correct = abs(given - Decimal(question.answer)) <= tolerance
        answer_given = format_answer(question, given)
        mistakes = {Decimal(wrong): feedback for wrong, feedback in question.common_mistakes}
        specific = next((text for wrong, text in mistakes.items() if abs(given - wrong) <= tolerance), None)
    else:
        labels = dict(question.options)
        if raw_answer not in labels:
            return Marked(False, False, "Pick one of the options.")
        correct = raw_answer == question.answer
        answer_given = labels[raw_answer]
        specific = dict(question.common_mistakes).get(raw_answer)

    if correct:
        return Marked(True, True, f"Correct. {question.working}", answer_given)
    if attempt >= ATTEMPTS_BEFORE_REVEAL:
        return Marked(False, True, f"Not quite. {question.working}", answer_given)
    return Marked(False, False, f"Not quite. {specific or question.hint} Have another go.", answer_given)
