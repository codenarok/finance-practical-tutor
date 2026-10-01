"""Short lessons whose answers are marked in code, not by the model.

Every number in a lesson is computed from the UK figures table and the calculators,
so lessons roll over with the tax year. The browser never receives an answer until
the learner gets it right or has used their attempts.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal, Optional

from app.services import calculators, uk_figures as uk

ATTEMPTS_BEFORE_REVEAL = 2
NUMBER_TOLERANCE = Decimal("1")  # answers within £1 count, so rounding is never the reason for a miss
MAX_AMOUNT = Decimal("1000000000")  # anything larger is not a serious answer and is not echoed back


@dataclass(frozen=True)
class Question:
    id: str
    prompt: str
    kind: Literal["number", "choice"]
    answer: str  # a number of pounds, or the key of the right option
    hint: str
    working: str
    options: tuple[tuple[str, str], ...] = ()
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


def _pounds(amount: Decimal | int) -> str:
    amount = Decimal(amount)
    return f"£{amount:,.0f}" if amount == amount.to_integral_value() else f"£{amount:,.2f}"


def parse_amount(raw: str) -> Optional[Decimal]:
    """Read an amount typed by a learner: '£7,430', '7430.00' and ' 7 430 ' are all 7430."""

    cleaned = raw.replace("£", "").replace(",", "").replace(" ", "")
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
        correct = abs(given - Decimal(question.answer)) <= NUMBER_TOLERANCE
        answer_given = _pounds(given)
        mistakes = {Decimal(wrong): feedback for wrong, feedback in question.common_mistakes}
        specific = next((text for wrong, text in mistakes.items() if abs(given - wrong) <= NUMBER_TOLERANCE), None)
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


def _income_tax_bands_lesson() -> Lesson:
    allowance = uk.PERSONAL_ALLOWANCE
    basic_limit = uk.BASIC_RATE_LIMIT

    sam_salary = 20_000
    sam_taxable = sam_salary - allowance
    sam_tax = calculators.income_tax(Decimal(sam_salary))

    priya_before, priya_after = 50_000, 52_000
    priya_higher_slice = priya_after - basic_limit
    priya_basic_slice = basic_limit - allowance
    priya_basic_tax = priya_basic_slice * uk.BASIC_RATE
    priya_higher_tax = priya_higher_slice * uk.HIGHER_RATE
    priya_tax = calculators.income_tax(Decimal(priya_after))
    priya_rise_kept = (priya_after - priya_before) - (
        priya_tax - calculators.income_tax(Decimal(priya_before))
    )

    return Lesson(
        id="income-tax-bands",
        title="How Income Tax bands work",
        topic="UK taxes",
        level="Beginner",
        summary="Why a pay rise never leaves you worse off, and how to work out the tax on a salary.",
        steps=(
            Step(
                text=(
                    "**Part 1: the tax-free slice**\n"
                    f"Everyone gets a Personal Allowance. In the {uk.TAX_YEAR_LABEL} tax year it is "
                    f"{_pounds(allowance)}: you pay no Income Tax on the first {_pounds(allowance)} you earn in the year. "
                    "Tax only starts on what you earn above it."
                ),
                question=Question(
                    id="taxable-income",
                    prompt=f"Sam earns {_pounds(sam_salary)} a year. How many pounds of that are taxed?",
                    kind="number",
                    answer=str(sam_taxable),
                    hint=f"Take the tax-free {_pounds(allowance)} away from Sam's salary.",
                    working=(
                        f"{_pounds(sam_salary)} minus the {_pounds(allowance)} allowance leaves "
                        f"{_pounds(sam_taxable)} that is taxed."
                    ),
                    common_mistakes=(
                        (str(sam_salary), "That is Sam's whole salary. The Personal Allowance comes off first."),
                        (str(allowance), "That is the tax-free part. The question asks for the part above it."),
                    ),
                ),
            ),
            Step(
                text=(
                    "**Part 2: the basic rate**\n"
                    f"Income between {_pounds(allowance + 1)} and {_pounds(basic_limit)} is taxed at the basic rate "
                    "of 20%. So 20p of each pound in that range goes in Income Tax. "
                    "(These bands are for England, Wales and Northern Ireland; Scotland has its own.)"
                ),
                question=Question(
                    id="basic-rate-tax",
                    prompt=f"How much Income Tax does Sam pay for the year on {_pounds(sam_salary)}?",
                    kind="number",
                    answer=str(sam_tax),
                    hint=f"Only the {_pounds(sam_taxable)} above the allowance is taxed. Find 20% of that.",
                    working=f"20% of {_pounds(sam_taxable)} is {_pounds(sam_tax)}.",
                    common_mistakes=(
                        (
                            str(sam_salary * uk.BASIC_RATE),
                            "That is 20% of the whole salary. The first "
                            f"{_pounds(allowance)} is tax-free, so take that off before finding 20%.",
                        ),
                    ),
                ),
            ),
            Step(
                text=(
                    "**Part 3: a rate applies to a slice, not to everything**\n"
                    f"Income above {_pounds(basic_limit)} is taxed at the higher rate of 40%. Many people think that "
                    "crossing into the higher band means all their pay is taxed at 40%. It does not. Each rate applies "
                    "only to the slice of income inside its band."
                ),
                question=Question(
                    id="crossing-the-band",
                    prompt=(
                        f"Priya gets a pay rise from {_pounds(priya_before)} to {_pounds(priya_after)}. "
                        "What happens to her Income Tax?"
                    ),
                    kind="choice",
                    answer="slice",
                    options=(
                        ("all", f"All {_pounds(priya_after)} is now taxed at 40%"),
                        ("rise", f"Her whole {_pounds(priya_after - priya_before)} pay rise is taxed at 40%"),
                        ("slice", f"Only the {_pounds(priya_higher_slice)} above {_pounds(basic_limit)} is taxed at 40%"),
                        ("worse", "She takes home less than before the rise"),
                    ),
                    hint=f"Look at how much of her new salary sits above {_pounds(basic_limit)}.",
                    working=(
                        f"Only the {_pounds(priya_higher_slice)} above {_pounds(basic_limit)} is in the higher band. "
                        "Everything below is taxed exactly as before."
                    ),
                    common_mistakes=(
                        ("all", "A rate never reaches back down. Income below the band keeps its lower rate."),
                        (
                            "rise",
                            f"Part of the rise, from {_pounds(priya_before)} up to {_pounds(basic_limit)}, "
                            "is still in the basic band.",
                        ),
                        (
                            "worse",
                            "A rise always leaves more after Income Tax, because the higher rate only "
                            "touches the extra pounds.",
                        ),
                    ),
                ),
            ),
            Step(
                text=(
                    "**Part 4: put it together**\n"
                    "To work out the tax on a salary, split it into slices and tax each slice at its own rate: "
                    f"nothing on the first {_pounds(allowance)}, 20% on the slice up to {_pounds(basic_limit)}, "
                    "and 40% on the slice above that."
                ),
                question=Question(
                    id="two-bands",
                    prompt=f"How much Income Tax does Priya pay for the year on {_pounds(priya_after)}?",
                    kind="number",
                    answer=str(priya_tax),
                    hint=(
                        f"Two slices: {_pounds(priya_basic_slice)} at 20% and {_pounds(priya_higher_slice)} at 40%. "
                        "Add the two results."
                    ),
                    working=(
                        f"20% of {_pounds(priya_basic_slice)} is {_pounds(priya_basic_tax)}. "
                        f"40% of {_pounds(priya_higher_slice)} is {_pounds(priya_higher_tax)}. "
                        f"Together that is {_pounds(priya_tax)}."
                    ),
                    common_mistakes=(
                        (
                            str(priya_after * uk.HIGHER_RATE),
                            "That is 40% of everything. Only the slice above "
                            f"{_pounds(basic_limit)} is taxed at 40%.",
                        ),
                        (
                            str((priya_after - allowance) * uk.BASIC_RATE),
                            f"That taxes everything above the allowance at 20%. The top {_pounds(priya_higher_slice)} "
                            "is in the higher band.",
                        ),
                    ),
                ),
            ),
        ),
        closing=(
            "**Lesson complete.** The idea to keep: each rate applies only to the slice of income inside its band, "
            f"so a pay rise always leaves you with more. Priya keeps {_pounds(priya_rise_kept)} of her "
            f"{_pounds(priya_after - priya_before)} rise after Income Tax. "
            "National Insurance is separate; the take-home pay calculator shows both together."
        ),
    )


LESSONS: dict[str, Lesson] = {lesson.id: lesson for lesson in (_income_tax_bands_lesson(),)}
