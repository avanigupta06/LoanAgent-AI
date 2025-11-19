# backend/workers/sales.py
def get_offers_for_customer(customer):
    # For demo: return two text lines describing offers
    p = customer.get("pre_approved_limit", 0)
    return [
        f"Offer A — up to ₹{p:,} at 13.5% p.a. (instant approval if within limit).",
        f"Offer B — up to ₹{p*2:,} at 14.5% p.a. (requires salary verification if > pre-approved limit)."
    ]
