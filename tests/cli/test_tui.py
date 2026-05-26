"""Tests for interactive TUI command handling."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from scribe.cli.tui import CommandOutcome, InteractiveMode


@pytest.mark.asyncio
async def test_help_command_lists_council_commands():
    """The shared help command should include writing-workflow commands."""
    mode = InteractiveMode(MagicMock(), "sid")
    lines: list[str] = []

    outcome = await mode._handle_command("/help", lines.append)

    assert outcome == CommandOutcome.HANDLED
    assert any("/council" in line for line in lines)
    assert any("/writers" in line for line in lines)
    assert any("/scope" in line for line in lines)
    assert any("/onboard" in line for line in lines)


@pytest.mark.asyncio
async def test_onboard_command_prints_quickstart_lines():
    """Users should be able to replay startup guidance inside the TUI."""
    mode = InteractiveMode(MagicMock(), "sid")
    lines: list[str] = []

    outcome = await mode._handle_command("/onboard", lines.append)

    assert outcome == CommandOutcome.HANDLED
    assert any("Quickstart" in line for line in lines)
    assert any("/council" in line for line in lines)


def test_interactive_mode_accepts_startup_lines():
    """Startup guidance should be injected by the CLI onboarding flow."""
    mode = InteractiveMode(MagicMock(), "sid", startup_lines=["Quickstart"])

    assert mode.startup_lines == ["Quickstart"]


@pytest.mark.asyncio
async def test_new_command_awaits_state_and_updates_session():
    """Async TUI commands should use the running event loop."""
    state = MagicMock()
    state.create_session = AsyncMock(return_value="new-session-id")
    mode = InteractiveMode(state, "old-session-id")
    lines: list[str] = []

    outcome = await mode._handle_command("/new", lines.append)

    assert outcome == CommandOutcome.HANDLED
    assert mode.session_id == "new-session-id"
    state.create_session.assert_awaited_once_with(None)
    assert lines == ["  New session: new-sess\n"]


@pytest.mark.asyncio
async def test_regular_message_streams_without_forced_newlines():
    """Streaming deltas should use a separate writer from line output."""
    state = MagicMock()

    async def send_message_streaming(_session_id, _text, queue):
        await queue.put("hel")
        await queue.put("lo")
        return "hello"

    state.send_message_streaming = AsyncMock(side_effect=send_message_streaming)
    mode = InteractiveMode(state, "sid")
    lines: list[str] = []
    deltas: list[str] = []

    await mode._send_regular_message("Hi", lines.append, deltas.append)

    assert lines == [""]
    assert deltas == ["Scribe> ", "hel", "lo"]
    assert mode.messages == [("You", "Hi"), ("Scribe", "hello")]
