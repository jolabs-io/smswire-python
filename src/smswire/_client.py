from __future__ import annotations

import os
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Sequence, cast

import httpx

from . import _requests as r
from ._http import Request, Settings, send, send_async
from ._version import __version__
from .types import (
    BulkItem,
    BulkResult,
    Message,
    MessagePage,
    MessageStatus,
    MessageType,
    Otp,
    OtpVerification,
    Schedule,
    SchedulePage,
    ScheduleRecipient,
)
from .webhooks import verify_webhook

DEFAULT_BASE_URL = "https://api.smswire.app"


def _settings(api_key: Optional[str], project: Optional[str], base_url: Optional[str], max_retries: int, max_retry_wait: float, timeout: float) -> "tuple[Settings, r.Paths]":
    key = api_key or os.environ.get("SMSWIRE_KEY")
    slug = project or os.environ.get("SMSWIRE_PROJECT")
    if not key:
        raise ValueError("SMSWire: pass api_key or set SMSWIRE_KEY")
    if not slug:
        raise ValueError("SMSWire: pass project or set SMSWIRE_PROJECT")
    settings = Settings(
        api_key=key,
        base_url=base_url or os.environ.get("SMSWIRE_URL") or DEFAULT_BASE_URL,
        max_retries=max_retries,
        max_retry_wait=max_retry_wait,
        timeout=timeout,
        user_agent=f"smswire-python/{__version__}",
    )
    return settings, r.Paths(slug)


class _Webhooks:
    def __init__(self, secret: Optional[str]) -> None:
        self._secret = secret

    def verify(self, raw_body: "bytes | str", signature: Optional[str], *, tolerance: int = 300) -> Dict[str, Any]:
        """Checks X-SMSWire-Signature over the raw body and returns the event; raises SignatureError."""
        if not self._secret:
            raise ValueError("SMSWire: pass webhook_secret or set SMSWIRE_WEBHOOK_SECRET")
        return verify_webhook(raw_body, signature, self._secret, tolerance=tolerance)


# ── Sync ─────────────────────────────────────────────────────────────────────


class Messages:
    def __init__(self, call: Any, paths: r.Paths) -> None:
        self._call, self._paths = call, paths

    def send(
        self,
        to: str,
        body: Optional[str] = None,
        *,
        template: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        sim: Optional[int] = None,
        type: Optional[MessageType] = None,
        tags: Optional[Sequence[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        send_at: r.When = None,
        idempotency_key: Optional[str] = None,
    ) -> Message:
        """Queues one SMS. ``idempotency_key`` (default: random) makes repeating the call safe."""
        req = r.send_message(self._paths, idempotency_key, to=to, body=body, template=template, variables=variables, sim=sim, type=type, tags=tags, metadata=metadata, send_at=send_at)
        return cast(Message, self._call(req))

    def send_bulk(
        self,
        messages: Sequence[BulkItem],
        *,
        name: Optional[str] = None,
        body: Optional[str] = None,
        template: Optional[str] = None,
        rate: Optional[int] = None,
        sim: Optional[int] = None,
        type: Optional[MessageType] = None,
        tags: Optional[Sequence[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        send_at: r.When = None,
    ) -> BulkResult:
        """Queues a batch; invalid or opted-out items come back in ``rejected``."""
        req = r.send_bulk(self._paths, messages=messages, name=name, body=body, template=template, rate=rate, sim=sim, type=type, tags=tags, metadata=metadata, send_at=send_at)
        return cast(BulkResult, self._call(req))

    def get(self, id: str) -> Message:
        return cast(Message, self._call(r.get_message(self._paths, id)))

    def cancel(self, id: str) -> Message:
        """Stops a message that hasn't reached a phone yet."""
        return cast(Message, self._call(r.cancel_message(self._paths, id)))

    def list(
        self,
        *,
        status: Optional[MessageStatus] = None,
        type: Optional[MessageType] = None,
        tag: Optional[str] = None,
        to: Optional[str] = None,
        batch_id: Optional[str] = None,
        since: r.When = None,
        until: r.When = None,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> MessagePage:
        """One page, newest first; pass ``next_cursor`` back as ``cursor`` for the next."""
        req = r.list_messages(self._paths, status=status, type=type, tag=tag, to=to, batch_id=batch_id, until=until, cursor=cursor, limit=limit, **{"from": since})
        return cast(MessagePage, self._call(req))

    def list_all(self, **filters: Any) -> Iterator[Message]:
        """Every matching message, newest first, fetching pages as you go."""
        cursor: Optional[str] = None
        while True:
            page = self.list(**filters, cursor=cursor)
            yield from page["data"]
            cursor = page.get("next_cursor")
            if not cursor:
                return


class OneTimeCodes:
    def __init__(self, call: Any, paths: r.Paths) -> None:
        self._call, self._paths = call, paths

    def send(self, to: str, *, length: Optional[int] = None, ttl: Optional[int] = None, body: Optional[str] = None, template: Optional[str] = None, sim: Optional[int] = None) -> Otp:
        """Texts a fresh code to ``to``. Keep the returned ``id`` for verify()."""
        return cast(Otp, self._call(r.send_otp(self._paths, to=to, length=length, ttl=ttl, body=body, template=template, sim=sim)))

    def verify(self, id: str, code: str) -> OtpVerification:
        """``valid`` is False with a ``reason`` when the code is wrong, expired or used."""
        return cast(OtpVerification, self._call(r.verify_otp(self._paths, id, code)))


class Schedules:
    def __init__(self, call: Any, paths: r.Paths) -> None:
        self._call, self._paths = call, paths

    def create(
        self,
        cron: str,
        *,
        name: Optional[str] = None,
        timezone: Optional[str] = None,
        to: Optional[str] = None,
        messages: Optional[List[ScheduleRecipient]] = None,
        group_ids: Optional[List[str]] = None,
        body: Optional[str] = None,
        template: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        type: Optional[MessageType] = None,
        tags: Optional[Sequence[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        sim: Optional[int] = None,
        rate: Optional[int] = None,
        ends_at: r.When = None,
        max_runs: Optional[int] = None,
        enabled: Optional[bool] = None,
    ) -> Schedule:
        """A message (or batch) sent again and again on a cron schedule."""
        req = r.create_schedule(self._paths, cron=cron, name=name, timezone=timezone, to=to, messages=messages, group_ids=group_ids, body=body, template=template, variables=variables, type=type, tags=tags, metadata=metadata, sim=sim, rate=rate, ends_at=ends_at, max_runs=max_runs, enabled=enabled)
        return cast(Schedule, self._call(req))

    def list(self) -> SchedulePage:
        return cast(SchedulePage, self._call(r.list_schedules(self._paths)))

    def get(self, id: str) -> Schedule:
        """One schedule, with its recent runs."""
        return cast(Schedule, self._call(r.get_schedule(self._paths, id)))

    def update(self, id: str, **changes: Any) -> Schedule:
        """Changes name, cron, timezone, body, template, type, ends_at, max_runs or enabled; None clears."""
        return cast(Schedule, self._call(r.update_schedule(self._paths, id, **changes)))

    def delete(self, id: str) -> None:
        self._call(r.delete_schedule(self._paths, id))


class SMSWire:
    """Client for one project. Settings default to SMSWIRE_KEY, SMSWIRE_PROJECT, SMSWIRE_URL, SMSWIRE_WEBHOOK_SECRET."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        project: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        max_retries: int = 2,
        max_retry_wait: float = 60,
        timeout: float = 30.0,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self._settings, paths = _settings(api_key, project, base_url, max_retries, max_retry_wait, timeout)
        self._own_client = http_client is None
        self._client = http_client or httpx.Client()
        self.messages = Messages(self._send, paths)
        self.otp = OneTimeCodes(self._send, paths)
        self.schedules = Schedules(self._send, paths)
        self.webhooks = _Webhooks(webhook_secret or os.environ.get("SMSWIRE_WEBHOOK_SECRET"))

    def _send(self, req: Request) -> Any:
        return send(self._client, self._settings, req)

    def close(self) -> None:
        if self._own_client:
            self._client.close()

    def __enter__(self) -> "SMSWire":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


# ── Async ────────────────────────────────────────────────────────────────────


class AsyncMessages:
    def __init__(self, call: Any, paths: r.Paths) -> None:
        self._call, self._paths = call, paths

    async def send(
        self,
        to: str,
        body: Optional[str] = None,
        *,
        template: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        sim: Optional[int] = None,
        type: Optional[MessageType] = None,
        tags: Optional[Sequence[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        send_at: r.When = None,
        idempotency_key: Optional[str] = None,
    ) -> Message:
        req = r.send_message(self._paths, idempotency_key, to=to, body=body, template=template, variables=variables, sim=sim, type=type, tags=tags, metadata=metadata, send_at=send_at)
        return cast(Message, await self._call(req))

    async def send_bulk(
        self,
        messages: Sequence[BulkItem],
        *,
        name: Optional[str] = None,
        body: Optional[str] = None,
        template: Optional[str] = None,
        rate: Optional[int] = None,
        sim: Optional[int] = None,
        type: Optional[MessageType] = None,
        tags: Optional[Sequence[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        send_at: r.When = None,
    ) -> BulkResult:
        req = r.send_bulk(self._paths, messages=messages, name=name, body=body, template=template, rate=rate, sim=sim, type=type, tags=tags, metadata=metadata, send_at=send_at)
        return cast(BulkResult, await self._call(req))

    async def get(self, id: str) -> Message:
        return cast(Message, await self._call(r.get_message(self._paths, id)))

    async def cancel(self, id: str) -> Message:
        return cast(Message, await self._call(r.cancel_message(self._paths, id)))

    async def list(
        self,
        *,
        status: Optional[MessageStatus] = None,
        type: Optional[MessageType] = None,
        tag: Optional[str] = None,
        to: Optional[str] = None,
        batch_id: Optional[str] = None,
        since: r.When = None,
        until: r.When = None,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> MessagePage:
        req = r.list_messages(self._paths, status=status, type=type, tag=tag, to=to, batch_id=batch_id, until=until, cursor=cursor, limit=limit, **{"from": since})
        return cast(MessagePage, await self._call(req))

    async def list_all(self, **filters: Any) -> AsyncIterator[Message]:
        cursor: Optional[str] = None
        while True:
            page = await self.list(**filters, cursor=cursor)
            for message in page["data"]:
                yield message
            cursor = page.get("next_cursor")
            if not cursor:
                return


class AsyncOneTimeCodes:
    def __init__(self, call: Any, paths: r.Paths) -> None:
        self._call, self._paths = call, paths

    async def send(self, to: str, *, length: Optional[int] = None, ttl: Optional[int] = None, body: Optional[str] = None, template: Optional[str] = None, sim: Optional[int] = None) -> Otp:
        return cast(Otp, await self._call(r.send_otp(self._paths, to=to, length=length, ttl=ttl, body=body, template=template, sim=sim)))

    async def verify(self, id: str, code: str) -> OtpVerification:
        return cast(OtpVerification, await self._call(r.verify_otp(self._paths, id, code)))


class AsyncSchedules:
    def __init__(self, call: Any, paths: r.Paths) -> None:
        self._call, self._paths = call, paths

    async def create(self, cron: str, **fields: Any) -> Schedule:
        """Same arguments as SMSWire.schedules.create."""
        return cast(Schedule, await self._call(r.create_schedule(self._paths, cron=cron, **fields)))

    async def list(self) -> SchedulePage:
        return cast(SchedulePage, await self._call(r.list_schedules(self._paths)))

    async def get(self, id: str) -> Schedule:
        return cast(Schedule, await self._call(r.get_schedule(self._paths, id)))

    async def update(self, id: str, **changes: Any) -> Schedule:
        return cast(Schedule, await self._call(r.update_schedule(self._paths, id, **changes)))

    async def delete(self, id: str) -> None:
        await self._call(r.delete_schedule(self._paths, id))


class AsyncSMSWire:
    """Async client for one project; same settings as SMSWire."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        project: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        max_retries: int = 2,
        max_retry_wait: float = 60,
        timeout: float = 30.0,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._settings, paths = _settings(api_key, project, base_url, max_retries, max_retry_wait, timeout)
        self._own_client = http_client is None
        self._client = http_client or httpx.AsyncClient()
        self.messages = AsyncMessages(self._send, paths)
        self.otp = AsyncOneTimeCodes(self._send, paths)
        self.schedules = AsyncSchedules(self._send, paths)
        self.webhooks = _Webhooks(webhook_secret or os.environ.get("SMSWIRE_WEBHOOK_SECRET"))

    async def _send(self, req: Request) -> Any:
        return await send_async(self._client, self._settings, req)

    async def aclose(self) -> None:
        if self._own_client:
            await self._client.aclose()

    async def __aenter__(self) -> "AsyncSMSWire":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()
