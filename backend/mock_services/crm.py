# backend/mock_services/crm.py
from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

router = APIRouter()
ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "customers.json"

with open(DATA_FILE, "r", encoding="utf-8") as f:
    CUSTOMERS = {c["id"]: c for c in json.load(f)}

@router.get("/{cid}")
def get_customer(cid: str):
    c = CUSTOMERS.get(cid)
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    return c

def get_credit_score(cid: str):
    c = CUSTOMERS.get(cid)
    if not c:
        return {"credit_score": 0}
    # return the credit score property if present
    return {"credit_score": c.get("credit_score", 0)}
