"""
Kernel configuration management.

Ports scribe-kernel/src/config.rs to Python with TOML loading/saving.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import toml


def _default_data_dir() -> Path:
    """Get the default data directory."""
    home = Path.home() if Path.home() != Path(".") else Path.cwd()
    return home / ".scribe" / "data"


def _default_persona_dir() -> Path:
    """Get the default persona directory."""
    home = Path.home() if Path.home() != Path(".") else Path.cwd()
    return home / ".scribe" / "persona"


def _default_skills_dir() -> Path:
    """Get the default skills directory."""
    home = Path.home() if Path.home() != Path(".") else Path.cwd()
    return home / ".scribe" / "skills"


@dataclass
class CoreConfig:
    """Core kernel configuration."""

    default_provider: str = "openai"
    default_model: str = "gpt-4o"
    data_dir: Path = field(default_factory=_default_data_dir)


@dataclass
class ProviderConfig:
    """LLM provider configuration."""

    api_key_env: str
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None


@dataclass
class LlmConfig:
    """LLM configuration with multiple providers."""

    openai: ProviderConfig | None = None
    anthropic: ProviderConfig | None = None
    deepseek: ProviderConfig | None = None


@dataclass
class MemoryConfig:
    """Memory system configuration."""

    episodic_enabled: bool = True
    semantic_enabled: bool = True
    procedural_enabled: bool = True
    style_update_interval: int = 10


@dataclass
class ToolsConfig:
    """Tools configuration."""

    enabled: list[str] = field(
        default_factory=lambda: [
            "file_read",
            "file_write",
            "web_search",
            "web_fetch",
            "memory_search",
            "palace_search",
        ]
    )
    web_search_provider: str = "duckduckgo"


@dataclass
class PersonaSettings:
    """Persona system settings."""

    enabled: bool = True
    dir: Path = field(default_factory=_default_persona_dir)


@dataclass
class WritingSettings:
    """Writing methodology settings."""

    enabled: bool = False
    genre: str = "general"
    audit_enabled: bool = True
    density_fun_per_chars: int = 300
    density_hook_per_chars: int = 500
    density_suspense_per_chars: int = 1500
    paragraph_min_chars: int = 40
    paragraph_target_min: int = 40
    paragraph_target_max: int = 120
    max_short_paragraphs: int = 5
    max_consecutive_short: int = 3


@dataclass
class PalaceSettings:
    """MemPalace integration settings."""

    enabled: bool = True
    path: str | None = None  # default: ~/.mempalace/palace
    auto_mine: bool = True
    default_wing: str | None = None
    default_room: str | None = None


def _default_llm_config() -> LlmConfig:
    """Create default LLM configuration."""
    return LlmConfig(
        openai=ProviderConfig(
            api_key_env="OPENAI_API_KEY",
            api_key=None,
            base_url="https://api.openai.com/v1",
            model=None,
        ),
        anthropic=ProviderConfig(
            api_key_env="ANTHROPIC_API_KEY",
            api_key=None,
            base_url=None,
            model=None,
        ),
        deepseek=ProviderConfig(
            api_key_env="DEEPSEEK_API_KEY",
            api_key=None,
            base_url="https://api.deepseek.com/v1",
            model=None,
        ),
    )


@dataclass
class KernelConfig:
    """Top-level kernel configuration."""

    core: CoreConfig = field(default_factory=CoreConfig)
    llm: LlmConfig = field(default_factory=_default_llm_config)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    tools: ToolsConfig = field(default_factory=ToolsConfig)
    persona: PersonaSettings = field(default_factory=PersonaSettings)
    writing: WritingSettings = field(default_factory=WritingSettings)
    palace: PalaceSettings = field(default_factory=PalaceSettings)


def load_from_file(path: Path) -> KernelConfig:
    """
    Load kernel configuration from a TOML file.

    If the file doesn't exist, returns default configuration.
    Warns about plaintext API keys.
    """
    if path.exists():
        content = path.read_text(encoding="utf-8")
        config = toml.loads(content)

        # Convert Path objects
        if "core" in config and "data_dir" in config["core"]:
            config["core"]["data_dir"] = Path(config["core"]["data_dir"])
        if "persona" in config and "dir" in config["persona"]:
            config["persona"]["dir"] = Path(config["persona"]["dir"])

        # Reconstruct the dataclass from dict
        result = _dict_to_config(config)

        # Warn about plaintext API keys
        for name, provider in [
            ("openai", result.llm.openai),
            ("anthropic", result.llm.anthropic),
            ("deepseek", result.llm.deepseek),
        ]:
            if provider and provider.api_key and provider.api_key.strip():
                print(
                    f"Warning: Plaintext API key for '{name}' in config.toml is deprecated. "
                    f"Use environment variable {provider.api_key_env} instead."
                )

        return result
    else:
        return KernelConfig()


def _dict_to_config(d: dict) -> KernelConfig:
    """Convert a dictionary to KernelConfig."""
    core = CoreConfig(
        default_provider=d.get("core", {}).get("default_provider", "openai"),
        default_model=d.get("core", {}).get("default_model", "gpt-4o"),
        data_dir=Path(d.get("core", {}).get("data_dir", _default_data_dir())),
    )

    llm_config = d.get("llm", {})
    llm = LlmConfig()

    if "openai" in llm_config:
        p = llm_config["openai"]
        llm.openai = ProviderConfig(
            api_key_env=p.get("api_key_env", "OPENAI_API_KEY"),
            api_key=p.get("api_key"),
            base_url=p.get("base_url"),
            model=p.get("model"),
        )

    if "anthropic" in llm_config:
        p = llm_config["anthropic"]
        llm.anthropic = ProviderConfig(
            api_key_env=p.get("api_key_env", "ANTHROPIC_API_KEY"),
            api_key=p.get("api_key"),
            base_url=p.get("base_url"),
            model=p.get("model"),
        )

    if "deepseek" in llm_config:
        p = llm_config["deepseek"]
        llm.deepseek = ProviderConfig(
            api_key_env=p.get("api_key_env", "DEEPSEEK_API_KEY"),
            api_key=p.get("api_key"),
            base_url=p.get("base_url"),
            model=p.get("model"),
        )

    mem = d.get("memory", {})
    memory = MemoryConfig(
        episodic_enabled=mem.get("episodic_enabled", True),
        semantic_enabled=mem.get("semantic_enabled", True),
        procedural_enabled=mem.get("procedural_enabled", True),
        style_update_interval=mem.get("style_update_interval", 10),
    )

    tools = d.get("tools", {})
    tools_cfg = ToolsConfig(
        enabled=tools.get(
            "enabled",
            ["file_read", "file_write", "web_search", "web_fetch", "memory_search"],
        ),
        web_search_provider=tools.get("web_search_provider", "duckduckgo"),
    )

    persona = d.get("persona", {})
    persona_settings = PersonaSettings(
        enabled=persona.get("enabled", True),
        dir=Path(persona.get("dir", _default_persona_dir())),
    )

    writing = d.get("writing", {})
    writing_settings = WritingSettings(
        enabled=writing.get("enabled", False),
        genre=writing.get("genre", "general"),
        audit_enabled=writing.get("audit_enabled", True),
        density_fun_per_chars=writing.get("density_fun_per_chars", 300),
        density_hook_per_chars=writing.get("density_hook_per_chars", 500),
        density_suspense_per_chars=writing.get("density_suspense_per_chars", 1500),
        paragraph_min_chars=writing.get("paragraph_min_chars", 40),
        paragraph_target_min=writing.get("paragraph_target_min", 40),
        paragraph_target_max=writing.get("paragraph_target_max", 120),
        max_short_paragraphs=writing.get("max_short_paragraphs", 5),
        max_consecutive_short=writing.get("max_consecutive_short", 3),
    )

    palace = d.get("palace", {})
    palace_settings = PalaceSettings(
        enabled=palace.get("enabled", True),
        path=palace.get("path"),
        auto_mine=palace.get("auto_mine", True),
        default_wing=palace.get("default_wing"),
        default_room=palace.get("default_room"),
    )

    return KernelConfig(
        core=core,
        llm=llm,
        memory=memory,
        tools=tools_cfg,
        persona=persona_settings,
        writing=writing_settings,
        palace=palace_settings,
    )


def save_to_file(config: KernelConfig, path: Path) -> None:
    """Save kernel configuration to a TOML file."""
    path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict
    d: dict[str, Any] = {
        "core": {
            "default_provider": config.core.default_provider,
            "default_model": config.core.default_model,
            "data_dir": str(config.core.data_dir),
        },
        "llm": {},
        "memory": {
            "episodic_enabled": config.memory.episodic_enabled,
            "semantic_enabled": config.memory.semantic_enabled,
            "procedural_enabled": config.memory.procedural_enabled,
            "style_update_interval": config.memory.style_update_interval,
        },
        "tools": {
            "enabled": config.tools.enabled,
            "web_search_provider": config.tools.web_search_provider,
        },
        "persona": {
            "enabled": config.persona.enabled,
            "dir": str(config.persona.dir),
        },
        "writing": {
            "enabled": config.writing.enabled,
            "genre": config.writing.genre,
            "audit_enabled": config.writing.audit_enabled,
            "density_fun_per_chars": config.writing.density_fun_per_chars,
            "density_hook_per_chars": config.writing.density_hook_per_chars,
            "density_suspense_per_chars": config.writing.density_suspense_per_chars,
            "paragraph_min_chars": config.writing.paragraph_min_chars,
            "paragraph_target_min": config.writing.paragraph_target_min,
            "paragraph_target_max": config.writing.paragraph_target_max,
            "max_short_paragraphs": config.writing.max_short_paragraphs,
            "max_consecutive_short": config.writing.max_consecutive_short,
        },
    }

    if config.llm.openai:
        d["llm"]["openai"] = {
            "api_key_env": config.llm.openai.api_key_env,
            "api_key": config.llm.openai.api_key,
            "base_url": config.llm.openai.base_url,
            "model": config.llm.openai.model,
        }

    if config.llm.anthropic:
        d["llm"]["anthropic"] = {
            "api_key_env": config.llm.anthropic.api_key_env,
            "api_key": config.llm.anthropic.api_key,
            "base_url": config.llm.anthropic.base_url,
            "model": config.llm.anthropic.model,
        }

    if config.llm.deepseek:
        d["llm"]["deepseek"] = {
            "api_key_env": config.llm.deepseek.api_key_env,
            "api_key": config.llm.deepseek.api_key,
            "base_url": config.llm.deepseek.base_url,
            "model": config.llm.deepseek.model,
        }

    content = toml.dumps(d)
    path.write_text(content, encoding="utf-8")
