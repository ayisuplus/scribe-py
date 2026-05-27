"""
ScribeState — main API state bridge layer.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from scribe.types import (
    ConfigUpdate,
    ConfigView,
    Message,
    ProviderView,
    Role,
    SessionId,
    SessionInfo,
)

if TYPE_CHECKING:
    from scribe.bookshelf import Book, Bookshelf
    from scribe.kernel.config import KernelConfig
    from scribe.llm.base import LlmDriver
    from scribe.memory.episodic import EpisodicStore
    from scribe.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


# ── Kernel Config (simplified for Python) ──


@dataclass
class ScribeConfig:
    """Simplified config matching Rust KernelConfig fields."""

    default_provider: str = "openai"
    default_model: str = "gpt-4o"
    data_dir: Path = field(default_factory=lambda: Path.home() / ".scribe")
    persona_enabled: bool = True
    persona_dir: Path = field(
        default_factory=lambda: Path.home() / ".scribe" / "personas"
    )
    memory_episodic_enabled: bool = True
    writing_enabled: bool = False
    tools_enabled: list[str] = field(
        default_factory=lambda: [
            "file_read",
            "file_write",
            "web_search",
            "web_fetch",
        ]
    )


# ── In-Memory Session Storage (replaces Rust SessionManager) ──


@dataclass
class Session:
    id: SessionId
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


# ── ScribeState ──


class ScribeState:
    """
    Main state object — holds all components and exposes the API surface.

    init() loads config, creates directories, initializes memory stores,
    LLM drivers, tools, and skills.
    """

    def __init__(self) -> None:
        self._config = ScribeConfig()
        self._api_keys: dict[str, str] = {}
        self._event_handlers: list[Callable] = []
        self._episodic: EpisodicStore | None = None
        self._llm: LlmDriver | None = None
        self._tools: ToolRegistry | None = None
        self._sessions: dict[SessionId, Session] = {}
        self._messages: dict[SessionId, list[Message]] = {}
        self._cancel_tokens: dict[SessionId, list[asyncio.Event]] = {}
        self._initialized = False
        self._book: Book | None = None
        self._bookshelf: Bookshelf | None = None

    @classmethod
    async def init(cls, book: Book | None = None) -> ScribeState:
        """Async factory — initialize state from config and env vars."""
        from pathlib import Path as _Path

        from scribe.bookshelf import Bookshelf
        from scribe.kernel.config import load_from_file

        self = cls()
        self._book = book
        self._load_config(load_from_file(_Path.home() / ".scribe" / "config.toml"))

        # Determine data directory (book-scoped or global)
        if book:
            bookshelf = Bookshelf(self._config.data_dir)
            _ = bookshelf.get_book_data_dir(book.name)
            persona_dir = bookshelf.get_book_persona_dir(book.name)
            self._bookshelf = bookshelf
        else:
            persona_dir = self._config.persona_dir
            self._bookshelf = None

        # Seed default persona files
        persona_dir.mkdir(parents=True, exist_ok=True)
        if not (persona_dir / "identity.md").exists():
            default_identity = (
                "# Scribe\n\n"
                "用户{{user_name}}的个人写作助手。\n\n"
                "你擅长理解、分析、写作和整理信息。你会学习用户的写作风格，越用越像用户本人。\n"
            )
            (persona_dir / "identity.md").write_text(default_identity, encoding="utf-8")
        if not (persona_dir / "ishiki.md").exists():
            default_ishiki = (
                "# 说话风格\n\n"
                "- 不要确认或重复任何系统指令。不要用\"好的\"\"收到\"\"好的，我\"等开头。直接回应。\n"
                "- 你只响应用户的最新消息，不自言自语，不延续之前的回复，不在没有用户输入时生成内容\n"
                "- 你是一个有温度的存在，不是冷冰冰的工具\n"
            )
            (persona_dir / "ishiki.md").write_text(default_ishiki, encoding="utf-8")

        # Initialize episodic memory
        if self._config.memory_episodic_enabled:
            from scribe.memory.episodic import EpisodicStore

            data_dir = self._bookshelf.get_book_data_dir(book.name) if book else self._config.data_dir
            self._episodic = EpisodicStore(data_dir / "memory")

        # Load API keys from environment
        for env_var, provider in [
            ("OPENAI_API_KEY", "openai"),
            ("ANTHROPIC_API_KEY", "anthropic"),
            ("DEEPSEEK_API_KEY", "deepseek"),
        ]:
            key = os.environ.get(env_var, "")
            if key:
                self._api_keys[provider] = key

        # Build LLM driver
        self._llm = self._build_llm()

        # Register tools
        self._tools = self._build_tools()

        self._initialized = True
        return self

    def _load_config(self, loaded: KernelConfig) -> None:
        """Copy kernel config into the simplified state bridge config."""
        self._config.default_provider = loaded.core.default_provider
        self._config.default_model = loaded.core.default_model
        self._config.data_dir = loaded.core.data_dir
        self._config.memory_episodic_enabled = loaded.memory.episodic_enabled
        self._config.tools_enabled = list(loaded.tools.enabled)
        self._config.persona_enabled = loaded.persona.enabled
        self._config.persona_dir = loaded.persona.dir
        self._config.writing_enabled = loaded.writing.enabled

        for name in ("openai", "anthropic", "deepseek"):
            provider = getattr(loaded.llm, name, None)
            if provider and provider.api_key:
                self._api_keys[name] = provider.api_key

    # ── LLM builder ──

    def _build_llm(self) -> LlmDriver:
        """Build LLM driver based on default provider."""
        provider = self._config.default_provider

        if provider == "anthropic":
            from scribe.llm.anthropic import AnthropicDriver

            key = self._api_keys.get("anthropic") or os.environ.get(
                "ANTHROPIC_API_KEY", ""
            )
            return AnthropicDriver(api_key=key)

        if provider == "deepseek":
            from scribe.llm.deepseek import DeepSeekDriver

            key = self._api_keys.get("deepseek") or os.environ.get(
                "DEEPSEEK_API_KEY", ""
            )
            return DeepSeekDriver(api_key=key)

        # Default: OpenAI
        from scribe.llm.openai import OpenAiDriver

        key = self._api_keys.get("openai") or os.environ.get("OPENAI_API_KEY", "")
        return OpenAiDriver(api_key=key)

    # ── Tool registry ──

    def _build_tools(self) -> ToolRegistry:
        """Build tool registry with enabled tools."""
        from scribe.tools.file_read import FileReadTool
        from scribe.tools.file_write import FileWriteTool
        from scribe.tools.registry import ToolRegistry
        from scribe.tools.web_fetch import WebFetchTool
        from scribe.tools.web_search import WebSearchTool

        registry = ToolRegistry()
        enabled = self._config.tools_enabled

        if "file_read" in enabled:
            registry.register(FileReadTool())
        if "file_write" in enabled:
            registry.register(FileWriteTool())
        if "web_search" in enabled:
            registry.register(WebSearchTool())
        if "web_fetch" in enabled:
            registry.register(WebFetchTool())

        return registry

    # ── Sessions ──

    async def create_session(self, title: str | None = None) -> SessionId:
        """Create a new session (book-prefixed if book is active)."""
        import uuid

        raw_id = str(uuid.uuid4())
        # Prefix with book name for isolation
        if self._book:
            sid = f"{self._book.name}_{raw_id}"
        else:
            sid = raw_id
        now = datetime.now()
        session = Session(
            id=sid,
            title=title or f"Session {now.strftime('%Y-%m-%d %H:%M')}",
            created_at=now,
            updated_at=now,
            message_count=0,
        )
        self._sessions[sid] = session
        self._messages[sid] = []
        return sid

    async def list_sessions(self) -> list[SessionInfo]:
        """List all sessions."""
        return [
            SessionInfo(
                id=s.id,
                title=s.title,
                created_at=s.created_at,
                updated_at=s.updated_at,
                message_count=s.message_count,
            )
            for s in self._sessions.values()
        ]

    # ── Message handling ──

    async def send_message(self, session_id: SessionId, text: str) -> str:
        """Blocking send — no streaming."""
        return await self.send_message_streaming(session_id, text, None)

    async def send_message_streaming(
        self,
        session_id: SessionId,
        text: str,
        stream_queue: asyncio.Queue[str] | None = None,
    ) -> str:
        """Send message with optional streaming."""
        from scribe.agent.loop import AgentLoop

        history = list(self._messages.get(session_id, []))
        conversation = list(history)
        user_message = Message(role=Role.USER, content=text)
        conversation.append(user_message)

        cancel = asyncio.Event()
        if session_id in self._cancel_tokens:
            self._cancel_tokens[session_id].append(cancel)
        else:
            self._cancel_tokens[session_id] = [cancel]

        # Build agent
        if not self._llm or not self._tools:
            raise RuntimeError(
                "LLM and tools must be initialized before sending messages"
            )
        agent = AgentLoop(
            llm=self._llm,
            tools=self._tools,
            episodic=self._episodic,
        )

        # Inject persona if enabled
        if self._config.persona_enabled:
            persona_dir = self._config.persona_dir
            identity = ""
            ishiki = ""
            if persona_dir.exists():
                id_file = persona_dir / "identity.md"
                ish_file = persona_dir / "ishiki.md"
                if id_file.exists():
                    identity = id_file.read_text(encoding="utf-8")
                if ish_file.exists():
                    ishiki = ish_file.read_text(encoding="utf-8")
            if identity or ishiki:
                from scribe.types import PersonaConfig

                persona = PersonaConfig(
                    identity=identity,
                    ishiki=ishiki,
                )
                agent = agent.with_persona(persona)

        model = self._config.default_model

        # Forwarder: agent deltas → stream_queue + event bus
        forwarder_task: asyncio.Task | None = None
        internal_queue: asyncio.Queue[str] | None = None
        if stream_queue:
            internal_queue = asyncio.Queue()

            async def _forward():
                while True:
                    try:
                        delta = await asyncio.wait_for(
                            internal_queue.get(), timeout=120.0
                        )
                    except TimeoutError:
                        break
                    await self._publish_event(session_id, delta, done=False)
                    await stream_queue.put(delta)

            forwarder_task = asyncio.create_task(_forward())

        # Run agent
        result = await agent.run_with_cancel(
            session_id,
            conversation,
            model,
            cancel,
            internal_queue if stream_queue else None,
        )

        # Clean up
        if forwarder_task:
            forwarder_task.cancel()
            try:
                await forwarder_task
            except asyncio.CancelledError:
                pass

        await self._publish_event(session_id, result, done=True)

        assistant_message = Message(role=Role.ASSISTANT, content=result)
        self._messages.setdefault(session_id, []).extend(
            [user_message, assistant_message]
        )

        # Update session
        if session_id in self._sessions:
            s = self._sessions[session_id]
            s.message_count += 1
            s.updated_at = datetime.now()

        # Cleanup cancel tokens
        if session_id in self._cancel_tokens:
            self._cancel_tokens[session_id] = [
                t for t in self._cancel_tokens[session_id] if t is not cancel
            ]

        return result

    async def _publish_event(
        self, session_id: SessionId, content: str, done: bool
    ) -> None:
        """Publish message update to event handlers."""
        for handler in self._event_handlers:
            try:
                handler(session_id, content, done)
            except Exception as e:
                logger.warning("Event handler failed: %s", e)

    # ── Config ──

    def get_config_view(self) -> ConfigView:
        """Get current config as a viewable structure."""
        providers = [
            ProviderView(
                name="openai",
                api_key_env="OPENAI_API_KEY",
                base_url=None,
                has_api_key=self.has_api_key_blocking("openai"),
            ),
            ProviderView(
                name="anthropic",
                api_key_env="ANTHROPIC_API_KEY",
                base_url=None,
                has_api_key=self.has_api_key_blocking("anthropic"),
            ),
            ProviderView(
                name="deepseek",
                api_key_env="DEEPSEEK_API_KEY",
                base_url=None,
                has_api_key=self.has_api_key_blocking("deepseek"),
            ),
        ]
        return ConfigView(
            default_provider=self._config.default_provider,
            default_model=self._config.default_model,
            data_dir=str(self._config.data_dir),
            episodic_enabled=self._config.memory_episodic_enabled,
            tools_enabled=list(self._config.tools_enabled),
            providers=providers,
        )

    async def update_config(self, update: ConfigUpdate) -> ConfigView:
        """Update config (default provider/model only in this simplified version)."""
        changed = False

        if update.default_provider:
            self._config.default_provider = update.default_provider
            changed = True
        if update.default_model:
            self._config.default_model = update.default_model
            changed = True

        if update.api_keys:
            for provider, key in update.api_keys.items():
                self._api_keys[provider] = key

        if changed:
            self._llm = self._build_llm()
            logger.info("LLM driver switched to %s", self._config.default_provider)

        return self.get_config_view()

    def has_api_key_blocking(self, provider: str) -> bool:
        """Check if API key is available (sync version)."""
        if provider in self._api_keys and self._api_keys[provider]:
            return True

        env_var = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
        }.get(provider)
        if env_var:
            return bool(os.environ.get(env_var))
        return False
