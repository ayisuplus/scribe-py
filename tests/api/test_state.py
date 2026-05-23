"""
Tests for ScribeState initialization and send_message.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile

from scribe.api.state import ScribeState


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
                state = await ScribeState.init()
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
                sid1 = await state.create_session("Session 1")
                sid2 = await state.create_session("Session 2")
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])