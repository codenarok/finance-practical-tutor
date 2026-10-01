"""Spot chat messages that ask for a sum the calculators can do, and do it in code.

"How much tax on 45000?" should never be worked out by the model. This module reads
the message with plain pattern matching (no model call), and when it is confident
about both the question and the numbers it runs the matching calculator.

It is deliberately cautious. If a message is ambiguous, mentions a kind of tax or pay
the calculators do not cover, or is missing a number, nothing is detected and the
tutor answers in words as before.
"""
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from app.services import calculators

MAX_MONEY = Decimal(10_000_000)
MIN_SALARY = Decimal(1_000)

_NUMBER = re.compile(
    r"(?<![\w.])(?P<pound>£\s?)?(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)(?P<k>\s?k\b)?",
    re.IGNORECASE,
)
_PERCENT_AFTER = re.compile(r"\s*(?:%|percent\b|per cent\b)", re.IGNORECASE)
_YEARS_AFTER = re.compile(r"[\s-]*(?:years?|yrs?)\b", re.IGNORECASE)
_MONTHLY_AFTER = re.compile(r"\s*(?:(?:a|per|each|every)\s+month\b|/\s?month\b|monthly\b|pm\b|p\.m\.)", re.IGNORECASE)
_OTHER_PERIOD_AFTER = re.compile(
    r"\s*(?:(?:a|an|per|each|every)\s+(?:week|day|hour|fortnight)\b|/\s?(?:week|day|hour)\b|weekly\b|hourly\b|daily\b)",
    re.IGNORECASE,
)

_DEBT_WORDS = re.compile(r"\b(?:owe|owed|debt|debts|credit card|loan|overdraft|balance|pay(?:ing)? off|apr)\b", re.IGNORECASE)
_SAVING_WORDS = re.compile(
    r"\b(?:sav(?:e|es|ed|ing|ings)|invest(?:s|ed|ing)?|put(?:ting)? (?:away|aside|in)|pay(?:ing)? in|deposit(?:s|ed|ing)?|grow(?:s|n|th)?|compound(?:s|ed|ing)?)\b",
    re.IGNORECASE,
)
_PAY_TAX_WORDS = re.compile(
    r"\b(?:take[- ]?home|net pay|after tax|income tax|national insurance|ni|paye|"
    r"how much tax|tax (?:on|would|will|do|does|for)|in tax|taxed)\b",
    re.IGNORECASE,
)
# Kinds of tax, pay or situation the take-home calculator does not cover.
_NOT_SALARY_TAX = re.compile(
    r"\b(?:capital gains?|cgt|dividends?|inheritance|vat|corporation|council|stamp duty|road tax|"
    r"interest|pensions?|isa|self[- ]employed|sole trader|freelanc\w*|scotland|scottish|bonus|"
    r"pay ?rise|raise|redundancy|rent(?:al)?|property|shares?|crypto|student loan|second job|two jobs)\b",
    re.IGNORECASE,
)


@dataclass
class _Numbers:
    """The numbers in a message, sorted by what they are."""

    amounts: list[tuple[Decimal, bool]] = field(default_factory=list)  # (value, is a monthly amount)
    percents: list[Decimal] = field(default_factory=list)
    years: list[int] = field(default_factory=list)
    unsupported_period: bool = False  # weekly, daily or hourly amounts: not handled


def _read_numbers(message: str) -> _Numbers:
    found = _Numbers()
    for match in _NUMBER.finditer(message):
        value = Decimal(match["num"].replace(",", ""))
        marked = bool(match["pound"] or match["k"])
        if match["k"]:
            value *= 1000
        rest = message[match.end():]
        if _PERCENT_AFTER.match(rest):
            found.percents.append(value)
        elif not marked and _YEARS_AFTER.match(rest):
            if value == value.to_integral_value():
                found.years.append(int(value))
        elif _OTHER_PERIOD_AFTER.match(rest):
            found.unsupported_period = True
        elif not marked and "," not in match["num"] and 1990 <= value <= 2100:
            continue  # a calendar or tax year, not money
        else:
            monthly = bool(_MONTHLY_AFTER.match(rest))
            # A bare small number ("I'm 30", "2 jobs") is not money unless it is marked or per month.
            if marked or monthly or value >= 1000:
                found.amounts.append((value, monthly))
    return found


def _debt(message: str, numbers: _Numbers) -> Optional[str]:
    if not _DEBT_WORDS.search(message) or len(numbers.percents) != 1 or len(numbers.amounts) != 2:
        return None
    balances = [value for value, monthly in numbers.amounts if not monthly]
    payments = [value for value, monthly in numbers.amounts if monthly]
    if len(balances) != 1 or len(payments) != 1:
        return None
    balance, payment, apr = balances[0], payments[0], numbers.percents[0]
    if not (0 < balance <= MAX_MONEY and 0 < payment <= MAX_MONEY and apr <= 100):
        return None
    try:
        return calculators.debt_payoff(balance, apr, payment).summary
    except calculators.CalculationError as exc:
        return str(exc)


def _savings(message: str, numbers: _Numbers) -> Optional[str]:
    if not _SAVING_WORDS.search(message) or _DEBT_WORDS.search(message):
        return None
    if len(numbers.percents) != 1 or len(numbers.years) != 1 or not 1 <= len(numbers.amounts) <= 2:
        return None
    lump_sums = [value for value, monthly in numbers.amounts if not monthly]
    monthly_amounts = [value for value, monthly in numbers.amounts if monthly]
    if len(lump_sums) > 1 or len(monthly_amounts) > 1:
        return None
    initial = lump_sums[0] if lump_sums else Decimal(0)
    monthly = monthly_amounts[0] if monthly_amounts else Decimal(0)
    rate, years = numbers.percents[0], numbers.years[0]
    if not (initial <= MAX_MONEY and monthly <= MAX_MONEY and rate <= 100 and 1 <= years <= 60):
        return None
    return calculators.savings_growth(initial, monthly, rate, years).summary


def _take_home(message: str, numbers: _Numbers) -> Optional[str]:
    if not _PAY_TAX_WORDS.search(message) or _NOT_SALARY_TAX.search(message) or _DEBT_WORDS.search(message):
        return None
    if numbers.percents or len(numbers.amounts) != 1:
        return None
    value, monthly = numbers.amounts[0]
    salary = value * 12 if monthly else value
    if not MIN_SALARY <= salary <= MAX_MONEY:
        return None
    return calculators.take_home_pay(salary).summary


def detect_calculation(message: str) -> Optional[str]:
    """The calculator result a message is asking for, or None when it is not clearly asking for one."""

    numbers = _read_numbers(message)
    if numbers.unsupported_period:
        return None
    return _debt(message, numbers) or _savings(message, numbers) or _take_home(message, numbers)
