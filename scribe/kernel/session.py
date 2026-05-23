"""
Session management.

Ports scribe-kernel/src/session.rs to Python with JSON file storage.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scribe.types import SessionInfo, SessionId, new_session_id


@dataclass
class SessionManager:
    """
    Manages sessions with JSON file persistence.
    
    Sessions are stored as individual JSON files in the sessions directory.
    """
    sessions_dir: Path
    sessions: dict[SessionId, SessionInfo]

    def __init__(self, sessions_dir: Path):
        self.sessions_dir = sessions_dir
        self.sessions = {}
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load all session JSON files from disk."""
        if not self.sessions_dir.exists():
            return

        for entry in self.sessions_dir.iterdir():
            if entry.suffix != ".json":
                continue
            try:
                content = entry.read_text(encoding="utf-8")
                info = SessionInfo.from_dict(json.loads(content))
                self.sessions[info.id] = info
            except Exception:
                continue

    def _save_session(self, info: SessionInfo) -> None:
        """Save a session to its JSON file."""
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        path = self.sessions_dir / f"{info.id}.json"
        try:
            content = json.dumps(info.to_dict(), indent=2, ensure_ascii=False)
            path.write_text(content, encoding="utf-8")
        except Exception:
            pass

    def create_session(self, title: Optional[str] = None) -> SessionId:
        """
        Create a new session and return its ID.
        
        Args:
            title: Optional title for the session. If None, uses a generated title.
        """
        session_id = new_session_id()
        now = datetime.now(timezone.utc)
        
        if title is None:
            title = f"Session {now.strftime('%Y-%m-%d %H:%M')}"
        
        info = SessionInfo(
            id=session_id,
            title=title,
            created_at=now,
            updated_at=now,
            message_count=0,
        )
        
        self._save_session(info)
        self.sessions[session_id] = info
        return session_id

    def list_sessions(self) -> list[SessionInfo]:
        """
        List all sessions, sorted by most recently updated.
        """
        sessions = list(self.sessions.values())
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    def get_session(self, session_id: SessionId) -> Optional[SessionInfo]:
        """Get a session by ID."""
        return self.sessions.get(session_id)

    def increment_message_count(self, session_id: SessionId) -> None:
        """Increment the message count and update timestamp."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.message_count += 1
            session.updated_at = datetime.now(timezone.utc)
            self._save_session(session)
