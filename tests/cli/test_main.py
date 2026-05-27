"""
Tests for scribe.cli.main module.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import toml
from click.testing import CliRunner

import scribe
from scribe.cli.main import (
    auto_configure,
    cli,
    ensure_config,
    get_api_key_from_env,
    run,
    write_config,
)


def test_version_metadata_is_current():
    """Package, project, and CLI version should stay aligned."""
    pyproject = toml.loads(
        (Path(__file__).parents[2] / "pyproject.toml").read_text(encoding="utf-8")
    )
    result = CliRunner().invoke(cli, ["--version"])

    assert scribe.__version__ == "0.3.1"
    assert pyproject["project"]["version"] == "0.3.1"
    assert result.exit_code == 0
    assert "0.3.1" in result.output


class TestGetApiKeyFromEnv:
    """Test get_api_key_from_env function."""

    def test_openai_key(self):
        """Test getting OpenAI API key from environment."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test-key'}):
            result = get_api_key_from_env("openai")
            assert result == "sk-test-key"

    def test_anthropic_key(self):
        """Test getting Anthropic API key from environment."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test-key'}):
            result = get_api_key_from_env("anthropic")
            assert result == "sk-ant-test-key"

    def test_deepseek_key(self):
        """Test getting DeepSeek API key from environment."""
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'sk-ds-test-key'}):
            result = get_api_key_from_env("deepseek")
            assert result == "sk-ds-test-key"

    def test_missing_key(self):
        """Test getting missing API key returns None."""
        with patch.dict('os.environ', {}, clear=True):
            result = get_api_key_from_env("openai")
            assert result is None

    def test_unknown_provider(self):
        """Test getting API key for unknown provider returns None."""
        result = get_api_key_from_env("unknown")
        assert result is None


class TestAutoConfig:
    """Test auto_configure function."""

    def test_auto_config_openai(self, tmp_path):
        """Test auto-config with OpenAI key."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test'}, clear=True):
            with patch('scribe.cli.main.DATA_DIR', tmp_path):
                with patch('scribe.cli.main.CONFIG_PATH', tmp_path / "config.toml"):
                    result = auto_configure()
                    assert result["provider"] == "openai"
                    assert result["model"] == "gpt-4o"
                    assert (tmp_path / "config.toml").exists()
                    toml.loads((tmp_path / "config.toml").read_text(encoding="utf-8"))

    def test_auto_config_anthropic(self, tmp_path):
        """Test auto-config with Anthropic key."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-test'}, clear=True):
            with patch('scribe.cli.main.DATA_DIR', tmp_path):
                with patch('scribe.cli.main.CONFIG_PATH', tmp_path / "config.toml"):
                    result = auto_configure()
                    assert result["provider"] == "anthropic"
                    assert result["model"] == "claude-sonnet-4-6"

    def test_auto_config_deepseek(self, tmp_path):
        """Test auto-config with DeepSeek key."""
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'sk-ds-test'}, clear=True):
            with patch('scribe.cli.main.DATA_DIR', tmp_path):
                with patch('scribe.cli.main.CONFIG_PATH', tmp_path / "config.toml"):
                    result = auto_configure()
                    assert result["provider"] == "deepseek"
                    assert result["model"] == "deepseek-chat"

    def test_write_config_writes_parseable_toml(self, tmp_path):
        """Setup config should be valid TOML on Windows paths."""
        config_path = tmp_path / "config.toml"

        with patch('scribe.cli.main.DATA_DIR', tmp_path):
            with patch('scribe.cli.main.CONFIG_PATH', config_path):
                write_config(
                    {
                        "provider": "openai",
                        "model": "gpt-4o",
                        "api_key": "sk-test",
                    }
                )

        parsed = toml.loads(config_path.read_text(encoding="utf-8"))
        assert parsed["core"]["default_provider"] == "openai"


class TestEnsureConfig:
    """Test ensure_config function."""

    def test_ensure_config_exists(self, tmp_path):
        """Test ensure_config when config already exists."""
        config_path = tmp_path / "config.toml"
        config_path.write_text("[core]\n", encoding="utf-8")
        
        with patch('scribe.cli.main.CONFIG_PATH', config_path):
            # Should not raise
            ensure_config()

    def test_ensure_config_creates(self, tmp_path):
        """Test ensure_config creates config when missing."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test'}, clear=True):
            with patch('scribe.cli.main.DATA_DIR', tmp_path):
                with patch('scribe.cli.main.CONFIG_PATH', tmp_path / "config.toml"):
                    ensure_config()
                    assert (tmp_path / "config.toml").exists()

    def test_ensure_config_runs_setup_when_no_config_or_env(self, tmp_path):
        """Missing config and env keys should launch guided setup."""
        setup_result = {
            "provider": "openai",
            "model": "gpt-4o",
            "api_key": "sk-test",
        }

        with patch.dict('os.environ', {}, clear=True):
            with patch('scribe.cli.main.DATA_DIR', tmp_path):
                with patch('scribe.cli.main.CONFIG_PATH', tmp_path / "config.toml"):
                    with patch('scribe.cli.main.setup_wizard', return_value=setup_result) as wizard:
                        with patch('scribe.cli.main.write_config') as write_config:
                            ensure_config()

        wizard.assert_called_once_with()
        write_config.assert_called_once_with(setup_result)


class TestRunCommandFlow:
    """Test high-level run command routing."""

    def test_bare_cli_starts_guided_tui(self):
        """Running `scribe` with no subcommand should enter onboarding and TUI."""
        state = MagicMock()
        book = SimpleNamespace(name="Novel")
        onboarding = SimpleNamespace(book=book, intent="chat", startup_lines=["Quickstart"])
        mode = MagicMock()

        with patch("scribe.cli.main.ensure_config"):
            with patch("scribe.cli.main.Bookshelf"):
                with patch("scribe.cli.main.run_onboarding", return_value=onboarding) as onboard:
                    with patch("scribe.cli.main.ScribeState.init", new=AsyncMock(return_value=state)):
                        with patch("scribe.cli.main.resolve_session", new=AsyncMock(return_value="sid")):
                            with patch("scribe.cli.main.InteractiveMode", return_value=mode) as mode_cls:
                                result = CliRunner().invoke(cli, [])

        assert result.exit_code == 0
        onboard.assert_called_once()
        mode_cls.assert_called_once_with(state, "sid", startup_lines=["Quickstart"])
        mode.run.assert_called_once()


