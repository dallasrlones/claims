# app/main.py

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import claim
from app.middleware.lowercase_keys_middleware import LowercaseKeysMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Claim Process API",
    description="API for processing and retrieving claims.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LowercaseKeysMiddleware)

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "development":
    from sqlmodel import SQLModel
    from app.db.connection import async_engine

    @app.on_event("startup")
    async def on_startup():
        """Create all tables on startup if they don't already exist (dev only)."""
        async with async_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

@app.get("/health", tags=["Health"])
async def health_check():
    """Simple health check endpoint."""
    return {"status": "OK"}

app.include_router(claim.router, prefix="/claims", tags=["Claims"])
