"""Calculator controller: arithmetic done in code and handed to the conversation as a signed result."""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.controllers.auth_controller import get_current_user
from app.models.user import User
from app.services import calculators
from app.services.signing import sign_reply


router = APIRouter(prefix="/api/calculate", tags=["calculators"])

Money = Field(..., ge=0, le=10_000_000, max_digits=10, decimal_places=2)
Rate = Field(..., ge=0, le=100, max_digits=5, decimal_places=2)


class TakeHomeRequest(BaseModel):
    salary: Decimal = Money


class SavingsGrowthRequest(BaseModel):
    initial: Decimal = Money
    monthly: Decimal = Money
    annual_rate_percent: Decimal = Rate
    years: int = Field(..., ge=1, le=60)


class DebtPayoffRequest(BaseModel):
    balance: Decimal = Field(..., gt=0, le=10_000_000, max_digits=10, decimal_places=2)
    apr_percent: Decimal = Rate
    monthly_payment: Decimal = Field(..., gt=0, le=10_000_000, max_digits=10, decimal_places=2)


class CalculationResponse(BaseModel):
    """A result the browser shows and adds to the conversation as a trusted tutor turn."""

    summary: str
    sig: str


def _respond(user: User, summary: str) -> CalculationResponse:
    return CalculationResponse(summary=summary, sig=sign_reply(user.id, summary))


@router.post("/take-home", response_model=CalculationResponse)
def take_home(payload: TakeHomeRequest, user: User = Depends(get_current_user)) -> CalculationResponse:
    """Estimate pay after Income Tax and National Insurance."""

    return _respond(user, calculators.take_home_pay(payload.salary).summary)


@router.post("/savings-growth", response_model=CalculationResponse)
def savings_growth(payload: SavingsGrowthRequest, user: User = Depends(get_current_user)) -> CalculationResponse:
    """Project savings with compound growth."""

    result = calculators.savings_growth(payload.initial, payload.monthly, payload.annual_rate_percent, payload.years)
    return _respond(user, result.summary)


@router.post("/debt-payoff", response_model=CalculationResponse)
def debt_payoff(payload: DebtPayoffRequest, user: User = Depends(get_current_user)) -> CalculationResponse:
    """Work out how long a debt takes to clear."""

    try:
        result = calculators.debt_payoff(payload.balance, payload.apr_percent, payload.monthly_payment)
    except calculators.CalculationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _respond(user, result.summary)
