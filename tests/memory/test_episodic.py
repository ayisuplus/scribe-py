"""
Tests for EpisodicStore.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime, timezone

from scribe.memory.episodic import EpisodicStore
from scribe.types import MemoryEvent, Role, SessionId


class TestEpisodicStore:
    """Test EpisodicStore operations."""

    @pytest.fixture
    def store(self, temp_dir):
        """Create an EpisodicStore with temp directory."""
        return EpisodicStore(data_dir=temp_dir)

    @pytest.fixture
    def sample_event(self):
        """Create a sample MemoryEvent."""
        return MemoryEvent(
            id=1,
            session_id="test-session",
            role=Role.USER,
            content="Hello, how are you?",
            timestamp=datetime.now(timezone.utc),
            tags=["greeting"],
        )

    @pytest.mark.asyncio
    async def test_record_and_get_events(self, store, sample_event):
        """Test recording and retrieving events."""
        await store.record_event(sample_event)
        events = await store.get_session_events("test-session")
        assert len(events) == 1
        assert events[0].content == "Hello, how are you?"
        assert events[0].role == Role.USER

    @pytest.mark.asyncio
    async def test_get_events_empty_session(self, store):
        """Test getting events from non-existent session."""
        events = await store.get_session_events("non-existent")
        assert events == []

    @pytest.mark.asyncio
    async def test_record_multiple_events(self, store):
        """Test recording multiple events to same session."""
        for i in range(3):
            event = MemoryEvent(
                id=i + 1,
                session_id="test-session",
                role=Role.USER if i % 2 == 0 else Role.ASSISTANT,
                content=f"Message {i}",
                timestamp=datetime.now(timezone.utc),
            )
            await store.record_event(event)

        events = await store.get_session_events("test-session")
        assert len(events) == 3
        assert events[0].content == "Message 0"
        assert events[2].content == "Message 2"

    @pytest.mark.asyncio
    async def test_search_by_content(self, store):
        """Test searching events by content."""
        event1 = MemoryEvent(
            id=1,
            session_id="test-session",
            role=Role.USER,
            content="Hello world",
            timestamp=datetime.now(timezone.utc),
        )
        event2 = MemoryEvent(
            id=2,
            session_id="test-session",
            role=Role.USER,
            content="Goodbye world",
            timestamp=datetime.now(timezone.utc),
        )
        await store.record_event(event1)
        await store.record_event(event2)

        results = await store.search_by_content("world")
        assert len(results) == 2

        results = await store.search_by_content("hello")
        assert len(results) == 1
        assert results[0].content == "Hello world"

    @pytest.mark.asyncio
    async def test_event_persistence(self, temp_dir, sample_event):
        """Test that events persist across store instances."""
        store1 = EpisodicStore(data_dir=temp_dir)
        await store1.record_event(sample_event)

        store2 = EpisodicStore(data_dir=temp_dir)
        events = await store2.get_session_events("test-session")
        assert len(events) == 1
        assert events[0].content == "Hello, how are you?"