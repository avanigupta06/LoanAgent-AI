# **LoanAgent AI**
### *Agentic AI–powered Personal Loan Sales Assistant for Tata Capital*

LoanAgent AI is an end-to-end Agentic AI system designed for the **EY Techathon 6.0 – BFSI Challenge (Tata Capital)**.  
It simulates how a financial institution can leverage **multi-agent orchestration, automation, and intelligent decisioning** to sell personal loans through a **web-based chatbot**.

Built using a **Master Agent + Worker Agents architecture**, LoanAgent AI handles the entire loan journey — from sales pitch to sanction letter — using synthetic data and mock APIs.

> ⭐ **If you find this project useful or inspiring, please consider giving it a star!**

---

## 🚀 **Key Features**

### **1. Agentic Orchestration**
- **Master Agent** controls conversation flow and delegates tasks.
- **Worker Agents** independently handle specialized tasks:
  - **Sales Agent** – explains products, negotiates loan terms  
  - **Verification Agent** – performs KYC & validates user profile from CRM  
  - **Underwriting Agent** – evaluates credit score, salary, and risk rules  
  - **Sanction Agent** – auto-generates sanction letter (PDF)

---

## 🧠 **Loan Decisioning Logic**
- Uses **synthetic customer data** & a **mock credit bureau**.
- **Instant Approval** if the loan request ≤ pre-approved limit.
- If amount ≤ 2× pre-approved limit → request salary slip → approve if **EMI ≤ 50% of salary**.
- Reject if:
  - Loan > 2× limit  
  - Credit score < 700  

---

## 📁 **Repository Structure**
```bash
backend/
│── app.py
│── master_agent.py
│── workers/
│ ├── sales.py
│ ├── verification.py
│ ├── underwriting.py
│ └── sanction.py
│
│── mock_services/
│ ├── crm.py
│ ├── credit.py
│ └── offers.py
│
│── data/
│ └── customers.json
│
│── uploads/ # salary slips
│── sanctions/ # generated PDFs

chatbot-ui (React)/
```

---

---

## 🛠️ **Tech Stack**

### **Backend**
- Python  
- FastAPI  
- Agentic AI architecture  
- Mocked CRM, Offer Mart & Credit Bureau APIs  
- ReportLab (PDF generation)

### **Frontend**
- React  
- Chat interface  
- Tailwind CSS (optional)

---

## 🧪 **Demo Capabilities**
Supports:
- Customer identification  
- Dynamic sales pitch  
- Loan negotiation  
- Salary slip upload  
- Automatic underwriting  
- PDF sanction letter generation  
- Edge cases (low credit score, high loan request, incorrect KYC, etc.)

---

## 📦 **Setup Instructions**

### **Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```
### **Frontend**
```bash
cd chatbot-ui
npm install
npm start
```

⭐ If this project helped or inspired you, please consider giving the repository a star!