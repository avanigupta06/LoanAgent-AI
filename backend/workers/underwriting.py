# backend/workers/underwriting.py

"""
Underwriting Agent

Responsible for:
- EMI calculation
- Credit risk evaluation
- Final loan approval / rejection decisions

Implements rule-based underwriting logic for the demo system.
"""

from decimal import Decimal, ROUND_HALF_UP, getcontext

# High precision for financial calculations
getcontext().prec = 28


def compute_emi(P, annual_rate, months):
    """
    Computes the monthly EMI using the standard amortization formula.

    Args:
        P: Principal loan amount
        annual_rate: Annual interest rate (percentage)
        months: Loan tenure in months

    Returns:
        Monthly EMI rounded to two decimal places
    """
    P = Decimal(P)
    r = Decimal(annual_rate) / Decimal(12) / Decimal(100)
    n = Decimal(months)

    # Zero-interest edge case
    if r == 0:
        return (P / n).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    one_plus_r_n = (Decimal(1) + r) ** n
    emi = (P * r * one_plus_r_n) / (one_plus_r_n - Decimal(1))

    return emi.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def evaluate_loan(
    customer: dict,
    requested_amount: int,
    tenure_months: int,
    credit_score: int,
    fileId=None,
    file_path=None
):
    """
    Evaluates loan eligibility using business underwriting rules.

    Decision rules:
    1. Reject if credit score < 700
    2. Auto-approve if amount ≤ pre-approved limit
    3. Require salary verification if amount ≤ 2× pre-approved limit
    4. Reject if amount > 2× pre-approved limit
    """
    pre_approved = Decimal(customer.get("pre_approved_limit", 0))
    req_amount = Decimal(requested_amount)

    # Interest rates
    rate_within_limit = Decimal("13.5")
    rate_above_limit = Decimal("14.5")

    # --------------------------------------------------
    # 1️⃣ Credit Score Check
    # --------------------------------------------------
    if credit_score < 700:
        return {
            "status": "REJECT",
            "reason": f"Rejected: credit score {credit_score} below threshold 700."
        }

    # --------------------------------------------------
    # 2️⃣ Within Pre-approved Limit
    # --------------------------------------------------
    if req_amount <= pre_approved:
        emi = compute_emi(req_amount, rate_within_limit, tenure_months)
        return {
            "status": "APPROVE",
            "approved_amount": int(req_amount),
            "emi": emi,
            "rate": float(rate_within_limit)
        }

    # --------------------------------------------------
    # 3️⃣ Up to 2× Pre-approved Limit (Salary Verification)
    # --------------------------------------------------
    if req_amount <= pre_approved * 2:
        monthly_salary = None

        # Simulated salary extraction (demo only)
        if file_path:
            monthly_salary = customer.get(
                "salary_info", {}
            ).get("salary", 65000)

        if not monthly_salary:
            return {
                "status": "REQ_DOC",
                "reason": "Please upload salary slip for verification."
            }

        emi = compute_emi(req_amount, rate_above_limit, tenure_months)
        salary_limit = Decimal(monthly_salary) * Decimal("0.5")

        # Human-readable formatting for rejection messages
        emi_str = f"{emi:,.2f}"
        salary_limit_str = f"{salary_limit:,.2f}"

        if emi <= salary_limit:
            return {
                "status": "APPROVE",
                "approved_amount": int(req_amount),
                "emi": emi,
                "rate": float(rate_above_limit)
            }
        else:
            return {
                "status": "REJECT",
                "reason": (
                    f"Rejected: EMI {emi_str} exceeds "
                    f"50% of salary ({salary_limit_str})."
                )
            }

    # --------------------------------------------------
    # 4️⃣ Above 2× Pre-approved Limit
    # --------------------------------------------------
    return {
        "status": "REJECT",
        "reason": (
            f"Rejected: requested amount {req_amount} exceeds "
            f"2× pre-approved limit ({pre_approved * 2})."
        )
    }
