"""
Main FastAPI application for NerdNostalgia backend.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from api.users import router as users_router

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
app.include_router(users_router)


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
