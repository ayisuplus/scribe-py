"""
Scribe CLI — AI writing companion.

Usage:
  python -m scribe              Interactive TUI session
  python -m scribe -p "msg"    Single-shot prompt
  python -m scribe --setup      Configure API keys and model
  python -m scribe --mcp        MCP stdio JSON-RPC server
  python -m scribe --list-sessions  List saved sessions
  python -m scribe -s <id>     Resume a session
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

import click

from scribe.api.state import ConfigUpdate, ScribeState
from scribe.bookshelf import Book, Bookshelf
from scribe.cli.onboarding import run_onboarding
from scribe.cli.tui import InteractiveMode

logger = logging.getLogger(__name__)

DATA_DIR = Path.home() / ".scribe"
CONFIG_PATH = DATA_DIR / "config.toml"


# ── Config helpers ─────────────────────────────────────────────────────


def _toml_path(path: Path) -> str:
    """Return a TOML-safe path string."""
    return path.as_posix()


def get_api_key_from_env(provider: str) -> str | None:
    """Get API key from environment variable."""
    env_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
    }
    env_var = env_map.get(provider)
    if env_var:
        return os.environ.get(env_var)
    return None


def auto_configure() -> dict:
    """
    Auto-create config.toml if it doesn't exist and env keys are available.
    Returns the auto-detected provider/model.
    """
    provider = "openai"
    model = "gpt-4o"

    if os.environ.get("ANTHROPIC_API_KEY"):
        provider = "anthropic"
        model = "claude-sonnet-4-6"
    elif os.environ.get("DEEPSEEK_API_KEY"):
        provider = "deepseek"
        model = "deepseek-chat"

    # Write minimal config
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data_dir = _toml_path(DATA_DIR / "data")
    config_toml = f"""[core]
default_provider = "{provider}"
default_model = "{model}"
data_dir = "{data_dir}"

[llm.openai]
api_key_env = "OPENAI_API_KEY"
base_url = "https://api.openai.com/v1"

[llm.anthropic]
api_key_env = "ANTHROPIC_API_KEY"

[llm.deepseek]
api_key_env = "DEEPSEEK_API_KEY"
base_url = "https://api.deepseek.com/v1"

[memory]
episodic_enabled = true
semantic_enabled = true
procedural_enabled = true
style_update_interval = 10

[tools]
enabled = ["file_read", "file_write", "web_search", "web_fetch", "memory_search"]
"""
    CONFIG_PATH.write_text(config_toml, encoding="utf-8")
    print(f"  Auto-configured with {provider} / {model}\n", file=sys.stderr)
    return {"provider": provider, "model": model}


def ensure_config() -> None:
    """Ensure config exists. May run interactive setup wizard as side effect."""
    if CONFIG_PATH.exists():
        return

    has_env_keys = bool(
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
    )

    if has_env_keys:
        auto_configure()
        return

    # No config, no env keys: run setup before anything needs an LLM.
    print("  No configuration found. Launching setup wizard...\n", file=sys.stderr)
    result = setup_wizard()
    write_config(result)


# ── Setup wizard ────────────────────────────────────────────────────────


def setup_wizard() -> dict:
    """
    Interactive setup wizard. Returns dict with provider, model, api_key.
    """
    print("  Scribe Setup — configure your AI provider\n")

    existing = [
        (name, env_var)
        for name, env_var in [
            ("openai", "OPENAI_API_KEY"),
            ("anthropic", "ANTHROPIC_API_KEY"),
            ("deepseek", "DEEPSEEK_API_KEY"),
        ]
        if os.environ.get(env_var)
    ]

    if existing:
        print("  Found API keys in environment:")
        for name, env_var in existing:
            print(f"    {name}  (from ${env_var})")
        print()

    # Pick provider
    print("  Choose your AI provider:")
    print("    [1] OpenAI     (api.openai.com)")
    print("    [2] Anthropic  (api.anthropic.com)")
    print("    [3] DeepSeek   (api.deepseek.com)")
    print()

    while True:
        choice = input("  Select [1-3] (default: 1): ").strip()
        if choice in ("", "1"):
            provider = "openai"
        elif choice == "2":
            provider = "anthropic"
        elif choice == "3":
            provider = "deepseek"
        else:
            print("  Invalid choice. Enter 1, 2, or 3.")
            continue
        break

    # Resolve API key
    env_var_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
    }
    env_var = env_var_map[provider]
    api_key = os.environ.get(env_var, "")

    if not api_key:
        print()
        print(f"  Enter your {provider} API key")
        print("  (Find it at your provider's dashboard — won't echo)")
        import getpass

        api_key = getpass.getpass("  API key: ")
        api_key = api_key.strip()
        if not api_key:
            print("  Error: API key cannot be empty. Run `scribe --setup` to retry.")
            sys.exit(1)
        masked = (
            f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "****"
        )
        print(f"  Key set: {masked}")

    # Pick model
    defaults = {
        "openai": [
            ("gpt-4o", "GPT-4o — best overall"),
            ("gpt-4o-mini", "GPT-4o Mini — fast, affordable"),
        ],
        "anthropic": [
            ("claude-sonnet-4-6", "Claude Sonnet 4.6 — best balance"),
            ("claude-opus-4-7", "Claude Opus 4.7 — most capable"),
            ("claude-haiku-4-5-20251001", "Claude Haiku 4.5 — fastest"),
        ],
        "deepseek": [
            ("deepseek-chat", "DeepSeek Chat — general purpose"),
            ("deepseek-reasoner", "DeepSeek Reasoner — reasoning"),
        ],
    }

    print()
    print("  Choose default model (can change later with /model):")
    opts = defaults.get(provider, [])
    for i, (model_id, desc) in enumerate(opts, 1):
        print(f"    [{i}] {model_id} — {desc}")
    print("    [c] Custom — enter model name manually")

    while True:
        choice = input(f"  Select [1-{len(opts)}] or c (default: 1): ").strip()
        if choice in ("", "1"):
            model = opts[0][0]
        elif choice.lower() == "c":
            model = input("  Enter model name: ").strip()
            if not model:
                continue
        else:
            try:
                idx = int(choice)
                if 1 <= idx <= len(opts):
                    model = opts[idx - 1][0]
                else:
                    print("  Invalid choice.")
                    continue
            except ValueError:
                print("  Invalid choice.")
                continue
        break

    print()
    print("  Configuration complete!")
    print(f"    Provider : {provider}")
    print(f"    Model    : {model}")
    print()

    return {"provider": provider, "model": model, "api_key": api_key}


def write_config(result: dict) -> None:
    """Save setup result to config.toml."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    provider = result["provider"]
    model = result["model"]
    api_key = result.get("api_key", "")

    env_var_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
    }
    env_var = env_var_map[provider]

    if api_key:
        os.environ[env_var] = api_key

    data_dir = _toml_path(DATA_DIR / "data")
    config_toml = f"""[core]
default_provider = "{provider}"
default_model = "{model}"
data_dir = "{data_dir}"

[llm.openai]
api_key_env = "OPENAI_API_KEY"
base_url = "https://api.openai.com/v1"

[llm.anthropic]
api_key_env = "ANTHROPIC_API_KEY"

[llm.deepseek]
api_key_env = "DEEPSEEK_API_KEY"
base_url = "https://api.deepseek.com/v1"

[memory]
episodic_enabled = true
semantic_enabled = true
procedural_enabled = true
style_update_interval = 10

[tools]
enabled = ["file_read", "file_write", "web_search", "web_fetch", "memory_search"]
"""
    CONFIG_PATH.write_text(config_toml, encoding="utf-8")
    print(f"  Config saved to: {CONFIG_PATH}", file=sys.stderr)


# ── Session helpers ─────────────────────────────────────────────────────


async def resolve_session(state: ScribeState, requested: str | None) -> str:
    """Resolve session ID from prefix or create new."""
    if requested:
        sessions = await state.list_sessions()
        found = next((s for s in sessions if s.id.startswith(requested)), None)
        if found:
            return found.id
        print(f"  Session '{requested}' not found, creating new one.", file=sys.stderr)
    return await state.create_session(None)


async def list_sessions_cmd(state: ScribeState) -> None:
    """List all sessions."""
    sessions = await state.list_sessions()
    if not sessions:
        print("No saved sessions. Start with: python -m scribe")
        return
    print(f"{'ID':<10} {'Msgs':>6}  {'Updated':<20}  Title")
    print("-" * 65)
    for s in sessions:
        updated = s.updated_at.strftime("%Y-%m-%d %H:%M")
        print(
            f"{s.id[:8]:<10} {s.message_count:>6}  {updated:<20}  {s.title}"
        )


# ── Single-shot ────────────────────────────────────────────────────────


async def run_single_prompt(state: ScribeState, session_id: str, prompt: str) -> None:
    """Run a single-shot prompt with streaming output."""
    queue: asyncio.Queue[str] = asyncio.Queue()

    async def stream_drain():
        while True:
            try:
                delta = await asyncio.wait_for(queue.get(), timeout=120.0)
            except asyncio.TimeoutError:
                break
            print(delta, end="", flush=True)

    drain_task = asyncio.create_task(stream_drain())
    try:
        await state.send_message_streaming(session_id, prompt, queue)
    finally:
        drain_task.cancel()
        try:
            await drain_task
        except asyncio.CancelledError:
            pass
    print()


# ── Main CLI group ─────────────────────────────────────────────────────


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version="0.3.0", prog_name="scribe")
def cli(ctx: click.Context) -> None:
    """Scribe — AI writing companion."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(run)


@cli.command()
def setup() -> None:
    """Run the setup wizard to configure API keys and model."""
    result = setup_wizard()
    write_config(result)
    print("  Run `python -m scribe` to start your writing session!")


@cli.command()
@click.option("-p", "--prompt", help="Single-shot prompt (non-interactive)")
@click.option("-s", "--session", "session_id", help="Resume a specific session by ID prefix")
@click.option("--list-sessions", is_flag=True, help="List all saved sessions")
@click.option("--model", help="Model override for this invocation")
@click.option("--book", help="Book name to open (skips selection prompt)")
@click.option("--new-book", help="Create a new book and open it")
@click.option("--list-books", is_flag=True, help="List all books on the bookshelf")
@click.option("--council", is_flag=True, help="启动作家议会向导")
def run(
    prompt: str | None,
    session_id: str | None,
    list_sessions: bool,
    model: str | None,
    book: str | None,
    new_book: str | None,
    list_books: bool,
    council: bool,
) -> None:
    """
    Run Scribe.

    With no arguments: interactive TUI session
    """
    # Setup mode handled by separate command
    ensure_config()

    # Bookshelf operations
    bookshelf = Bookshelf()

    if list_books:
        books = bookshelf.list_books()
        if not books:
            print("  No books yet. Create one with: scribe run --new-book \"书名\"")
            return
        active = bookshelf.get_active()
        print("\n  📚 书架")
        print("  " + "─" * 30)
        for b in books:
            marker = " ← 当前" if active and b.name == active.name else ""
            print(f"  · {b.name} ({b.genre}){marker}")
        print()
        return

    # Select or create book
    selected_book: Book | None = None
    startup_lines: list[str] | None = None

    if new_book:
        description = click.prompt("  简介 (可选)", default="", show_default=False)
        genre = click.prompt("  类型", default="fiction", show_default=True)
        selected_book = bookshelf.create(new_book, description=description, genre=genre)
        print(f"\n  📖 已创建: {new_book}")
    elif book:
        selected_book = bookshelf.get_book(book)
        if not selected_book:
            print(f"  Book not found: {book}", file=sys.stderr)
            sys.exit(1)
        bookshelf.select(book)
    else:
        onboarding = run_onboarding(bookshelf)
        selected_book = onboarding.book
        startup_lines = onboarding.startup_lines

    # 向导模式（选书后自动进入）
    if selected_book and council:
        from scribe.council.wizard import CouncilWizard
        try:
            from scribe.llm import create_llm
            if CONFIG_PATH.exists():
                import toml
                cfg = toml.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                provider = cfg.get("core", {}).get("default_provider", "openai")
                model_name = cfg.get("core", {}).get("default_model", "gpt-4o")
            else:
                provider, model_name = "openai", "gpt-4o"
            llm = create_llm(provider, model_name)
            wizard = CouncilWizard(llm, bookshelf)
            result = asyncio.run(wizard.run(selected_book))
            print(result)
            return
        except Exception as e:
            print(f"  向导模式启动失败: {e}", file=sys.stderr)
            print("  进入普通TUI模式...", file=sys.stderr)

    # Init state with book scope
    try:
        state = asyncio.run(ScribeState.init(book=selected_book))
    except Exception as e:
        print(f"  Failed to initialize Scribe: {e}", file=sys.stderr)
        print("  Try `python -m scribe setup` first.", file=sys.stderr)
        sys.exit(1)

    async def _prepare_state() -> str | None:
        """Batch async startup operations to avoid multiple event-loop creations."""
        if model:
            await state.update_config(
                ConfigUpdate(default_provider=None, default_model=model)
            )
        if list_sessions:
            await list_sessions_cmd(state)
            return None
        return await resolve_session(state, session_id)

    sid = asyncio.run(_prepare_state())
    if sid is None:
        return

    if prompt:
        asyncio.run(run_single_prompt(state, sid, prompt))
        return

    if startup_lines is None:
        mode = InteractiveMode(state, sid)
    else:
        mode = InteractiveMode(state, sid, startup_lines=startup_lines)
    mode.run()


def main() -> None:
    """Console script entry point."""
    cli()


if __name__ == "__main__":
    main()
