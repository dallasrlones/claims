# app/models/claim.py

from sqlmodel import SQLModel, Field, Relationship
from decimal import Decimal
import uuid
from datetime import datetime
from typing import Optional, List

class ClaimProcedure(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    claim_id: uuid.UUID = Field(foreign_key="claim.id", nullable=False, index=True)
    service_date: datetime
    submitted_procedure: str
    quadrant: Optional[str] = None
    provider_npi: str = Field(index=True)
    provider_fees: Decimal
    allowed_fees: Decimal
    member_coinsurance: Decimal
    member_copay: Decimal
    net_fee: Decimal = Decimal("0.00")
    status: str = Field(default="PENDING")

    # Back-reference to the parent claim
    claim: Optional["Claim"] = Relationship(back_populates="procedures")

    def calculate_and_store_net_fee(self):
        """Calculate and store the net fee for the procedure."""
        # Net fee calculation per the assignment
        self.net_fee = (
            self.provider_fees
            + self.member_coinsurance
            + self.member_copay
            - self.allowed_fees
        )

class Claim(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    claim_number: str = Field(unique=True, index=True)
    plan_group: str
    subscriber_number: str
    net_fee: Decimal = Decimal("0.00")
    status: str = Field(default="PENDING")

    # One-to-Many relationship with ClaimProcedure
    procedures: List[ClaimProcedure] = Relationship(back_populates="claim")

    def calculate_and_store_net_fee(self):
        """Calculate and update the net fee based on related procedures."""
        self.net_fee = sum(procedure.net_fee for procedure in self.procedures)

    def update_status(self):
        """Update the status based on the status of related procedures."""
        statuses = {procedure.status for procedure in self.procedures}
        if "FAILED" in statuses and "SUCCESS" in statuses:
            self.status = "PARTIAL_FAILURE"
        elif "FAILED" in statuses:
            self.status = "FAILURE"
        elif all(status == "SUCCESS" for status in statuses):
            self.status = "SUCCESS"
        else:
            self.status = "PROCESSING"
