"""
Tests for AgentLoop — basic flow with mock LLM.
"""

import asyncio
import pytest
from unittest.mock import MagicMock

from scribe.agent.loop import AgentLoop
from scribe.agent import AgentConfig
from scribe.agent.retry import RetryConfig
from scribe.types import (
    ChatResponse,
    ChatRequest,
    Message,
    Role,
    ToolCall,
    FunctionCall,
    ToolResult,
)


class MockLlmDriver:
    """Mock LLM that returns simple text responses."""

    def __init__(self, responses: list[ChatResponse] | None = None):
        self._responses = responses or []
        self._call_count = 0
        self._last_request: ChatRequest | None = None
        self._streaming_enabled = False

    async def chat(self, req: ChatRequest) -> ChatResponse:
        self._last_request = req
        self._call_count += 1
        if self._responses and self._call_count <= len(self._responses):
            return self._responses[self._call_count - 1]
        return ChatResponse(content="Mock response text.")

    async def stream_chat(self, req: ChatRequest, queue) -> None:
        """Stream a single chunk then done."""
        if queue is None:
            queue = asyncio.Queue()
        await queue.put("Mock streamed text")
        from scribe.types import StreamChunk
        await queue.put(StreamChunk(delta="", tool_calls=None, done=True))

    def supports_tools(self) -> bool:
        return True

    def supports_vision(self) -> bool:
        return False

    def max_context_tokens(self) -> int:
        return 128_000


class MockToolRegistry:
    """Mock registry that returns results for specific tools."""

    def __init__(self):
        self._tools: dict[str, MagicMock] = {}
        self.defs_return = []

    def register(self, name: str, mock_fn):
        self._tools[name] = mock_fn

    def get(self, name: str):
        return self._tools.get(name)

    def definitions(self):
        return self.defs_return


class TestAgentLoopBasic:
    @pytest.mark.asyncio
    async def test_run_returns_text_when_no_tools(self):
        llm = MockLlmDriver()
        registry = MockToolRegistry()
        agent = AgentLoop(
            llm=llm,
            tools=registry,
            episodic=None,
            semantic=None,
            procedural=None,
        )

        result = await agent.run(
            session_id="test-session",
            conversation=[Message(role=Role.USER, content="Hello")],
            model="gpt-4o",
        )

        assert result == "Mock response text."
        assert llm._call_count == 1

    @pytest.mark.asyncio
    async def test_run_executes_tool_and_returns_result(self):
        """Test that AgentLoop executes a tool call and returns the result."""
        # LLM returns a tool call
        llm = MockLlmDriver(responses=[
            ChatResponse(
                content="I'll search for that.",
                tool_calls=[
        ToolCall(
            id="call_1",
            call_type="function",
            function=FunctionCall(
                name="web_search",
                arguments='{"query":"Python async"}',
            ),
        )
                ],
            ),
            ChatResponse(content="Found: Python async is great."),  # after tool
        ])
        registry = MockToolRegistry()

        # Mock tool
        async def mock_search(params, ctx):
            return ToolResult(content="Web search result: Python async tutorial", is_error=False)

        registry._tools["web_search"] = mock_search

        agent = AgentLoop(llm=llm, tools=registry)
        result = await agent.run(
            session_id="test-session",
            conversation=[Message(role=Role.USER, content="What's new in Python?")],
            model="gpt-4o",
        )

        assert llm._call_count >= 1
        # Final response should contain the follow-up
        assert "Found" in result or "Python" in result

    @pytest.mark.asyncio
    async def test_max_continuations_respected(self):
        """Verify max_continuations caps the loop."""
        # LLM always returns a tool call
        llm = MockLlmDriver(responses=[
            ChatResponse(
                content="Tool call",
                tool_calls=[
                    ToolCall(
                        id=f"call_{i}",
                        call_type="function",
                        function=FunctionCall(
                            name="web_search",
                            arguments='{"query":"test"}',
                        ),
                    )
                ],
            )
            for i in range(10)
        ])
        registry = MockToolRegistry()
        registry._tools["web_search"] = lambda params, ctx: ToolResult(content="ok")

        agent = AgentLoop(
            llm=llm,
            tools=registry,
        ).with_agent_config(AgentConfig(max_continuations=3))

        result = await agent.run(
            session_id="test-session",
            conversation=[Message(role=Role.USER, content="test")],
            model="gpt-4o",
        )

        assert "maximum continuation limit" in result.lower()
        assert llm._call_count == 3

    @pytest.mark.asyncio
    async def test_builder_pattern(self):
        """Test with_persona, with_user_name, with_skills builder methods."""
        llm = MockLlmDriver()
        registry = MockToolRegistry()
        agent = (
            AgentLoop(llm=llm, tools=registry)
            .with_user_name("Alice")
            .with_retry_config(RetryConfig())
            .with_agent_config(AgentConfig(max_continuations=3))
        )
        assert agent._user_name == "Alice"
        assert agent._agent_config.max_continuations == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])