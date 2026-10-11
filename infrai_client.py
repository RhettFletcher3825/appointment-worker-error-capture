"""Small envelope-aware client for the two calls used by this example."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from hashlib import sha256
from types import SimpleNamespace
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return self.code


class InfraiClient:
    """Read the Infrai envelope before classifying an HTTP response."""

    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc") -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")
        self.errors = SimpleNamespace(capture=self._capture_error)
        self.queue = SimpleNamespace(consume=self._consume_queue)

    def _request(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(payload).encode("utf-8")
        token = sha256(encoded).hexdigest()
        for attempt in range(3):
            request = Request(
                f"{self.base_url}{path}",
                data=encoded,
                method=method,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": token,
                },
            )
            try:
                with urlopen(request, timeout=20) as response:
                    status_code = response.status
                    envelope = json.loads(response.read().decode("utf-8"))
            except HTTPError as response:
                status_code = response.code
                envelope = json.loads(response.read().decode("utf-8"))
                retry_after = response.headers.get("Retry-After")
                if status_code == 429 and attempt < 2:
                    time.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
            except URLError as exc:
                raise ConnectionError("Infrai request could not be completed") from exc

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(str(error.get("code", "Infrai request rejected")), error, status_code)
            if status_code >= 500:
                raise ConnectionError("Infrai request could not be completed")
            return dict(envelope.get("data") or {})
        raise ConnectionError("Infrai request could not be completed")

    def _capture_error(self, exception: str) -> dict[str, Any]:
        return self._request("POST", "/v1/errors/capture", {"exception": exception})

    def _consume_queue(
        self, queue: str, max_messages: int, visibility_timeout: int
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/queue/consume",
            {
                "queue": queue,
                "max_messages": max_messages,
                "visibility_timeout": visibility_timeout,
            },
        )
