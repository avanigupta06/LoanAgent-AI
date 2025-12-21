# backend/master_agent.py

"""
Master Agent for Loan Processing System

This service acts as an orchestrator between multiple worker agents:
- Sales Agent (offers & greeting)
- Verification Agent (KYC)
- Underwriting Agent (loan decision)
- Sanction Agent (PDF generation)

It maintains session-level state to enable a true agentic, multi-step workflow.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
import uuid, json, re
from decimal import Decimal, getcontext

# Worker agents
from workers import sales, verification, underwriting, sanction as sanction_worker

# External mock services
# CRM → customer/KYC data
# Credit Bureau → credit score
from mock_services import crm as crm_service
from mock_services import credit as credit_service

# High precision for financial calculations
getcontext().prec = 28

# -------------------- Directory Setup --------------------
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
UPLOAD_DIR = ROOT / "uploads"
SANCTION_DIR = ROOT / "sanctions"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SANCTION_DIR.mkdir(parents=True, exist_ok=True)

# -------------------- Load Customer Master Data --------------------
CUSTOMERS_FILE = DATA_DIR / "customers.json"
with open(CUSTOMERS_FILE, "r", encoding="utf-8") as f:
    CUSTOMERS = {c["id"]: c for c in json.load(f)}

router = APIRouter()

# -------------------- In-memory Storage --------------------
# fileId → uploaded file path (demo-only, non-persistent)
UPLOAD_MAP = {}

# sessionId → conversational state
# Enables multi-turn, agentic behavior
SESSIONS = {}

# -------------------- Request Schema --------------------
class ChatRequest(BaseModel):
    sessionId: str
    customerId: str
    message: str = ""
    fileId: str | None = None


# =========================================================
# 📤 File Upload API
# =========================================================
@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Stores uploaded documents (e.g., salary slips)
    and returns a short-lived fileId.
    """
    uid = uuid.uuid4().hex
    filename = f"{uid}_{file.filename}"
    path = UPLOAD_DIR / filename

    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)

    UPLOAD_MAP[uid] = str(path)

    return {
        "fileId": uid,
        "filename": file.filename
    }


# =========================================================
# 📄 Sanction Letter Download
# =========================================================
@router.get("/sanction/{filename}")
def get_sanction(filename: str):
    """
    Serves generated sanction letter PDFs.
    """
    p = SANCTION_DIR / filename
    if not p.exists():
        raise HTTPException(status_code=404, detail="Sanction letter not found")

    return FileResponse(p, media_type="application/pdf", filename=filename)


# =========================================================
# 🧠 MASTER AGENT — MAIN ENTRY POINT
# =========================================================
@router.post("/chat")
def master_chat(req: ChatRequest):
    cid = req.customerId

    # -------- Validate Customer --------
    if cid not in CUSTOMERS:
        return {
            "replies": [
                {
                    "role": "system",
                    "text": f"Customer ID '{cid}' not found. Please check and try again."
                }
            ]
        }

    customer = CUSTOMERS[cid]
    text = (req.message or "").strip()

    # -------- Initialize / Restore Session --------
    session = SESSIONS.setdefault(req.sessionId, {
        "customerId": cid,
        "stage": "INIT"
    })

    # =====================================================
    # 1️⃣ Initial Greeting → Sales Agent
    # =====================================================
    if not text:
        session["stage"] = "SALES"

        offers = sales.get_offers_for_customer(customer)

        replies = [
            {
                "role": "master",
                "text": (
                    f"Hi {customer['name']} 👋 "
                    f"You’re pre-approved for a personal loan up to "
                    f"₹{customer['pre_approved_limit']:,}."
                )
            }
        ]

        replies += [{"role": "sales", "text": o} for o in offers]

        replies.append({
            "role": "master",
            "text": (
                "Tell me the loan amount and tenure you prefer "
                "(e.g., ₹150000 for 24 months)."
            )
        })

        return {"replies": replies}

    # =====================================================
    # 2️⃣ KYC Verification → Verification Agent
    # =====================================================
    if re.search(r"\bkyc\b|\bverify\b|\bphone\b|\baddress\b", text, re.IGNORECASE):
        kyc = verification.verify_kyc(customer)

        if kyc["verified"]:
            session["stage"] = "KYC_DONE"
            return {
                "replies": [
                    {"role": "verification", "text": "✅ KYC verified successfully."}
                ]
            }
        else:
            return {
                "replies": [
                    {"role": "verification", "text": "❌ KYC mismatch detected."}
                ]
            }

    # =====================================================
    # 3️⃣ Document Collection (Salary Slip)
    # =====================================================
    if re.search(r"salary|salary slip|upload", text, re.IGNORECASE):
        session["stage"] = "DOC_PENDING"
        return {
            "replies": [
                {
                    "role": "master",
                    "text": (
                        "Please upload your salary slip using the upload button, "
                        "then type 'Attached'."
                    )
                }
            ]
        }

    # =====================================================
    # 4️⃣ Loan Parsing + Underwriting Decision
    # =====================================================
    amount, tenure_months = parse_amount_and_tenure(text)

    if amount and tenure_months:
        session["stage"] = "UNDERWRITING"

        # Credit score fetched from Credit Bureau
        credit = credit_service.get_credit_score(cid)
        credit_score = credit.get("credit_score", 0)

        # Optional uploaded document
        file_path = UPLOAD_MAP.get(req.fileId) if req.fileId else None

        decision = underwriting.evaluate_loan(
            customer=customer,
            requested_amount=amount,
            tenure_months=tenure_months,
            credit_score=credit_score,
            fileId=req.fileId,
            file_path=file_path
        )

        # -------- Decision Outcomes --------
        if decision["status"] == "REJECT":
            session["stage"] = "REJECTED"
            return {
                "replies": [
                    {"role": "underwriting", "text": decision["reason"]}
                ]
            }

        if decision["status"] == "REQ_DOC":
            session["stage"] = "DOC_PENDING"
            return {
                "replies": [
                    {"role": "underwriting", "text": decision["reason"]}
                ]
            }

        if decision["status"] == "APPROVE":
            session["stage"] = "APPROVED"

            sanction_path = sanction_worker.generate_sanction(
                customer=customer,
                amount=decision["approved_amount"],
                tenure_months=tenure_months,
                rate=decision["rate"],
                emi=decision["emi"],
                out_dir=SANCTION_DIR
            )

            filename = sanction_path.name

            return {
                "replies": [
                    {
                        "role": "underwriting",
                        "text": (
                            f"✅ Loan approved for "
                            f"{format_inr(decision['approved_amount'])} "
                            f"at {decision['rate']}% p.a.\n"
                            f"Tenure: {tenure_months} months\n"
                            f"EMI: {format_inr(decision['emi'])}"
                        )
                    },
                    {
                        "role": "sanction",
                        "text": "📄 Sanction letter generated successfully.",
                        "meta": {"link": f"/api/sanction/{filename}"}
                    }
                ],
                "sanctionUrl": f"/api/sanction/{filename}"
            }

    # =====================================================
    # 5️⃣ Fallback / Guidance
    # =====================================================
    return {
        "replies": [
            {
                "role": "master",
                "text": (
                    f"Hi {customer['name']}, I can help you get an instant "
                    f"personal loan. Please tell me the amount and tenure."
                )
            }
        ]
    }


# =========================================================
# 🔧 Helper Functions
# =========================================================
def parse_amount_and_tenure(text: str):
    """
    Extracts loan amount and tenure (months) from free-text input.

    Examples:
    - ₹150000 for 24 months
    - 2 years loan of 3,00,000
    """
    amount_match = re.search(
        r"(?:₹\s*)?(\d{1,3}(?:,\d{3})+|\d+)", text
    )
    tenure_match = re.search(
        r"(\d{1,2})\s*(months?|yrs?|years?)",
        text,
        re.IGNORECASE
    )

    amount = (
        int(amount_match.group(1).replace(",", ""))
        if amount_match else None
    )

    tenure = None
    if tenure_match:
        t = int(tenure_match.group(1))
        tenure = t * 12 if "year" in tenure_match.group(2).lower() else t

    return amount, tenure


def format_inr(x):
    """
    Formats numeric values into Indian Rupee format.
    """
    try:
        val = x if isinstance(x, Decimal) else Decimal(str(x))
        return f"₹{val.quantize(Decimal('0.01')):,.2f}"
    except Exception:
        try:
            return f"₹{int(x):,}"
        except Exception:
            return f"₹{x}"
