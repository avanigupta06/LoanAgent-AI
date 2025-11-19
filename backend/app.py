import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# import routers from package modules
from master_agent import router as master_router
from mock_services import crm, credit, offers

app = FastAPI(title="TataCapital - Agentic Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount master agent (public chat endpoints) at /api so frontend's /api/chat works
app.include_router(master_router, prefix="/api")

# Mount mock services
app.include_router(crm.router, prefix="/api/mock/crm")
app.include_router(credit.router, prefix="/api/mock/credit")
app.include_router(offers.router, prefix="/api/mock/offers")


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
