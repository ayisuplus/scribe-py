"""
DeepSeek LLM driver.
"""

from __future__ import annotations

import asyncio
import os
from typing import Optional

from scribe.llm.openai import _chat_with_retry, _stream_chat_openai
from scribe.llm.base import LlmDriver
from scribe.types import ChatRequest, ChatResponse


class DeepSeekDriver(LlmDriver):
    """
    DeepSeek LLM driver.
    API-compatible with OpenAI's /chat/completions endpoint.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "deepseek-chat",
    ):
        self._api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self._base_url = base_url or os.environ.get(
            "DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat"
        )
        self._model = model
        self._client = None  # lazily initialized

    @property
    def _httpx_client(self):
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        return self._client

    async def chat(self, req: ChatRequest) -> ChatResponse:
        model = req.model or self._model
        return await _chat_with_retry(
            self._httpx_client, self._base_url, self._api_key, req, model
        )

    async def stream_chat(
        self, req: ChatRequest, queue: Optional[asyncio.Queue[str]] = None
    ) -> None:
        model = req.model or self._model
        if queue is None:
            queue = asyncio.Queue()
        await _stream_chat_openai(
            self._httpx_client, self._base_url, self._api_key, req, model, queue
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def supports_tools(self) -> bool:
        return True

    def supports_vision(self) -> bool:
        return False

    def max_context_tokens(self) -> int:
        return 64_000