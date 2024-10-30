# app/routers/claim.py

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import func, desc
from slowapi.util import get_remote_address
from slowapi import Limiter
from uuid import UUID
import logging

from app.tasks import enqueue_process_claim
from app.db.connection import get_session
from app.models import Claim, ClaimProcedure
from app.schemas.claim import ClaimCreate

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

logger = logging.getLogger(__name__)

@router.get("/top-npis/", response_model=list[dict])
@limiter.limit("10/minute")
async def get_top_npis(
    request: Request,
    session: AsyncSession = Depends(get_session),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Return the top NPIs by total net fees generated with pagination."""
    try:
        query = (
            select(
                ClaimProcedure.provider_npi,
                func.sum(ClaimProcedure.net_fee).label("total_net_fee")
            )
            .group_by(ClaimProcedure.provider_npi)
            .order_by(desc("total_net_fee"))
            .limit(limit)
            .offset(offset)
        )

        # Execute the query and fetch results
        results = (await session.execute(query)).all()
        return [{"provider_npi": npi, "total_net_fee": net_fee} for npi, net_fee in results]
    except Exception as e:
        logger.error(f"Error fetching top NPIs: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/", response_model=UUID)
async def create_claim(
    claim: ClaimCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new claim and add it to the processing queue."""
    existing_claim = (await session.execute(
        select(Claim).where(Claim.claim_number == claim.claim_number)
    )).scalar_one_or_none()

    if existing_claim:
        raise HTTPException(status_code=400, detail="Claim number already exists")

    claim_data = Claim(
        claim_number=claim.claim_number,
        plan_group=claim.plan_group,
        subscriber_number=claim.subscriber_number,
        status="PENDING"
    )

    session.add(claim_data)
    await session.commit()
    await session.refresh(claim_data)

    # Enqueue the claim processing task using ARQ
    await enqueue_process_claim(claim_data.id, claim.procedures)

    return claim_data.id
