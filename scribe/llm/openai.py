"""
OpenAI-compatible LLM driver (OpenAI, DeepSeek, etc.).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Optional

import httpx

from scribe.llm.base import LlmDriver
from scribe.types import (
    ChatRequest,
    ChatResponse,
    FunctionCall,
    Message,
    StreamChunk,
    ToolCall,
    ToolDefinition,
    Usage,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_MS = 1000


def _build_messages(messages: list[Message]) -> list[dict]:
    """Convert Message list to OpenAI-compatible format."""
    result = []
    for m in messages:
        msg = {"role": m.role.value, "content": m.content}
        if m.name:
            msg["name"] = m.name
        if m.tool_call_id:
            msg["tool_call_id"] = m.tool_call_id
        if m.tool_calls:
            calls = []
            for tc in m.tool_calls:
                calls.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                })
            msg["tool_calls"] = calls
        result.append(msg)
    return result


def _build_body(req: ChatRequest, model: str) -> dict:
    """Build request body for OpenAI-compatible API."""
    body = {
        "model": model,
        "messages": _build_messages(req.messages),
        "temperature": req.temperature if req.temperature is not None else 0.7,
        "max_tokens": req.max_tokens if req.max_tokens is not None else 4096,
        "stream": False,
    }
    if req.tools:
        body["tools"] = [
            {"type": d.tool_type, "function": {
                "name": d.function.name,
                "description": d.function.description,
                "parameters": d.function.parameters,
            }}
            for d in req.tools
        ]
    return body


def _parse_response(resp_json: dict) -> ChatResponse:
    """Parse OpenAI-compatible response."""
    if "error" in resp_json:
        msg = resp_json["error"].get("message", "Unknown API error")
        code = resp_json["error"].get("code", "unknown")
        raise Exception(f"API error [{code}]: {msg}")

    choices = resp_json.get("choices", [])
    if not choices:
        raise Exception("No choices in response")

    message = choices[0].get("message", {})
    raw_content = message.get("content", "")
    content = raw_content if raw_content else None

    tool_calls = None
    raw_calls = message.get("tool_calls")
    if raw_calls:
        calls = []
        for tc in raw_calls:
            if tc.get("function"):
                calls.append(ToolCall(
                    id=tc["id"],
                    call_type=tc.get("type", "function"),
                    function=FunctionCall(
                        name=tc["function"]["name"],
                        arguments=tc["function"]["arguments"],
                    ),
                ))
        if calls:
            tool_calls = calls

    usage = Usage(
        prompt_tokens=resp_json.get("usage", {}).get("prompt_tokens", 0),
        completion_tokens=resp_json.get("usage", {}).get("completion_tokens", 0),
    )

    return ChatResponse(content=content, tool_calls=tool_calls, usage=usage)


async def _stream_chat_openai(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    req: ChatRequest,
    model: str,
    queue: asyncio.Queue[str],
) -> None:
    """SSE streaming for OpenAI-compatible APIs."""
    url = f"{base_url}/chat/completions"
    body = _build_body(req, model)
    body["stream"] = True

    headers = {"Authorization": f"Bearer {api_key}"}

    async with client.stream("POST", url, json=body, headers=headers, timeout=60.0) as resp:
        if resp.status_code != 200:
            text = await resp.text()
            raise Exception(f"HTTP {resp.status_code}: {text}")

        # Track parallel tool calls by index
        tool_accum: dict[int, tuple[str, str, str]] = {}

        async for line in resp.aiter_lines():
            line = line.strip()
            if not line:
                continue

            data = line.removeprefix("data: ")
            if data in ("", "[DONE]"):
                continue

            try:
                json_data = json.loads(data)
            except json.JSONDecodeError:
                continue

            for choice in json_data.get("choices", []):
                delta = choice.get("delta", {})

                # Text delta
                if isinstance(delta.get("content"), str):
                    text = delta["content"]
                    await queue.put(text)

                # Tool call delta
                for tc in delta.get("tool_calls", []):
                    idx = tc.get("index", 0)
                    if idx not in tool_accum:
                        tool_accum[idx] = ("", "", "")
                    entry = tool_accum[idx]
                    id_part = tc.get("id") or ""
                    name_part = tc.get("function", {}).get("name", "")
                    args_part = tc.get("function", {}).get("arguments", "")
                    tool_accum[idx] = (
                        id_part or entry[0],
                        name_part + entry[1],
                        args_part + entry[2],
                    )

        # Send accumulated tool calls
        indices = sorted(tool_accum.keys())
        final_calls = []
        for idx in indices:
            id_val, name, args = tool_accum[idx]
            if name:
                final_calls.append(ToolCall(
                    id=id_val,
                    type="function",
                    function=FunctionCall(name=name, arguments=args),
                ))


async def _chat_with_retry(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    req: ChatRequest,
    model: str,
) -> ChatResponse:
    """Send chat request with retry on 429 / 5xx."""
    url = f"{base_url}/chat/completions"
    body = _build_body(req, model)
    headers = {"Authorization": f"Bearer {api_key}"}
    last_err: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        if attempt > 0:
            delay_ms = RETRY_BASE_MS * (2 ** (attempt - 1))
            logger.warning(
                "OpenAI retry attempt %d/%d after %d ms",
                attempt, MAX_RETRIES, delay_ms
            )
            await asyncio.sleep(delay_ms / 1000.0)

        try:
            resp = await client.post(url, json=body, headers=headers, timeout=30.0)
        except Exception as e:
            last_err = e
            continue

        status = resp.status_code
        if status == 200:
            return _parse_response(resp.json())

        # Retry on 429 and 5xx
        if status in (429,) or (500 <= status < 600):
            try:
                err_json = resp.json()
                msg = err_json.get("error", {}).get("message", "Unknown error")
            except Exception:
                msg = "Unknown error"
            logger.warning("HTTP %d: %s (will retry)", status, msg)
            continue

        # Non-retryable error
        try:
            err_json = resp.json()
            msg = err_json.get("error", {}).get("message", "Unknown error")
        except Exception:
            msg = resp.text()[:200]
        raise Exception(f"HTTP {status}: {msg}")

    raise last_err or Exception("Max retries exceeded")


class OpenAiDriver(LlmDriver):
    """
    OpenAI-compatible LLM driver.

    Reads API key from OPENAI_API_KEY env var by default.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "gpt-4o",
    ):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._base_url = base_url or os.environ.get(
            "OPENAI_BASE_URL", "https://api.openai.com/v1"
        )
        self._model = model
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))

    async def chat(self, req: ChatRequest) -> ChatResponse:
        model = req.model or self._model
        return await _chat_with_retry(
            self._client, self._base_url, self._api_key, req, model
        )

    async def stream_chat(
        self, req: ChatRequest, queue: Optional[asyncio.Queue[str]] = None
    ) -> None:
        model = req.model or self._model
        if queue is None:
            queue = asyncio.Queue()
        await _stream_chat_openai(
            self._client, self._base_url, self._api_key, req, model, queue
        )

    async def close(self) -> None:
        await self._client.aclose()

    def supports_tools(self) -> bool:
        return True

    def supports_vision(self) -> bool:
        return True

    def max_context_tokens(self) -> int:
        return 128_000