"""
Scribe: A writing agent framework with multi-layer memory.

This package provides:
- types: Core type definitions for messages, memory, and configuration
- kernel: Session management, configuration loading, and event bus
- memory: Three-layer memory system (episodic, semantic, procedural)
"""

__version__ = "0.3.1"
__all__ = [
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
    "Entity",
    "Relation",
    "StyleProfile",
    "Tone",
    "PunctuationStyle",
    "EllipsisStyle",
    "QuoteStyle",
    "ToolResult",
    "SessionInfo",
    "PersonaConfig",
    "ConsciousnessMode",
    "ConsciousnessBlock",
    "ConsciousnessSection",
    "WritingMethodologyConfig",
    "DensityRules",
    "ParagraphRules",
    "WritingAuditResult",
    "AuditIssue",
    "HookHealthIssue",
    "HookEntry",
    "HookStatus",
    "HookLedger",
    "new_session_id",
    "PalaceHit",
    "PalaceStatus",
    "KernelConfig",
    "SessionManager",
    "EventBus",
    "EpisodicStore",
    "SemanticStore",
    "ProceduralStore",
    "ContextAssembler",
    "PersonaLoader",
    "WritingMethodology",
    "HookLedgerManager",
    "EntityExtractor",
    "MemPalaceStore",
    "ScribeState",
    "Book",
    "Bookshelf",
]

from scribe.types import (
    Role,
    Message,
    ToolCall,
    FunctionCall,
    ChatRequest,
    ToolDefinition,
    FunctionDefinition,
    ChatResponse,
    Usage,
    StreamChunk,
    MemoryEvent,
    Entity,
    Relation,
    StyleProfile,
    Tone,
    PunctuationStyle,
    EllipsisStyle,
    QuoteStyle,
    ToolResult,
    SessionInfo,
    PersonaConfig,
    ConsciousnessMode,
    ConsciousnessBlock,
    ConsciousnessSection,
    WritingMethodologyConfig,
    DensityRules,
    ParagraphRules,
    WritingAuditResult,
    AuditIssue,
    HookHealthIssue,
    HookEntry,
    HookStatus,
    HookLedger,
    new_session_id,
    PalaceHit,
    PalaceStatus,
)

from scribe.kernel import (
    KernelConfig,
    SessionManager,
    EventBus,
)

from scribe.memory import (
    EpisodicStore,
    SemanticStore,
    ProceduralStore,
    ContextAssembler,
    PersonaLoader,
    WritingMethodology,
    HookLedgerManager,
    EntityExtractor,
    MemPalaceStore,
)

from scribe.api.state import ScribeState

from scribe.bookshelf import Book, Bookshelf
