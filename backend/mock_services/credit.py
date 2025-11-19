# backend/mock_services/credit.py
from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

router = APIRouter()
ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "customers.json"

with open(DATA_FILE, "r", encoding="utf-8") as f:
    CUSTOMERS = {c["id"]: c for c in json.load(f)}

@router.get("/{cid}")
def get_credit(cid: str):
    c = CUSTOMERS.get(cid)
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"customer_id": cid, "credit_score": c.get("credit_score", 0)}
