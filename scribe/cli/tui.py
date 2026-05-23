"""
Interactive TUI for Scribe — simplified rich + prompt_toolkit version.

Shows a title bar, scrollable message history, input line, and status bar.
Streams agent response token-by-token.
"""

from __future__ import annotations

import asyncio
import sys
from enum import Enum
from typing import Optional

from scribe.api.state import ConfigUpdate, ScribeState


# Try optional rich/prompt_toolkit imports
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

# Try prompt_toolkit
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.keys import Keys
    from prompt_toolkit.styles import Style

    _HAS_PROMPT = True
except ImportError:
    _HAS_PROMPT = False


class TuiResult(Enum):
    """Outcome of a TUI run."""
    SWITCH_SESSION = "switch_session"
    QUIT = "quit"


class InteractiveMode:
    """
    Simplified interactive mode.
    Falls back to plain print/input if rich/prompt_toolkit not available.
    """

    def __init__(self, state: ScribeState, session_id: str) -> None:
        self.state = state
        self.session_id = session_id
        self.messages: list[tuple[str, str]] = []  # (role, content)

    def run(self) -> None:
        """Run the interactive loop."""
        if _HAS_RICH and _HAS_PROMPT:
            asyncio.run(self._run_rich())
        else:
            asyncio.run(self._run_fallback())

    async def _run_fallback(self) -> None:
        """Plain print/input fallback."""
        cfg = self.state.get_config_view()
        print("  Scribe — AI writing companion")
        print(f"  provider: {cfg.default_provider}  model: {cfg.default_model}")
        print(f"  session: {self.session_id[:8]}")
        print("  Type /help for commands, /quit to exit.\n")

        while True:
            try:
                text = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                continue

            if text in ("/quit", "/exit", "/q"):
                break

            if text == "/new":
                self.session_id = asyncio.run(self.state.create_session(None))
                print(f"  New session: {self.session_id[:8]}\n")
                continue

            if text in ("/sessions", "/ls"):
                sessions = asyncio.run(self.state.list_sessions())
                if not sessions:
                    print("  No saved sessions.")
                else:
                    for s in sessions:
                        marker = "*" if s.id == self.session_id else " "
                        updated = s.updated_at.strftime("%Y-%m-%d %H:%M")
                        print(
                            f"  {marker} {s.id[:8]}  {s.message_count:>4} msgs  "
                            f"{updated}  {s.title}"
                        )
                continue

            if text == "/status":
                cfg = self.state.get_config_view()
                has_key = self.state.has_api_key_blocking(cfg.default_provider)
                print(
                    f"  provider: {cfg.default_provider}  "
                    f"model: {cfg.default_model}  "
                    f"key: {'yes' if has_key else 'NO'}"
                )
                print(f"  session: {self.session_id[:8]}  messages: {len(self.messages)}")
                continue

            if text in ("/help", "/h"):
                print("\n  Commands:")
                print("  /help          Show this help")
                print("  /status        Show config and session info")
                print("  /skills        List available skills")
                print("  /provider <p>  Switch provider (openai|anthropic|deepseek)")
                print("  /model <name>  Switch model")
                print("  /clear         Clear current conversation")
                print("  /sessions      List saved sessions")
                print("  /new           Start new session")
                print("  /switch <id>   Resume a session")
                print("  /council       重新执行作家团向导")
                print("  /writers       查看可用作家列表")
                print("  /scope <范围>  查看/设置写作范围")
                print("  /theme         查看主题摘要")
                print("  /quit          Exit Scribe")
                print()
                continue

            if text == "/skills":
                skills = self.state.list_skills()
                if not skills:
                    print("  No skills loaded.")
                else:
                    print(f"  {len(skills)} skill(s) loaded:")
                    for s in skills:
                        print(f"  - {s.name}: {s.description}")
                continue

            if text.startswith("/provider "):
                arg = text.split(" ", 1)[1].strip()
                if arg not in ("openai", "anthropic", "deepseek"):
                    print(f"  Unknown provider: {arg}")
                    continue
                if not self.state.has_api_key_blocking(arg):
                    print(f"  No API key for {arg}. Set env var or run setup.")
                    continue
                cfg = asyncio.run(
                    self.state.update_config(ConfigUpdate(default_provider=arg))
                )
                print(f"  Provider set to {cfg.default_provider}.")
                continue

            if text.startswith("/model "):
                arg = text.split(" ", 1)[1].strip()
                cfg = asyncio.run(
                    self.state.update_config(ConfigUpdate(default_model=arg))
                )
                print(f"  Model set to {cfg.default_model}.")
                continue

            if text == "/clear":
                self.session_id = asyncio.run(self.state.create_session(None))
                self.messages.clear()
                print(f"  Conversation cleared. New session: {self.session_id[:8]}\n")
                continue

            if text.startswith("/switch "):
                arg = text.split(" ", 1)[1].strip()
                sessions = asyncio.run(self.state.list_sessions())
                found = next((s for s in sessions if s.id.startswith(arg)), None)
                if found:
                    self.session_id = found.id
                    self.messages.clear()
                    print(f"  Switched to session: {self.session_id[:8]}\n")
                else:
                    print(f"  Session not found: {arg}")
                continue

            if text == "/council":
                from scribe.council.wizard import CouncilWizard
                from scribe.bookshelf import Bookshelf
                bookshelf = Bookshelf()
                book = bookshelf.get_active()
                if not book:
                    print("  请先选书：scribe run --book <书名>")
                    continue
                try:
                    from scribe.llm import create_llm
                    import toml
                    from pathlib import Path
                    cfg_path = Path.home() / ".scribe" / "config.toml"
                    if cfg_path.exists():
                        cfg = toml.loads(cfg_path.read_text(encoding="utf-8"))
                        provider = cfg.get("core", {}).get("default_provider", "openai")
                        model_name = cfg.get("core", {}).get("default_model", "gpt-4o")
                    else:
                        provider, model_name = "openai", "gpt-4o"
                    llm = create_llm(provider, model_name)
                    wizard = CouncilWizard(llm, bookshelf)
                    result = asyncio.run(wizard.run(book))
                    print(result)
                except Exception as e:
                    print(f"  向导执行失败: {e}")
                continue

            if text == "/writers":
                print("  可用作家：")
                from scribe.council.router import WriterRouter
                for wid, genres in WriterRouter.WRITER_GENRES.items():
                    print(f"    {wid}: {', '.join(list(genres)[:3])}...")
                continue

            if text.startswith("/scope"):
                parts = text.split(" ", 1)
                if len(parts) > 1:
                    from scribe.council.wizard import ScopeParser
                    parser = ScopeParser()
                    scope = parser.parse(parts[1])
                    print(f"  范围：{scope.description}")
                    print(f"  模式：{scope.mode}")
                    if scope.target:
                        print(f"  目标：{scope.target}")
                else:
                    print("  用法：/scope <范围>")
                    print("  示例：/scope 第3章  /scope 大纲  /scope 整本")
                continue

            if text == "/theme":
                print("  主题摘要需要先执行 /council 向导")
                continue

            # Regular message — stream response
            print("Scribe> ", end="", flush=True)
            queue: asyncio.Queue[str] = asyncio.Queue()

            async def collect():
                while True:
                    try:
                        delta = await asyncio.wait_for(queue.get(), timeout=120.0)
                    except asyncio.TimeoutError:
                        break
                    print(delta, end="", flush=True)

            task = asyncio.create_task(collect())
            try:
                await self.state.send_message_streaming(
                    self.session_id, text, queue
                )
            finally:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            print()

    async def _run_rich(self) -> None:
        """Rich-based interactive mode."""
        console = Console()
        session_id = self.session_id
        messages: list[tuple[str, str]] = []

        style = Style.from_dict({
            "prompt": "#ansigreen bold",
            "": "#ffffff",
        })

        while True:
            # Print messages
            console.print(
                Panel(
                    f"[cyan]Scribe v0.1[/cyan]  session:[yellow]{session_id[:8]}[/yellow]",
                    title="",
                    border_style="cyan",
                )
            )

            for role, content in messages:
                color = "green" if role == "You" else "cyan" if role == "Scribe" else "red"
                console.print(f"[{color} bold]{role}>[/{color}] {content}")

            try:
                text = console.input("\n[green]>[/green] ")
            except (EOFError, KeyboardInterrupt):
                break

            text = text.strip()
            if not text:
                continue

            if text in ("/quit", "/exit", "/q"):
                break

            if text in ("/help", "/h"):
                table = Table(title="Commands", show_header=False, box=None)
                table.add_column("Command")
                table.add_column("Description")
                for cmd, desc in [
                    ("/help", "Show this help"),
                    ("/status", "Show config and session info"),
                    ("/skills", "List available skills"),
                    ("/provider <p>", "Switch provider"),
                    ("/model <name>", "Switch model"),
                    ("/clear", "Clear current conversation"),
                    ("/sessions", "List saved sessions"),
                    ("/new", "Start new session"),
                    ("/switch <id>", "Resume a session"),
                    ("/quit", "Exit Scribe"),
                ]:
                    table.add_row(f"[cyan]{cmd}[/cyan]", desc)
                console.print(table)
                continue

            if text == "/status":
                cfg = self.state.get_config_view()
                has_key = self.state.has_api_key_blocking(cfg.default_provider)
                console.print(
                    f"[cyan]provider:[/cyan] {cfg.default_provider}  "
                    f"[cyan]model:[/cyan] {cfg.default_model}  "
                    f"[cyan]key:[/cyan] {'[green]yes[/green]' if has_key else '[red]NO[/red]'}"
                )
                continue

            if text == "/skills":
                skills = self.state.list_skills()
                if not skills:
                    console.print("[yellow]No skills loaded.[/yellow]")
                else:
                    console.print(f"[green]{len(skills)} skill(s) loaded:[/green]")
                    for s in skills:
                        console.print(f"  [cyan]- {s.name}:[/cyan] {s.description}")
                continue

            if text == "/new":
                session_id = asyncio.run(self.state.create_session(None))
                messages.clear()
                console.print(f"[green]New session: {session_id[:8]}[/green]\n")
                continue

            if text in ("/sessions", "/ls"):
                sessions = asyncio.run(self.state.list_sessions())
                if not sessions:
                    console.print("[yellow]No saved sessions.[/yellow]")
                else:
                    for s in sessions:
                        marker = "[green]*[/green]" if s.id == session_id else " "
                        updated = s.updated_at.strftime("%Y-%m-%d %H:%M")
                        console.print(
                            f"  {marker} {s.id[:8]}  {s.message_count:>4} msgs  "
                            f"{updated}  {s.title}"
                        )
                continue

            if text == "/clear":
                session_id = asyncio.run(self.state.create_session(None))
                messages.clear()
                console.print(f"[green]Conversation cleared. New session: {session_id[:8]}[/green]\n")
                continue

            if text.startswith("/provider "):
                arg = text.split(" ", 1)[1].strip()
                if arg not in ("openai", "anthropic", "deepseek"):
                    console.print(f"[red]Unknown provider: {arg}[/red]")
                    continue
                if not self.state.has_api_key_blocking(arg):
                    console.print(f"[red]No API key for {arg}.[/red]")
                    continue
                cfg = await self.state.update_config(ConfigUpdate(default_provider=arg))
                console.print(f"[green]Provider set to {cfg.default_provider}.[/green]")
                continue

            if text.startswith("/model "):
                arg = text.split(" ", 1)[1].strip()
                cfg = await self.state.update_config(ConfigUpdate(default_model=arg))
                console.print(f"[green]Model set to {cfg.default_model}.[/green]")
                continue

            if text.startswith("/switch "):
                arg = text.split(" ", 1)[1].strip()
                sessions = await self.state.list_sessions()
                found = next((s for s in sessions if s.id.startswith(arg)), None)
                if found:
                    session_id = found.id
                    messages.clear()
                    console.print(f"[green]Switched to session: {session_id[:8]}[/green]\n")
                else:
                    console.print(f"[red]Session not found: {arg}[/red]")
                continue

            # Regular message
            messages.append(("You", text))

            console.print("[cyan]Scribe>[/cyan] ", end="", flush=True)
            queue: asyncio.Queue[str] = asyncio.Queue()
            async def stream_print():
                while True:
                    try:
                        delta = await asyncio.wait_for(queue.get(), timeout=120.0)
                    except asyncio.TimeoutError:
                        break
                    console.print(delta, end="", flush=True)

            task = asyncio.create_task(stream_print())
            try:
                response = await asyncio.wait_for(
                    self.state.send_message_streaming(session_id, text, queue),
                    timeout=300.0,
                )
                messages.append(("Scribe", response))
            except asyncio.TimeoutError:
                messages.append(("Scribe", "[timeout]"))
            except Exception as e:
                messages.append(("Error", str(e)))
            finally:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            console.print()
            self.session_id = session_id