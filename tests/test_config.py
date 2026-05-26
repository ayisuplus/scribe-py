"""
Tests for scribe.kernel.config module.
"""

import tempfile
from pathlib import Path

import pytest

from scribe.kernel.config import (
    KernelConfig,
    PersonaSettings,
    PalaceSettings,
    load_from_file,
    save_to_file,
)


class TestKernelConfigDefaults:
    """Test KernelConfig default values."""

    def test_default_core_config(self):
        """Test default CoreConfig values."""
        config = KernelConfig()
        
        assert config.core.default_provider == "openai"
        assert config.core.default_model == "gpt-4o"
        assert "scribe" in str(config.core.data_dir)

    def test_default_llm_config(self):
        """Test default LLM config has all providers."""
        config = KernelConfig()
        
        assert config.llm.openai is not None
        assert config.llm.openai.api_key_env == "OPENAI_API_KEY"
        assert "api.openai.com" in (config.llm.openai.base_url or "")
        
        assert config.llm.anthropic is not None
        assert config.llm.anthropic.api_key_env == "ANTHROPIC_API_KEY"
        
        assert config.llm.deepseek is not None
        assert config.llm.deepseek.api_key_env == "DEEPSEEK_API_KEY"
        assert "api.deepseek.com" in (config.llm.deepseek.base_url or "")

    def test_default_memory_config(self):
        """Test default MemoryConfig values."""
        config = KernelConfig()
        
        assert config.memory.episodic_enabled is True
        assert config.memory.semantic_enabled is True
        assert config.memory.procedural_enabled is True
        assert config.memory.style_update_interval == 10

    def test_default_tools_config(self):
        """Test default ToolsConfig values."""
        config = KernelConfig()
        
        assert "file_read" in config.tools.enabled
        assert "file_write" in config.tools.enabled
        assert "web_search" in config.tools.enabled
        assert config.tools.web_search_provider == "duckduckgo"

    def test_default_writing_settings(self):
        """Test default WritingSettings values."""
        config = KernelConfig()
        
        assert config.writing.enabled is False
        assert config.writing.genre == "general"
        assert config.writing.audit_enabled is True
        assert config.writing.density_fun_per_chars == 300
        assert config.writing.density_hook_per_chars == 500
        assert config.writing.density_suspense_per_chars == 1500
        assert config.writing.paragraph_min_chars == 40
        assert config.writing.paragraph_target_min == 40
        assert config.writing.paragraph_target_max == 120
        assert config.writing.max_short_paragraphs == 5
        assert config.writing.max_consecutive_short == 3


class TestLoadFromFile:
    """Test loading configuration from TOML file."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def config_path(self, temp_dir):
        """Get path for config file."""
        return temp_dir / "config.toml"

    def test_load_nonexistent_file_returns_default(self, config_path):
        """Test that loading non-existent file returns defaults."""
        config = load_from_file(config_path)
        
        assert config.core.default_provider == "openai"

    def test_load_valid_config(self, config_path):
        """Test loading a valid TOML config file."""
        toml_content = """
[core]
default_provider = "anthropic"
default_model = "claude-3-sonnet"

[llm.openai]
api_key_env = "OPENAI_API_KEY"
base_url = "https://api.openai.com/v1"
"""
        config_path.write_text(toml_content, encoding="utf-8")
        
        config = load_from_file(config_path)
        
        assert config.core.default_provider == "anthropic"
        assert config.core.default_model == "claude-3-sonnet"
        assert config.llm.openai is not None


class TestSaveToFile:
    """Test saving configuration to TOML file."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def config_path(self, temp_dir):
        """Get path for config file."""
        return temp_dir / "config.toml"

    def test_save_and_load_roundtrip(self, config_path):
        """Test save and load round-trip."""
        config = KernelConfig()
        config.core.default_model = "gpt-4-turbo"
        
        save_to_file(config, config_path)
        
        assert config_path.exists()
        
        loaded = load_from_file(config_path)
        assert loaded.core.default_model == "gpt-4-turbo"

    def test_save_creates_parent_directories(self, temp_dir):
        """Test that save creates parent directories."""
        config = KernelConfig()
        config_path = temp_dir / "subdir" / "config.toml"
        
        save_to_file(config, config_path)
        
        assert config_path.exists()
        assert config_path.parent.exists()


class TestPersonaSettings:
    """Test PersonaSettings defaults."""

    def test_default_persona_settings(self):
        """Test default PersonaSettings values."""
        settings = PersonaSettings()
        
        assert settings.enabled is True
        assert "scribe" in str(settings.dir)
        assert "persona" in str(settings.dir)


class TestPalaceSettings:
    """Test PalaceSettings defaults."""

    def test_default_palace_settings(self):
        """Test default PalaceSettings values."""
        settings = PalaceSettings()

        assert settings.enabled is True
        assert settings.auto_mine is True
        assert settings.path is None
