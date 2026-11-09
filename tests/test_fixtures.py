"""The shared vectors in sdks/fixtures, which every SDK passes the same way."""

from __future__ import annotations

import asyncio
from typing import Any, Dict

import httpx
import pytest

from smswire import AsyncSMSWire, SignatureError, SMSWire, SMSWireError, verify_webhook

from .conftest import Recorder, fixture, ok

WEBHOOKS = fixture("webhooks.json")
ERRORS = fixture("errors.json")


@pytest.mark.parametrize("case", WEBHOOKS["cases"], ids=lambda c: c["name"])
def test_webhook_signatures(case: Dict[str, Any]) -> None:
    def verify(body: Any) -> Dict[str, Any]:
        return verify_webhook(body, case["header"], WEBHOOKS["secret"], tolerance=WEBHOOKS["tolerance"], now=case["now"])

    if case["valid"]:
        assert verify(case["body"])["event"] == case.get("event", "message.status")
        assert verify(case["body"].encode("utf-8"))["event"] == case.get("event", "message.status")
    else:
        with pytest.raises(SignatureError):
            verify(case["body"])


def answer(case: Dict[str, Any]) -> Recorder:
    first = lambda _: httpx.Response(case["status"], headers=case["headers"], content=case["body"].encode())
    return Recorder(first, ok({"id": "msg_1", "to": "+1", "expires_at": "", "message_id": "msg_1"}))


def check(case: Dict[str, Any], flag: str, recorder: Recorder, run: Any) -> None:
    if case[flag]:
        assert run()
        assert len(recorder.requests) == 2
    else:
        with pytest.raises(SMSWireError) as raised:
            run()
        err = raised.value
        assert (err.status, err.code, err.message, err.retry_after) == (case["status"], case["code"], case["message"], case["retry_after"])
        assert len(recorder.requests) == 1


@pytest.mark.parametrize("case", ERRORS["cases"], ids=lambda c: c["name"])
def test_safe_request_errors(case: Dict[str, Any]) -> None:
    rec = answer(case)
    sms = SMSWire("k", "p", http_client=rec.client(), max_retries=1, max_retry_wait=ERRORS["max_retry_wait"])
    check(case, "retry", rec, lambda: sms.messages.get("msg_1"))


@pytest.mark.parametrize("case", ERRORS["cases"], ids=lambda c: c["name"])
def test_unsafe_post_errors(case: Dict[str, Any]) -> None:
    rec = answer(case)
    sms = SMSWire("k", "p", http_client=rec.client(), max_retries=1, max_retry_wait=ERRORS["max_retry_wait"])
    check(case, "retry_post", rec, lambda: sms.otp.send("+1"))


@pytest.mark.parametrize("case", ERRORS["cases"], ids=lambda c: c["name"])
def test_async_errors(case: Dict[str, Any]) -> None:
    rec = answer(case)
    sms = AsyncSMSWire("k", "p", http_client=rec.async_client(), max_retries=1, max_retry_wait=ERRORS["max_retry_wait"])
    check(case, "retry", rec, lambda: asyncio.run(sms.messages.get("msg_1")))
