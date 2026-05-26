"""
Core type definitions for Scribe.

Ports scribe-types/src/lib.rs to Python with dataclasses.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any


# ── IDs ──

type AgentId = str
type SessionId = str


def new_session_id() -> SessionId:
    """Generate a new unique session ID."""
    return str(uuid.uuid4())


# ── Message Types ──


class Role(str, Enum):
    """Message role enumeration."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """A chat message with role and content."""
    role: Role
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None
    timestamp: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary, skipping None values."""
        result = {"role": self.role.value, "content": self.content}
        if self.name is not None:
            result["name"] = self.name
        if self.tool_call_id is not None:
            result["tool_call_id"] = self.tool_call_id
        if self.tool_calls is not None:
            result["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
        if self.timestamp is not None:
            result["timestamp"] = self.timestamp.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: dict) -> Message:
        """Deserialize from dictionary."""
        role = Role(data["role"])
        content = data["content"]
        name = data.get("name")
        tool_call_id = data.get("tool_call_id")
        tool_calls = None
        if "tool_calls" in data and data["tool_calls"]:
            tool_calls = [ToolCall.from_dict(tc) for tc in data["tool_calls"]]
        timestamp = None
        if "timestamp" in data and data["timestamp"]:
            timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        return cls(role=role, content=content, name=name, tool_call_id=tool_call_id,
                   tool_calls=tool_calls, timestamp=timestamp)


@dataclass
class ToolCall:
    """A tool call with id, type, and function details."""
    id: str
    call_type: str
    function: FunctionCall

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.call_type,
            "function": self.function.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> ToolCall:
        return cls(
            id=data["id"],
            call_type=data["type"],
            function=FunctionCall.from_dict(data["function"]),
        )


@dataclass
class FunctionCall:
    """A function call with name and arguments."""
    name: str
    arguments: str

    def to_dict(self) -> dict:
        return {"name": self.name, "arguments": self.arguments}

    @classmethod
    def from_dict(cls, data: dict) -> FunctionCall:
        return cls(name=data["name"], arguments=data["arguments"])


# ── LLM Types ──


@dataclass
class ChatRequest:
    """LLM chat request."""
    model: str
    messages: list[Message]
    tools: Optional[list[ToolDefinition]] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = False

    def to_dict(self) -> dict:
        result = {
            "model": self.model,
            "messages": [msg.to_dict() for msg in self.messages],
            "stream": self.stream,
        }
        if self.tools is not None:
            result["tools"] = [t.to_dict() for t in self.tools]
        if self.temperature is not None:
            result["temperature"] = self.temperature
        if self.max_tokens is not None:
            result["max_tokens"] = self.max_tokens
        return result


@dataclass
class ToolDefinition:
    """Tool definition for LLM function calling."""
    tool_type: str
    function: FunctionDefinition

    def to_dict(self) -> dict:
        return {"type": self.tool_type, "function": self.function.to_dict()}


@dataclass
class FunctionDefinition:
    """Function definition with name, description, and parameters."""
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


@dataclass
class Usage:
    """Token usage statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class ChatResponse:
    """LLM chat response."""
    content: Optional[str]
    tool_calls: Optional[list[ToolCall]] = None
    usage: Usage = field(default_factory=Usage)


@dataclass
class StreamChunk:
    """A streaming response chunk."""
    delta: str
    tool_calls: Optional[list[ToolCall]] = None
    done: bool = False


# ── Memory Types ──


@dataclass
class MemoryEvent:
    """An episodic memory event from a conversation."""
    id: int
    session_id: SessionId
    role: Role
    content: str
    timestamp: datetime
    tags: list[str] = field(default_factory=list)
    tool_call_id: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None
    tool_name: Optional[str] = None

    def to_dict(self) -> dict:
        result = {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
        }
        if self.tool_call_id is not None:
            result["tool_call_id"] = self.tool_call_id
        if self.tool_calls is not None:
            result["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
        if self.tool_name is not None:
            result["tool_name"] = self.tool_name
        return result

    @classmethod
    def from_dict(cls, data: dict) -> MemoryEvent:
        role = Role(data["role"])
        timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        tool_calls = None
        if "tool_calls" in data and data["tool_calls"]:
            tool_calls = [ToolCall.from_dict(tc) for tc in data["tool_calls"]]
        return cls(
            id=data["id"],
            session_id=data["session_id"],
            role=role,
            content=data["content"],
            timestamp=timestamp,
            tags=data.get("tags", []),
            tool_call_id=data.get("tool_call_id"),
            tool_calls=tool_calls,
            tool_name=data.get("tool_name"),
        )


@dataclass
class Entity:
    """A named entity in the semantic store."""
    id: int
    name: str
    entity_type: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class Relation:
    """A relation between two entities."""
    id: int
    subject_id: int
    predicate: str
    object_id: int


# ── Style Types ──


class Tone(str, Enum):
    """Writing tone enumeration."""
    FORMAL = "formal"
    CASUAL = "casual"
    ACADEMIC = "academic"


class EllipsisStyle(str, Enum):
    """Ellipsis style enumeration."""
    THREE_DOTS = "threedots"
    UNICODE_ELLIPSIS = "unicodeellipsis"


class QuoteStyle(str, Enum):
    """Quote style enumeration."""
    DOUBLE = "double"
    SINGLE = "single"
    CHINESE = "chinese"


@dataclass
class PunctuationStyle:
    """Punctuation style preferences."""
    use_oxford_comma: bool = False
    ellipsis_style: EllipsisStyle = EllipsisStyle.THREE_DOTS
    quote_style: QuoteStyle = QuoteStyle.DOUBLE


@dataclass
class StyleProfile:
    """A user's writing style profile."""
    tone: Tone = Tone.CASUAL
    avg_sentence_length: float = 20.0
    preferred_structures: list[str] = field(default_factory=list)
    vocabulary_patterns: list[str] = field(default_factory=list)
    punctuation_style: PunctuationStyle = field(default_factory=PunctuationStyle)
    paragraph_density: float = 3.0
    transition_words: list[str] = field(default_factory=list)


# ── Tool Types ──


@dataclass
class ToolResult:
    """Result of a tool execution."""
    content: str
    is_error: bool = False


# ── Session Types ──


@dataclass
class SessionInfo:
    """Information about a session."""
    id: SessionId
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "message_count": self.message_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SessionInfo:
        return cls(
            id=data["id"],
            title=data["title"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
            message_count=data.get("message_count", 0),
        )


# ── Persona Types ──


class ConsciousnessMode(str, Enum):
    """Consciousness mode for persona."""
    NONE = "none"
    MOOD = "mood"
    REFLECT = "reflect"


@dataclass
class PersonaConfig:
    """Persona configuration loaded from markdown files."""
    identity: str
    ishiki: str
    name: Optional[str] = None
    yuan: Optional[str] = None
    consciousness_mode: ConsciousnessMode = ConsciousnessMode.NONE


@dataclass
class ConsciousnessBlock:
    """A block of consciousness sections."""
    mode: ConsciousnessMode
    sections: list[ConsciousnessSection]


@dataclass
class ConsciousnessSection:
    """A named section with consciousness items."""
    name: str
    items: list[str]


# ── Writing Methodology Types ──


@dataclass
class DensityRules:
    """Rules for content density (fun, hooks, suspense)."""
    fun_per_chars: int = 300
    hook_per_chars: int = 500
    suspense_per_chars: int = 1500


@dataclass
class ParagraphRules:
    """Rules for paragraph structure."""
    min_narrative_chars: int = 40
    target_min_chars: int = 40
    target_max_chars: int = 120
    max_short_paragraphs: int = 5
    max_consecutive_short: int = 3


@dataclass
class WritingMethodologyConfig:
    """Configuration for writing methodology rules."""
    enabled: bool = False
    genre: str = "general"
    density_rules: DensityRules = field(default_factory=DensityRules)
    paragraph_rules: ParagraphRules = field(default_factory=ParagraphRules)
    audit_enabled: bool = True


@dataclass
class AuditIssue:
    """A single issue found during writing audit."""
    category: str
    severity: str
    location: str
    suggestion: str


@dataclass
class HookHealthIssue:
    """A health issue with a hook."""
    hook_id: str
    issue: str


@dataclass
class WritingAuditResult:
    """Result of a writing audit."""
    score: float
    issues: list[AuditIssue]
    hook_health: list[HookHealthIssue] = field(default_factory=list)


# ── MemPalace Types ──


@dataclass
class PalaceHit:
    """A single search result from MemPalace."""
    text: str
    wing: str
    room: str
    source_file: str
    similarity: float


@dataclass
class PalaceStatus:
    """Palace overview."""
    wings: dict[str, list[str]]  # wing_name -> [room_names]
    total_drawers: int


# ── Hook Ledger Types ──


class HookStatus(str, Enum):
    """Hook status enumeration."""
    PLANTED = "planted"
    PRESSURED = "pressured"
    RESOLVED = "resolved"
    DEFERRED = "deferred"


@dataclass
class HookEntry:
    """A foreshadowing hook entry."""
    id: str
    description: str
    seed_chapter: int
    status: HookStatus
    last_mention_chapter: Optional[int] = None
    payoff_text: Optional[str] = None


@dataclass
class HookLedger:
    """A ledger of all foreshadowing hooks."""
    hooks: list[HookEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "hooks": [
                {
                    "id": h.id,
                    "description": h.description,
                    "seed_chapter": h.seed_chapter,
                    "status": h.status.value,
                    "last_mention_chapter": h.last_mention_chapter,
                    "payoff_text": h.payoff_text,
                }
                for h in self.hooks
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> HookLedger:
        """Deserialize from dictionary."""
        hooks = []
        for h_data in data.get("hooks", []):
            hooks.append(HookEntry(
                id=h_data["id"],
                description=h_data["description"],
                seed_chapter=h_data["seed_chapter"],
                status=HookStatus(h_data["status"]),
                last_mention_chapter=h_data.get("last_mention_chapter"),
                payoff_text=h_data.get("payoff_text"),
            ))
        return cls(hooks=hooks)


# ── API Config Types ──


@dataclass
class ConfigUpdate:
    """Update request for ScribeState configuration."""
    default_provider: Optional[str] = None
    default_model: Optional[str] = None
    api_keys: Optional[dict[str, str]] = None
    base_urls: Optional[dict[str, str]] = None
    models: Optional[dict[str, str]] = None


@dataclass
class ProviderView:
    """View of a provider's configuration."""
    name: str
    api_key_env: str
    base_url: Optional[str] = None
    has_api_key: bool = False


@dataclass
class ConfigView:
    """View of the current ScribeState configuration."""
    default_provider: str = "openai"
    default_model: str = "gpt-4o"
    data_dir: str = ""
    episodic_enabled: bool = True
    semantic_enabled: bool = True
    procedural_enabled: bool = True
    style_update_interval: int = 10
    tools_enabled: list[str] = field(default_factory=list)
    providers: list[ProviderView] = field(default_factory=list)


# ── Tests ──

def _test_message_serialization():
    """Test Message serialization round-trip."""
    msg = Message(role=Role.USER, content="hello")
    import json
    json_str = json.dumps(msg.to_dict())
    deserialized = Message.from_dict(json.loads(json_str))
    assert deserialized.role == Role.USER
    assert deserialized.content == "hello"
    print("✓ test_message_serialization passed")


def _test_style_profile_default():
    """Test StyleProfile default values."""
    profile = StyleProfile()
    assert profile.tone == Tone.CASUAL
    assert profile.avg_sentence_length > 0.0
    print("✓ test_style_profile_default passed")


if __name__ == "__main__":
    _test_message_serialization()
    _test_style_profile_default()
    print("All tests passed!")
