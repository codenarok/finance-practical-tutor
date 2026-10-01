"""Money arithmetic done in code, so the model explains numbers and never works them out.

Each calculator returns a result with a plain-text `summary`. The summary is what the
learner sees and what the tutor is given to explain.
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.services import uk_figures as uk

PENNY = Decimal("0.01")
MAX_PAYOFF_MONTHS = 1200  # 100 years; beyond this the debt is treated as never cleared


class CalculationError(ValueError):
    """The inputs describe something that cannot be worked out."""


def _pence(amount: Decimal) -> Decimal:
    return amount.quantize(PENNY, rounding=ROUND_HALF_UP)


def _money(amount: Decimal) -> str:
    return f"£{_pence(amount):,.2f}"


def personal_allowance(gross_annual: Decimal) -> Decimal:
    """The tax-free allowance for a given income, after the taper above £100,000."""

    excess = gross_annual - uk.PERSONAL_ALLOWANCE_TAPER_START
    if excess <= 0:
        return Decimal(uk.PERSONAL_ALLOWANCE)
    reduction = (excess / 2).to_integral_value(rounding="ROUND_FLOOR")
    return max(Decimal(0), Decimal(uk.PERSONAL_ALLOWANCE) - reduction)


def income_tax(gross_annual: Decimal) -> Decimal:
    """Income Tax for a year of employment income (England, Wales, Northern Ireland)."""

    taxable = max(Decimal(0), gross_annual - personal_allowance(gross_annual))
    basic_band = Decimal(uk.BASIC_RATE_LIMIT - uk.PERSONAL_ALLOWANCE)
    additional_from = Decimal(uk.ADDITIONAL_RATE_THRESHOLD)
    basic = min(taxable, basic_band)
    higher = max(Decimal(0), min(taxable, additional_from) - basic_band)
    additional = max(Decimal(0), taxable - additional_from)
    return _pence(basic * uk.BASIC_RATE + higher * uk.HIGHER_RATE + additional * uk.ADDITIONAL_RATE)


def employee_ni(pay: Decimal, threshold: int, upper_limit: int) -> Decimal:
    """Category A employee National Insurance for one pay period."""

    main = max(Decimal(0), min(pay, Decimal(upper_limit)) - threshold)
    upper = max(Decimal(0), pay - upper_limit)
    return _pence(main * uk.NI_MAIN_RATE + upper * uk.NI_UPPER_RATE)


@dataclass(frozen=True)
class TakeHomePay:
    gross_annual: Decimal
    personal_allowance: Decimal
    income_tax: Decimal
    national_insurance: Decimal
    net_annual: Decimal
    net_monthly: Decimal
    summary: str


def take_home_pay(gross_annual: Decimal) -> TakeHomePay:
    """Estimate pay after Income Tax and National Insurance for a salaried employee."""

    allowance = personal_allowance(gross_annual)
    tax = income_tax(gross_annual)
    ni = employee_ni(gross_annual / 12, uk.NI_PRIMARY_THRESHOLD_MONTHLY, uk.NI_UPPER_LIMIT_MONTHLY) * 12
    net = gross_annual - tax - ni
    summary = (
        f"**Take-home pay estimate for a salary of {_money(gross_annual)} a year** ({uk.TAX_YEAR_LABEL} tax year)\n"
        f"- Tax-free Personal Allowance: {_money(allowance)}\n"
        f"- Income Tax: {_money(tax)} a year\n"
        f"- National Insurance: {_money(ni)} a year\n"
        f"- Take-home pay: {_money(net)} a year, about {_money(net / 12)} a month\n"
        "Assumes one job in England, Wales or Northern Ireland, equal monthly pay, the standard tax code, "
        "NI category A, and no pension contributions, student loan or benefits."
    )
    return TakeHomePay(gross_annual, allowance, tax, ni, _pence(net), _pence(net / 12), summary)


@dataclass(frozen=True)
class SavingsGrowth:
    final_value: Decimal
    total_paid_in: Decimal
    growth: Decimal
    summary: str


def savings_growth(initial: Decimal, monthly: Decimal, annual_rate_percent: Decimal, years: int) -> SavingsGrowth:
    """Grow a starting amount plus monthly payments at a steady yearly rate, compounded monthly."""

    monthly_rate = annual_rate_percent / 100 / 12
    value = initial
    for _ in range(years * 12):
        value = value * (1 + monthly_rate) + monthly  # payment arrives at the end of each month
    paid_in = initial + monthly * years * 12
    growth = value - paid_in
    summary = (
        f"**Savings growth over {years} year{'s' if years != 1 else ''} at {annual_rate_percent}% a year**\n"
        f"- Starting amount: {_money(initial)}\n"
        f"- Paid in each month: {_money(monthly)}\n"
        f"- Total paid in: {_money(paid_in)}\n"
        f"- Growth: {_money(growth)}\n"
        f"- Final value: {_money(value)}\n"
        "Assumes the same rate every year, compounded monthly, payments at the end of each month, "
        "and no fees, tax or inflation. Real investment returns go up and down and are not guaranteed."
    )
    return SavingsGrowth(_pence(value), _pence(paid_in), _pence(growth), summary)


@dataclass(frozen=True)
class DebtPayoff:
    months: int
    total_interest: Decimal
    total_paid: Decimal
    summary: str


def debt_payoff(balance: Decimal, apr_percent: Decimal, monthly_payment: Decimal) -> DebtPayoff:
    """Work out how long a fixed monthly payment takes to clear a debt, and the interest paid."""

    monthly_rate = apr_percent / 100 / 12
    first_interest = _pence(balance * monthly_rate)
    if monthly_payment <= first_interest:
        raise CalculationError(
            f"A payment of {_money(monthly_payment)} does not cover the first month's interest of "
            f"{_money(first_interest)}, so this debt would never be cleared."
        )
    remaining = balance
    total_interest = Decimal(0)
    months = 0
    while remaining > 0:
        if months == MAX_PAYOFF_MONTHS:
            raise CalculationError("At this payment the debt would take more than 100 years to clear.")
        interest = _pence(remaining * monthly_rate)
        total_interest += interest
        remaining = remaining + interest - min(monthly_payment, remaining + interest)
        months += 1
    years, extra_months = divmod(months, 12)
    duration = f"{months} month{'s' if months != 1 else ''}"
    if years:
        duration += f" ({years} year{'s' if years != 1 else ''}" + (f" {extra_months} months)" if extra_months else ")")
    summary = (
        f"**Paying off {_money(balance)} at {apr_percent}% APR with {_money(monthly_payment)} a month**\n"
        f"- Time to clear: {duration}\n"
        f"- Total interest: {_money(total_interest)}\n"
        f"- Total paid: {_money(balance + total_interest)}\n"
        "Assumes a fixed rate, interest added monthly, no new spending and no fees. "
        "A real lender's figures will differ slightly."
    )
    return DebtPayoff(months, _pence(total_interest), _pence(balance + total_interest), summary)
