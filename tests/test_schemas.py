# tests/test_schemas.py

import pytest
from pydantic import ValidationError
from app.schemas.procedure import ProcedureCreate

def test_procedure_create_validation_success():
    data = {
        "service_date": "2024-10-29T10:00:00",
        "submitted_procedure": "D0120",
        "provider_npi": "1234567890",
        "provider_fees": 100.0,
        "allowed_fees": 80.0,
        "member_coinsurance": 10.0,
        "member_copay": 5.0
    }
    procedure = ProcedureCreate(**data)
    assert procedure.submitted_procedure == "D0120"
    assert procedure.provider_npi == "1234567890"

def test_procedure_create_validation_failure():
    data = {
        "service_date": "2024-10-29T10:00:00",
        "submitted_procedure": "X0120",
        "provider_npi": "1234567890",
        "provider_fees": -100.0,
        "allowed_fees": 80.0,
        "member_coinsurance": 10.0,
        "member_copay": 5.0
    }
    with pytest.raises(ValidationError):
        ProcedureCreate(**data)
