# tests/test_e2e.py

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import SQLModel, select
from app.main import app
from app.db.connection import get_session
from app.models import Claim, ClaimProcedure
from uuid import UUID
import os
from datetime import datetime

# Configure DATABASE_URL based on environment variable or default to 'localhost'
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres_change_me@localhost:5432/claims_db"
)

# Create a new engine and sessionmaker for tests
test_engine = create_async_engine(DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    expire_on_commit=False
)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the event loop for all tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="module")
async def setup_database():
    """Create the database schema before tests and drop it after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

@pytest_asyncio.fixture
async def client():
    """Create a new FastAPI test client with overridden dependencies."""
    async def get_test_session():
        async with TestSessionLocal() as session:
            yield session
    app.dependency_overrides[get_session] = get_test_session
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.pop(get_session, None)

@pytest.mark.asyncio
async def test_create_claim(setup_database, client):
    claim_data = {
        "claim_number": "123456",
        "plan_group": "GRP-1000",
        "subscriber_number": "3730189502",
        "procedures": [
            {
                "service_date": "2024-10-29T10:00:00",
                "submitted_procedure": "D0120",
                "provider_npi": "1497775530",
                "provider_fees": 100.0,
                "allowed_fees": 80.0,
                "member_coinsurance": 10.0,
                "member_copay": 5.0
            }
        ]
    }

    # Perform the POST request
    response = await client.post("/claims/", json=claim_data)
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    
    # Extract the claim_id from the response
    claim_id = response.json()
    assert isinstance(claim_id, str), f"Expected claim_id to be a string, got {type(claim_id)}"

    # Define a timeout for waiting
    timeout = 15  # seconds
    interval = 1  # seconds
    total_time = 0
    status = 'PENDING'

    while total_time < timeout and status == 'PENDING':
        await asyncio.sleep(interval)
        total_time += interval
        async with TestSessionLocal() as session:
            stmt = select(Claim).where(Claim.id == UUID(claim_id))
            result = await session.execute(stmt)
            claim = result.scalars().first()
            if claim:
                status = claim.status
            else:
                status = None

    assert status == "SUCCESS", f"Expected claim status 'SUCCESS' but got '{status}' after {total_time} seconds"
