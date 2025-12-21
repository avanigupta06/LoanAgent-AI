# backend/mock_services/crm.py

"""
Mock CRM Service

Responsible for providing customer profile and KYC-related data.
This service intentionally does NOT own credit score logic,
which belongs to the Credit Bureau service.
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

router = APIRouter()

# --------------------------------------------------
# Load customer master data
# --------------------------------------------------
ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "customers.json"

with open(DATA_FILE, "r", encoding="utf-8") as f:
    CUSTOMERS = {c["id"]: c for c in json.load(f)}

# --------------------------------------------------
# API Endpoint
# --------------------------------------------------
@router.get("/{cid}")
def get_customer(cid: str):
    """
    Returns full customer profile for a given customer ID.
    """
    customer = CUSTOMERS.get(cid)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return customer
