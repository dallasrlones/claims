# app/tasks.py

import os
import logging
import json
from uuid import UUID
from typing import List, Dict

from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker, selectinload

from app.models import Claim, ClaimProcedure
from app.schemas.procedure import ProcedureCreate

logger = logging.getLogger(__name__)

# Get the DATABASE_URL from environment variables
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres_change_me@db:5432/claims_db"
)

# Log the DATABASE_URL for debugging purposes
logger.info(f"DATABASE_URL in worker tasks: {DATABASE_URL}")

# Create the async engine within this file to ensure it's initialized properly
async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800
)

# Create an async session factory
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def enqueue_process_claim(claim_id: UUID, procedures_data: List[ProcedureCreate]):
    """Enqueue the process_claim task using ARQ."""
    redis = await create_pool(
        RedisSettings(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379))
        )
    )

    # Store procedures_data in Redis for retries
    procedures_data_key = f"claim_procedures:{claim_id}"

    # Serialize procedures data to JSON string
    procedures_json = json.dumps(
        [procedure.dict() for procedure in procedures_data],
        default=str  # Handle datetime and Decimal serialization
    )

    # Save the serialized data to Redis
    await redis.set(procedures_data_key, procedures_json)

    # Enqueue the job to process the claim
    await redis.enqueue_job(
        'process_claim',
        str(claim_id),
        [procedure.dict() for procedure in procedures_data]
    )
    await redis.close()

async def process_claim(ctx, claim_id: str, procedures_data: List[dict]):
    """Asynchronous task to process a claim."""
    async with AsyncSessionLocal() as session:
        try:
            stmt = (
                select(Claim)
                .options(selectinload(Claim.procedures))
                .where(Claim.id == UUID(claim_id))
            )
            result = await session.execute(stmt)
            claim = result.scalars().first()

            if not claim:
                raise ValueError(f"Claim with ID {claim_id} not found")

            all_success = True
            new_procedures = []

            # Process each procedure and update status
            for procedure_data in procedures_data:
                procedure = ClaimProcedure(**procedure_data, claim_id=UUID(claim_id))
                procedure.calculate_and_store_net_fee()

                if procedure.net_fee < 0:
                    procedure.status = "FAILED"
                    all_success = False
                else:
                    procedure.status = "SUCCESS"

                session.add(procedure)
                new_procedures.append(procedure)

            await session.flush()
            claim.procedures.extend(new_procedures)

            # Calculate net fee and update claim status
            claim.calculate_and_store_net_fee()
            claim.update_status()
            session.add(claim)
            await session.commit()

            net_fee = float(claim.net_fee)

            # Enqueue further tasks if needed
            if all_success:
                await ctx['redis'].enqueue_job(
                    'process_payment',
                    claim_id=claim_id,
                    net_fee=net_fee
                )
            else:
                await ctx['redis'].enqueue_job(
                    'retry_claim',
                    claim_id=claim_id
                )

        except Exception as e:
            await session.rollback()
            logger.error(f"Error processing claim {claim_id}: {e}", exc_info=True)
            # Enqueue retry task
            await ctx['redis'].enqueue_job(
                'retry_claim',
                claim_id=claim_id
            )

async def process_payment(ctx, claim_id: str, net_fee: float):
    """Asynchronous task to process a payment."""
    logger.info(f"Processing payment for claim {claim_id} with net fee {net_fee}")

    # Enqueue payment processing on the same Redis host
    await ctx['redis'].enqueue_job(
        'process_payment_task',
        claim_id=claim_id,
        net_fee=net_fee,
        _job_id=f"payment_{claim_id}"
    )

async def process_payment_task(ctx, claim_id: str, net_fee: float):
    """Simulate payment processing."""
    try:
        # Simulate payment processing logic
        logger.info(f"Payment processed for claim {claim_id} with net fee {net_fee}")
    except Exception as e:
        logger.error(f"Payment processing failed for claim {claim_id}: {e}", exc_info=True)
        raise

async def retry_claim(ctx, claim_id: str):
    """Asynchronous task to retry processing a claim."""
    max_retries = 5  # Maximum number of retries
    retry_count_key = f"claim_retry_count:{claim_id}"

    # Get the current retry count from Redis
    retry_count = await ctx['redis'].get(retry_count_key) or 0
    retry_count = int(retry_count)

    if retry_count < max_retries:
        # Increment the retry count
        await ctx['redis'].set(retry_count_key, retry_count + 1)

        logger.info(f"Retrying claim {claim_id}, attempt {retry_count + 1}")

        # Retrieve the procedures data from Redis
        procedures_data_key = f"claim_procedures:{claim_id}"
        procedures_data_json = await ctx['redis'].get(procedures_data_key)

        if procedures_data_json:
            # Deserialize procedures_data
            procedures_data = json.loads(procedures_data_json)

            # Enqueue the process_claim task again
            await ctx['redis'].enqueue_job(
                'process_claim',
                claim_id=claim_id,
                procedures_data=procedures_data
            )
        else:
            logger.error(f"No procedures data found for claim {claim_id}")
            # Mark the claim as FAILED
            await mark_claim_as_failed(claim_id)
    else:
        logger.error(f"Max retries reached for claim {claim_id}")
        # Enqueue to dead letter queue
        await ctx['redis'].enqueue_job(
            'dead_letter_queue',
            claim_id=claim_id
        )
        # Mark the claim as FAILED
        await mark_claim_as_failed(claim_id)

async def mark_claim_as_failed(claim_id: str):
    """Helper function to mark a claim as FAILED in the database."""
    async with AsyncSessionLocal() as session:
        stmt = select(Claim).where(Claim.id == UUID(claim_id))
        result = await session.execute(stmt)
        claim = result.scalars().first()

        if claim:
            claim.status = "FAILED"
            session.add(claim)
            await session.commit()
            logger.info(f"Claim {claim_id} marked as FAILED in the database")

async def dead_letter_queue(ctx, claim_id: str):
    """Handle tasks that have failed after maximum retries."""
    logger.error(f"Claim {claim_id} moved to dead letter queue")

    # Implement any additional logic for dead letter queue processing
    # For example, alerting, logging to external systems, etc.

class WorkerSettings:
    functions = [
        process_claim,
        process_payment,
        retry_claim,
        dead_letter_queue,
        process_payment_task
    ]
    redis_settings = RedisSettings(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379))
    )
    max_jobs = 10  # Adjust based on your requirements

    # Retry configuration
    retry_jobs = False  # We handle retries manually in the code
