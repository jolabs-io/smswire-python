from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import httpx
import pytest

from smswire import AsyncSMSWire, SMSWire, SMSWireError

from .conftest import Recorder, ok


def test_send_carries_key_path_body_and_a_fresh_idempotency_key() -> None:
    rec = Recorder(ok({"id": "msg_1"}, 202))
    sms = SMSWire("smswire_live_x", "prj_1", base_url="https://gw.test/", http_client=rec.client())
    sms.messages.send("+251911234567", "Hi", tags=["login"], send_at=datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc))
    sms.messages.send("+251911234567", "Hi")
    first, second = rec.requests
    assert str(first.url) == "https://gw.test/v1/p/prj_1/messages"
    assert first.method == "POST"
    assert first.headers["authorization"] == "Bearer smswire_live_x"
    assert first.headers["user-agent"].startswith("smswire-python/")
    assert json.loads(first.content) == {"to": "+251911234567", "body": "Hi", "tags": ["login"], "send_at": "2026-01-02T03:04:00+00:00"}
    assert len(first.headers["idempotency-key"]) == 36
    assert first.headers["idempotency-key"] != second.headers["idempotency-key"]


def test_keeps_your_idempotency_key_across_retries() -> None:
    def drop(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    rec = Recorder(drop, ok({"id": "msg_1"}, 202))
    SMSWire("k", "p", http_client=rec.client()).messages.send("+1", "x", idempotency_key="order-1234")
    assert [r.headers["idempotency-key"] for r in rec.requests] == ["order-1234", "order-1234"]


def test_does_not_retry_a_bulk_send_after_a_dropped_connection() -> None:
    def drop(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    rec = Recorder(drop)
    with pytest.raises(SMSWireError) as raised:
        SMSWire("k", "p", http_client=rec.client()).messages.send_bulk([{"to": "+1", "body": "x"}])
    assert (raised.value.status, raised.value.code) == (None, "network_error")
    assert len(rec.requests) == 1


def test_gives_up_after_max_retries() -> None:
    rec = Recorder(ok({"error": "internal_error", "message": "Boom"}, 503))
    with pytest.raises(SMSWireError) as raised:
        SMSWire("k", "p", http_client=rec.client(), max_retries=3).messages.get("msg_1")
    assert raised.value.code == "internal_error"
    assert len(rec.requests) == 4


def test_reports_a_timeout() -> None:
    def slow(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    with pytest.raises(SMSWireError) as raised:
        SMSWire("k", "p", http_client=Recorder(slow).client(), max_retries=0).messages.get("msg_1")
    assert (raised.value.status, raised.value.code) == (None, "timeout")


def test_lists_with_filters_and_walks_every_page() -> None:
    rec = Recorder(ok({"data": [{"id": "a"}, {"id": "b"}], "next_cursor": "c1"}), ok({"data": [{"id": "c"}], "next_cursor": None}))
    sms = SMSWire("k", "p", http_client=rec.client())
    ids = [m["id"] for m in sms.messages.list_all(status="delivered", tag="login", since="2026-01-01", limit=2)]
    assert ids == ["a", "b", "c"]
    assert dict(rec.requests[0].url.params) == {"status": "delivered", "tag": "login", "from": "2026-01-01", "limit": "2"}
    assert rec.requests[1].url.params["cursor"] == "c1"


def test_async_client_walks_pages() -> None:
    rec = Recorder(ok({"data": [{"id": "a"}], "next_cursor": "c1"}), ok({"data": [{"id": "b"}], "next_cursor": None}))

    async def run() -> list:
        async with AsyncSMSWire("k", "p", http_client=rec.async_client()) as sms:
            return [m["id"] async for m in sms.messages.list_all()]

    assert asyncio.run(run()) == ["a", "b"]


def test_update_sends_only_what_changes_and_none_clears() -> None:
    rec = Recorder(ok({"id": "sch_1"}))
    SMSWire("k", "p", http_client=rec.client()).schedules.update("sch_1", enabled=False, ends_at=None)
    assert rec.requests[0].method == "PATCH"
    assert json.loads(rec.requests[0].content) == {"enabled": False, "ends_at": None}


def test_reads_settings_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMSWIRE_KEY", "env_key")
    monkeypatch.setenv("SMSWIRE_PROJECT", "env_project")
    monkeypatch.setenv("SMSWIRE_URL", "https://env.test")
    rec = Recorder(ok({"data": []}))
    SMSWire(http_client=rec.client()).schedules.list()
    assert str(rec.requests[0].url) == "https://env.test/v1/p/env_project/schedules"
    assert rec.requests[0].headers["authorization"] == "Bearer env_key"


def test_needs_a_key_and_a_project(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SMSWIRE_KEY", raising=False)
    monkeypatch.delenv("SMSWIRE_PROJECT", raising=False)
    with pytest.raises(ValueError, match="api_key"):
        SMSWire(project="p")
    with pytest.raises(ValueError, match="project"):
        SMSWire(api_key="k")


def test_204_is_none() -> None:
    rec = Recorder(lambda _: httpx.Response(204))
    assert SMSWire("k", "p", http_client=rec.client()).schedules.delete("sch_1") is None
