"""The public API's calls as Requests; the sync and async clients only differ in how they send them."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Sequence, Union
from urllib.parse import quote

from ._http import Request

When = Union[str, datetime, None]


def _iso(value: When) -> Optional[str]:
    return value.isoformat() if isinstance(value, datetime) else value


def _clean(**fields: Any) -> Dict[str, Any]:
    """The JSON body: None means "not given", so it is left out."""
    return {k: (_iso(v) if isinstance(v, datetime) else v) for k, v in fields.items() if v is not None}


class Paths:
    def __init__(self, project: str) -> None:
        p = f"/v1/p/{quote(project, safe='')}"
        self.messages = f"{p}/messages"
        self.otp = f"{p}/otp"
        self.schedules = f"{p}/schedules"

    @staticmethod
    def one(base: str, id: str) -> str:
        return f"{base}/{quote(id, safe='')}"


def send_message(paths: Paths, idempotency_key: Optional[str], **fields: Any) -> Request:
    return Request(
        "POST",
        paths.messages,
        body=_clean(**fields),
        headers={"Idempotency-Key": idempotency_key or str(uuid.uuid4())},
        idempotent=True,
    )


def send_bulk(paths: Paths, **fields: Any) -> Request:
    messages: Sequence[Any] = fields.pop("messages")
    return Request("POST", f"{paths.messages}/bulk", body={**_clean(**fields), "messages": [_clean(**m) for m in messages]}, idempotent=False)


def get_message(paths: Paths, id: str) -> Request:
    return Request("GET", Paths.one(paths.messages, id))


def cancel_message(paths: Paths, id: str) -> Request:
    return Request("DELETE", Paths.one(paths.messages, id))


def list_messages(paths: Paths, **query: Any) -> Request:
    return Request("GET", paths.messages, query=query)


def send_otp(paths: Paths, **fields: Any) -> Request:
    return Request("POST", paths.otp, body=_clean(**fields), idempotent=False)


def verify_otp(paths: Paths, id: str, code: str) -> Request:
    return Request("POST", f"{paths.otp}/verify", body={"id": id, "code": code}, idempotent=False)


def create_schedule(paths: Paths, **fields: Any) -> Request:
    return Request("POST", paths.schedules, body=_clean(**fields), idempotent=False)


def list_schedules(paths: Paths) -> Request:
    return Request("GET", paths.schedules)


def get_schedule(paths: Paths, id: str) -> Request:
    return Request("GET", Paths.one(paths.schedules, id))


def update_schedule(paths: Paths, id: str, **changes: Any) -> Request:
    # Only what's passed changes; an explicit None clears the field.
    return Request("PATCH", Paths.one(paths.schedules, id), body={k: _iso(v) for k, v in changes.items()})


def delete_schedule(paths: Paths, id: str) -> Request:
    return Request("DELETE", Paths.one(paths.schedules, id))
