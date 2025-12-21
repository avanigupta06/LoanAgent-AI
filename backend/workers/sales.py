# backend/workers/sales.py

"""
Sales Agent

Responsible for generating loan offers based on
customer eligibility and pre-approved limits.
"""

def get_offers_for_customer(customer: dict) -> list[str]:
    """
    Returns a list of human-readable loan offers for a customer.

    Offer logic:
    - Offer A: Within pre-approved limit (lower interest, instant approval)
    - Offer B: Extended limit (higher interest, requires salary verification)
    """
    pre_approved_limit = customer.get("pre_approved_limit", 0)

    return [
        (
            f"Offer A — up to ₹{pre_approved_limit:,} "
            f"at 13.5% p.a. (instant approval within pre-approved limit)."
        ),
        (
            f"Offer B — up to ₹{pre_approved_limit * 2:,} "
            f"at 14.5% p.a. "
            f"(salary verification required if exceeding pre-approved limit)."
        )
    ]
