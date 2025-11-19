# backend/mock_services/offers.py
from fastapi import APIRouter
from pathlib import Path
import json

router = APIRouter()
ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "customers.json"

with open(DATA_FILE, "r", encoding="utf-8") as f:
    CUSTOMERS = {c["id"]: c for c in json.load(f)}

@router.get("/{cid}")
def get_offers(cid: str):
    c = CUSTOMERS.get(cid)
    if not c:
        return {"offers": []}
    pre = c.get("pre_approved_limit", 0)
    return {"offers": [
        {"product_id":"P-PL-01","max_limit":pre,"rate":13.5},
        {"product_id":"P-PL-02","max_limit":pre*2,"rate":14.5}
    ]}
