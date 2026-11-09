"""Shapes the API returns, as TypedDicts (plain dicts at runtime). Mirrors sdks/openapi.json."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict

MessageType = Literal["otp", "transactional", "notification", "marketing"]
MessageStatus = Literal["queued", "sending", "sent", "delivered", "failed", "cancelled"]
OtpFailure = Literal["invalid", "expired", "too_many_attempts", "already_used"]


class _MessageRequired(TypedDict):
    id: str
    to: str
    status: MessageStatus
    segments: int
    type: MessageType
    tags: List[str]
    received_at: str


class Message(_MessageRequired, total=False):
    error: Optional[str]
    metadata: Optional[Dict[str, Any]]
    batch_id: Optional[str]
    scheduled_at: Optional[str]
    sent_at: Optional[str]
    delivered_at: Optional[str]
    redacted: bool


class _MessagePageRequired(TypedDict):
    data: List[Message]


class MessagePage(_MessagePageRequired, total=False):
    next_cursor: Optional[str]


class RejectedItem(TypedDict):
    index: int
    to: str
    reason: str


class BulkResult(TypedDict):
    batch_id: str
    accepted: int
    rejected: List[RejectedItem]


class Otp(TypedDict):
    id: str
    to: str
    expires_at: str
    message_id: str


class _OtpVerificationRequired(TypedDict):
    valid: bool


class OtpVerification(_OtpVerificationRequired, total=False):
    reason: Optional[OtpFailure]


class _ScheduleRunRequired(TypedDict):
    at: str
    status: Literal["sent", "failed", "skipped"]
    accepted: int
    rejected: int


class ScheduleRun(_ScheduleRunRequired, total=False):
    message_id: Optional[str]
    batch_id: Optional[str]
    error: Optional[str]


class _ScheduleRecipients(TypedDict):
    numbers: int
    group_ids: List[str]


class _ScheduleRequired(TypedDict):
    id: str
    name: str
    cron: str
    timezone: str
    enabled: bool
    tags: List[str]
    recipients: _ScheduleRecipients
    run_count: int
    created_at: str


class Schedule(_ScheduleRequired, total=False):
    body: Optional[str]
    template_id: Optional[str]
    type: Optional[MessageType]
    next_run_at: Optional[str]
    last_run_at: Optional[str]
    ends_at: Optional[str]
    max_runs: Optional[int]
    last_run: Optional[ScheduleRun]
    runs: Optional[List[ScheduleRun]]


class SchedulePage(TypedDict):
    data: List[Schedule]


class BulkItem(TypedDict, total=False):
    to: str
    body: Optional[str]
    variables: Optional[Dict[str, Any]]
    type: Optional[MessageType]
    tags: Optional[List[str]]
    metadata: Optional[Dict[str, Any]]


class ScheduleRecipient(TypedDict, total=False):
    to: str
    variables: Optional[Dict[str, Any]]
