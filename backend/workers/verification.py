# backend/workers/verification.py
def verify_kyc(customer):
    # Dummy verify: check phone present and treat as verified
    phone = customer.get("phone")
    address = customer.get("address", "Address not present in demo")
    # For demo we mark verified if phone exists
    return {"verified": bool(phone), "details": {"phone": phone, "address": address}}
