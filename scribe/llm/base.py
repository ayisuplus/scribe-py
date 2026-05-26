"""
LlmDriver abstract base class.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    pass

from scribe.types import ChatRequest, ChatResponse


class LlmDriver(ABC):
    """
    Abstract interface for LLM drivers.
    Drivers are async and thread-safe (Send + Sync).
    """

    @abstractmethod
    async def chat(self, req: ChatRequest) -> ChatResponse:
        """
        Send a non-streaming chat request.
        Returns the full ChatResponse with content and/or tool_calls.
        """
        ...

    async def stream_chat(
        self, req: ChatRequest, queue: "Optional[asyncio.Queue[str]]" = None
    ) -> None:
        """
        Streaming chat — sends text deltas via the provided queue.

        Default implementation: call chat(), send content to queue.
        Subclasses should override for true streaming.
        """
        response = await self.chat(req)
        content = response.content or ""
        await queue.put(content)

    # ── Lifecycle ──

    async def close(self) -> None:
        """Release resources (HTTP clients, connections). Override in subclasses."""

    async def __aenter__(self) -> "LlmDriver":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    # ── Capabilities ──

    def supports_tools(self) -> bool:
        return True

    def supports_vision(self) -> bool:
        return False

    def max_context_tokens(self) -> int:
        """Maximum context window size."""
        return 128_000