"""
Anthropic (Claude) LLM driver.
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
    Role,
    StreamChunk,
    ToolCall,
    ToolDefinition,
    Usage,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _role_str(role: Role) -> str:
    return {
        Role.SYSTEM: "system",
        Role.USER: "user",
        Role.ASSISTANT: "assistant",
        Role.TOOL: "user",
    }.get(role, "user")


def _build_messages(req: ChatRequest) -> tuple[list[dict], list[dict] | None]:
    """Split into system blocks and conversation messages."""
    system_blocks = []
    conv_messages = []

    for m in req.messages:
        if m.role == Role.SYSTEM:
            system_blocks.append({
                "type": "text",
                "text": m.content,
            })
        else:
            role_str = _role_str(m.role)
            msg: dict = {"role": role_str, "content": m.content}

            if m.tool_calls:
                blocks = []
                if m.content:
                    blocks.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    blocks.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.function.name,
                        "input": json.loads(tc.function.arguments or "{}"),
                    })
                msg["content"] = blocks

            if m.tool_call_id:
                msg["content"] = [{
                    "type": "tool_result",
                    "tool_use_id": m.tool_call_id,
                    "content": m.content,
                }]

            conv_messages.append(msg)

    return system_blocks, conv_messages


def _build_tools(tools: list[ToolDefinition]) -> list[dict]:
    """Build Anthropic tools format."""
    return [
        {
            "name": d.function.name,
            "description": d.function.description,
            "input_schema": d.function.parameters,
        }
        for d in tools
    ]


def _parse_response(resp_json: dict) -> ChatResponse:
    """Parse Anthropic /messages response."""
    if "error" in resp_json:
        msg = resp_json["error"].get("message", "Unknown error")
        raise Exception(f"Anthropic error: {msg}")

    content_blocks = resp_json.get("content", [])
    content = None
    tool_calls: list[ToolCall] = []

    for block in content_blocks:
        btype = block.get("type")
        if btype == "text":
            content = block.get("text")
        elif btype == "tool_use":
            tc = ToolCall(
                id=block.get("id", ""),
                type="function",
                function=FunctionCall(
                    name=block.get("name", ""),
                    arguments=json.dumps(block.get("input", {})),
                ),
            )
            tool_calls.append(tc)

    usage = Usage(
        prompt_tokens=resp_json.get("usage", {}).get("input_tokens", 0),
        completion_tokens=resp_json.get("usage", {}).get("output_tokens", 0),
    )

    return ChatResponse(
        content=content,
        tool_calls=tool_calls if tool_calls else None,
        usage=usage,
    )


async def _stream_anthropic(
    client: httpx.AsyncClient,
    api_key: str,
    system_blocks: list[dict],
    messages: list[dict],
    tools: list[dict] | None,
    model: str,
    max_tokens: int,
    queue: asyncio.Queue[str],
) -> None:
    """SSE streaming for Anthropic /messages."""
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    body: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
        "stream": True,
    }
    if system_blocks:
        body["system"] = system_blocks
    if tools:
        body["tools"] = tools

    async with client.stream("POST", url, json=body, headers=headers, timeout=60.0) as resp:
        if resp.status_code != 200:
            text = await resp.text()
            raise Exception(f"HTTP {resp.status_code}: {text}")

        tool_accum: dict[str, tuple[str, str]] = {}
        active_tool_id: str | None = None

        async for line in resp.aiter_lines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("event: "):
                continue

            data = line.removeprefix("data: ")
            if not data:
                continue

            try:
                json_data = json.loads(data)
            except json.JSONDecodeError:
                continue

            evt_type = json_data.get("type", "")

            if evt_type == "content_block_start":
                cb = json_data.get("content_block", {})
                if cb.get("type") == "tool_use":
                    block_id = cb.get("id", "")
                    block_name = cb.get("name", "")
                    tool_accum[block_id] = (block_name, "")
                    active_tool_id = block_id
                else:
                    active_tool_id = None

            elif evt_type == "content_block_delta":
                delta = json_data.get("delta", {})
                dtype = delta.get("type")

                if dtype == "text_delta":
                    text = delta.get("text", "")
                    if text:
                        await queue.put(text)

                elif dtype == "input_json_delta":
                    partial = delta.get("partial_json", "")
                    if partial and active_tool_id:
                        entry = tool_accum.get(active_tool_id)
                        if entry:
                            tool_accum[active_tool_id] = (entry[0], entry[1] + partial)

            elif evt_type == "message_stop":
                final_calls = []
                for bid, (name, args) in tool_accum.items():
                    if name:
                        final_calls.append(ToolCall(
                            id=bid,
                            type="function",
                            function=FunctionCall(name=name, arguments=args),
                        ))


class AnthropicDriver(LlmDriver):
    """
    Anthropic Claude LLM driver.

    Uses Anthropic's /v1/messages API (not the /messages/stream endpoint).
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
    ):
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._model = model
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))

    async def chat(self, req: ChatRequest) -> ChatResponse:
        model = req.model or self._model
        system_blocks, messages = _build_messages(req)
        tools = _build_tools(req.tools) if req.tools else None
        max_tokens = req.max_tokens or 4096

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "anthropic-beta": "prompt-caching-2024-07-31",
        }

        body: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system_blocks:
            body["system"] = system_blocks
        if tools:
            body["tools"] = tools

        # Retry loop
        last_err: Exception | None = None
        for attempt in range(MAX_RETRIES + 1):
            if attempt > 0:
                delay = (2 ** (attempt - 1))
                logger.warning(
                    "Anthropic retry attempt %d/%d after %ds", attempt, MAX_RETRIES, delay
                )
                await asyncio.sleep(delay)

            try:
                resp = await self._client.post(url, json=body, headers=headers)
            except Exception as e:
                last_err = e
                continue

            if resp.status_code == 200:
                return _parse_response(resp.json())

            msg = "Unknown error"
            try:
                err_json = resp.json()
                msg = err_json.get("error", {}).get("message", "Unknown error")
            except Exception:
                pass

            if resp.status_code in (429, 500, 502, 503) and attempt < MAX_RETRIES:
                logger.warning("Anthropic HTTP %d: %s (will retry)", resp.status_code, msg)
                last_err = Exception(msg)
                continue

            raise Exception(f"HTTP {resp.status_code}: {msg}")

        raise last_err or Exception("Max retries exceeded")

    async def stream_chat(
        self, req: ChatRequest, queue: Optional[asyncio.Queue[str]] = None
    ) -> None:
        model = req.model or self._model
        system_blocks, messages = _build_messages(req)
        tools = _build_tools(req.tools) if req.tools else None
        max_tokens = req.max_tokens or 4096
        if queue is None:
            queue = asyncio.Queue()
        await _stream_anthropic(
            self._client,
            self._api_key,
            system_blocks,
            messages,
            tools,
            model,
            max_tokens,
            queue,
        )

    async def close(self) -> None:
        await self._client.aclose()

    def supports_tools(self) -> bool:
        return True

    def supports_vision(self) -> bool:
        return True

    def max_context_tokens(self) -> int:
        return 200_000