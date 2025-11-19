# backend/mock_services/__init__.py
from . import crm, credit, offers
from .crm import router as crm_router
from .credit import router as credit_router
from .offers import router as offers_router
