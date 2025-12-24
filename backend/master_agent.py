from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
import uuid, json, re
from decimal import Decimal, getcontext

from workers import sales, underwriting, sanction as sanction_worker
from mock_services import credit as credit_service

getcontext().prec = 28

# -------------------- Paths --------------------
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
UPLOAD_DIR = ROOT / "uploads"
SANCTION_DIR = ROOT / "sanctions"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SANCTION_DIR.mkdir(parents=True, exist_ok=True)

with open(DATA_DIR / "customers.json", "r", encoding="utf-8") as f:
    CUSTOMERS = {c["id"]: c for c in json.load(f)}

router = APIRouter()
UPLOAD_MAP = {}
SESSIONS = {}


class ChatRequest(BaseModel):
    sessionId: str
    customerId: str
    message: str = ""
    fileId: str | None = None


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    uid = uuid.uuid4().hex
    path = UPLOAD_DIR / f"{uid}_{file.filename}"
    with open(path, "wb") as f:
        f.write(await file.read())
    UPLOAD_MAP[uid] = str(path)
    return {"fileId": uid, "filename": file.filename}


@router.get("/sanction/{filename}")
def get_sanction(filename: str):
    path = SANCTION_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Sanction letter not found")
    return FileResponse(path, media_type="application/pdf", filename=filename)


# =========================================================
# 🧠 MASTER AGENT
# =========================================================
@router.post("/chat")
def master_chat(req: ChatRequest):
    cid = req.customerId

    if cid not in CUSTOMERS:
        return {"replies": [{"role": "system", "text": "Invalid Customer ID."}]}

    customer = CUSTOMERS[cid]
    text = (req.message or "").strip()

    session = SESSIONS.setdefault(req.sessionId, {
        "customerId": cid,
        "stage": "INIT"
    })

    # ---------------- TC-03: User not interested ----------------
    if re.search(r"\b(no|not interested|don’t want|dont want)\b", text, re.IGNORECASE):
        session["stage"] = "CLOSED"
        return {
            "replies": [
                {
                    "role": "master",
                    "text": (
                        "No problem 👍 Thanks for your time. "
                        "If you ever need a personal loan in the future, "
                        "I’ll be happy to help. Have a great day!"
                    )
                }
            ]
        }

    # ---------------- TC-04: Generic query ----------------
    if re.search(r"\b(what loans|what do you offer|loan options)\b", text, re.IGNORECASE):
        return {
            "replies": [
                {
                    "role": "sales",
                    "text": (
                        "We offer instant personal loans with minimal documentation, "
                        "competitive interest rates, and flexible tenures. "
                        "Tell me the amount and tenure you’re considering, and I’ll help you further."
                    )
                }
            ]
        }

    # =====================================================
    # 🔐 PHONE-BASED KYC
    # =====================================================
    if session["stage"] == "INIT":
        session["stage"] = "KYC_PENDING"
        return {
            "replies": [
                {
                    "role": "master",
                    "text": (
                        f"Hi {customer['name']} 👋\n\n"
                        "For security reasons, please confirm your "
                        "**registered phone number** to continue."
                    )
                }
            ]
        }

    if session["stage"] == "KYC_PENDING":
        user_phone = re.sub(r"\D", "", text)
        actual_phone = re.sub(r"\D", "", customer.get("phone", ""))

        if user_phone == actual_phone and user_phone:
            session["stage"] = "KYC_VERIFIED"
            return {
                "replies": [
                    {
                        "role": "verification",
                        "text": "✅ Phone number verified successfully."
                    }
                ]
            }
        return {
            "replies": [
                {
                    "role": "master",
                    "text": "❌ Phone number does not match our records. Please try again."
                }
            ]
        }

    # ---------------- Block flow until KYC ----------------
    if session["stage"] not in ["KYC_VERIFIED", "UNDERWRITING", "CONSENT_PENDING"]:
        return {
            "replies": [
                {
                    "role": "master",
                    "text": "Please complete phone verification before proceeding."
                }
            ]
        }

    # =====================================================
    # ✋ CONSENT HANDLING
    # =====================================================
    if session["stage"] == "CONSENT_PENDING":
        if text.lower() in ["yes", "y", "confirm", "proceed"]:
            data = session.pop("pending_approval")

            sanction_path = sanction_worker.generate_sanction(
                customer=customer,
                amount=data["amount"],
                tenure_months=data["tenure"],
                rate=data["rate"],
                emi=data["emi"],
                out_dir=SANCTION_DIR
            )

            session["stage"] = "APPROVED"

            return {
                "replies": [
                    {
                        "role": "sanction",
                        "text": "📄 Sanction letter generated successfully.",
                        "meta": {"link": f"/api/sanction/{sanction_path.name}"}
                    }
                ],
                "sanctionUrl": f"/api/sanction/{sanction_path.name}"
            }

        session["stage"] = "CLOSED"
        return {
            "replies": [
                {
                    "role": "master",
                    "text": "Alright 👍 I won’t proceed further. Feel free to reach out anytime."
                }
            ]
        }

    # =====================================================
    # 🧠 INTENT + UNDERWRITING
    # =====================================================
    amount, tenure_months = parse_amount_and_tenure(text)

    # ---------------- TC-08: Invalid amount ----------------
    if amount is not None and amount <= 0:
        return {
            "replies": [
                {
                    "role": "master",
                    "text": "Please enter a valid loan amount greater than zero."
                }
            ]
        }

    if amount and tenure_months:
        session["stage"] = "UNDERWRITING"

        credit_score = credit_service.get_credit_score(cid).get("credit_score", 0)
        file_path = UPLOAD_MAP.get(req.fileId) if req.fileId else None

        decision = underwriting.evaluate_loan(
            customer=customer,
            requested_amount=amount,
            tenure_months=tenure_months,
            credit_score=credit_score,
            fileId=req.fileId,
            file_path=file_path
        )

        if decision["status"] == "REJECT":
            session["stage"] = "CLOSED"
            return {"replies": [{"role": "underwriting", "text": decision["reason"]}]}

        if decision["status"] == "REQ_DOC":
            return {
                "replies": [
                    {
                        "role": "master",
                        "text": "Please upload your salary slip to continue the process."
                    }
                ]
            }

        if decision["status"] == "APPROVE":
            session["stage"] = "CONSENT_PENDING"
            session["pending_approval"] = {
                "amount": decision["approved_amount"],
                "tenure": tenure_months,
                "rate": decision["rate"],
                "emi": decision["emi"]
            }

            return {
                "replies": [
                    {
                        "role": "master",
                        "text": (
                            "Your loan is eligible for approval ✅\n\n"
                            f"Amount: {format_inr(decision['approved_amount'])}\n"
                            f"Tenure: {tenure_months} months\n"
                            f"EMI: {format_inr(decision['emi'])}\n\n"
                            "Do you want to proceed with this loan? (Yes / No)"
                        )
                    }
                ]
            }

    # =====================================================
    # Fallback
    # =====================================================
    return {
        "replies": [
            {
                "role": "master",
                "text": "Please tell me the loan amount and tenure you’re looking for."
            }
        ]
    }


# -------------------- Helpers --------------------
def parse_amount_and_tenure(text: str):
    amount_match = re.search(r"(?:₹\s*)?(\d{1,3}(?:,\d{3})+|\d+)", text)
    tenure_match = re.search(r"(\d{1,2})\s*(months?|yrs?|years?)", text, re.IGNORECASE)

    amount = int(amount_match.group(1).replace(",", "")) if amount_match else None
    tenure = None

    if tenure_match:
        t = int(tenure_match.group(1))
        tenure = t * 12 if "year" in tenure_match.group(2).lower() else t

    return amount, tenure


def format_inr(x):
    try:
        val = x if isinstance(x, Decimal) else Decimal(str(x))
        return f"₹{val.quantize(Decimal('0.01')):,.2f}"
    except Exception:
        return f"₹{x}"
