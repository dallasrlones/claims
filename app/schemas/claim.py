# app/schemas/claim.py

from pydantic import BaseModel, Field
from typing import List
from app.schemas.procedure import ProcedureCreate

class ClaimCreate(BaseModel):
    claim_number: str = Field(
        ...,
        min_length=5,
        max_length=20,
        description="Claim number must be between 5 and 20 characters."
    )
    plan_group: str
    subscriber_number: str
    procedures: List[ProcedureCreate]
