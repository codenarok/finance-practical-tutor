"""Calculators: checked against gov.uk's worked examples and hand-worked cases."""
from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient

from app.services import calculators, uk_figures as uk


def test_income_tax_matches_the_gov_uk_example() -> None:
    # gov.uk/income-tax-rates: £35,000 of income, standard allowance, 20% on £22,430.
    assert calculators.income_tax(D("35000")) == D("4486.00")


def test_weekly_national_insurance_matches_the_gov_uk_example() -> None:
    # gov.uk/national-insurance-rates-letters: category A, £1,000 in a week, £58.66.
    ni = calculators.employee_ni(D("1000"), uk.NI_PRIMARY_THRESHOLD_WEEKLY, uk.NI_UPPER_LIMIT_WEEKLY)
    assert ni == D("58.66")


@pytest.mark.parametrize(
    ("salary", "expected_tax"),
    [
        ("0", "0.00"),
        ("12570", "0.00"),
        ("12571", "0.20"),
        ("50270", "7540.00"),
        ("60000", "11432.00"),
        ("150000", "53703.00"),
    ],
)
def test_income_tax_across_the_bands(salary: str, expected_tax: str) -> None:
    assert calculators.income_tax(D(salary)) == D(expected_tax)


@pytest.mark.parametrize(
    ("salary", "expected_allowance"),
    [("100000", "12570"), ("100001", "12570"), ("110000", "7570"), ("125140", "0"), ("200000", "0")],
)
def test_personal_allowance_tapers_above_100k(salary: str, expected_allowance: str) -> None:
    assert calculators.personal_allowance(D(salary)) == D(expected_allowance)


def test_take_home_pay_for_60k() -> None:
    result = calculators.take_home_pay(D("60000"))
    assert result.income_tax == D("11432.00")
    assert result.national_insurance == D("3210.00")  # monthly: 8% of £3,141 + 2% of £811 = £267.50
    assert result.net_annual == D("45358.00")
    assert result.net_monthly == D("3779.83")
    assert "£45,358.00 a year" in result.summary
    assert "2026 to 2027 tax year" in result.summary


def test_savings_growth_compounds_monthly() -> None:
    result = calculators.savings_growth(D("1000"), D("0"), D("12"), 1)
    assert result.final_value == D("1126.83")  # 1000 x 1.01^12
    assert result.growth == D("126.83")


def test_savings_growth_at_zero_percent_is_just_what_was_paid_in() -> None:
    result = calculators.savings_growth(D("0"), D("100"), D("0"), 10)
    assert result.final_value == result.total_paid_in == D("12000.00")
    assert result.growth == D("0.00")


def test_debt_payoff_hand_worked_case() -> None:
    # Month 1: £1.00 interest, £60 paid, £41.00 left. Month 2: £0.41 interest, cleared.
    result = calculators.debt_payoff(D("100"), D("12"), D("60"))
    assert (result.months, result.total_interest, result.total_paid) == (2, D("1.41"), D("101.41"))


def test_debt_payoff_without_interest() -> None:
    result = calculators.debt_payoff(D("1000"), D("0"), D("100"))
    assert (result.months, result.total_interest) == (10, D("0.00"))


def test_debt_that_never_clears_is_an_error_not_a_loop() -> None:
    with pytest.raises(calculators.CalculationError, match="never be cleared"):
        calculators.debt_payoff(D("1000"), D("12"), D("10"))


def test_calculators_need_a_token(client: TestClient) -> None:
    assert client.post("/api/calculate/take-home", json={"salary": "30000"}).status_code == 401


def test_calculation_result_is_signed_and_trusted_as_history(client: TestClient, auth_headers, fake_ollama) -> None:
    res = client.post("/api/calculate/take-home", json={"salary": "60000"}, headers=auth_headers)
    assert res.status_code == 200
    result = res.json()
    assert "£11,432.00" in result["summary"]

    history = [{"role": "assistant", "content": result["summary"], "sig": result["sig"]}]
    client.post("/api/chat", json={"message": "Why is my tax that much?", "history": history}, headers=auth_headers)
    sent = fake_ollama.requests[0]["messages"]
    assert sent[1] == {"role": "assistant", "content": result["summary"]}


def test_savings_and_debt_endpoints(client: TestClient, auth_headers) -> None:
    savings = client.post(
        "/api/calculate/savings-growth",
        json={"initial": "1000", "monthly": "0", "annual_rate_percent": "12", "years": 1},
        headers=auth_headers,
    )
    assert "£1,126.83" in savings.json()["summary"]
    debt = client.post(
        "/api/calculate/debt-payoff",
        json={"balance": "100", "apr_percent": "12", "monthly_payment": "60"},
        headers=auth_headers,
    )
    assert "2 months" in debt.json()["summary"]


def test_debt_endpoint_explains_a_payment_that_is_too_small(client: TestClient, auth_headers) -> None:
    res = client.post(
        "/api/calculate/debt-payoff",
        json={"balance": "1000", "apr_percent": "12", "monthly_payment": "10"},
        headers=auth_headers,
    )
    assert res.status_code == 400
    assert "never be cleared" in res.json()["detail"]


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("take-home", {"salary": "-1"}),
        ("take-home", {"salary": "99999999999"}),
        ("take-home", {"salary": "lots"}),
        ("savings-growth", {"initial": "0", "monthly": "100", "annual_rate_percent": "5", "years": 500}),
        ("savings-growth", {"initial": "0", "monthly": "100", "annual_rate_percent": "900", "years": 5}),
        ("debt-payoff", {"balance": "0", "apr_percent": "20", "monthly_payment": "50"}),
    ],
)
def test_out_of_range_inputs_are_rejected(client: TestClient, auth_headers, path: str, payload: dict) -> None:
    assert client.post(f"/api/calculate/{path}", json=payload, headers=auth_headers).status_code == 422
