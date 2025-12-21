# backend/mock_services/offers.py

"""
Mock Offers Service

Provides available loan products and offers for a customer
based on pre-approved eligibility.
"""

from fastapi import APIRouter
from pathlib import Path
import json

router = APIRouter()

# --------------------------------------------------
# Load customer eligibility data
# --------------------------------------------------
ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "customers.json"

with open(DATA_FILE, "r", encoding="utf-8") as f:
    CUSTOMERS = {c["id"]: c for c in json.load(f)}

# --------------------------------------------------
# API Endpoint
# --------------------------------------------------
@router.get("/{cid}")
def get_offers(cid: str):
    """
    Returns a list of loan offers available to the customer.

    Each offer includes:
    - product_id
    - maximum eligible loan amount
    - interest rate
    """
    customer = CUSTOMERS.get(cid)
    if not customer:
        return {"offers": []}

    pre_approved_limit = customer.get("pre_approved_limit", 0)

    return {
        "offers": [
            {
                "product_id": "P-PL-01",
                "max_limit": pre_approved_limit,
                "rate": 13.5
            },
            {
                "product_id": "P-PL-02",
                "max_limit": pre_approved_limit * 2,
                "rate": 14.5
            }
        ]
    }
