# backend/workers/verification.py

"""
Verification Agent

Responsible for performing basic KYC verification.
In this demo implementation, verification is rule-based
and does not integrate with real KYC providers.
"""

def verify_kyc(customer: dict) -> dict:
    """
    Verifies customer KYC details.

    Demo logic:
    - If a phone number exists, KYC is treated as verified
    - Address is returned for completeness (if available)

    Args:
        customer: Customer profile dictionary

    Returns:
        Dictionary containing verification status and details
    """
    phone = customer.get("phone")
    address = customer.get("address", "Address not available in demo")

    return {
        "verified": bool(phone),
        "details": {
            "phone": phone,
            "address": address
        }
    }
