"""
Tests for scribe.types module.
"""

import pytest
from datetime import datetime, timezone

from scribe.types import (
    Role,
    Message,
    ToolCall,
    FunctionCall,
    StyleProfile,
    Tone,
    PunctuationStyle,
    SessionInfo,
    PersonaConfig,
    ConsciousnessMode,
    HookEntry,
    HookStatus,
    HookLedger,
    new_session_id,
)


class TestMessageSerialization:
    """Test Message serialization round-trip."""

    def test_message_to_dict(self):
        """Test Message to_dict serialization."""
        msg = Message(role=Role.USER, content="Hello, world!")
        data = msg.to_dict()
        
        assert data["role"] == "user"
        assert data["content"] == "Hello, world!"
        assert "name" not in data
        assert "timestamp" not in data

    def test_message_from_dict(self):
        """Test Message from_dict deserialization."""
        data = {"role": "user", "content": "Hello, world!"}
        msg = Message.from_dict(data)
        
        assert msg.role == Role.USER
        assert msg.content == "Hello, world!"

    def test_message_roundtrip(self):
        """Test full serialization round-trip."""
        msg = Message(
            role=Role.USER,
            content="Test message",
            name="test_user",
            timestamp=datetime.now(timezone.utc),
        )
        
        data = msg.to_dict()
        restored = Message.from_dict(data)
        
        assert restored.role == msg.role
        assert restored.content == msg.content
        assert restored.name == msg.name

    def test_message_with_tool_calls(self):
        """Test Message with tool calls."""
        tool_call = ToolCall(
            id="call_123",
            call_type="function",
            function=FunctionCall(name="get_weather", arguments='{"city":"Beijing"}'),
        )
        msg = Message(
            role=Role.ASSISTANT,
            content="The weather is sunny",
            tool_calls=[tool_call],
        )
        
        data = msg.to_dict()
        restored = Message.from_dict(data)
        
        assert len(restored.tool_calls) == 1
        assert restored.tool_calls[0].function.name == "get_weather"


class TestStyleProfile:
    """Test StyleProfile defaults."""

    def test_style_profile_default(self):
        """Test StyleProfile default values match Rust defaults."""
        profile = StyleProfile()
        
        assert profile.tone == Tone.CASUAL
        assert profile.avg_sentence_length == 20.0
        assert profile.paragraph_density == 3.0
        assert profile.preferred_structures == []
        assert profile.vocabulary_patterns == []
        assert profile.transition_words == []

    def test_style_profile_punctuation_defaults(self):
        """Test PunctuationStyle defaults."""
        style = PunctuationStyle()
        
        assert style.use_oxford_comma is False
        assert style.ellipsis_style.value == "threedots"
        assert style.quote_style.value == "double"


class TestSessionInfo:
    """Test SessionInfo serialization."""

    def test_session_info_roundtrip(self):
        """Test SessionInfo serialization round-trip."""
        now = datetime.now(timezone.utc)
        info = SessionInfo(
            id="test-session-id",
            title="Test Session",
            created_at=now,
            updated_at=now,
            message_count=5,
        )
        
        data = info.to_dict()
        restored = SessionInfo.from_dict(data)
        
        assert restored.id == info.id
        assert restored.title == info.title
        assert restored.message_count == info.message_count


class TestHookLedger:
    """Test HookLedger serialization."""

    def test_hook_ledger_default(self):
        """Test default HookLedger is empty."""
        ledger = HookLedger()
        assert ledger.hooks == []

    def test_hook_ledger_roundtrip(self):
        """Test HookLedger serialization round-trip."""
        ledger = HookLedger(hooks=[
            HookEntry(
                id="H001",
                description="神秘信件",
                seed_chapter=1,
                status=HookStatus.PLANTED,
            ),
            HookEntry(
                id="H002",
                description="失踪的戒指",
                seed_chapter=2,
                status=HookStatus.PRESSURED,
                last_mention_chapter=5,
            ),
        ])
        
        data = ledger.to_dict()
        restored = HookLedger.from_dict(data)
        
        assert len(restored.hooks) == 2
        assert restored.hooks[0].id == "H001"
        assert restored.hooks[0].status == HookStatus.PLANTED
        assert restored.hooks[1].status == HookStatus.PRESSURED


class TestNewSessionId:
    """Test new_session_id function."""

    def test_new_session_id_format(self):
        """Test that new session IDs are valid UUIDs."""
        session_id = new_session_id()
        
        # Should be a valid UUID format (8-4-4-4-12)
        parts = session_id.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12

    def test_new_session_id_unique(self):
        """Test that new session IDs are unique."""
        ids = {new_session_id() for _ in range(100)}
        assert len(ids) == 100


class TestPersonaConfig:
    """Test PersonaConfig structure."""

    def test_persona_config_defaults(self):
        """Test PersonaConfig default values."""
        config = PersonaConfig(
            identity="I am a test persona.",
            ishiki="I speak in test mode.",
        )
        
        assert config.yuan is None
        assert config.consciousness_mode == ConsciousnessMode.NONE

    def test_consciousness_mode_values(self):
        """Test all ConsciousnessMode values."""
        assert ConsciousnessMode.NONE.value == "none"
        assert ConsciousnessMode.MOOD.value == "mood"
        assert ConsciousnessMode.REFLECT.value == "reflect"
