"""
Async event bus for kernel events.

Ports scribe-kernel/src/event_bus.rs to Python with asyncio.Queue.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum


@dataclass
class KernelEvent:
    """Base kernel event."""
    pass


@dataclass
class MessageUpdateEvent(KernelEvent):
    """Event for streaming message updates."""
    session_id: str
    content: str
    done: bool


@dataclass
class ToolExecutionEvent(KernelEvent):
    """Event for tool execution status changes."""
    tool_name: str
    status: str


class KernelEventType(str, Enum):
    """Event type enumeration."""
    MESSAGE_UPDATE = "message_update"
    TOOL_EXECUTION = "tool_execution"


class EventBus:
    """
    Async publish/subscribe event bus.
    
    Uses asyncio.Queue for async event distribution.
    """
    def __init__(self, capacity: int = 100):
        self._queue: asyncio.Queue[KernelEvent] = asyncio.Queue(maxsize=capacity)
        self._running = True

    async def publish(self, event: KernelEvent) -> None:
        """
        Publish an event to all subscribers.
        
        Non-blocking: drops event if queue is full.
        """
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            pass

    async def subscribe(self) -> AsyncIterator[KernelEvent]:
        """
        Subscribe to events. Returns an async iterator.
        
        Usage:
            async for event in bus.subscribe():
                handle(event)
        """
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                yield event
            except asyncio.TimeoutError:
                continue

    def close(self) -> None:
        """Stop the event bus."""
        self._running = False


class AsyncIterator:
    """Helper for async iteration over events."""
    def __init__(self, queue: asyncio.Queue, running: bool):
        self._queue = queue
        self._running = running

    def __aiter__(self):
        return self

    async def __anext__(self) -> KernelEvent:
        while self._running:
            try:
                return await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
        raise StopAsyncIteration
