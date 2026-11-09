from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List

import httpx
import pytest

SDKS = Path(__file__).resolve().parents[2]


def fixture(name: str) -> Dict[str, Any]:
    return json.loads((SDKS / "fixtures" / name).read_text("utf-8"))


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch: pytest.MonkeyPatch) -> None:
    """Retries don't really sleep."""
    import asyncio

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("smswire._http.time.sleep", lambda _: None)
    monkeypatch.setattr("smswire._http.asyncio.sleep", no_sleep)


class Recorder:
    """An httpx transport that answers from a script and remembers each request."""

    def __init__(self, *answers: Callable[[httpx.Request], httpx.Response]) -> None:
        self.answers = answers
        self.requests: List[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.answers[min(len(self.requests), len(self.answers)) - 1](request)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self))

    def async_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self))


def ok(body: Any, status: int = 200) -> Callable[[httpx.Request], httpx.Response]:
    return lambda _: httpx.Response(status, json=body)
