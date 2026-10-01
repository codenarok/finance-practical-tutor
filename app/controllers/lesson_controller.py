"""Lesson controller: serves lessons without their answers and marks attempts in code."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.controllers.auth_controller import get_current_user
from app.models.user import User
from app.services import lessons
from app.services.lesson_library import LESSONS
from app.services.signing import sign_reply


router = APIRouter(prefix="/api/lessons", tags=["lessons"])


class SignedText(BaseModel):
    """Text the server wrote, which the browser may add to the conversation as a trusted tutor turn."""

    text: str
    sig: str


class OptionView(BaseModel):
    key: str
    label: str


class QuestionView(BaseModel):
    """A question as the learner sees it: no answer, hint or working."""

    id: str
    prompt: str
    kind: Literal["number", "choice"]
    options: list[OptionView]
    unit: Literal["pounds", "percent", "count"]
    unit_label: str


class StepView(BaseModel):
    explanation: SignedText
    question: QuestionView


class LessonSummary(BaseModel):
    id: str
    title: str
    topic: str
    level: str
    summary: str
    questions: int


class LessonView(LessonSummary):
    steps: list[StepView]
    closing: SignedText


class AnswerRequest(BaseModel):
    question_id: str = Field(..., max_length=60)
    answer: str = Field(..., min_length=1, max_length=40)
    attempt: int = Field(1, ge=1, le=20, description="Which try this is; the working is shown from the second")


class AnswerResponse(BaseModel):
    correct: bool
    revealed: bool
    counted: bool  # false when the answer could not be read, so it does not use up a try
    feedback: str
    # Present once the question is finished: a record for the conversation, so the tutor can discuss it.
    record: Optional[SignedText] = None


def _signed(user: User, text: str) -> SignedText:
    return SignedText(text=text, sig=sign_reply(user.id, text, source="app"))


def _summary(lesson: lessons.Lesson) -> dict:
    return {
        "id": lesson.id,
        "title": lesson.title,
        "topic": lesson.topic,
        "level": lesson.level,
        "summary": lesson.summary,
        "questions": len(lesson.steps),
    }


def _get_lesson(lesson_id: str) -> lessons.Lesson:
    lesson = LESSONS.get(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    return lesson


@router.get("", response_model=list[LessonSummary])
def list_lessons(user: User = Depends(get_current_user)) -> list[LessonSummary]:
    """List the available lessons."""

    del user  # only checked for authentication
    return [LessonSummary(**_summary(lesson)) for lesson in LESSONS.values()]


@router.get("/{lesson_id}", response_model=LessonView)
def get_lesson(lesson_id: str, user: User = Depends(get_current_user)) -> LessonView:
    """Return a lesson's explanations and questions, without the answers."""

    lesson = _get_lesson(lesson_id)
    steps = [
        StepView(
            explanation=_signed(user, step.text),
            question=QuestionView(
                id=step.question.id,
                prompt=step.question.prompt,
                kind=step.question.kind,
                options=[OptionView(key=key, label=label) for key, label in step.question.options],
                unit=step.question.unit,
                unit_label=step.question.unit_label,
            ),
        )
        for step in lesson.steps
    ]
    return LessonView(**_summary(lesson), steps=steps, closing=_signed(user, lesson.closing))


@router.post("/{lesson_id}/answer", response_model=AnswerResponse)
def answer_question(lesson_id: str, payload: AnswerRequest, user: User = Depends(get_current_user)) -> AnswerResponse:
    """Mark one answer in code."""

    lesson = _get_lesson(lesson_id)
    question = lesson.question(payload.question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    marked = lessons.mark(question, payload.answer, payload.attempt)
    record = None
    if marked.revealed:
        # Built from the server's reading of the answer, never the learner's raw text.
        outcome = "which is correct" if marked.correct else "which is not correct"
        record = _signed(
            user,
            f"Lesson question: {question.prompt}\n"
            f"The learner answered {marked.answer_given}, {outcome}.\n"
            f"Working: {question.working}",
        )
    return AnswerResponse(
        correct=marked.correct,
        revealed=marked.revealed,
        counted=marked.answer_given is not None,
        feedback=marked.feedback,
        record=record,
    )
