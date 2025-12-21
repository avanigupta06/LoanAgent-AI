import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# API routers
from master_agent import router as master_router
from mock_services import crm, credit, offers

"""
Application entry point for the Agentic Loan Processing Demo.

This service:
- Hosts the Master Agent (chat orchestration)
- Exposes mock backend services (CRM, Credit Bureau, Offers)
- Acts as the single backend consumed by the frontend
"""

# --------------------------------------------------
# FastAPI App Initialization
# --------------------------------------------------
app = FastAPI(title="TataCapital - Agentic Demo")

# --------------------------------------------------
# CORS Configuration
# Allows frontend (any origin in demo mode) to call APIs
# --------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Open for demo; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# API Routing
# --------------------------------------------------

# Master Agent routes (chat, upload, sanction)
# Mounted at /api so frontend can call /api/chat
app.include_router(master_router, prefix="/api")

# Mock backend services
# Used internally by the Master Agent
app.include_router(crm.router, prefix="/api/mock/crm")
app.include_router(credit.router, prefix="/api/mock/credit")
app.include_router(offers.router, prefix="/api/mock/offers")

# --------------------------------------------------
# Local Development Server
# --------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload during development
    )
