from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal

class ProcedureCreate(BaseModel):
    service_date: datetime
    submitted_procedure: str = Field(
        ...,
        pattern=r"^D\d{4}$",
        description="Procedure must start with 'D' followed by 4 digits."
    )
    provider_npi: str = Field(
        ...,
        min_length=10,
        max_length=10,
        pattern=r"^\d{10}$",
        description="Provider NPI must be exactly 10 digits."
    )
    provider_fees: Decimal = Field(..., gt=0, description="Provider fees must be greater than 0.")
    allowed_fees: Decimal = Field(..., gt=0, description="Allowed fees must be greater than 0.")
    member_coinsurance: Decimal = Field(..., ge=0, description="Coinsurance must be non-negative.")
    member_copay: Decimal = Field(..., ge=0, description="Copay must be non-negative.")
    quadrant: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),  # Converts datetime to ISO 8601 string
        }
