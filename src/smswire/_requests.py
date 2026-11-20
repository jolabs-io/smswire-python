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
    """The JSON body: None means "not given", so it is left out. ``from_`` is sent as ``from``."""
    return {k.rstrip("_"): (_iso(v) if isinstance(v, datetime) else v) for k, v in fields.items() if v is not None}


class Paths:
    def __init__(self, project: str) -> None:
        p = f"/v1/p/{quote(project, safe='')}"
        self.messages = f"{p}/messages"
        self.otp = f"{p}/otp"
        self.schedules = f"{p}/schedules"
        self.groups = f"{p}/groups"
        self.campaigns = f"{p}/campaigns"

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
    messages: Sequence[Any] = fields.pop("messages") or ()
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


def create_group(paths: Paths, **fields: Any) -> Request:
    return Request("POST", paths.groups, body=_clean(**fields), idempotent=False)


def list_groups(paths: Paths) -> Request:
    return Request("GET", paths.groups)


def get_group(paths: Paths, id: str) -> Request:
    return Request("GET", Paths.one(paths.groups, id))


def update_group(paths: Paths, id: str, **changes: Any) -> Request:
    # Only what's passed changes; keywords=[] turns joining by text off, join_reply=None clears it.
    return Request("PATCH", Paths.one(paths.groups, id), body=dict(changes))


def delete_group(paths: Paths, id: str) -> Request:
    return Request("DELETE", Paths.one(paths.groups, id))


def create_campaign(paths: Paths, **fields: Any) -> Request:
    return Request("POST", paths.campaigns, body=_clean(**fields), idempotent=False)


def list_campaigns(paths: Paths) -> Request:
    return Request("GET", paths.campaigns)


def get_campaign(paths: Paths, id: str) -> Request:
    return Request("GET", Paths.one(paths.campaigns, id))


def update_campaign(paths: Paths, id: str, **changes: Any) -> Request:
    # Only what's passed changes; the rest of the campaign stays as it is.
    return Request("PATCH", Paths.one(paths.campaigns, id), body=dict(changes))


def delete_campaign(paths: Paths, id: str) -> Request:
    return Request("DELETE", Paths.one(paths.campaigns, id))


def preview_campaign(paths: Paths, id: str) -> Request:
    return Request("GET", f"{Paths.one(paths.campaigns, id)}/preview")


def campaign_results(paths: Paths, id: str) -> Request:
    return Request("GET", f"{Paths.one(paths.campaigns, id)}/results")


def send_campaign(paths: Paths, id: str) -> Request:
    return Request("POST", f"{Paths.one(paths.campaigns, id)}/send", idempotent=False)


def control_campaign(paths: Paths, id: str, status: str) -> Request:
    return Request("POST", f"{Paths.one(paths.campaigns, id)}/control", body={"status": status})


def cancel_campaign(paths: Paths, id: str) -> Request:
    return Request("POST", f"{Paths.one(paths.campaigns, id)}/cancel")


def list_group_members(paths: Paths, id: str, **query: Any) -> Request:
    return Request("GET", f"{Paths.one(paths.groups, id)}/members", query={k: v for k, v in query.items() if v is not None})


def add_group_members(paths: Paths, id: str, members: Sequence[Any]) -> Request:
    return Request("POST", f"{Paths.one(paths.groups, id)}/members", body={"members": [_clean(**m) for m in members]})


def remove_group_member(paths: Paths, id: str, phone: str) -> Request:
    return Request("DELETE", f"{Paths.one(paths.groups, id)}/members/{quote(phone, safe='')}")

