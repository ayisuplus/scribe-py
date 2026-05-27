"""
Episodic memory store for conversation events.

Ports scribe-memory/src/episodic.rs to Python with JSON file storage.
Async-first implementation.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

from scribe.types import MemoryEvent, SessionId


class EpisodicStore:
    """
    Stores conversation events with JSON file backend.

    Events are stored in a single JSON file per session.
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._lock = asyncio.Lock()
        self._next_id: dict[str, int] = {}  # session_id -> next id

    def _get_file_path(self, session_id: str) -> Path:
        """Get the JSON file path for a session."""
        return self.data_dir / f"episodic_{session_id}.json"

    async def _load_events(self, session_id: str) -> list[MemoryEvent]:
        """Load events for a session from disk."""
        path = self._get_file_path(session_id)
        if not path.exists():
            return []
        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            return [MemoryEvent.from_dict(e) for e in data]
        except Exception:
            return []

    async def _save_events(self, session_id: str, events: list[MemoryEvent]) -> None:
        """Save events for a session to disk."""
        path = self._get_file_path(session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [e.to_dict() for e in events]
        content = json.dumps(data, indent=2, ensure_ascii=False)
        path.write_text(content, encoding="utf-8")

    async def record_event(self, event: MemoryEvent) -> int:
        """
        Record a new event and return its assigned ID.

        The event's session_id is used to organize storage.
        """
        async with self._lock:
            events = await self._load_events(event.session_id)

            # Assign ID if not set
            if event.id == 0:
                next_id = self._next_id.get(event.session_id, 1)
                event.id = next_id
                self._next_id[event.session_id] = next_id + 1

            events.append(event)
            await self._save_events(event.session_id, events)
            return event.id

    async def search_by_content(self, query: str, limit: int = 10) -> list[MemoryEvent]:
        """
        Search events by content substring.

        Returns events matching the query, sorted by most recent.
        """
        query_lower = query.lower()
        results: list[tuple[datetime, MemoryEvent]] = []

        if not self.data_dir.exists():
            return []

        for path in self.data_dir.glob("episodic_*.json"):
            try:
                content = path.read_text(encoding="utf-8")
                events = [MemoryEvent.from_dict(e) for e in json.loads(content)]
                for event in events:
                    if query_lower in event.content.lower():
                        results.append((event.timestamp, event))
            except Exception:
                continue

        results.sort(key=lambda x: x[0], reverse=True)
        return [event for _, event in results[:limit]]

    async def get_session_events(self, session_id: SessionId) -> list[MemoryEvent]:
        """
        Get all events for a session, sorted by timestamp ascending.
        """
        events = await self._load_events(session_id)
        events.sort(key=lambda e: e.timestamp)
        return events
