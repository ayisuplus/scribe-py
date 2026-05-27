"""
Scribe: A writing agent framework with simplified memory.

This package provides:
- types: Core type definitions for messages and configuration
- kernel: Session management, configuration loading, and event bus
- memory: Simplified memory system (episodic + persona + methodology)
"""

__version__ = "0.3.1"
__all__ = [
    # Core types
    "Role",
    "Message",
    "ToolCall",
    "FunctionCall",
    "ChatRequest",
    "ToolDefinition",
    "FunctionDefinition",
    "ChatResponse",
    "Usage",
    "StreamChunk",
    "MemoryEvent",
    "ToolResult",
    "SessionInfo",
    # Persona
    "PersonaConfig",
    # Writing Methodology
    "WritingMethodologyConfig",
    "DensityRules",
    "ParagraphRules",
    "AuditIssue",
    # Utils
    "new_session_id",
    # Kernel
    "KernelConfig",
    "SessionManager",
    "EventBus",
    # Memory
    "EpisodicStore",
    "PersonaLoader",
    "WritingMethodology",
    # API
    "ScribeState",
    # Bookshelf
    "Book",
    "Bookshelf",
]

from scribe.api.state import ScribeState
from scribe.bookshelf import Book, Bookshelf
from scribe.kernel import (
    EventBus,
    KernelConfig,
    SessionManager,
)
from scribe.memory import (
    EpisodicStore,
    PersonaLoader,
    WritingMethodology,
)
from scribe.types import (
    AuditIssue,
    ChatRequest,
    ChatResponse,
    DensityRules,
    FunctionCall,
    FunctionDefinition,
    MemoryEvent,
    Message,
    ParagraphRules,
    PersonaConfig,
    Role,
    SessionInfo,
    StreamChunk,
    ToolCall,
    ToolDefinition,
    ToolResult,
    Usage,
    WritingMethodologyConfig,
    new_session_id,
)
