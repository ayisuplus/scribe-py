"""
Integration smoke test — verifies core API operations.
Run: python tests/smoke_test.py
"""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure the package is on the path
sys.path.insert(0, ".")

from scribe.api.state import ScribeState, KernelConfig


async def test_create_session():
    """Test create_session returns a valid SessionId."""
    state = ScribeState()
    sid = await state.create_session(title="Test session")
    assert sid is not None
    assert isinstance(sid, str) and len(sid) > 0
    print(f"[PASS] create_session -> {sid}")


async def test_list_sessions():
    """Test list_sessions returns a list (empty initially)."""
    state = ScribeState()
    await state.create_session(title="Session 1")
    await state.create_session(title="Session 2")
    sessions = await state.list_sessions()
    assert isinstance(sessions, list)
    assert len(sessions) == 2
    assert sessions[0].title == "Session 1"
    assert sessions[1].title == "Session 2"
    print(f"[PASS] list_sessions -> {len(sessions)} sessions")


async def test_send_message_mock_llm():
    """Test send_message with a mocked LLM returns text."""
    state = ScribeState()
    sid = await state.create_session()

    # Mock the LLM driver to avoid real HTTP calls
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Hello from mocked LLM!"
    mock_response.content = "Hello from mocked LLM!"
    mock_response.tool_calls = None
    mock_response.usage = MagicMock()
    mock_response.usage.input_tokens = 10
    mock_response.usage.output_tokens = 5

    async def mock_chat(*args, **kwargs):
        return mock_response

    mock_llm.chat = AsyncMock(side_effect=mock_chat)
    mock_llm.max_context_tokens = MagicMock(return_value=128000)

    # Mock tools registry
    mock_tools = MagicMock()
    mock_tools.definitions = MagicMock(return_value=[])

    # Patch the LLM on the state instance
    with patch.object(state, "_llm", mock_llm):
        with patch.object(state, "_tools", mock_tools):
            with patch.object(state, "_episodic", None):
                with patch.object(state, "_semantic", None):
                    with patch.object(state, "_procedural", None):
                        result = await state.send_message(sid, "Hello!")
                        assert result == "Hello from mocked LLM!"
                        print(f"[PASS] send_message -> {result!r}")


async def test_kernel_config_defaults():
    """Test KernelConfig has expected defaults."""
    config = KernelConfig()
    assert config.default_provider == "openai"
    assert config.default_model == "gpt-4o"
    assert "file_read" in config.tools_enabled
    print("[PASS] KernelConfig defaults correct")


async def main():
    print("=" * 50)
    print("Scribe Integration Smoke Tests")
    print("=" * 50)

    await test_kernel_config_defaults()
    await test_create_session()
    await test_list_sessions()
    await test_send_message_mock_llm()

    print("=" * 50)
    print("All smoke tests PASSED")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())