from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from .errors import SignatureError

#: The header the signature arrives in.
SIGNATURE_HEADER = "X-SMSWire-Signature"

_HEX = re.compile(r"^[0-9a-fA-F]{64}$")


def _parse(header: str) -> Optional[Tuple[int, List[str]]]:
    t: Optional[int] = None
    signatures: List[str] = []
    for part in header.split(","):
        key, sep, value = part.partition("=")
        if not sep:
            continue
        key, value = key.strip(), value.strip()
        if key == "t" and value.isdigit():
            t = int(value)
        elif key == "v1" and _HEX.match(value):
            signatures.append(value.lower())
    if t is None or not signatures:
        return None
    return t, signatures


def verify_webhook(
    raw_body: Union[bytes, str],
    signature: Optional[str],
    secret: str,
    *,
    tolerance: int = 300,
    now: Optional[float] = None,
) -> Dict[str, Any]:
    """Checks a webhook's X-SMSWire-Signature against the **raw** request body and returns the event.

    Raises SignatureError when the signature is missing, wrong, or more than ``tolerance``
    seconds off. Pass the body exactly as received, not re-serialised JSON.
    """
    if not secret:
        raise SignatureError("No webhook signing secret given")
    parsed = _parse(signature or "")
    if parsed is None:
        raise SignatureError(f"Missing or malformed {SIGNATURE_HEADER} header")
    t, signatures = parsed
    current = time.time() if now is None else now
    if abs(current - t) > tolerance:
        raise SignatureError("Signature timestamp is outside the tolerance")
    body = raw_body.encode("utf-8") if isinstance(raw_body, str) else raw_body
    expected = hmac.new(secret.encode("utf-8"), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(s, expected) for s in signatures):
        raise SignatureError("Signature does not match")
    return cast(Dict[str, Any], json.loads(body))
