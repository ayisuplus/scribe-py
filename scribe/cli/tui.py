"""
Interactive TUI for Scribe.

The renderer can be rich or plain text, but command handling stays shared.
"""

from __future__ import annotations

import asyncio
import importlib.util
from collections.abc import Callable
from enum import Enum

from scribe import __version__
from scribe.api.state import ConfigUpdate, ScribeState

try:
    from rich.console import Console
    from rich.panel import Panel

    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

_HAS_PROMPT = importlib.util.find_spec("prompt_toolkit") is not None


class TuiResult(Enum):
    """Outcome of a TUI run."""

    SWITCH_SESSION = "switch_session"
    QUIT = "quit"


class CommandOutcome(Enum):
    """Outcome of processing a command line."""

    HANDLED = "handled"
    QUIT = "quit"
    NOT_COMMAND = "not_command"


HELP_LINES = [
    "",
    "  Commands:",
    "  /help          Show this help",
    "  /status        Show config and session info",
    "  /provider <p>  Switch provider (openai|anthropic|deepseek)",
    "  /model <name>  Switch model",
    "  /clear         Clear current conversation",
    "  /sessions      List saved sessions",
    "  /new           Start new session",
    "  /switch <id>   Resume a session",
    "  /council       Run writer council wizard",
    "  /writers       List available writers",
    "  /scope <range> Parse writing scope",
    "  /theme         Show current theme summary",
    "  /onboard       Show quickstart guidance",
    "  /quit          Exit Scribe",
    "",
]


class InteractiveMode:
    """Interactive mode with shared async command handling."""

    def __init__(
        self,
        state: ScribeState,
        session_id: str,
        startup_lines: list[str] | None = None,
    ) -> None:
        self.state = state
        self.session_id = session_id
        self.startup_lines = startup_lines or self._default_startup_lines()
        self.messages: list[tuple[str, str]] = []

    def run(self) -> None:
        """Run the interactive loop."""
        if _HAS_RICH and _HAS_PROMPT:
            asyncio.run(self._run_rich())
        else:
            asyncio.run(self._run_fallback())

    async def _handle_command(
        self,
        text: str,
        emit: Callable[[str], None],
    ) -> CommandOutcome:
        """Handle slash commands shared by rich and fallback renderers."""
        if not text.startswith("/"):
            return CommandOutcome.NOT_COMMAND

        if text in ("/quit", "/exit", "/q"):
            return CommandOutcome.QUIT

        if text == "/new":
            self.session_id = await self.state.create_session(None)
            self.messages.clear()
            emit(f"  New session: {self.session_id[:8]}\n")
            return CommandOutcome.HANDLED

        if text in ("/sessions", "/ls"):
            sessions = await self.state.list_sessions()
            if not sessions:
                emit("  No saved sessions.")
            else:
                for s in sessions:
                    marker = "*" if s.id == self.session_id else " "
                    updated = s.updated_at.strftime("%Y-%m-%d %H:%M")
                    emit(
                        f"  {marker} {s.id[:8]}  {s.message_count:>4} msgs  "
                        f"{updated}  {s.title}"
                    )
            return CommandOutcome.HANDLED

        if text == "/status":
            cfg = self.state.get_config_view()
            has_key = self.state.has_api_key_blocking(cfg.default_provider)
            emit(
                f"  provider: {cfg.default_provider}  "
                f"model: {cfg.default_model}  "
                f"key: {'yes' if has_key else 'NO'}"
            )
            emit(f"  session: {self.session_id[:8]}  messages: {len(self.messages)}")
            return CommandOutcome.HANDLED

        if text in ("/help", "/h"):
            for line in HELP_LINES:
                emit(line)
            return CommandOutcome.HANDLED

        if text in ("/onboard", "/start"):
            for line in self.startup_lines:
                emit(line)
            return CommandOutcome.HANDLED

        if text.startswith("/provider "):
            arg = text.split(" ", 1)[1].strip()
            if arg not in ("openai", "anthropic", "deepseek"):
                emit(f"  Unknown provider: {arg}")
                return CommandOutcome.HANDLED
            if not self.state.has_api_key_blocking(arg):
                emit(f"  No API key for {arg}. Set env var or run setup.")
                return CommandOutcome.HANDLED
            cfg = await self.state.update_config(ConfigUpdate(default_provider=arg))
            emit(f"  Provider set to {cfg.default_provider}.")
            return CommandOutcome.HANDLED

        if text.startswith("/model "):
            arg = text.split(" ", 1)[1].strip()
            cfg = await self.state.update_config(ConfigUpdate(default_model=arg))
            emit(f"  Model set to {cfg.default_model}.")
            return CommandOutcome.HANDLED

        if text == "/clear":
            self.session_id = await self.state.create_session(None)
            self.messages.clear()
            emit(f"  Conversation cleared. New session: {self.session_id[:8]}\n")
            return CommandOutcome.HANDLED

        if text.startswith("/switch "):
            arg = text.split(" ", 1)[1].strip()
            sessions = await self.state.list_sessions()
            found = next((s for s in sessions if s.id.startswith(arg)), None)
            if found:
                self.session_id = found.id
                self.messages.clear()
                emit(f"  Switched to session: {self.session_id[:8]}\n")
            else:
                emit(f"  Session not found: {arg}")
            return CommandOutcome.HANDLED

        if text == "/council":
            await self._run_council(emit)
            return CommandOutcome.HANDLED

        if text == "/writers":
            from scribe.council.router import WriterRouter

            emit("  Available writers:")
            for wid, genres in WriterRouter.WRITER_GENRES.items():
                emit(f"    {wid}: {', '.join(list(genres)[:3])}...")
            return CommandOutcome.HANDLED

        if text.startswith("/scope"):
            parts = text.split(" ", 1)
            if len(parts) > 1:
                from scribe.council.wizard import ScopeParser

                scope = ScopeParser().parse(parts[1])
                emit(f"  Scope: {scope.description}")
                emit(f"  Mode: {scope.mode}")
                if scope.target:
                    emit(f"  Target: {scope.target}")
            else:
                emit("  Usage: /scope <range>")
                emit("  Examples: /scope 第3章  /scope 大纲  /scope 整本")
            return CommandOutcome.HANDLED

        if text == "/theme":
            emit("  Theme summary is available after running /council.")
            return CommandOutcome.HANDLED

        emit(f"  Unknown command: {text}")
        return CommandOutcome.HANDLED

    def _default_startup_lines(self) -> list[str]:
        """Build quickstart guidance without requiring CLI onboarding state."""
        return [
            "Quickstart",
            "  Try: write chapter 1 opening in 800 words",
            "  Try: summarize my current plot and list contradictions",
            "  Commands: /help  /council  /writers  /status  /quit",
        ]

    async def _run_council(self, emit: Callable[[str], None]) -> None:
        """Run writer council against the active book."""
        from scribe.bookshelf import Bookshelf
        from scribe.council.wizard import CouncilWizard
        from scribe.llm import create_llm

        bookshelf = Bookshelf()
        book = bookshelf.get_active()
        if not book:
            emit("  Select a book first: scribe run --book <name>")
            return

        try:
            cfg = self.state.get_config_view()
            llm = create_llm(cfg.default_provider, cfg.default_model)
            wizard = CouncilWizard(llm, bookshelf)
            result = await wizard.run(book)
            emit(result)
        except Exception as e:
            emit(f"  Council wizard failed: {e}")

    async def _send_regular_message(
        self,
        text: str,
        emit: Callable[[str], None],
        emit_delta: Callable[[str], None] | None = None,
    ) -> None:
        """Stream a regular user message to the current session."""
        if emit_delta is None:
            emit_delta = emit
        emit_delta("Scribe> ")
        queue: asyncio.Queue[str] = asyncio.Queue()

        async def collect() -> None:
            while True:
                try:
                    delta = await asyncio.wait_for(queue.get(), timeout=120.0)
                except TimeoutError:
                    break
                emit_delta(delta)

        task = asyncio.create_task(collect())
        try:
            response = await self.state.send_message_streaming(
                self.session_id,
                text,
                queue,
            )
            while not queue.empty():
                emit_delta(queue.get_nowait())
            self.messages.append(("You", text))
            self.messages.append(("Scribe", response))
        except Exception as e:
            self.messages.append(("Error", str(e)))
            emit(str(e))
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        emit("")

    async def _run_fallback(self) -> None:
        """Plain print/input fallback."""
        cfg = self.state.get_config_view()
        print("  Scribe - AI writing companion")
        print(f"  provider: {cfg.default_provider}  model: {cfg.default_model}")
        print(f"  session: {self.session_id[:8]}")
        print("  Type /help for commands, /quit to exit.\n")
        for line in self.startup_lines:
            print(line)
        print()

        while True:
            try:
                text = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                continue

            outcome = await self._handle_command(text, print)
            if outcome == CommandOutcome.QUIT:
                break
            if outcome == CommandOutcome.HANDLED:
                continue

            await self._send_regular_message(
                text,
                lambda value: print(value),
                lambda value: print(value, end="", flush=True),
            )

    async def _run_rich(self) -> None:
        """Rich-based interactive mode."""
        console = Console()
        shown_startup = False

        while True:
            console.print(
                Panel(
                    f"[cyan]Scribe v{__version__}[/cyan]  session:[yellow]{self.session_id[:8]}[/yellow]",
                    title="",
                    border_style="cyan",
                )
            )

            if not shown_startup:
                for line in self.startup_lines:
                    console.print(line)
                shown_startup = True

            for role, content in self.messages:
                color = (
                    "green" if role == "You" else "cyan" if role == "Scribe" else "red"
                )
                console.print(f"[{color} bold]{role}>[/{color}] {content}")

            try:
                text = console.input("\n[green]>[/green] ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                continue

            outcome = await self._handle_command(text, console.print)
            if outcome == CommandOutcome.QUIT:
                break
            if outcome == CommandOutcome.HANDLED:
                continue

            await self._send_regular_message(
                text,
                console.print,
                lambda value: console.print(value, end=""),
            )
