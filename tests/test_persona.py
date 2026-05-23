"""
Tests for scribe.memory.persona module.
"""

import tempfile
from pathlib import Path

import pytest

from scribe.types import PersonaConfig, ConsciousnessMode
from scribe.memory.persona import PersonaLoader


class TestPersonaLoader:
    """Test PersonaLoader functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_load_basic(self, temp_dir):
        """Test loading basic persona files."""
        identity_path = temp_dir / "identity.md"
        ishiki_path = temp_dir / "ishiki.md"
        
        identity_path.write_text("# Test Identity\nUser assistant", encoding="utf-8")
        ishiki_path.write_text("# Style\nBe concise", encoding="utf-8")
        
        config = PersonaLoader.load(temp_dir)
        
        assert "Test Identity" in config.identity
        assert "Style" in config.ishiki
        assert config.yuan is None
        assert config.consciousness_mode == ConsciousnessMode.NONE

    def test_load_with_yuan_mood(self, temp_dir):
        """Test loading persona with yuan.md in MOOD mode."""
        identity_path = temp_dir / "identity.md"
        ishiki_path = temp_dir / "ishiki.md"
        yuan_path = temp_dir / "yuan.md"
        
        identity_path.write_text("id", encoding="utf-8")
        ishiki_path.write_text("style", encoding="utf-8")
        yuan_path.write_text("## MOOD\n\nVibe: happy", encoding="utf-8")
        
        config = PersonaLoader.load(temp_dir)
        
        assert config.yuan is not None
        assert config.consciousness_mode == ConsciousnessMode.MOOD

    def test_load_with_yuan_reflect(self, temp_dir):
        """Test loading persona with yuan.md in REFLECT mode."""
        identity_path = temp_dir / "identity.md"
        ishiki_path = temp_dir / "ishiki.md"
        yuan_path = temp_dir / "yuan.md"
        
        identity_path.write_text("id", encoding="utf-8")
        ishiki_path.write_text("style", encoding="utf-8")
        yuan_path.write_text("## REFLECT\n\nPremise: Test", encoding="utf-8")
        
        config = PersonaLoader.load(temp_dir)
        
        assert config.yuan is not None
        assert config.consciousness_mode == ConsciousnessMode.REFLECT

    def test_load_missing_identity_raises(self, temp_dir):
        """Test that missing identity.md raises FileNotFoundError."""
        ishiki_path = temp_dir / "ishiki.md"
        ishiki_path.write_text("style", encoding="utf-8")
        
        with pytest.raises(FileNotFoundError):
            PersonaLoader.load(temp_dir)

    def test_load_missing_ishiki_raises(self, temp_dir):
        """Test that missing ishiki.md raises FileNotFoundError."""
        identity_path = temp_dir / "identity.md"
        identity_path.write_text("id", encoding="utf-8")
        
        with pytest.raises(FileNotFoundError):
            PersonaLoader.load(temp_dir)


class TestBuildPrompt:
    """Test build_prompt functionality."""

    def test_build_prompt_replaces_user_name(self):
        """Test that {{user_name}} is replaced."""
        config = PersonaConfig(
            identity="我是{{user_name}}的助手。",
            ishiki="说话简洁。",
        )
        
        prompt = PersonaLoader.build_prompt(config, "小明")
        
        assert "小明" in prompt
        assert "{{user_name}}" not in prompt

    def test_build_prompt_with_mood_mode(self):
        """Test prompt includes yuan content in MOOD mode."""
        config = PersonaConfig(
            identity="Identity",
            ishiki="Style",
            yuan="## MOOD\n\nVibe: happy",
            consciousness_mode=ConsciousnessMode.MOOD,
        )
        
        prompt = PersonaLoader.build_prompt(config, "User")
        
        assert "Identity" in prompt
        assert "Style" in prompt
        assert "## MOOD" in prompt

    def test_build_prompt_with_reflect_mode(self):
        """Test prompt includes yuan content in REFLECT mode."""
        config = PersonaConfig(
            identity="Identity",
            ishiki="Style",
            yuan="## REFLECT\n\nPremise: Test",
            consciousness_mode=ConsciousnessMode.REFLECT,
        )
        
        prompt = PersonaLoader.build_prompt(config, "User")
        
        assert "## REFLECT" in prompt

    def test_build_prompt_no_yuan_when_none_mode(self):
        """Test yuan content not included when mode is NONE."""
        config = PersonaConfig(
            identity="Identity",
            ishiki="Style",
            yuan="Some yuan content",
            consciousness_mode=ConsciousnessMode.NONE,
        )
        
        prompt = PersonaLoader.build_prompt(config, "User")
        
        assert "Some yuan content" not in prompt


class TestDetectConsciousnessMode:
    """Test consciousness mode detection via loading."""

    def test_detect_mood_mode(self, temp_dir):
        """Test MOOD mode detection with ## MOOD."""
        identity_path = temp_dir / "identity.md"
        ishiki_path = temp_dir / "ishiki.md"
        yuan_path = temp_dir / "yuan.md"
        
        identity_path.write_text("id", encoding="utf-8")
        ishiki_path.write_text("style", encoding="utf-8")
        yuan_path.write_text("## MOOD\n\nVibe: something", encoding="utf-8")
        
        config = PersonaLoader.load(temp_dir)
        assert config.consciousness_mode == ConsciousnessMode.MOOD

    def test_detect_reflect_mode(self, temp_dir):
        """Test REFLECT mode detection with ## REFLECT."""
        identity_path = temp_dir / "identity.md"
        ishiki_path = temp_dir / "ishiki.md"
        yuan_path = temp_dir / "yuan.md"
        
        identity_path.write_text("id", encoding="utf-8")
        ishiki_path.write_text("style", encoding="utf-8")
        yuan_path.write_text("## REFLECT\n\nPremise: something", encoding="utf-8")
        
        config = PersonaLoader.load(temp_dir)
        assert config.consciousness_mode == ConsciousnessMode.REFLECT

    def test_detect_none_mode_without_yuan(self, temp_dir):
        """Test NONE mode when no yuan.md exists."""
        identity_path = temp_dir / "identity.md"
        ishiki_path = temp_dir / "ishiki.md"
        
        identity_path.write_text("id", encoding="utf-8")
        ishiki_path.write_text("style", encoding="utf-8")
        
        config = PersonaLoader.load(temp_dir)
        assert config.consciousness_mode == ConsciousnessMode.NONE
