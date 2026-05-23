"""
Tests for scribe.kernel.session module.
"""

import json
import tempfile
from pathlib import Path

import pytest

from scribe.kernel.session import SessionManager
from scribe.types import SessionInfo


class TestSessionManager:
    """Test SessionManager functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sessions_dir(self, temp_dir):
        """Get sessions directory."""
        return temp_dir / "sessions"

    def test_create_session(self, sessions_dir):
        """Test creating a new session."""
        manager = SessionManager(sessions_dir)
        session_id = manager.create_session("Test Session")
        
        assert session_id is not None
        assert len(session_id) == 36  # UUID format
        
        session = manager.get_session(session_id)
        assert session is not None
        assert session.title == "Test Session"
        assert session.message_count == 0

    def test_create_session_with_default_title(self, sessions_dir):
        """Test creating session with auto-generated title."""
        manager = SessionManager(sessions_dir)
        session_id = manager.create_session()
        
        session = manager.get_session(session_id)
        assert session is not None
        assert "Session" in session.title

    def test_list_sessions(self, sessions_dir):
        """Test listing sessions sorted by updated_at."""
        manager = SessionManager(sessions_dir)
        
        id1 = manager.create_session("First")
        id2 = manager.create_session("Second")
        
        # Update first session to make it more recent
        import time
        time.sleep(0.01)
        manager.increment_message_count(id1)
        
        sessions = manager.list_sessions()
        
        assert len(sessions) == 2
        assert sessions[0].id == id1  # Most recently updated first

    def test_get_session(self, sessions_dir):
        """Test getting a session by ID."""
        manager = SessionManager(sessions_dir)
        session_id = manager.create_session("Test")
        
        session = manager.get_session(session_id)
        
        assert session is not None
        assert session.id == session_id

    def test_get_nonexistent_session(self, sessions_dir):
        """Test getting non-existent session returns None."""
        manager = SessionManager(sessions_dir)
        
        session = manager.get_session("nonexistent-id")
        
        assert session is None

    def test_increment_message_count(self, sessions_dir):
        """Test incrementing message count."""
        manager = SessionManager(sessions_dir)
        session_id = manager.create_session("Test")
        
        manager.increment_message_count(session_id)
        manager.increment_message_count(session_id)
        
        session = manager.get_session(session_id)
        assert session.message_count == 2

    def test_session_persistence(self, sessions_dir):
        """Test that sessions persist to disk."""
        # Create session in first manager
        manager1 = SessionManager(sessions_dir)
        session_id = manager1.create_session("Persisted")
        
        # Load in new manager
        manager2 = SessionManager(sessions_dir)
        session = manager2.get_session(session_id)
        
        assert session is not None
        assert session.title == "Persisted"

    def test_load_from_disk(self, sessions_dir):
        """Test loading existing sessions from disk."""
        # Create a session file directly
        session_data = {
            "id": "test-session-id",
            "title": "Direct File",
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-01T00:00:00+00:00",
            "message_count": 5,
        }
        sessions_dir.mkdir(parents=True, exist_ok=True)
        (sessions_dir / "test-session-id.json").write_text(
            json.dumps(session_data), encoding="utf-8"
        )
        
        manager = SessionManager(sessions_dir)
        session = manager.get_session("test-session-id")
        
        assert session is not None
        assert session.title == "Direct File"
        assert session.message_count == 5


class TestSessionInfo:
    """Test SessionInfo structure."""

    def test_session_info_to_dict(self):
        """Test SessionInfo serialization."""
        from datetime import datetime, timezone
        
        info = SessionInfo(
            id="test-id",
            title="Test",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            message_count=3,
        )
        
        data = info.to_dict()
        
        assert data["id"] == "test-id"
        assert data["title"] == "Test"
        assert data["message_count"] == 3
