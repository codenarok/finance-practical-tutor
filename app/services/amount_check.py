"""Find money amounts in a tutor reply that the app did not supply.

The model is told not to do its own sums, but a small model sometimes does anyway
and gets them wrong. This check is the code-side backstop: any £ amount in a reply
that does not appear in text the app trusts is reported, so the learner is told.
"""
import re
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, InvalidOperation

_REPLY_AMOUNT = re.compile(r"£\s?(\d[\d,]*(?:\.\d+)?)")
_ANY_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _value(text: str) -> Decimal | None:
    try:
        return Decimal(text.replace(",", "").rstrip("."))
    except InvalidOperation:
        return None


def numbers_in(text: str) -> set[Decimal]:
    """Every number in a piece of trusted text, with or without a £ sign."""

    return {value for match in _ANY_NUMBER.findall(text) if (value := _value(match)) is not None}


def unchecked_amounts(reply: str, trusted_texts: list[str]) -> list[str]:
    """£ amounts in `reply`, in order and without repeats, that appear in none of the trusted texts."""

    trusted: set[Decimal] = set()
    for text in trusted_texts:
        trusted |= numbers_in(text)
    # Quoting a trusted amount to the nearest pound is fine: £1,233.92 may be written as £1,234.
    rounded = {value.to_integral_value(rounding=mode) for value in trusted for mode in (ROUND_FLOOR, ROUND_CEILING)}
    trusted |= rounded
    found: list[str] = []
    seen: set[Decimal] = set()
    for match in _REPLY_AMOUNT.findall(reply):
        value = _value(match)
        if value is None or value in trusted or value in seen:
            continue
        seen.add(value)
        found.append(f"£{match.rstrip('.,')}")
    return found
