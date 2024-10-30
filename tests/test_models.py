# tests/test_models.py

from app.models import Claim, ClaimProcedure
from decimal import Decimal
from uuid import uuid4

def test_calculate_and_store_net_fee():
    procedure = ClaimProcedure(
        provider_fees=Decimal("100.00"),
        allowed_fees=Decimal("80.00"),
        member_coinsurance=Decimal("10.00"),
        member_copay=Decimal("5.00")
    )
    procedure.calculate_and_store_net_fee()
    assert procedure.net_fee == Decimal("35.00")

def test_claim_calculate_and_store_net_fee():
    claim = Claim()
    procedure1 = ClaimProcedure(net_fee=Decimal("35.00"))
    procedure2 = ClaimProcedure(net_fee=Decimal("15.00"))
    claim.procedures = [procedure1, procedure2]
    claim.calculate_and_store_net_fee()
    assert claim.net_fee == Decimal("50.00")

def test_claim_update_status():
    claim = Claim()
    procedure1 = ClaimProcedure(status="SUCCESS")
    procedure2 = ClaimProcedure(status="FAILED")
    claim.procedures = [procedure1, procedure2]
    claim.update_status()
    assert claim.status == "PARTIAL_FAILURE"

    claim.procedures = [procedure1, procedure1]
    claim.update_status()
    assert claim.status == "SUCCESS"

    claim.procedures = [procedure2, procedure2]
    claim.update_status()
    assert claim.status == "FAILURE"
