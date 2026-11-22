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


CampaignStatus = Literal["draft", "scheduled", "sending", "paused", "done", "cancelled"]


class CampaignAudience(TypedDict, total=False):
    group_ids: List[str]
    numbers: List[str]
    messages: List[ScheduleRecipient]


class CampaignExclude(TypedDict, total=False):
    group_ids: List[str]
    recent_days: Optional[int]
    no_reply_to_campaign_id: Optional[str]


class CampaignQuietHours(TypedDict):
    start: str
    end: str
    timezone: str


class _CampaignRequired(TypedDict):
    id: str
    name: str
    status: CampaignStatus
    body: str
    type: MessageType
    tags: List[str]
    audience: CampaignAudience
    exclude: CampaignExclude
    rate: int
    consent: bool
    total: int
    runs: int
    created_at: str


class Campaign(_CampaignRequired, total=False):
    sim: Optional[int]
    quiet_hours: Optional[CampaignQuietHours]
    stop_footer: Optional[str]
    next_run_at: Optional[str]
    last_run_at: Optional[str]
    cron: Optional[str]
    timezone: Optional[str]


class CampaignList(TypedDict):
    data: List[Campaign]


class CampaignRun(TypedDict):
    batch_id: str
    total: int
    delivered: int
    failed: int
    created_at: str


class _CampaignResultsRequired(TypedDict):
    delivered: int
    failed: int
    awaiting: int
    waiting: int
    parts: int
    replies: int
    opt_outs: int
    runs: List[CampaignRun]


class CampaignResults(_CampaignResultsRequired, total=False):
    delivery_rate: Optional[float]


class CampaignExcluded(TypedDict):
    group: int
    recent: int
    replied: int
    duplicate: int


class CampaignPreview(TypedDict):
    recipients: int
    excluded: CampaignExcluded


class _CampaignSendRequired(TypedDict):
    status: Literal["queued", "scheduled"]
    accepted: int
    rejected: List[RejectedItem]


class CampaignSendResult(_CampaignSendRequired, total=False):
    batch_id: Optional[str]


GroupJoinSource = Literal["manual", "import", "keyword", "api"]


class _GroupRequired(TypedDict):
    id: str
    name: str
    size: int
    keywords: List[str]
    created_at: str


class Group(_GroupRequired, total=False):
    join_reply: Optional[str]


class GroupList(TypedDict):
    data: List[Group]


class _GroupMemberRequired(TypedDict):
    contact_id: str
    phone: str
    fields: Dict[str, str]
    joined_at: str
    source: GroupJoinSource
    opted_out: bool


class GroupMember(_GroupMemberRequired, total=False):
    name: Optional[str]


class _GroupMemberPageRequired(TypedDict):
    data: List[GroupMember]


class GroupMemberPage(_GroupMemberPageRequired, total=False):
    next_cursor: Optional[str]


class InvalidMember(TypedDict):
    index: int
    phone: str


class AddMembersResult(TypedDict):
    added: int
    already: int
    invalid: List[InvalidMember]


class GroupMemberInput(TypedDict, total=False):
    phone: str
    name: Optional[str]
    fields: Optional[Dict[str, str]]
    language: Optional[str]

