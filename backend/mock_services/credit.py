# backend/mock_services/credit.py

"""
Mock Credit Bureau Service

Provides credit score information for customers.
Used both as:
1. An HTTP API (for testing / inspection)
2. A service-style function (for internal agent calls)
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

router = APIRouter()

# --------------------------------------------------
# Load customer credit data
# --------------------------------------------------
ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "customers.json"

with open(DATA_FILE, "r", encoding="utf-8") as f:
    CUSTOMERS = {c["id"]: c for c in json.load(f)}

# --------------------------------------------------
# API Endpoint
# --------------------------------------------------
@router.get("/{cid}")
def get_credit(cid: str):
    """
    Returns credit score for a given customer ID.
    """
    customer = CUSTOMERS.get(cid)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return {
        "customer_id": cid,
        "credit_score": customer.get("credit_score", 0)
    }


# --------------------------------------------------
# Internal Service Function (used by Master Agent)
# --------------------------------------------------
def get_credit_score(cid: str) -> dict:
    """
    Service-style helper for internal calls without HTTP overhead.
    """
    customer = CUSTOMERS.get(cid)
    if not customer:
        return {"credit_score": 0}

    return {"credit_score": customer.get("credit_score", 0)}
