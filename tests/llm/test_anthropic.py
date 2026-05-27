"""
Tests for AnthropicDriver — mocks httpx to verify request format.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from scribe.llm.anthropic import AnthropicDriver, _build_messages
from scribe.types import ChatRequest, Message, Role, ToolDefinition, FunctionDefinition


class TestAnthropicDriverBuildMessages:
    def test_build_messages_basic(self):
        req = ChatRequest(
            model="claude-sonnet-4-6",
            messages=[
                Message(role=Role.USER, content="hello"),
                Message(role=Role.ASSISTANT, content="hi there"),
            ],
            stream=False,
        )
        system_blocks, conv_messages = _build_messages(req)
        assert conv_messages is not None
        assert len(conv_messages) == 2
        assert conv_messages[0]["role"] == "user"
        assert conv_messages[0]["content"] == "hello"
        assert conv_messages[1]["role"] == "assistant"
        assert conv_messages[1]["content"] == "hi there"
        assert len(system_blocks) == 0

    def test_build_messages_system(self):
        req = ChatRequest(
            model="claude-sonnet-4-6",
            messages=[
                Message(role=Role.SYSTEM, content="You are helpful"),
                Message(role=Role.USER, content="hello"),
            ],
            stream=False,
        )
        system_blocks, conv_messages = _build_messages(req)
        assert conv_messages is not None
        assert len(system_blocks) == 1
        assert system_blocks[0]["text"] == "You are helpful"
        assert len(conv_messages) == 1
        assert conv_messages[0]["role"] == "user"


class TestAnthropicDriverChat:
    @pytest.mark.asyncio
    async def test_chat_basic(self):
        """Test basic chat completion."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Hello!"}],
            "model": "claude-sonnet-4-6",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.post = AsyncMock(return_value=mock_response)

            driver = AnthropicDriver(api_key="sk-ant-test")
            req = ChatRequest(
                model="claude-sonnet-4-6",
                messages=[Message(role=Role.USER, content="Hello")],
                stream=False,
            )
            result = await driver.chat(req)
            assert result.content == "Hello!"
            assert result.tool_calls is None

    @pytest.mark.asyncio
    async def test_chat_with_tools(self):
        """Test chat with tool definitions."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [
                {
                    "type": "tool_use",
                    "id": "tool_1",
                    "name": "get_weather",
                    "input": {"location": "Tokyo"},
                }
            ],
            "model": "claude-sonnet-4-6",
            "usage": {"input_tokens": 20, "output_tokens": 15},
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.post = AsyncMock(return_value=mock_response)

            driver = AnthropicDriver(api_key="sk-ant-test")
            tools = [
                ToolDefinition(
                    tool_type="function",
                    function=FunctionDefinition(
                        name="get_weather",
                        description="Get weather for a location",
                        parameters={
                            "type": "object",
                            "properties": {
                                "location": {"type": "string"},
                            },
                            "required": ["location"],
                        },
                    )
                )
            ]
            req = ChatRequest(
                model="claude-sonnet-4-6",
                messages=[Message(role=Role.USER, content="What's the weather?")],
                tools=tools,
                stream=False,
            )
            result = await driver.chat(req)
            assert result.tool_calls is not None
            assert len(result.tool_calls) == 1
            assert result.tool_calls[0].function.name == "get_weather"

    @pytest.mark.asyncio
    async def test_chat_error(self):
        """Test chat with API error."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {"message": "Invalid request"}
        }
        mock_response.text = '{"error": {"message": "Invalid request"}}'

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client.return_value)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value.post = AsyncMock(return_value=mock_response)

            driver = AnthropicDriver(api_key="sk-ant-test")
            req = ChatRequest(
                model="claude-sonnet-4-6",
                messages=[Message(role=Role.USER, content="Hello")],
                stream=False,
            )
            with pytest.raises(Exception):
                await driver.chat(req)
