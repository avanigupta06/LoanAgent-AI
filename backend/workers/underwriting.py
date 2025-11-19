# backend/workers/underwriting.py
from decimal import Decimal, ROUND_HALF_UP, getcontext
getcontext().prec = 28

def compute_emi(P, annual_rate, months):
    P = Decimal(P)
    r = Decimal(annual_rate) / Decimal(12) / Decimal(100)
    n = Decimal(months)
    if r == 0:
        return (P / n).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    one_plus_r_n = (Decimal(1) + r) ** n
    emi = (P * r * one_plus_r_n) / (one_plus_r_n - Decimal(1))
    return emi.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def evaluate_loan(customer, requested_amount, tenure_months, credit_score, fileId=None, file_path=None):
    pre = Decimal(customer.get("pre_approved_limit", 0))
    req_amt = Decimal(requested_amount)
    # rates
    rate_in = Decimal("13.5")
    rate_above = Decimal("14.5")

    # 1. credit score check
    if credit_score < 700:
        return {"status":"REJECT", "reason": f"Rejected: credit score {credit_score} below threshold 700."}

    # 2. within pre-approved
    if req_amt <= pre:
        emi = compute_emi(req_amt, rate_in, tenure_months)
        return {"status":"APPROVE", "approved_amount": int(req_amt), "emi": emi, "rate": float(rate_in)}

    # 3. <= 2x pre-approved -> require salary slip
    if req_amt <= pre * 2:
        # if file provided (file_path), simulate parsing salary
        monthly_salary = None
        if file_path:
            # demo: don't parse PDF, simulate salary extraction from customer's data if exists, else assume 65000
            monthly_salary = customer.get("salary_info", {}).get("salary", 65000)
        if not monthly_salary:
            return {"status":"REQ_DOC", "reason": "Please upload salary slip for verification."}
        emi = compute_emi(req_amt, rate_above, tenure_months)
        if emi <= Decimal(monthly_salary) * Decimal("0.5"):
            return {"status":"APPROVE", "approved_amount": int(req_amt), "emi": emi, "rate": float(rate_above)}
        else:
            return {"status":"REJECT", "reason": f"Rejected: EMI {emi} exceeds 50% of salary ({Decimal(monthly_salary)*Decimal('0.5')})."}
    # 4. > 2x pre-approved
    return {"status":"REJECT", "reason": f"Rejected: requested amount {req_amt} > 2× pre-approved limit ({pre*2})."}
