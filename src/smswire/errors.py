from __future__ import annotations

from typing import Optional


class SMSWireError(Exception):
    """A request that failed: the API's answer, or a network problem (``status`` is None)."""

    def __init__(self, status: Optional[int], code: str, message: str, retry_after: Optional[float] = None) -> None:
        super().__init__(message)
        #: HTTP status, or None when no answer arrived.
        self.status = status
        #: Stable machine code: ``invalid_request``, ``rate_limited``, ``network_error``, ``timeout``, …
        self.code = code
        self.message = message
        #: Seconds until trying again makes sense (from Retry-After), when the API said.
        self.retry_after = retry_after

    def __repr__(self) -> str:
        return f"SMSWireError(status={self.status!r}, code={self.code!r}, message={self.message!r})"


class SignatureError(Exception):
    """A webhook whose signature is missing, wrong or too old. Answer it with 400."""
