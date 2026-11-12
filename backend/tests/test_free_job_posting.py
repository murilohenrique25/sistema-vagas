"""Regression checks for the free job-posting business rule."""

import inspect

from app.api.v1.routes import jobs
from app.schemas.payment import PublicPaymentConfigResponse, ServicePaymentPurpose


def test_create_job_route_has_no_wallet_charge() -> None:
    source = inspect.getsource(jobs.create_job)
    assert "WalletService" not in source
    assert ".debit(" not in source
    assert "get_price" not in source


def test_job_posting_is_not_a_paid_service() -> None:
    assert "job_posting" not in {purpose.value for purpose in ServicePaymentPurpose}
    assert "job_posting" not in PublicPaymentConfigResponse.model_json_schema()["$defs"]["ServicePricesResponse"]["properties"]
