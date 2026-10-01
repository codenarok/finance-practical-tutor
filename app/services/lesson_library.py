"""The lessons themselves. The engine that marks them is in `lessons.py`.

Every amount is computed from the UK figures table and the calculators, never typed
in, so lessons roll over with the tax year and cannot drift from the rest of the app.
To add a lesson, write a builder function and add it to `_BUILDERS`.
"""
from decimal import Decimal

from app.services import calculators, uk_figures as uk
from app.services.lessons import Lesson, Question, Step, pounds


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
                    f"{pounds(allowance)}: you pay no Income Tax on the first {pounds(allowance)} you earn in the year. "
                    "Tax only starts on what you earn above it."
                ),
                question=Question(
                    id="taxable-income",
                    prompt=f"Sam earns {pounds(sam_salary)} a year. How many pounds of that are taxed?",
                    kind="number",
                    answer=str(sam_taxable),
                    hint=f"Take the tax-free {pounds(allowance)} away from Sam's salary.",
                    working=(
                        f"{pounds(sam_salary)} minus the {pounds(allowance)} allowance leaves "
                        f"{pounds(sam_taxable)} that is taxed."
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
                    f"Income between {pounds(allowance + 1)} and {pounds(basic_limit)} is taxed at the basic rate "
                    "of 20%. So 20p of each pound in that range goes in Income Tax. "
                    "(These bands are for England, Wales and Northern Ireland; Scotland has its own.)"
                ),
                question=Question(
                    id="basic-rate-tax",
                    prompt=f"How much Income Tax does Sam pay for the year on {pounds(sam_salary)}?",
                    kind="number",
                    answer=str(sam_tax),
                    hint=f"Only the {pounds(sam_taxable)} above the allowance is taxed. Find 20% of that.",
                    working=f"20% of {pounds(sam_taxable)} is {pounds(sam_tax)}.",
                    common_mistakes=(
                        (
                            str(sam_salary * uk.BASIC_RATE),
                            "That is 20% of the whole salary. The first "
                            f"{pounds(allowance)} is tax-free, so take that off before finding 20%.",
                        ),
                    ),
                ),
            ),
            Step(
                text=(
                    "**Part 3: a rate applies to a slice, not to everything**\n"
                    f"Income above {pounds(basic_limit)} is taxed at the higher rate of 40%. Many people think that "
                    "crossing into the higher band means all their pay is taxed at 40%. It does not. Each rate applies "
                    "only to the slice of income inside its band."
                ),
                question=Question(
                    id="crossing-the-band",
                    prompt=(
                        f"Priya gets a pay rise from {pounds(priya_before)} to {pounds(priya_after)}. "
                        "What happens to her Income Tax?"
                    ),
                    kind="choice",
                    answer="slice",
                    options=(
                        ("all", f"All {pounds(priya_after)} is now taxed at 40%"),
                        ("rise", f"Her whole {pounds(priya_after - priya_before)} pay rise is taxed at 40%"),
                        ("slice", f"Only the {pounds(priya_higher_slice)} above {pounds(basic_limit)} is taxed at 40%"),
                        ("worse", "She takes home less than before the rise"),
                    ),
                    hint=f"Look at how much of her new salary sits above {pounds(basic_limit)}.",
                    working=(
                        f"Only the {pounds(priya_higher_slice)} above {pounds(basic_limit)} is in the higher band. "
                        "Everything below is taxed exactly as before."
                    ),
                    common_mistakes=(
                        ("all", "A rate never reaches back down. Income below the band keeps its lower rate."),
                        (
                            "rise",
                            f"Part of the rise, from {pounds(priya_before)} up to {pounds(basic_limit)}, "
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
                    f"nothing on the first {pounds(allowance)}, 20% on the slice up to {pounds(basic_limit)}, "
                    "and 40% on the slice above that."
                ),
                question=Question(
                    id="two-bands",
                    prompt=f"How much Income Tax does Priya pay for the year on {pounds(priya_after)}?",
                    kind="number",
                    answer=str(priya_tax),
                    hint=(
                        f"Two slices: {pounds(priya_basic_slice)} at 20% and {pounds(priya_higher_slice)} at 40%. "
                        "Add the two results."
                    ),
                    working=(
                        f"20% of {pounds(priya_basic_slice)} is {pounds(priya_basic_tax)}. "
                        f"40% of {pounds(priya_higher_slice)} is {pounds(priya_higher_tax)}. "
                        f"Together that is {pounds(priya_tax)}."
                    ),
                    common_mistakes=(
                        (
                            str(priya_after * uk.HIGHER_RATE),
                            "That is 40% of everything. Only the slice above "
                            f"{pounds(basic_limit)} is taxed at 40%.",
                        ),
                        (
                            str((priya_after - allowance) * uk.BASIC_RATE),
                            f"That taxes everything above the allowance at 20%. The top {pounds(priya_higher_slice)} "
                            "is in the higher band.",
                        ),
                    ),
                ),
            ),
        ),
        closing=(
            "**Lesson complete.** The idea to keep: each rate applies only to the slice of income inside its band, "
            f"so a pay rise always leaves you with more. Priya keeps {pounds(priya_rise_kept)} of her "
            f"{pounds(priya_after - priya_before)} rise after Income Tax. "
            "National Insurance is separate; the take-home pay calculator shows both together."
        ),
    )


def _take_home_lesson() -> Lesson:
    monthly_pay = 2_500
    salary = monthly_pay * 12
    ni_threshold = uk.NI_PRIMARY_THRESHOLD_MONTHLY
    ni_charged_on = monthly_pay - ni_threshold
    monthly_ni = calculators.employee_ni(Decimal(monthly_pay), ni_threshold, uk.NI_UPPER_LIMIT_MONTHLY)
    yearly_tax = calculators.income_tax(Decimal(salary))
    monthly_tax = yearly_tax / 12
    result = calculators.take_home_pay(Decimal(salary))

    return Lesson(
        id="salary-to-take-home",
        title="From salary to take-home pay",
        topic="UK taxes",
        level="Beginner",
        summary="The two deductions on a payslip, and how to get from a salary to what lands in the bank.",
        steps=(
            Step(
                text=(
                    "**Part 1: two deductions, two sets of rules**\n"
                    "An employee's pay has two main deductions: Income Tax and National Insurance (NI). They are worked "
                    f"out separately. In the {uk.TAX_YEAR_LABEL} tax year, most employees pay no NI on the first "
                    f"{pounds(ni_threshold)} of pay in a month, then 8% on pay up to {pounds(uk.NI_UPPER_LIMIT_MONTHLY)} "
                    "a month and 2% on anything above that."
                ),
                question=Question(
                    id="ni-charged-on",
                    prompt=f"Alex is paid {pounds(monthly_pay)} a month. On how many pounds of that is NI charged?",
                    kind="number",
                    answer=str(ni_charged_on),
                    hint=f"NI starts above {pounds(ni_threshold)} a month. Take that off Alex's monthly pay.",
                    working=f"{pounds(monthly_pay)} minus {pounds(ni_threshold)} leaves {pounds(ni_charged_on)}.",
                    common_mistakes=(
                        (str(monthly_pay), f"NI is not charged on all of it. The first {pounds(ni_threshold)} a month is free of NI."),
                    ),
                ),
            ),
            Step(
                text=(
                    "**Part 2: working out the NI**\n"
                    f"Alex's pay is below {pounds(uk.NI_UPPER_LIMIT_MONTHLY)} a month, so only the 8% rate applies, "
                    f"and only to the {pounds(ni_charged_on)} above the threshold."
                ),
                question=Question(
                    id="monthly-ni",
                    prompt="How much NI does Alex pay each month?",
                    kind="number",
                    answer=str(monthly_ni),
                    hint=f"Find 8% of {pounds(ni_charged_on)}.",
                    working=f"8% of {pounds(ni_charged_on)} is {pounds(monthly_ni)}.",
                    common_mistakes=(
                        (
                            str(monthly_pay * uk.NI_MAIN_RATE),
                            f"That is 8% of the whole {pounds(monthly_pay)}. Only the part above {pounds(ni_threshold)} is charged.",
                        ),
                    ),
                ),
            ),
            Step(
                text=(
                    "**Part 3: Income Tax works on the year**\n"
                    f"Income Tax looks at the whole year. Alex's salary is {pounds(salary)}. The first "
                    f"{pounds(uk.PERSONAL_ALLOWANCE)} is tax-free and the rest, being below {pounds(uk.BASIC_RATE_LIMIT)}, "
                    "is taxed at 20%."
                ),
                question=Question(
                    id="yearly-tax",
                    prompt=f"How much Income Tax does Alex pay for the year on {pounds(salary)}?",
                    kind="number",
                    answer=str(yearly_tax),
                    hint=f"Take {pounds(uk.PERSONAL_ALLOWANCE)} off the salary, then find 20% of what is left.",
                    working=(
                        f"{pounds(salary)} minus {pounds(uk.PERSONAL_ALLOWANCE)} is {pounds(salary - uk.PERSONAL_ALLOWANCE)}. "
                        f"20% of that is {pounds(yearly_tax)}."
                    ),
                    common_mistakes=(
                        (str(salary * uk.BASIC_RATE), "That is 20% of the whole salary. The Personal Allowance comes off first."),
                    ),
                ),
            ),
            Step(
                text=(
                    "**Part 4: what lands in the bank**\n"
                    f"Spread over twelve months, Alex's Income Tax is {pounds(monthly_tax)} a month, and you worked out "
                    f"NI of {pounds(monthly_ni)} a month. Take-home pay is what is left after both."
                ),
                question=Question(
                    id="monthly-take-home",
                    prompt=f"How much of the {pounds(monthly_pay)} does Alex take home each month?",
                    kind="number",
                    answer=str(result.net_monthly),
                    hint=f"Take both the {pounds(monthly_tax)} tax and the {pounds(monthly_ni)} NI off {pounds(monthly_pay)}.",
                    working=(
                        f"{pounds(monthly_pay)} minus {pounds(monthly_tax)} tax minus {pounds(monthly_ni)} NI "
                        f"leaves {pounds(result.net_monthly)}."
                    ),
                    common_mistakes=(
                        (str(monthly_pay - monthly_tax), "That takes off the Income Tax only. NI comes off as well."),
                    ),
                ),
            ),
        ),
        closing=(
            "**Lesson complete.** Two deductions, worked out separately: NI on each month's pay above its threshold, "
            "Income Tax on the year's income above the Personal Allowance. A real payslip may also show a pension "
            "contribution or a student loan repayment. The take-home pay calculator does this sum for any salary."
        ),
    )


def _budget_lesson() -> Lesson:
    take_home = 2_000
    needs = take_home * 50 // 100
    wants = take_home * 30 // 100
    saving = take_home * 20 // 100
    high_needs = 1_200
    high_needs_percent = high_needs * 100 // take_home

    return Lesson(
        id="first-budget",
        title="A first budget: 50/30/20",
        topic="Budgeting",
        level="Beginner",
        summary="A simple way to split take-home pay between needs, wants and saving.",
        steps=(
            Step(
                text=(
                    "**Part 1: needs**\n"
                    "The 50/30/20 budget is a rule of thumb, not a law. It splits take-home pay three ways. "
                    "Half goes on needs: the things you must pay, such as rent or mortgage, bills, food and travel to work."
                ),
                question=Question(
                    id="needs",
                    prompt=f"Jo takes home {pounds(take_home)} a month. How much does the rule set aside for needs?",
                    kind="number",
                    answer=str(needs),
                    hint=f"Find 50% (half) of {pounds(take_home)}.",
                    working=f"Half of {pounds(take_home)} is {pounds(needs)}.",
                ),
            ),
            Step(
                text=(
                    "**Part 2: wants, then saving**\n"
                    f"30% goes on wants: things that are nice but optional, such as eating out, subscriptions and holidays. "
                    f"For Jo that is {pounds(wants)}. The last 20% goes to saving and to paying off debt faster than the minimum."
                ),
                question=Question(
                    id="saving",
                    prompt="How much does the rule set aside each month for Jo's saving and extra debt payments?",
                    kind="number",
                    answer=str(saving),
                    hint=f"Find 20% of {pounds(take_home)}. 10% is {pounds(take_home // 10)}.",
                    working=f"20% of {pounds(take_home)} is {pounds(saving)}.",
                    common_mistakes=((str(wants), "That is the 30% for wants. Saving is the 20% share."),),
                ),
            ),
            Step(
                text=(
                    "**Part 3: when real life does not fit**\n"
                    f"When Jo adds up the bills, needs come to {pounds(high_needs)} a month, not {pounds(needs)}. "
                    "This is common, especially where rent is high. The first step is to see how far off the split is."
                ),
                question=Question(
                    id="needs-percent",
                    prompt=f"What percentage of Jo's {pounds(take_home)} take-home pay is {pounds(high_needs)}?",
                    kind="number",
                    unit="percent",
                    tolerance="0.5",
                    answer=str(high_needs_percent),
                    hint=f"Divide {pounds(high_needs)} by {pounds(take_home)}, then multiply by 100.",
                    working=f"{pounds(high_needs)} divided by {pounds(take_home)} is 0.6, which is {high_needs_percent}%.",
                ),
            ),
            Step(
                text=(
                    "**Part 4: adjusting the plan**\n"
                    f"Jo's needs take {high_needs_percent}%, which is {high_needs_percent - 50} points over the guide. "
                    "Something else has to give."
                ),
                question=Question(
                    id="adjusting",
                    prompt="What is the sensible way for Jo to use the 50/30/20 rule now?",
                    kind="choice",
                    answer="adjust",
                    options=(
                        ("failed", "Give up on it: the budget has failed"),
                        ("adjust", "Treat it as a guide: trim wants first and keep some saving going"),
                        ("stop", "Stop saving until needs fall back to 50%"),
                        ("borrow", "Borrow the difference so the split still adds up"),
                    ),
                    hint="The rule is a starting point. Which share is the most flexible?",
                    working=(
                        "The split is a guide. Wants are the flexible part, so they are trimmed first, "
                        "and keeping even a small amount of saving going protects against surprises."
                    ),
                    common_mistakes=(
                        ("failed", "A budget that does not match the guide is still a budget. The numbers show where to adjust."),
                        ("stop", "Stopping saving altogether leaves nothing for an unexpected bill. Wants are the flexible part."),
                        ("borrow", "Borrowing to cover regular spending adds interest on top and makes next month harder."),
                    ),
                ),
            ),
        ),
        closing=(
            "**Lesson complete.** 50/30/20 is a starting point: needs, wants, then saving and extra debt payments. "
            f"If Jo manages the full 20%, that is {pounds(saving * 12)} over a year. "
            "When needs are higher, trim wants first and keep some saving going."
        ),
    )


def _compound_growth_lesson() -> Lesson:
    start = Decimal(1_000)
    rate = Decimal("0.05")
    year_one_interest = start * rate
    after_one = start + year_one_interest
    year_two_interest = after_one * rate
    after_two = after_one + year_two_interest
    monthly = Decimal(100)
    early = calculators.savings_growth(Decimal(0), monthly, Decimal(5), 40)
    late = calculators.savings_growth(Decimal(0), monthly, Decimal(5), 30)

    return Lesson(
        id="compound-growth",
        title="How compound growth works",
        topic="Investing basics",
        level="Beginner",
        summary="Why growth earns its own growth, and why starting early matters more than it seems.",
        steps=(
            Step(
                text=(
                    "**Part 1: one year of growth**\n"
                    "Growth is usually quoted as a percentage per year. Savings interest is fixed in advance; "
                    "investment returns go up and down and are never guaranteed. To see the mechanics, "
                    "assume a steady 5% a year, added once a year."
                ),
                question=Question(
                    id="year-one",
                    prompt=f"{pounds(start)} grows by 5% in a year. How much growth is that in pounds?",
                    kind="number",
                    answer=str(year_one_interest),
                    hint=f"Find 5% of {pounds(start)}. 10% is {pounds(start / 10)}.",
                    working=f"5% of {pounds(start)} is {pounds(year_one_interest)}.",
                ),
            ),
            Step(
                text=(
                    "**Part 2: growth on the growth**\n"
                    f"After year one there is {pounds(after_one)}. In year two the 5% applies to all of it, "
                    "including last year's growth. That is compounding."
                ),
                question=Question(
                    id="year-two",
                    prompt="How much growth is added in year two?",
                    kind="number",
                    tolerance="0.5",
                    answer=str(year_two_interest),
                    hint=f"Find 5% of {pounds(after_one)}, not of {pounds(start)}.",
                    working=f"5% of {pounds(after_one)} is {pounds(year_two_interest)}, so the total is now {pounds(after_two)}.",
                    common_mistakes=(
                        (
                            str(year_one_interest),
                            f"That is year one's growth again. Year two's 5% applies to {pounds(after_one)}.",
                        ),
                    ),
                ),
            ),
            Step(
                text=(
                    "**Part 3: time does the heavy lifting**\n"
                    f"The extra {pounds(year_two_interest - year_one_interest)} in year two looks tiny. "
                    "But each year's growth is slightly bigger than the last, and over decades that adds up."
                ),
                question=Question(
                    id="starting-early",
                    prompt=(
                        f"Asha and Ben each pay in {pounds(monthly)} a month at the same steady 5% a year until age 65. "
                        "Asha starts at 25, Ben at 35. Who ends up with more?"
                    ),
                    kind="choice",
                    answer="asha-much",
                    options=(
                        ("same", "About the same: they pay in the same amount each month"),
                        ("asha-bit", "Asha, by about a third, because she pays in for a third longer"),
                        ("asha-much", "Asha, by far more than a third, because her early money compounds for longest"),
                        ("ben", "Ben, because his money is invested more recently"),
                    ),
                    hint="Asha pays in for 40 years, Ben for 30. Think about how long Asha's first payments have to grow.",
                    working=(
                        f"Using the savings growth calculator: Asha pays in {pounds(early.total_paid_in)} and ends with about "
                        f"{pounds(early.final_value.quantize(Decimal(1)))}; Ben pays in {pounds(late.total_paid_in)} and ends with about "
                        f"{pounds(late.final_value.quantize(Decimal(1)))}. Asha paid in a third more but ends with nearly twice as much."
                    ),
                    common_mistakes=(
                        ("same", "Same monthly amount, but Asha pays for ten more years and her money grows for longer."),
                        ("asha-bit", "She does pay in a third more, but her earliest payments also get ten extra years of compounding."),
                        ("ben", "When the money went in recently, it has had less time to grow, not more."),
                    ),
                ),
            ),
            Step(
                text=(
                    "**Part 4: check the two-year total**\n"
                    f"Back to the {pounds(start)}. You found {pounds(year_one_interest)} of growth in year one and "
                    f"{pounds(year_two_interest)} in year two."
                ),
                question=Question(
                    id="two-year-total",
                    prompt=f"What is the {pounds(start)} worth after the two years?",
                    kind="number",
                    tolerance="0.5",
                    answer=str(after_two),
                    hint=f"Add both years' growth to the starting {pounds(start)}.",
                    working=(
                        f"{pounds(start)} plus {pounds(year_one_interest)} plus {pounds(year_two_interest)} "
                        f"is {pounds(after_two)}."
                    ),
                    common_mistakes=(
                        (
                            str(start + 2 * year_one_interest),
                            f"That adds {pounds(year_one_interest)} twice. Year two's growth was {pounds(year_two_interest)}.",
                        ),
                    ),
                ),
            ),
        ),
        closing=(
            "**Lesson complete.** Compounding means growth earns its own growth, so time matters more than it first "
            "appears. The steady 5% here is only an illustration: real investments rise and fall, and can be worth "
            "less than was paid in. The savings growth calculator lets you try other amounts and timescales."
        ),
    )


def _isa_lesson() -> Lesson:
    allowance = uk.ISA_ALLOWANCE
    cash_paid, shares_paid = 6_000, 9_000
    remaining = allowance - cash_paid - shares_paid
    lisa_paid = 3_000
    lisa_bonus = lisa_paid * uk.LIFETIME_ISA_BONUS_RATE
    after_full_lisa = allowance - uk.LIFETIME_ISA_LIMIT

    return Lesson(
        id="how-isas-work",
        title="How ISAs work",
        topic="Investing basics",
        level="Beginner",
        summary="What an ISA shelters from tax, what the yearly allowance means, and the Lifetime ISA bonus.",
        steps=(
            Step(
                text=(
                    "**Part 1: the yearly allowance**\n"
                    "An ISA is a wrapper around savings or investments. Interest, income and gains inside it are tax-free. "
                    f"In the {uk.TAX_YEAR_LABEL} tax year you can pay in up to {pounds(allowance)} in total, "
                    "in one ISA or split across several types."
                ),
                question=Question(
                    id="allowance-left",
                    prompt=(
                        f"This tax year Sam has paid {pounds(cash_paid)} into a cash ISA and {pounds(shares_paid)} into a "
                        "stocks and shares ISA. How much more can Sam pay into ISAs this tax year?"
                    ),
                    kind="number",
                    answer=str(remaining),
                    hint=f"Add up what Sam has paid in and take it from {pounds(allowance)}.",
                    working=(
                        f"{pounds(cash_paid)} plus {pounds(shares_paid)} is {pounds(cash_paid + shares_paid)}. "
                        f"{pounds(allowance)} minus that leaves {pounds(remaining)}."
                    ),
                    common_mistakes=(
                        (str(allowance), "The allowance is shared across all of Sam's ISAs, not given once per ISA."),
                        (str(allowance - cash_paid), "That only takes off the cash ISA. The stocks and shares ISA counts too."),
                    ),
                ),
            ),
            Step(
                text=(
                    "**Part 2: what an ISA does not do**\n"
                    "ISAs are often confused with pensions. A pension gives tax relief on the way in. "
                    "An ISA works the other way round."
                ),
                question=Question(
                    id="no-relief",
                    prompt="Sam pays £5,000 into an ISA from take-home pay. What happens to Sam's Income Tax bill?",
                    kind="choice",
                    answer="nothing",
                    options=(
                        ("relief", "It falls: ISA payments get tax relief"),
                        ("nothing", "Nothing: the money was already taxed, and the benefit is tax-free growth and withdrawals"),
                        ("bonus", "The government adds 20% to whatever is paid in"),
                        ("later", "Nothing now, but tax is due when the money is taken out"),
                    ),
                    hint="Think about when the tax benefit of an ISA arrives: going in, or while inside and coming out?",
                    working=(
                        "Money goes into an ISA from income that has already been taxed, with no relief. "
                        "The benefit is that interest, income and gains inside are tax-free, and so are withdrawals."
                    ),
                    common_mistakes=(
                        ("relief", "That describes a pension. ISA payments do not reduce your tax bill."),
                        ("bonus", "Only the Lifetime ISA has a bonus, and it is 25% on a limited amount."),
                        ("later", "That describes a pension. Money taken out of an ISA is not taxed."),
                    ),
                ),
            ),
            Step(
                text=(
                    "**Part 3: the Lifetime ISA**\n"
                    f"A Lifetime ISA is for a first home or for later life. You can pay in up to "
                    f"{pounds(uk.LIFETIME_ISA_LIMIT)} a tax year and the government adds a 25% bonus. "
                    "It must be opened before age 40."
                ),
                question=Question(
                    id="lisa-bonus",
                    prompt=f"Sam pays {pounds(lisa_paid)} into a Lifetime ISA in a tax year. How much bonus is added?",
                    kind="number",
                    answer=str(lisa_bonus),
                    hint=f"Find 25% (a quarter) of {pounds(lisa_paid)}.",
                    working=f"25% of {pounds(lisa_paid)} is {pounds(lisa_bonus)}.",
                    common_mistakes=(
                        (
                            str(uk.LIFETIME_ISA_MAX_BONUS),
                            f"That is the most the bonus can be, for someone paying in the full {pounds(uk.LIFETIME_ISA_LIMIT)}.",
                        ),
                    ),
                ),
            ),
            Step(
                text=(
                    "**Part 4: one allowance for everything**\n"
                    f"The Lifetime ISA limit is not extra. Whatever goes into it counts towards the {pounds(allowance)} total."
                ),
                question=Question(
                    id="after-lisa",
                    prompt=(
                        f"If Sam pays the full {pounds(uk.LIFETIME_ISA_LIMIT)} into a Lifetime ISA, how much of the year's "
                        "ISA allowance is left for other ISAs?"
                    ),
                    kind="number",
                    answer=str(after_full_lisa),
                    hint=f"Take the {pounds(uk.LIFETIME_ISA_LIMIT)} from the {pounds(allowance)} total.",
                    working=f"{pounds(allowance)} minus {pounds(uk.LIFETIME_ISA_LIMIT)} leaves {pounds(after_full_lisa)}.",
                    common_mistakes=(
                        (str(allowance), "The Lifetime ISA uses up part of the same allowance; it is not on top."),
                    ),
                ),
            ),
        ),
        closing=(
            "**Lesson complete.** An ISA does not cut your tax bill on the way in; it keeps growth and withdrawals "
            f"tax-free. One {pounds(allowance)} allowance covers every ISA you pay into in the tax year. "
            "A Lifetime ISA adds a 25% bonus, but taking money out before age 60 for anything other than a first home "
            "usually carries a 25% charge, which takes back more than the bonus."
        ),
    )


def _workplace_pension_lesson() -> Lesson:
    salary = 30_000
    lower = uk.AUTO_ENROLMENT_QUALIFYING_LOWER
    qualifying = salary - lower
    employer = Decimal(qualifying) * Decimal("0.03")
    own = Decimal(qualifying) * Decimal("0.05")
    total = employer + own

    return Lesson(
        id="workplace-pension",
        title="Workplace pensions: your employer pays in too",
        topic="Retirement",
        level="Beginner",
        summary="How automatic enrolment works and what the minimum contributions add up to.",
        steps=(
            Step(
                text=(
                    "**Part 1: which earnings count**\n"
                    "Most employees are put into a workplace pension automatically. In most schemes, contributions are "
                    f"based on 'qualifying earnings': the part of your pay between {pounds(lower)} and "
                    f"{pounds(uk.AUTO_ENROLMENT_QUALIFYING_UPPER)} a year. Some schemes use all of your pay instead."
                ),
                question=Question(
                    id="qualifying-earnings",
                    prompt=f"Riya earns {pounds(salary)} a year. How much of that counts as qualifying earnings?",
                    kind="number",
                    answer=str(qualifying),
                    hint=f"Take the first {pounds(lower)} off Riya's salary.",
                    working=f"{pounds(salary)} minus {pounds(lower)} leaves {pounds(qualifying)}.",
                    common_mistakes=(
                        (str(salary), f"In most schemes the first {pounds(lower)} does not count."),
                    ),
                ),
            ),
            Step(
                text=(
                    "**Part 2: the employer's share**\n"
                    "The minimum total contribution is 8% of qualifying earnings. The employer must pay at least 3% of it."
                ),
                question=Question(
                    id="employer-share",
                    prompt="At the minimum, how much does Riya's employer pay into her pension over the year?",
                    kind="number",
                    answer=str(employer),
                    hint=f"Find 3% of {pounds(qualifying)}.",
                    working=f"3% of {pounds(qualifying)} is {pounds(employer)}.",
                    common_mistakes=(
                        (str(salary * Decimal("0.03")), f"That is 3% of the whole salary. Use the {pounds(qualifying)} of qualifying earnings."),
                    ),
                ),
            ),
            Step(
                text=(
                    "**Part 3: the total going in**\n"
                    f"The other 5% comes from Riya, and that 5% includes tax relief the government adds. "
                    f"For Riya it comes to {pounds(own)} a year."
                ),
                question=Question(
                    id="total-contribution",
                    prompt="How much goes into Riya's pension in total over the year, at the minimum 8%?",
                    kind="number",
                    answer=str(total),
                    hint=f"Add the employer's {pounds(employer)} to Riya's {pounds(own)}, or find 8% of {pounds(qualifying)}.",
                    working=f"{pounds(employer)} plus {pounds(own)} is {pounds(total)}, which is 8% of {pounds(qualifying)}.",
                    common_mistakes=((str(own), "That is Riya's 5% share alone. The employer's 3% goes in on top."),),
                ),
            ),
            Step(
                text=(
                    "**Part 4: opting out**\n"
                    "Employees can choose to leave the scheme. It raises take-home pay a little today."
                ),
                question=Question(
                    id="opting-out",
                    prompt="If Riya opts out, what happens to the money her employer was paying in?",
                    kind="choice",
                    answer="lost",
                    options=(
                        ("salary", "It is added to her salary instead"),
                        ("lost", "It stops: she gives up the employer's contribution"),
                        ("saved", "It is kept for her until she rejoins"),
                        ("state", "It goes towards her State Pension"),
                    ),
                    hint="The employer's contribution exists only because she is in the scheme.",
                    working=(
                        f"The employer's contribution stops. For Riya that is {pounds(employer)} a year "
                        "she would not get any other way."
                    ),
                    common_mistakes=(
                        ("salary", "Employers do not have to pay it as wages instead, and usually do not."),
                        ("saved", "Nothing is set aside while she is out of the scheme."),
                        ("state", "The State Pension is built from National Insurance, not from workplace pension money."),
                    ),
                ),
            ),
        ),
        closing=(
            "**Lesson complete.** In a workplace pension the employer adds money you would not otherwise receive, "
            f"and tax relief adds more. At the minimum, {pounds(total)} a year goes into Riya's pension. "
            "These are legal minimums for most schemes; your own scheme's rules may be more generous, so check them."
        ),
    )


def _debt_cost_lesson() -> Lesson:
    balance = Decimal(1_200)
    apr = Decimal(24)
    monthly_rate_percent = apr / 12
    first_interest = balance * monthly_rate_percent / 100
    low_payment, high_payment = Decimal(50), Decimal(100)
    off_balance = low_payment - first_interest
    slow = calculators.debt_payoff(balance, apr, low_payment)
    fast = calculators.debt_payoff(balance, apr, high_payment)
    interest_saved = slow.total_interest - fast.total_interest

    return Lesson(
        id="what-debt-costs",
        title="What a debt really costs",
        topic="Debt management",
        level="Beginner",
        summary="How interest is charged each month, and why a bigger payment saves more than it seems.",
        steps=(
            Step(
                text=(
                    "**Part 1: a month of interest**\n"
                    "A card's interest is quoted as a yearly rate, the APR, but it is charged every month. "
                    f"As a simple guide, divide the APR by 12: a {apr}% APR is roughly {monthly_rate_percent}% a month "
                    "on whatever is owed."
                ),
                question=Question(
                    id="first-interest",
                    prompt=f"Dan owes {pounds(balance)} on a card at {apr}% APR. Roughly how much interest is charged in the first month?",
                    kind="number",
                    answer=str(first_interest),
                    hint=f"Find {monthly_rate_percent}% of {pounds(balance)}.",
                    working=f"{monthly_rate_percent}% of {pounds(balance)} is {pounds(first_interest)}.",
                    common_mistakes=(
                        (str(balance * apr / 100), "That is a whole year's interest. One month is about a twelfth of it."),
                    ),
                ),
            ),
            Step(
                text=(
                    "**Part 2: where a payment goes**\n"
                    "Each payment first covers that month's interest. Only what is left reduces the debt itself."
                ),
                question=Question(
                    id="off-the-balance",
                    prompt=f"Dan pays {pounds(low_payment)} in the first month. How much of that actually comes off the {pounds(balance)}?",
                    kind="number",
                    answer=str(off_balance),
                    hint=f"Take the {pounds(first_interest)} of interest away from the {pounds(low_payment)} payment.",
                    working=(
                        f"{pounds(low_payment)} minus {pounds(first_interest)} interest leaves {pounds(off_balance)} "
                        "to reduce the debt."
                    ),
                    common_mistakes=(
                        (str(low_payment), "Not all of it. The first slice of every payment goes on interest."),
                    ),
                ),
            ),
            Step(
                text=(
                    "**Part 3: the trap**\n"
                    "The smaller the payment, the larger the share that interest takes."
                ),
                question=Question(
                    id="interest-only",
                    prompt=f"What happens if Dan pays only {pounds(first_interest)} a month and spends nothing more on the card?",
                    kind="choice",
                    answer="never",
                    options=(
                        ("slow", "The debt clears, but slowly"),
                        ("never", "The debt never goes down: the payment only covers the interest"),
                        ("grows", "The debt grows every month"),
                        ("four-years", f"It clears in about four years, since {pounds(first_interest)} is a fiftieth of {pounds(balance)}"),
                    ),
                    hint=f"Compare the payment with the {pounds(first_interest)} of interest charged each month.",
                    working=(
                        f"A {pounds(first_interest)} payment exactly matches the month's interest, so nothing comes off the "
                        f"{pounds(balance)}. Dan could pay for ever and still owe the same."
                    ),
                    common_mistakes=(
                        ("slow", "For the debt to fall, the payment has to be bigger than the interest."),
                        ("grows", "It would grow if he paid less than the interest. Paying exactly the interest keeps it level."),
                        ("four-years", "That ignores interest. Every pound of the payment is used up by it."),
                    ),
                ),
            ),
            Step(
                text=(
                    "**Part 4: what a bigger payment buys**\n"
                    f"The debt payoff calculator gives these results for Dan. Paying {pounds(low_payment)} a month: "
                    f"{slow.months} months and {pounds(slow.total_interest)} of interest. Paying {pounds(high_payment)} a month: "
                    f"{fast.months} months and {pounds(fast.total_interest)} of interest."
                ),
                question=Question(
                    id="interest-saved",
                    prompt=f"How much interest does Dan save by paying {pounds(high_payment)} a month instead of {pounds(low_payment)}?",
                    kind="number",
                    answer=str(interest_saved),
                    hint="Take the smaller interest total away from the larger one.",
                    working=(
                        f"{pounds(slow.total_interest)} minus {pounds(fast.total_interest)} is {pounds(interest_saved)} saved, "
                        f"and the debt is gone {slow.months - fast.months} months sooner."
                    ),
                ),
            ),
        ),
        closing=(
            "**Lesson complete.** Interest is charged on what is still owed, so every extra pound paid early stops "
            f"interest on that pound in every later month. Doubling Dan's payment cut the time from {slow.months} months to "
            f"{fast.months}. If repayments are a struggle, free debt advice exists; MoneyHelper, the government-backed service, "
            "can point you to it."
        ),
    )


def _emergency_fund_lesson() -> Lesson:
    essentials = 1_400
    months_target = 3
    target = essentials * months_target
    monthly_saving = 150
    months_needed = target // monthly_saving

    return Lesson(
        id="emergency-fund",
        title="An emergency fund, and why to spread risk",
        topic="Risk management",
        level="Beginner",
        summary="How big a safety cushion to aim for, where it belongs, and the idea behind diversification.",
        steps=(
            Step(
                text=(
                    "**Part 1: the cushion**\n"
                    "Risk management starts with the dull risks: a broken boiler, a gap between jobs. "
                    "A common rule of thumb is to build an emergency fund covering about three months of essential costs. "
                    "It is a guide; some people want more."
                ),
                question=Question(
                    id="fund-target",
                    prompt=f"Mia's essential costs are {pounds(essentials)} a month. What is a three-month emergency fund for her?",
                    kind="number",
                    answer=str(target),
                    hint=f"Multiply {pounds(essentials)} by 3.",
                    working=f"3 times {pounds(essentials)} is {pounds(target)}.",
                ),
            ),
            Step(
                text=(
                    "**Part 2: getting there**\n"
                    "The target can look out of reach. Breaking it into a monthly amount makes it a plan."
                ),
                question=Question(
                    id="months-to-target",
                    prompt=f"Mia can put aside {pounds(monthly_saving)} a month. Ignoring interest, how many months until she reaches {pounds(target)}?",
                    kind="number",
                    unit="count",
                    unit_label="months",
                    tolerance="0",
                    answer=str(months_needed),
                    hint=f"Divide {pounds(target)} by {pounds(monthly_saving)}.",
                    working=f"{pounds(target)} divided by {pounds(monthly_saving)} is {months_needed} months.",
                ),
            ),
            Step(
                text=(
                    "**Part 3: where it lives**\n"
                    "An emergency fund has one job: to be there, in full, on the day it is needed."
                ),
                question=Question(
                    id="where-to-keep",
                    prompt="Which is the best home for Mia's emergency fund?",
                    kind="choice",
                    answer="easy-access",
                    options=(
                        ("shares", "Shares, because they tend to grow most over time"),
                        ("easy-access", "An easy-access savings account she can withdraw from straight away"),
                        ("fixed", "A five-year fixed account, for the higher interest rate"),
                        ("current", "Mixed in with everyday spending money in her current account"),
                    ),
                    hint="Two things matter: can she get it immediately, and will it all still be there?",
                    working=(
                        "Easy-access savings can be withdrawn at once and do not fall in value. Shares can be down just "
                        "when the money is needed, a fixed account locks it away, and money mixed into everyday spending tends to get spent."
                    ),
                    common_mistakes=(
                        ("shares", "Shares can fall sharply in the short term, which is exactly when an emergency might strike."),
                        ("fixed", "A fixed account usually cannot be opened early, or charges a penalty for it."),
                        ("current", "It is reachable, but with no separation it is easy to spend without noticing."),
                    ),
                ),
            ),
            Step(
                text=(
                    "**Part 4: spreading risk**\n"
                    "Money invested for the long term faces a different risk: any one company can do badly or fail. "
                    "Diversification means spreading money across many investments so no single one decides the outcome."
                ),
                question=Question(
                    id="diversification",
                    prompt="Two people each invest £5,000. Which of them is taking more risk?",
                    kind="choice",
                    answer="one-company",
                    options=(
                        ("one-company", "The one who puts it all into a single company's shares"),
                        ("fund", "The one who puts it into a fund holding hundreds of companies"),
                        ("same", "Neither: the amount is the same, so the risk is the same"),
                    ),
                    hint="What happens to each of them if one company collapses?",
                    working=(
                        "With a single company, one failure can wipe out most of the money. Spread across hundreds, "
                        "one failure barely shows. Diversified investments still rise and fall with the market, "
                        "but they do not depend on one company's fate."
                    ),
                    common_mistakes=(
                        ("fund", "The fund spreads the money, so a single company failing has only a small effect."),
                        ("same", "Risk depends on what the money is in, not only on how much there is."),
                    ),
                ),
            ),
        ),
        closing=(
            f"**Lesson complete.** Deal with everyday risk first: an emergency fund ({pounds(target)} for Mia, "
            f"reached in {months_needed} months at {pounds(monthly_saving)} a month) kept where it is safe and reachable. "
            "For long-term money, spreading it widely means no single failure decides the result."
        ),
    )


def _profit_and_cash_lesson() -> Lesson:
    revenue = 8_000
    costs = 6_500
    profit = revenue - costs
    margin = Decimal(profit) / Decimal(revenue) * 100
    received = 4_500
    cash_fall = costs - received

    return Lesson(
        id="profit-is-not-cash",
        title="Profit is not cash",
        topic="Business finance",
        level="Beginner",
        summary="Revenue, costs, profit and margin, and why a profitable business can still run out of money.",
        steps=(
            Step(
                text=(
                    "**Part 1: profit**\n"
                    "Revenue is what a business bills its customers. Costs are what it spends to operate. "
                    "Profit is what is left when costs are taken from revenue."
                ),
                question=Question(
                    id="profit",
                    prompt=f"In March a design studio invoices {pounds(revenue)} and has costs of {pounds(costs)}. What is its profit for the month?",
                    kind="number",
                    answer=str(profit),
                    hint="Take the costs away from the revenue.",
                    working=f"{pounds(revenue)} minus {pounds(costs)} is {pounds(profit)}.",
                ),
            ),
            Step(
                text=(
                    "**Part 2: margin**\n"
                    "Profit in pounds does not show how efficient a business is. Profit margin does: it is profit as a "
                    "percentage of revenue, so businesses of different sizes can be compared."
                ),
                question=Question(
                    id="margin",
                    prompt="What is the studio's profit margin for March, as a percentage?",
                    kind="number",
                    unit="percent",
                    tolerance="0.3",
                    answer=str(margin),
                    hint=f"Divide the {pounds(profit)} profit by the {pounds(revenue)} revenue, then multiply by 100.",
                    working=f"{pounds(profit)} divided by {pounds(revenue)} is {margin / 100}, which is {margin.normalize()}%.",
                    common_mistakes=(
                        (
                            str((Decimal(profit) / Decimal(costs) * 100).quantize(Decimal("0.01"))),
                            "That divides profit by costs. Margin is profit divided by revenue.",
                        ),
                    ),
                ),
            ),
            Step(
                text=(
                    "**Part 3: cash**\n"
                    "An invoice is not money in the bank. Customers often pay 30 days or more after being billed, "
                    "while wages, rent and suppliers have to be paid on time."
                ),
                question=Question(
                    id="cash-fall",
                    prompt=(
                        f"By the end of March, customers have paid only {pounds(received)} of the {pounds(revenue)} invoiced, "
                        f"and the studio has paid all {pounds(costs)} of its costs. By how much did its bank balance fall in March?"
                    ),
                    kind="number",
                    answer=str(cash_fall),
                    hint=f"Compare the money that came in ({pounds(received)}) with the money that went out ({pounds(costs)}).",
                    working=(
                        f"{pounds(costs)} went out and {pounds(received)} came in, so the balance fell by {pounds(cash_fall)}, "
                        f"in a month with a {pounds(profit)} profit."
                    ),
                    common_mistakes=(
                        (str(profit), "That is the profit. The question is about money actually received and paid."),
                    ),
                ),
            ),
            Step(
                text=(
                    "**Part 4: why it matters**\n"
                    "Profit is measured when work is billed. Cash moves when money is actually paid."
                ),
                question=Question(
                    id="profitable-but-broke",
                    prompt="How can a profitable business run out of money?",
                    kind="choice",
                    answer="timing",
                    options=(
                        ("cannot", "It cannot: profit means there is money in the bank"),
                        ("timing", "Its bills fall due before its customers pay"),
                        ("tax", "Only if it forgets to pay tax"),
                        ("prices", "Only if its prices are too low"),
                    ),
                    hint="Look back at March: a profit on paper, and less money in the bank.",
                    working=(
                        "It is a timing problem. If customers pay later than the business has to pay its own bills, "
                        "the bank balance can hit zero while the accounts show a profit. This is why businesses "
                        "forecast cashflow as well as profit."
                    ),
                    common_mistakes=(
                        ("cannot", "March showed otherwise: a profit of " + pounds(profit) + " and a falling bank balance."),
                        ("tax", "Tax is one bill among many. The underlying cause is when cash comes in and goes out."),
                        ("prices", "Low prices hurt profit. A business with healthy profit can still be short of cash."),
                    ),
                ),
            ),
        ),
        closing=(
            f"**Lesson complete.** Profit and cash are different measures. The studio made {pounds(profit)} "
            f"({margin.normalize()}% margin) in March and still ended the month with {pounds(cash_fall)} less in the bank. "
            "A cashflow forecast, listing when money is expected in and out, is how a business sees that coming."
        ),
    )


_BUILDERS = (
    _budget_lesson,
    _income_tax_bands_lesson,
    _take_home_lesson,
    _compound_growth_lesson,
    _isa_lesson,
    _workplace_pension_lesson,
    _emergency_fund_lesson,
    _debt_cost_lesson,
    _profit_and_cash_lesson,
)

LESSONS: dict[str, Lesson] = {lesson.id: lesson for lesson in (build() for build in _BUILDERS)}
