"""Against the real API (apps/api's sdk-server: in-memory database, a phone that delivers at once).

Skipped outside the monorepo, or when the API's dependencies aren't installed.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Iterator, TypeVar

import pytest

from smswire import SMSWire, SMSWireError, SignatureError, verify_webhook

from .conftest import SDKS

API = SDKS.parent / "apps" / "api"
TSX = API / "node_modules" / ".bin" / "tsx"
T = TypeVar("T")

pytestmark = pytest.mark.skipif(not TSX.exists(), reason="needs apps/api with its dependencies (pnpm install)")


@pytest.fixture(scope="module")
def server() -> Iterator[Dict[str, Any]]:
    proc = subprocess.Popen([str(TSX), "test/sdkServer.ts"], cwd=API, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    assert proc.stdout is not None
    line = proc.stdout.readline()
    if not line:
        proc.kill()
        pytest.fail("sdk-server did not start")
    yield json.loads(line)
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture(scope="module")
def sms(server: Dict[str, Any]) -> Iterator[SMSWire]:
    with SMSWire(server["apiKey"], server["project"], base_url=server["baseUrl"], webhook_secret=server["webhookSecret"]) as client:
        yield client


def control(server: Dict[str, Any], path: str, body: Any = None) -> Any:
    data = None if body is None else json.dumps(body).encode()
    with urllib.request.urlopen(urllib.request.Request(server["control"] + path, data=data, method="POST" if data else "GET")) as res:
        return json.loads(res.read())


def eventually(read: Callable[[], T], ok: Callable[[T], bool]) -> T:
    for _ in range(100):
        value = read()
        if ok(value):
            return value
        time.sleep(0.05)
    raise AssertionError("timed out")


def test_sends_a_message_that_the_phone_delivers(sms: SMSWire) -> None:
    sent = sms.messages.send("+251911234567", "Your order shipped", tags=["orders"], metadata={"order": 7})
    assert (sent["status"], sent["tags"], sent["metadata"]) == ("queued", ["orders"], {"order": 7})
    delivered = eventually(lambda: sms.messages.get(sent["id"]), lambda m: m["status"] == "delivered")
    assert delivered["delivered_at"]
    assert sent["id"] in [m["id"] for m in sms.messages.list(tag="orders")["data"]]


def test_replays_a_send_with_the_same_idempotency_key(sms: SMSWire) -> None:
    a = sms.messages.send("+251911234567", "Once", idempotency_key="py-order-42")
    b = sms.messages.send("+251911234567", "Once", idempotency_key="py-order-42")
    assert a["id"] == b["id"]


def test_cancels_a_scheduled_message(sms: SMSWire) -> None:
    m = sms.messages.send("+251911234567", "Later", send_at=datetime.now(timezone.utc) + timedelta(hours=1))
    assert sms.messages.cancel(m["id"])["status"] == "cancelled"


def test_sends_a_batch_and_rejects_bad_numbers(sms: SMSWire) -> None:
    result = sms.messages.send_bulk(
        [{"to": "+251911234567", "variables": {"name": "Abebe"}}, {"to": "not a number", "variables": {"name": "Nobody"}}],
        name="SDK test",
        body="Hi {{name}}",
    )
    assert result["accepted"] == 1
    assert [(r["index"], r["to"]) for r in result["rejected"]] == [(1, "not a number")]


def test_sends_and_verifies_a_one_time_code(server: Dict[str, Any], sms: SMSWire) -> None:
    otp = sms.otp.send("+251933456789", length=6)
    texts = eventually(lambda: control(server, "/sms"), lambda all: any(s["messageId"] == otp["message_id"] for s in all))
    body = next(s["body"] for s in texts if s["messageId"] == otp["message_id"])
    code = re.search(r"\d{6}", body).group(0)  # type: ignore[union-attr]
    assert sms.otp.verify(otp["id"], "111111" if code == "000000" else "000000") == {"valid": False, "reason": "invalid"}
    assert sms.otp.verify(otp["id"], code)["valid"] is True
    assert sms.otp.verify(otp["id"], code)["reason"] == "already_used"


def test_manages_a_recurring_send(sms: SMSWire) -> None:
    created = sms.schedules.create("0 9 * * 1", name="Weekly", timezone="Africa/Addis_Ababa", to="+251911234567", body="Weekly report")
    assert (created["name"], created["enabled"], created["recipients"]["numbers"]) == ("Weekly", True, 1)
    assert sms.schedules.update(created["id"], enabled=False)["enabled"] is False
    assert created["id"] in [s["id"] for s in sms.schedules.list()["data"]]
    assert sms.schedules.get(created["id"])["id"] == created["id"]
    sms.schedules.delete(created["id"])
    with pytest.raises(SMSWireError) as raised:
        sms.schedules.get(created["id"])
    assert raised.value.status == 404


def test_verifies_the_webhooks_the_api_really_sends(server: Dict[str, Any], sms: SMSWire) -> None:
    control(server, "/reply", {"from": "+251911234567", "body": "ሰላም, thanks!"})
    hooks = eventually(
        lambda: control(server, "/webhooks"),
        lambda all: any(h["headers"]["X-SMSWire-Event"] == "message.received" for h in all),
    )
    for hook in hooks:
        event = sms.webhooks.verify(hook["body"].encode("utf-8"), hook["headers"]["X-SMSWire-Signature"])
        assert event["event"] == hook["headers"]["X-SMSWire-Event"]
    with pytest.raises(SignatureError):
        verify_webhook(hooks[0]["body"].replace("+251", "+252"), hooks[0]["headers"]["X-SMSWire-Signature"], server["webhookSecret"])


def test_turns_api_errors_into_smswire_error(server: Dict[str, Any], sms: SMSWire) -> None:
    with pytest.raises(SMSWireError) as raised:
        SMSWire("smswire_live_wrong", server["project"], base_url=server["baseUrl"]).messages.list()
    assert (raised.value.status, raised.value.code) == (401, "invalid_api_key")
    with pytest.raises(SMSWireError) as raised:
        sms.messages.send("+251911234567")
    assert (raised.value.status, raised.value.code) == (400, "invalid_request")
