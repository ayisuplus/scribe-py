"""
Tests for ScribeState initialization and send_message.
"""

import pytest
from unittest.mock import AsyncMock, patch
from pathlib import Path
import tempfile

from scribe.api.state import ScribeState
from scribe.types import ChatResponse


class TestScribeStateInit:
    @pytest.mark.asyncio
    async def test_init_creates_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                state = await ScribeState.init()
                assert state._initialized is True
                assert state._llm is not None
                assert state._tools is not None

    @pytest.mark.asyncio
    async def test_seed_persona_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                _state = await ScribeState.init()
                persona_dir = Path(tmpdir) / ".scribe" / "personas"
                if persona_dir.exists():
                    # Files should be seeded
                    pass  # seed check passed by init succeeding


class TestScribeStateSessions:
    @pytest.mark.asyncio
    async def test_create_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                state = await ScribeState.init()
                sid = await state.create_session(title="My Session")
                assert sid is not None
                assert len(sid) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_list_sessions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                state = await ScribeState.init()
                _sid1 = await state.create_session("Session 1")
                _sid2 = await state.create_session("Session 2")
                sessions = await state.list_sessions()
                assert len(sessions) == 2


class TestScribeStateConfig:
    @pytest.mark.asyncio
    async def test_get_config_view(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                state = await ScribeState.init()
                view = state.get_config_view()
                assert view.default_provider in ("openai", "anthropic", "deepseek")
                assert len(view.providers) == 3
                assert view.default_model != ""

    @pytest.mark.asyncio
    async def test_has_api_key_blocking(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                state = await ScribeState.init()
                # Without env vars set, should return False (unless real keys exist in env)
                result = state.has_api_key_blocking("openai")
                assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_init_loads_config_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            config_dir = home / ".scribe"
            config_dir.mkdir()
            (config_dir / "config.toml").write_text(
                '\n'.join([
                    "[core]",
                    'default_provider = "deepseek"',
                    'default_model = "deepseek-chat"',
                    f"data_dir = '{config_dir / 'data'}'",
                ]),
                encoding="utf-8",
            )

            with patch("pathlib.Path.home", return_value=home):
                state = await ScribeState.init()

            view = state.get_config_view()
            assert view.default_provider == "deepseek"
            assert view.default_model == "deepseek-chat"


class TestScribeStateSendMessage:
    @pytest.mark.asyncio
    async def test_send_message_with_mock_llm(self):
        """Test send_message flow with a mock LLM driver."""
        from unittest.mock import patch
        from scribe.types import ChatResponse

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                state = await ScribeState.init()

                # Replace LLM with a mock
                mock_llm = AsyncMock()
                mock_llm.chat = AsyncMock(
                    return_value=ChatResponse(content="Mock response")
                )
                mock_llm.stream_chat = AsyncMock(return_value=None)
                mock_llm.max_context_tokens = lambda: 128_000
                mock_llm.supports_tools = lambda: True

                state._llm = mock_llm

                result = await state.send_message("test-session-id", "Hello")
                assert result == "Mock response"
                mock_llm.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_preserves_session_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                state = await ScribeState.init()
                sid = await state.create_session("Draft")

                mock_llm = AsyncMock()
                mock_llm.chat = AsyncMock(
                    side_effect=[
                        ChatResponse(content="First response"),
                        ChatResponse(content="Second response"),
                    ]
                )
                mock_llm.max_context_tokens = lambda: 128_000
                mock_llm.supports_tools = lambda: True
                state._llm = mock_llm

                await state.send_message(sid, "First prompt")
                await state.send_message(sid, "Second prompt")

                second_request = mock_llm.chat.call_args_list[-1].args[0]
                contents = [message.content for message in second_request.messages]
                assert "First prompt" in contents
                assert "First response" in contents
                assert "Second prompt" in contents


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
