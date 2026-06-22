"""
Main FastAPI application for NerdNostalgia backend.
"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import os

from utils.limiter import limiter

from api.articles import router as articles_router
from api.auth import router as auth_router
from api.card_purchases import router as card_purchases_router
from api.consignment_sales import router as consignment_sales_router
from api.expenses import router as expenses_router
from api.categories import router as categories_router
from api.dashboard import router as dashboard_router
from api.inquiries import router as inquiries_router
from api.inventory import router as inventory_router
from api.lots import router as lots_router
from api.marketplace_fees import router as marketplace_fees_router
from api.platforms import router as platforms_router
from api.misc_sales import router as misc_sales_router
from api.orders import router as orders_router
from api.personal_cards import router as personal_cards_router
from api.users import router as users_router
from api.vinted import router as vinted_router
from api.wanted import router as wanted_router
from utils.scheduler import start_scheduler, stop_scheduler
from utils.session import get_db
from utils.storage import UPLOADS_DIR, ensure_dirs

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Startup/shutdown via lifespan (sostituisce @app.on_event deprecated)."""
    start_scheduler()
    yield
    stop_scheduler()


# Create FastAPI app
app = FastAPI(
    title="NerdNostalgia API",
    version="1.0.0",
    description="API for NerdNostalgia - Manage and publish articles to e-commerce platforms",
    lifespan=lifespan,
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(categories_router)
app.include_router(articles_router)
app.include_router(inquiries_router)
app.include_router(wanted_router)
app.include_router(marketplace_fees_router)
app.include_router(platforms_router)
app.include_router(card_purchases_router)
app.include_router(consignment_sales_router)
app.include_router(expenses_router)
app.include_router(misc_sales_router)
app.include_router(orders_router)
app.include_router(personal_cards_router)
app.include_router(inventory_router)
app.include_router(lots_router)
app.include_router(dashboard_router)
app.include_router(vinted_router)


# Static files (uploaded images)
ensure_dirs()
app.mount("/static", StaticFiles(directory=str(UPLOADS_DIR)), name="static")


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "Welcome to NerdNostalgia API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/status")
@app.get("/health")
def health(db=Depends(get_db)):
    """Health check. Verifica connessione DB con SELECT 1.

    Usa la dependency get_db cosi' i test overridano la sessione (in-memory)
    e CI/prod usano la SessionLocal standard.
    """
    from sqlalchemy import text
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # noqa: BLE001
        db_ok = False
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "ok" if db_ok else "down",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7373)
