"""
Tests for ContextAssembler — system prompt generation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from scribe.memory.assembler import ContextAssembler
from scribe.types import (
    PersonaConfig,
    WritingMethodologyConfig,
)


class TestContextAssembler:
    """Test ContextAssembler functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.episodic = MagicMock()
        self.semantic = MagicMock()
        self.procedural = MagicMock()
        self.procedural.get_style_prompt = AsyncMock(return_value=None)
        self.assembler = ContextAssembler(
            episodic=self.episodic,
            semantic=self.semantic,
            procedural=self.procedural,
        )

    def test_init(self):
        """Test assembler initialization."""
        assert self.assembler.episodic == self.episodic
        assert self.assembler.semantic == self.semantic
        assert self.assembler.procedural == self.procedural
        assert self.assembler.persona is None
        assert self.assembler.writing_config is None
        assert self.assembler.hook_ledger is None
        assert self.assembler.user_name == "User"
        assert self.assembler.palace is None

    def test_with_persona(self):
        """Test setting persona."""
        persona = PersonaConfig(
            identity="I am a writer",
            ishiki="I speak formally",
        )
        result = self.assembler.with_persona(persona)
        assert result == self.assembler
        assert self.assembler.persona == persona

    def test_with_writing_config(self):
        """Test setting writing config."""
        config = WritingMethodologyConfig()
        result = self.assembler.with_writing_config(config)
        assert result == self.assembler
        assert self.assembler.writing_config == config

    def test_with_hook_ledger(self):
        """Test setting hook ledger."""
        ledger = MagicMock()
        result = self.assembler.with_hook_ledger(ledger)
        assert result == self.assembler
        assert self.assembler.hook_ledger == ledger

    def test_with_user_name(self):
        """Test setting user name."""
        result = self.assembler.with_user_name("Alice")
        assert result == self.assembler
        assert self.assembler.user_name == "Alice"

    def test_with_palace(self):
        """Test setting palace."""
        palace = MagicMock()
        result = self.assembler.with_palace(palace)
        assert result == self.assembler
        assert self.assembler.palace == palace

    @pytest.mark.asyncio
    async def test_assemble_system_prompt_basic(self):
        """Test building basic system prompt."""
        self.episodic.get_recent_events.return_value = []
        self.semantic.get_style_profile.return_value = None
        self.procedural.get_skills.return_value = []

        prompt = await self.assembler.assemble_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    @pytest.mark.asyncio
    async def test_assemble_system_prompt_with_persona(self):
        """Test building system prompt with persona."""
        persona = PersonaConfig(
            identity="I am a creative writer",
            ishiki="I use vivid imagery",
        )
        self.assembler.with_persona(persona)

        self.episodic.get_recent_events.return_value = []
        self.semantic.get_style_profile.return_value = None
        self.procedural.get_skills.return_value = []

        prompt = await self.assembler.assemble_system_prompt()
        assert "creative writer" in prompt
        assert "vivid imagery" in prompt

    @pytest.mark.asyncio
    async def test_assemble_system_prompt_with_user_name(self):
        """Test building system prompt with user name."""
        persona = PersonaConfig(
            identity="I am a creative writer for {{user_name}}",
            ishiki="I use vivid imagery",
        )
        self.assembler.with_persona(persona)
        self.assembler.with_user_name("Alice")

        self.episodic.get_recent_events.return_value = []
        self.semantic.get_style_profile.return_value = None
        self.procedural.get_skills.return_value = []

        prompt = await self.assembler.assemble_system_prompt()
        assert "Alice" in prompt

    @pytest.mark.asyncio
    async def test_assemble_system_prompt_with_hooks(self):
        """Test building system prompt with hook ledger."""
        ledger = MagicMock()
        ledger.build_hook_prompt.return_value = "Active hooks: mystery, romance"
        self.assembler.with_hook_ledger(ledger)

        self.episodic.get_recent_events.return_value = []
        self.semantic.get_style_profile.return_value = None
        self.procedural.get_skills.return_value = []

        prompt = await self.assembler.assemble_system_prompt()
        assert "mystery" in prompt
        assert "romance" in prompt


class TestContextAssemblerExtractKeywords:
    """Test keyword extraction from text."""

    def test_extract_capitalized_words(self):
        """Test extracting capitalized words."""
        from scribe.memory.assembler import CAP_PATTERN
        text = "The Quick Brown Fox Jumps Over The Lazy Dog"
        matches = CAP_PATTERN.findall(text)
        # The pattern matches sequences of capitalized words
        assert len(matches) > 0

    def test_extract_acronyms(self):
        """Test extracting acronyms."""
        from scribe.memory.assembler import ACRONYM_PATTERN
        text = "Use API and HTTP for the MVP"
        matches = ACRONYM_PATTERN.findall(text)
        assert "API" in matches
        assert "HTTP" in matches
        assert "MVP" in matches
