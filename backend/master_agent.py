from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
import uuid, os, json, re
from decimal import Decimal, getcontext, ROUND_HALF_UP
from datetime import datetime
from workers import sales, verification, underwriting, sanction as sanction_worker
from mock_services import crm as crm_service

getcontext().prec = 28

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
UPLOAD_DIR = ROOT / "uploads"
SANCTION_DIR = ROOT / "sanctions"
UPLOAD_DIR.mkdir(exist_ok=True)
SANCTION_DIR.mkdir(exist_ok=True)

# load customers (for quick access)
CUSTOMERS_FILE = DATA_DIR / "customers.json"
with open(CUSTOMERS_FILE, "r", encoding="utf-8") as f:
    CUSTOMERS = {c["id"]: c for c in json.load(f)}

router = APIRouter()

class ChatRequest(BaseModel):
    sessionId: str
    customerId: str
    message: str = ""
    fileId: str | None = None  # keep if Python 3.10+; otherwise use Optional[str]

# Upload endpoint — stores the file and returns an id that can be passed in chat
# Also populate UPLOAD_MAP so later /chat can find the file path.
@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    uid = uuid.uuid4().hex
    filename = f"{uid}_{file.filename}"
    path = UPLOAD_DIR / filename
    content = await file.read()
    with open(path, "wb") as fh:
        fh.write(content)
    UPLOAD_MAP[uid] = str(path)
    return {"fileId": uid, "filename": file.filename, "path": str(path)}

# Map uploaded fileId -> path (simple in-memory map)
UPLOAD_MAP = {}  # fileId -> path

# Sanction file serve
@router.get("/sanction/{filename}")
def get_sanction(filename: str):
    p = SANCTION_DIR / filename
    if not p.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(p, media_type="application/pdf", filename=filename)

# Chat endpoint — the Master Agent entrypoint
@router.post("/chat")
def master_chat(req: ChatRequest):
    cid = req.customerId
    if cid not in CUSTOMERS:
        return {"replies": [{"role": "system", "text": f"Customer ID '{cid}' not found. Please check and try again."}]}

    customer = CUSTOMERS[cid]
    text = (req.message or "").strip()

    # 1) empty message -> initial greeting & offers via Sales Agent
    if not text:
        offers_resp = sales.get_offers_for_customer(customer)
        replies = [{"role":"master", "text": f"Hi {customer['name']} — welcome! Based on our records you are pre-approved up to ₹{customer['pre_approved_limit']:,}."}]
        replies += [{"role":"sales", "text": s} for s in offers_resp]
        replies.append({"role":"master", "text":"Tell me what loan amount you need and preferred tenure (e.g., '₹150000 for 24 months')."})
        return {"replies": replies}

    # 2) KYC verification triggers
    if re.search(r"\bverify\b|\bkyc\b|\bphone\b|\baddress\b", text, re.IGNORECASE):
        v = verification.verify_kyc(customer)
        if v["verified"]:
            return {"replies":[{"role":"verification","text":"KYC verified: phone & address matched."}]}
        else:
            return {"replies":[{"role":"verification","text":"KYC mismatch: please update your details."}]}

    # 3) if user mentions upload or salary slip, prompt file upload
    if re.search(r"salary slip|salary|upload", text, re.IGNORECASE):
        return {"replies":[{"role":"master","text":"Please use the file upload control to attach your salary slip. After upload, send 'Attached'."}]}

    # 4) parse loan request (amount + tenure)
    amount, tenure_months = parse_amount_and_tenure(text)
    if amount and tenure_months:
        # orchestrate underwriting
        # call mock credit bureau (crm_service.get_credit_score returns dict)
        credit = crm_service.get_credit_score(cid)
        score = credit.get("credit_score", 0)

        # find uploaded file path if fileId provided
        file_path = UPLOAD_MAP.get(req.fileId) if req.fileId else None

        # use underwriting worker to decide
        decision = underwriting.evaluate_loan(customer, amount, tenure_months, score, req.fileId, file_path)
        # decision contains: status, reasons, emi (Decimal), rate, sanction_file (optional)
        replies = []
        if decision["status"] == "REJECT":
            replies.append({"role":"underwriting", "text": decision["reason"]})
            return {"replies": replies}
        elif decision["status"] == "REQ_DOC":
            replies.append({"role":"underwriting","text": decision["reason"]})
            return {"replies": replies}
        elif decision["status"] == "APPROVE":
            # generate sanction letter
            sanction_path = sanction_worker.generate_sanction(customer, decision["approved_amount"], tenure_months, decision["rate"], decision["emi"], SANCTION_DIR)
            filename = sanction_path.name
            replies.append({"role":"underwriting", "text": f"✅ Approved for {format_inr(decision['approved_amount'])} at {decision['rate']}% p.a. Tenure: {tenure_months} months. EMI: {format_inr(decision['emi'])}."})
            # include meta.link because frontend checks msg.meta.link
            replies.append({"role":"sanction", "text": "Sanction letter generated.", "meta": {"link": f"/api/sanction/{filename}"}})
            return {"replies": replies, "sanctionUrl": f"/api/sanction/{filename}"}

    # 5) fallback
    return {"replies":[{"role":"master","text":f"Hi {customer['name']}, how can I help? You can ask for offers or send an amount + tenure (e.g., '₹150000 for 24 months')."}]}

# small helper parse
def parse_amount_and_tenure(text: str):
    # find numeric amount (handles commas and optional ₹)
    m = re.search(r"(?:₹\s?)?([\d,]{3,})", text)
    # look for months or years keyword near a number
    t = re.search(r"(\b\d{1,2})\s*(months|month|yrs|years|yr|y)\b", text, re.IGNORECASE)
    amount = int(m.group(1).replace(",", "")) if m else None
    tenure = None
    if t:
        tens = int(t.group(1))
        if re.search(r"(year|yr|y)", t.group(2), re.IGNORECASE) or re.search(r"(year|yr|y)", text, re.IGNORECASE):
            tenure = tens * 12
        else:
            tenure = tens
    return amount, tenure

def format_inr(x):
    if isinstance(x, Decimal):
        x = int(x.quantize(Decimal("1")))
    return f"₹{x:,}"
