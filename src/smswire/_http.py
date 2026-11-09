from __future__ import annotations

import asyncio
import email.utils
import json
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import httpx

from .errors import SMSWireError


@dataclass
class Request:
    method: str
    path: str
    query: Optional[Dict[str, Any]] = None
    body: Any = None
    headers: Dict[str, str] = field(default_factory=dict)
    #: Safe to repeat after a 5xx or a dropped connection (GET, PATCH, DELETE, or a POST with an Idempotency-Key).
    idempotent: bool = True


@dataclass
class Settings:
    api_key: str
    base_url: str
    max_retries: int
    max_retry_wait: float
    timeout: float
    user_agent: str


def _retry_after(header: Optional[str]) -> Optional[float]:
    if not header:
        return None
    try:
        return max(0.0, float(header))
    except ValueError:
        pass
    try:
        at = email.utils.parsedate_to_datetime(header)
    except (TypeError, ValueError):
        return None
    return max(0.0, at.timestamp() - time.time())


def error_from(res: httpx.Response) -> SMSWireError:
    code, message = "http_error", f"HTTP {res.status_code}"
    try:
        body = res.json()
        if isinstance(body, dict) and isinstance(body.get("error"), str) and isinstance(body.get("message"), str):
            code, message = body["error"], body["message"]
    except (ValueError, json.JSONDecodeError):
        pass  # Not JSON (a proxy's error page): keep the generic code.
    return SMSWireError(res.status_code, code, message, _retry_after(res.headers.get("retry-after")))


def retry_delay(err: SMSWireError, req: Request, attempt: int, settings: Settings) -> Optional[float]:
    """Seconds to wait before trying [err]'s request again, or None to give up."""
    if attempt >= settings.max_retries:
        return None
    retryable = err.status == 429 or (req.idempotent and (err.status is None or err.status >= 500))
    if not retryable:
        return None
    if err.retry_after is not None:
        return err.retry_after if err.retry_after <= settings.max_retry_wait else None
    return float(min(8.0, 0.5 * 2**attempt) * (1 + random.random() * 0.25))


def _build(settings: Settings, req: Request) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {settings.api_key}",
        "Accept": "application/json",
        "User-Agent": settings.user_agent,
        **req.headers,
    }
    params = {k: _query_value(v) for k, v in (req.query or {}).items() if v is not None}
    kwargs: Dict[str, Any] = {"method": req.method, "url": settings.base_url.rstrip("/") + req.path, "headers": headers, "params": params}
    if req.body is not None:
        kwargs["json"] = req.body
    return kwargs


def _query_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if hasattr(v, "isoformat"):
        return str(v.isoformat())
    return str(v)


def _network_error(e: Exception, settings: Settings, url: str) -> SMSWireError:
    if isinstance(e, httpx.TimeoutException):
        return SMSWireError(None, "timeout", f"No answer within {settings.timeout} s")
    return SMSWireError(None, "network_error", f"Could not reach {url}: {e}")


def _result(res: httpx.Response) -> Any:
    return res.json() if res.content else None


def send(client: httpx.Client, settings: Settings, req: Request) -> Any:
    kwargs = _build(settings, req)
    attempt = 0
    while True:
        try:
            res = client.request(**kwargs, timeout=settings.timeout)
        except httpx.TransportError as e:
            err = _network_error(e, settings, settings.base_url)
        else:
            if res.is_success:
                return _result(res)
            err = error_from(res)
        wait = retry_delay(err, req, attempt, settings)
        if wait is None:
            raise err
        time.sleep(wait)
        attempt += 1


async def send_async(client: httpx.AsyncClient, settings: Settings, req: Request) -> Any:
    kwargs = _build(settings, req)
    attempt = 0
    while True:
        try:
            res = await client.request(**kwargs, timeout=settings.timeout)
        except httpx.TransportError as e:
            err = _network_error(e, settings, settings.base_url)
        else:
            if res.is_success:
                return _result(res)
            err = error_from(res)
        wait = retry_delay(err, req, attempt, settings)
        if wait is None:
            raise err
        await asyncio.sleep(wait)
        attempt += 1
