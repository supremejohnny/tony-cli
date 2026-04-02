from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Iterator, Protocol

import httpx

from .models import ContentBlock, TextBlock, ToolUseBlock, TokenUsage

# ---------------------------------------------------------------------------
# Request / response structures
# ---------------------------------------------------------------------------

@dataclass
class MessageRequest:
    model: str
    max_tokens: int
    messages: list[dict]           # already-formatted API dicts
    system: list[dict] | None = None
    tools: list[dict] | None = None
    stream: bool = False


@dataclass
class MessageResponse:
    id: str
    content: list[ContentBlock]
    stop_reason: str
    usage: TokenUsage


# ---------------------------------------------------------------------------
# Stream events
# ---------------------------------------------------------------------------

@dataclass
class StreamEvent:
    type: str
    data: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

class ApiClient(Protocol):
    def send_message(self, req: MessageRequest) -> MessageResponse: ...
    def stream_message(self, req: MessageRequest) -> Iterator[StreamEvent]: ...


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RETRY_STATUSES = {408, 429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


def _parse_content(raw: list[dict]) -> list[ContentBlock]:
    blocks: list[ContentBlock] = []
    for item in raw:
        t = item.get("type")
        if t == "text":
            blocks.append(TextBlock(text=item.get("text", "")))
        elif t == "tool_use":
            blocks.append(ToolUseBlock(
                id=item.get("id", ""),
                name=item.get("name", ""),
                input=item.get("input", {}),
            ))
    return blocks


def _parse_usage(raw: dict) -> TokenUsage:
    return TokenUsage(
        input_tokens=raw.get("input_tokens", 0),
        output_tokens=raw.get("output_tokens", 0),
        cache_read_tokens=raw.get("cache_read_input_tokens", 0),
    )


# ---------------------------------------------------------------------------
# AnthropicClient
# ---------------------------------------------------------------------------

class AnthropicClient:
    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-6") -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY is not set")
        self.model = model
        self._client = httpx.Client(timeout=120.0)

    # ------------------------------------------------------------------
    def _headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

    def _build_body(self, req: MessageRequest) -> dict:
        body: dict = {
            "model": req.model,
            "max_tokens": req.max_tokens,
            "messages": req.messages,
        }
        if req.system:
            body["system"] = req.system
        if req.tools:
            body["tools"] = req.tools
        if req.stream:
            body["stream"] = True
        return body

    # ------------------------------------------------------------------
    def _request_with_retry(self, body: dict, stream: bool = False) -> httpx.Response:
        delay = _BASE_DELAY
        last_exc: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                resp = self._client.post(
                    ANTHROPIC_API_URL,
                    headers=self._headers(),
                    json=body,
                    # For streaming we need to use stream context, handled separately
                )
                if resp.status_code not in _RETRY_STATUSES:
                    resp.raise_for_status()
                    return resp
                # retryable HTTP status
                if attempt < _MAX_ATTEMPTS - 1:
                    time.sleep(delay)
                    delay *= 2
                last_exc = httpx.HTTPStatusError(
                    f"HTTP {resp.status_code}", request=resp.request, response=resp
                )
            except httpx.TimeoutException as exc:
                last_exc = exc
                if attempt < _MAX_ATTEMPTS - 1:
                    time.sleep(delay)
                    delay *= 2
        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    def send_message(self, req: MessageRequest) -> MessageResponse:
        body = self._build_body(req)
        resp = self._request_with_retry(body)
        data = resp.json()
        return MessageResponse(
            id=data.get("id", ""),
            content=_parse_content(data.get("content", [])),
            stop_reason=data.get("stop_reason", "end_turn"),
            usage=_parse_usage(data.get("usage", {})),
        )

    # ------------------------------------------------------------------
    def stream_message(self, req: MessageRequest) -> Iterator[StreamEvent]:
        """Yields StreamEvents from the SSE stream."""
        body = self._build_body(req)
        body["stream"] = True

        delay = _BASE_DELAY
        last_exc: Exception | None = None

        for attempt in range(_MAX_ATTEMPTS):
            try:
                with self._client.stream(
                    "POST",
                    ANTHROPIC_API_URL,
                    headers=self._headers(),
                    json=body,
                    timeout=120.0,
                ) as resp:
                    if resp.status_code in _RETRY_STATUSES:
                        if attempt < _MAX_ATTEMPTS - 1:
                            time.sleep(delay)
                            delay *= 2
                            last_exc = httpx.HTTPStatusError(
                                f"HTTP {resp.status_code}",
                                request=resp.request,
                                response=resp,
                            )
                            continue
                        resp.raise_for_status()

                    resp.raise_for_status()
                    yield from _parse_sse(resp)
                    return
            except httpx.TimeoutException as exc:
                last_exc = exc
                if attempt < _MAX_ATTEMPTS - 1:
                    time.sleep(delay)
                    delay *= 2

        raise last_exc  # type: ignore[misc]

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "AnthropicClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


# ---------------------------------------------------------------------------
# SSE parser
# ---------------------------------------------------------------------------

def _parse_sse(resp: httpx.Response) -> Iterator[StreamEvent]:
    """Iterate over SSE lines and yield typed StreamEvents."""
    event_type: str = ""
    data_lines: list[str] = []

    for line in resp.iter_lines():
        line = line.rstrip("\r")
        if line.startswith("event:"):
            event_type = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:"):].strip())
        elif line == "":
            # Dispatch event
            if event_type and data_lines:
                raw_data = "\n".join(data_lines)
                try:
                    parsed = json.loads(raw_data)
                except json.JSONDecodeError:
                    parsed = {"raw": raw_data}
                yield StreamEvent(type=event_type, data=parsed)
            event_type = ""
            data_lines = []
