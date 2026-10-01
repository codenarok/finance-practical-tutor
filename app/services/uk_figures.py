"""Official UK figures for one tax year, read from gov.uk and kept in code.

The model never supplies a rate or allowance from memory: the tutor prompt and the
calculators both read from here. To roll over to a new tax year, re-check every
`source` page on gov.uk, update the numbers, the dates and `CHECKED_ON`, and run
the tests (they include gov.uk's own worked examples).

Income tax bands are for England, Wales and Northern Ireland. Scotland has its own.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

TAX_YEAR_LABEL = "2026 to 2027"
TAX_YEAR_START = date(2026, 4, 6)
TAX_YEAR_END = date(2027, 4, 5)
CHECKED_ON = date(2026, 10, 1)

# Income Tax – https://www.gov.uk/income-tax-rates
PERSONAL_ALLOWANCE = 12_570
PERSONAL_ALLOWANCE_TAPER_START = 100_000  # allowance falls £1 for every £2 above this
PERSONAL_ALLOWANCE_GONE_AT = 125_140
BASIC_RATE_LIMIT = 50_270  # top of the basic rate band, with the standard allowance
ADDITIONAL_RATE_THRESHOLD = 125_140
BASIC_RATE = Decimal("0.20")
HIGHER_RATE = Decimal("0.40")
ADDITIONAL_RATE = Decimal("0.45")

# National Insurance, category A – https://www.gov.uk/national-insurance-rates-letters
NI_PRIMARY_THRESHOLD_WEEKLY = 242
NI_UPPER_LIMIT_WEEKLY = 967
NI_PRIMARY_THRESHOLD_MONTHLY = 1_048
NI_UPPER_LIMIT_MONTHLY = 4_189
NI_MAIN_RATE = Decimal("0.08")
NI_UPPER_RATE = Decimal("0.02")
EMPLOYER_NI_RATE = Decimal("0.15")
EMPLOYER_NI_THRESHOLD_WEEKLY = 96

# ISAs – https://www.gov.uk/individual-savings-accounts and https://www.gov.uk/lifetime-isa
ISA_ALLOWANCE = 20_000
LIFETIME_ISA_LIMIT = 4_000
LIFETIME_ISA_BONUS_RATE = Decimal("0.25")
LIFETIME_ISA_MAX_BONUS = 1_000

# Pensions – https://www.gov.uk/tax-on-your-private-pension and https://www.gov.uk/workplace-pensions
PENSION_ANNUAL_ALLOWANCE = 60_000
PENSION_RELIEF_LIMIT_NO_EARNINGS = 2_880
AUTO_ENROLMENT_EARNINGS_TRIGGER = 10_000
AUTO_ENROLMENT_QUALIFYING_LOWER = 6_240
AUTO_ENROLMENT_QUALIFYING_UPPER = 50_270

# State Pension – https://www.gov.uk/new-state-pension
NEW_STATE_PENSION_WEEKLY = Decimal("241.30")

# Savings, dividends, capital gains –
# https://www.gov.uk/apply-tax-free-interest-on-savings, https://www.gov.uk/tax-on-dividends,
# https://www.gov.uk/capital-gains-tax
STARTING_RATE_FOR_SAVINGS = 5_000
STARTING_RATE_INCOME_LIMIT = 17_570
DIVIDEND_ALLOWANCE = 500
CAPITAL_GAINS_ALLOWANCE = 3_000


@dataclass(frozen=True)
class Figure:
    """One fact the tutor may quote, with the gov.uk page it came from."""

    group: str
    text: str
    source: str


def _money(amount: int) -> str:
    return f"£{amount:,}"


FIGURES: tuple[Figure, ...] = (
    Figure(
        "income_tax",
        f"Personal Allowance: {_money(PERSONAL_ALLOWANCE)} of income is tax-free. It shrinks by £1 for every £2 of "
        f"income above {_money(PERSONAL_ALLOWANCE_TAPER_START)} and is zero from {_money(PERSONAL_ALLOWANCE_GONE_AT)}.",
        "https://www.gov.uk/income-tax-rates",
    ),
    Figure(
        "income_tax",
        f"Income Tax bands (England, Wales, Northern Ireland; Scotland differs): basic rate 20% on income from "
        f"{_money(PERSONAL_ALLOWANCE + 1)} to {_money(BASIC_RATE_LIMIT)}; higher rate 40% from "
        f"{_money(BASIC_RATE_LIMIT + 1)} to {_money(ADDITIONAL_RATE_THRESHOLD)}; additional rate 45% above "
        f"{_money(ADDITIONAL_RATE_THRESHOLD)}.",
        "https://www.gov.uk/income-tax-rates",
    ),
    Figure(
        "national_insurance",
        f"Employee National Insurance (category A): nothing on pay up to {_money(NI_PRIMARY_THRESHOLD_WEEKLY)} a week "
        f"({_money(NI_PRIMARY_THRESHOLD_MONTHLY)} a month); 8% on pay from there to {_money(NI_UPPER_LIMIT_WEEKLY)} a week "
        f"({_money(NI_UPPER_LIMIT_MONTHLY)} a month); 2% above that.",
        "https://www.gov.uk/national-insurance-rates-letters",
    ),
    Figure(
        "national_insurance",
        f"Employer National Insurance (category A): 15% on an employee's pay above "
        f"{_money(EMPLOYER_NI_THRESHOLD_WEEKLY)} a week.",
        "https://www.gov.uk/national-insurance-rates-letters",
    ),
    Figure(
        "isa",
        f"ISA allowance: up to {_money(ISA_ALLOWANCE)} can be paid into ISAs in the tax year. Interest, income and "
        "gains inside an ISA are tax-free. Paying into an ISA does not give tax relief; that is pensions.",
        "https://www.gov.uk/individual-savings-accounts",
    ),
    Figure(
        "isa",
        f"Lifetime ISA: up to {_money(LIFETIME_ISA_LIMIT)} a year (counts towards the ISA allowance), with a 25% "
        f"government bonus of up to {_money(LIFETIME_ISA_MAX_BONUS)} a year. Must be opened before age 40; "
        "payments stop at 50. Withdrawals other than for a first home, from age 60, or terminal illness "
        "carry a 25% charge.",
        "https://www.gov.uk/lifetime-isa",
    ),
    Figure(
        "pensions",
        f"Pension contributions: tax relief on contributions up to 100% of yearly earnings, with an annual "
        f"allowance of {_money(PENSION_ANNUAL_ALLOWANCE)}. With no earnings, up to "
        f"{_money(PENSION_RELIEF_LIMIT_NO_EARNINGS)} a year still gets basic rate relief.",
        "https://www.gov.uk/tax-on-your-private-pension",
    ),
    Figure(
        "pensions",
        f"Workplace pension automatic enrolment: applies from age 22 to State Pension age when earning at least "
        f"{_money(AUTO_ENROLMENT_EARNINGS_TRIGGER)} a year. Minimum contributions are 8% in total (at least 3% from "
        f"the employer, 5% from the employee including tax relief), usually on earnings between "
        f"{_money(AUTO_ENROLMENT_QUALIFYING_LOWER)} and {_money(AUTO_ENROLMENT_QUALIFYING_UPPER)}.",
        "https://www.gov.uk/workplace-pensions",
    ),
    Figure(
        "pensions",
        f"New State Pension: the full rate is £{NEW_STATE_PENSION_WEEKLY} a week. It usually takes 35 qualifying "
        "years of National Insurance for the full rate and at least 10 to get any.",
        "https://www.gov.uk/new-state-pension",
    ),
    Figure(
        "savings_and_investments",
        f"Savings interest: the Personal Savings Allowance is £1,000 for basic rate taxpayers, £500 for higher rate "
        f"and £0 for additional rate. A starting rate for savings covers up to {_money(STARTING_RATE_FOR_SAVINGS)} "
        f"of interest when other income is below {_money(STARTING_RATE_INCOME_LIMIT)}.",
        "https://www.gov.uk/apply-tax-free-interest-on-savings",
    ),
    Figure(
        "savings_and_investments",
        f"Dividends outside an ISA or pension: the first {_money(DIVIDEND_ALLOWANCE)} a year is tax-free; above that "
        "the rates are 10.75% (basic rate band), 35.75% (higher) and 39.35% (additional).",
        "https://www.gov.uk/tax-on-dividends",
    ),
    Figure(
        "savings_and_investments",
        f"Capital Gains Tax: the first {_money(CAPITAL_GAINS_ALLOWANCE)} of gains in the tax year is tax-free.",
        "https://www.gov.uk/capital-gains-tax/allowances",
    ),
)

ALL_GROUPS = ("income_tax", "national_insurance", "isa", "pensions", "savings_and_investments")

# Which facts each topic gets. Keeps the prompt short and on-subject.
GROUPS_BY_TOPIC: dict[str, tuple[str, ...]] = {
    "General": ALL_GROUPS,
    "UK taxes": ALL_GROUPS,
    "Budgeting": ("income_tax", "national_insurance"),
    "Investing basics": ("isa", "savings_and_investments"),
    "Retirement": ("pensions", "isa"),
    "Risk management": ("isa", "savings_and_investments"),
    "Debt management": (),
    "Business finance": ("income_tax", "national_insurance", "savings_and_investments"),
}


def figures_are_current(today: Optional[date] = None) -> bool:
    """True while `today` falls inside the tax year these figures belong to."""

    today = today or date.today()
    return TAX_YEAR_START <= today <= TAX_YEAR_END


def figures_for_topic(topic: str) -> list[Figure]:
    """The facts relevant to a topic, in table order."""

    groups = GROUPS_BY_TOPIC.get(topic, ALL_GROUPS)
    return [figure for figure in FIGURES if figure.group in groups]


def prompt_block(topic: str, today: Optional[date] = None) -> str:
    """The figures section of the tutor's instructions."""

    rule = (
        "For any rate, allowance or threshold that is not listed here, do not state a number; "
        "tell the learner to check gov.uk."
    )
    figures = figures_for_topic(topic)
    if not figures:
        return f"You have no official UK figures for this topic. {rule}"
    if figures_are_current(today):
        heading = (
            f"Official UK figures for the {TAX_YEAR_LABEL} tax year (6 April to 5 April), taken from gov.uk. "
            "Use these exact figures when they are relevant and say which tax year they are for."
        )
    else:
        heading = (
            f"UK figures for the {TAX_YEAR_LABEL} tax year, taken from gov.uk. That tax year is no longer the "
            "current one, so whenever you use one of these, say it may have changed and tell the learner to "
            "check gov.uk."
        )
    lines = "\n".join(f"- {figure.text}" for figure in figures)
    return f"{heading} {rule}\n{lines}"
