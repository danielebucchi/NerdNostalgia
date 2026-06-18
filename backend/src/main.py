"""
Main FastAPI application for NerdNostalgia backend.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from api.articles import router as articles_router
from api.auth import router as auth_router
from api.card_purchases import router as card_purchases_router
from api.categories import router as categories_router
from api.dashboard import router as dashboard_router
from api.inquiries import router as inquiries_router
from api.marketplace_fees import router as marketplace_fees_router
from api.misc_sales import router as misc_sales_router
from api.users import router as users_router
from api.wanted import router as wanted_router
from utils.storage import UPLOADS_DIR, ensure_dirs

# Create FastAPI app
app = FastAPI(
    title="NerdNostalgia API",
    version="1.0.0",
    description="API for NerdNostalgia - Manage and publish articles to e-commerce platforms",
)

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
app.include_router(card_purchases_router)
app.include_router(misc_sales_router)
app.include_router(dashboard_router)

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
def status():
    """Health check endpoint."""
    db_url = os.getenv("DATABASE_URL", "Not configured")
    return {
        "status": "healthy",
        "database": "connected" if db_url != "Not configured" else "not configured"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7373)
