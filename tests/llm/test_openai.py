"""
Tests for OpenAiDriver — mocks httpx to verify request format.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from scribe.llm.openai import OpenAiDriver
from scribe.types import ChatRequest, Message, Role, ToolDefinition


class TestOpenAiDriverBuildMessages:
    def test_build_messages_basic(self):
        from scribe.llm.openai import _build_messages
        msgs = [
            Message(role=Role.USER, content="hello"),
            Message(role=Role.ASSISTANT, content="hi there"),
        ]
        result = _build_messages(msgs)
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "hello"
        assert result[1]["role"] == "assistant"
        assert result[1]["content"] == "hi there"


class TestOpenAiDriverBuildBody:
    def test_build_body_basic(self):
        from scribe.llm.openai import _build_body
        req = ChatRequest(
            model="gpt-4o",
            messages=[Message(role=Role.USER, content="test")],
            temperature=0.5,
            max_tokens=100,
            stream=False,
        )
        body = _build_body(req, "gpt-4o")
        assert body["model"] == "gpt-4o"
        assert body["temperature"] == 0.5
        assert body["max_tokens"] == 100
        assert body["stream"] is False
        assert len(body["messages"]) == 1

    def test_build_body_with_tools(self):
        from scribe.llm.openai import _build_body
        from scribe.types import FunctionDefinition
        req = ChatRequest(
            model="gpt-4o",
            messages=[Message(role=Role.USER, content="test")],
            tools=[
                ToolDefinition(
                    tool_type="function",
                    function=FunctionDefinition(
                        name="test_tool",
                        description="A test tool",
                        parameters={"type": "object", "properties": {}},
                    ),
                )
            ],
            stream=False,
        )
        body = _build_body(req, "gpt-4o")
        assert "tools" in body
        assert body["tools"][0]["function"]["name"] == "test_tool"


class TestOpenAiDriverParseResponse:
    def test_parse_content_only(self):
        from scribe.llm.openai import _parse_response
        resp = {
            "choices": [{
                "message": {"content": "Hello, world!"}
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        result = _parse_response(resp)
        assert result.content == "Hello, world!"
        assert result.tool_calls is None

    def test_parse_with_tool_calls(self):
        from scribe.llm.openai import _parse_response
        resp = {
            "choices": [{
                "message": {
                    "content": "",
                    "tool_calls": [{
                        "id": "call_abc",
                        "type": "function",
                        "function": {
                            "name": "web_search",
                            "arguments": '{"query":"test"}',
                        },
                    }],
                }
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        result = _parse_response(resp)
        assert result.content is None
        assert result.tool_calls is not None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].function.name == "web_search"

    def test_parse_error(self):
        from scribe.llm.openai import _parse_response
        resp = {"error": {"message": "Invalid API key", "code": "invalid_api_key"}}
        with pytest.raises(Exception) as exc_info:
            _parse_response(resp)
        assert "invalid_api_key" in str(exc_info.value)


class TestOpenAiDriver:
    @pytest.mark.asyncio
    async def test_chat_sends_correct_format(self):
        mock_response = {
            "choices": [{"message": {"content": "Test response"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3},
        }

        with patch("scribe.llm.openai.httpx.AsyncClient") as MockClient:
            mock_instance = MagicMock()
            MockClient.return_value = mock_instance
            mock_instance.post = AsyncMock(
                return_value=MagicMock(
                    status_code=200,
                    json=MagicMock(return_value=mock_response),
                )
            )

            driver = OpenAiDriver(api_key="test-key", model="gpt-4o")
            req = ChatRequest(
                model="",
                messages=[Message(role=Role.USER, content="hello")],
            )
            resp = await driver.chat(req)

            assert resp.content == "Test response"
            mock_instance.post.assert_called_once()
            call_args = mock_instance.post.call_args
            assert call_args[0][0].endswith("/chat/completions")

    @pytest.mark.asyncio
    async def test_stream_queue_interface(self):
        """Verify stream_chat accepts an asyncio.Queue and feeds tokens into it."""
        driver = OpenAiDriver(api_key="test-key")
        queue: "asyncio.Queue[str]" = asyncio.Queue()
        req = ChatRequest(
            model="",
            messages=[Message(role=Role.USER, content="hello")],
        )

        async def fake_stream(client, base_url, api_key, request, model, q):
            await q.put("hello ")
            await q.put("world")

        with patch("scribe.llm.openai._stream_chat_openai", side_effect=fake_stream):
            await driver.stream_chat(req, queue)

        assert queue.get_nowait() == "hello "
        assert queue.get_nowait() == "world"
        assert queue.empty()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])