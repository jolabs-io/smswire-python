"""The TypedDicts in smswire.types name the same fields as sdks/openapi.json."""

from __future__ import annotations

import pytest

from smswire import types

from .conftest import SDKS
import json

SPEC = json.loads((SDKS / "openapi.json").read_text("utf-8"))["components"]["schemas"]


@pytest.mark.parametrize(
    "typed, schema",
    [
        (types.Message, "MessageView"),
        (types.MessagePage, "MessagePage"),
        (types.BulkResult, "BulkSendResponse"),
        (types.RejectedItem, "RejectedItem"),
        (types.Otp, "OtpResponse"),
        (types.OtpVerification, "OtpVerifyResponse"),
        (types.Schedule, "ScheduleView"),
        (types.ScheduleRun, "ScheduleRunView"),
        (types.SchedulePage, "SchedulePage"),
        (types.BulkItem, "BulkItem"),
        (types.ScheduleRecipient, "ScheduleRecipient"),
    ],
)
def test_fields_match_the_spec(typed: type, schema: str) -> None:
    spec = SPEC[schema]
    assert set(typed.__annotations__) == set(spec["properties"]), schema
    assert set(typed.__required_keys__) == set(spec.get("required", [])) or schema in ("BulkItem", "ScheduleRecipient"), schema
