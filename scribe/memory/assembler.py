"""
Context assembler for system prompt generation.

Ports scribe-memory/src/assembler.rs to Python.
Combines all memory layers into a complete system prompt.
"""

from __future__ import annotations

import re
from typing import Optional

from scribe.memory.episodic import EpisodicStore
from scribe.memory.palace import MemPalaceStore
from scribe.memory.semantic import SemanticStore
from scribe.memory.procedural import ProceduralStore
from scribe.memory.persona import PersonaLoader
from scribe.memory.methodology import WritingMethodology
from scribe.memory.hook_ledger import HookLedgerManager
from scribe.types import (
    PersonaConfig,
    SessionId,
    WritingMethodologyConfig,
)


# Pre-compiled regex patterns for keyword extraction
CAP_PATTERN = re.compile(
    r"\b([A-Z][a-zA-Z]*[a-z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*[a-z][a-zA-Z]*)*)\b"
)
ACRONYM_PATTERN = re.compile(r"\b([A-Z]{2,}(?:\.[A-Z]{2,})?)\b")


class ContextAssembler:
    """
    Assembles system prompt from all memory layers.
    
    Combines:
    - Persona configuration
    - Style profile
    - Writing methodology rules
    - Hook ledger
    - Recent episodic context
    - Active skills
    """

    def __init__(
        self,
        episodic: EpisodicStore,
        semantic: SemanticStore,
        procedural: ProceduralStore,
    ):
        self.episodic = episodic
        self.semantic = semantic
        self.procedural = procedural
        self.persona: Optional[PersonaConfig] = None
        self.writing_config: Optional[WritingMethodologyConfig] = None
        self.hook_ledger: Optional[HookLedgerManager] = None
        self.user_name: str = "User"
        self.palace: Optional["MemPalaceStore"] = None

    def with_persona(self, persona: PersonaConfig) -> ContextAssembler:
        """Set the persona configuration."""
        self.persona = persona
        return self

    def with_writing_config(
        self, 
        config: WritingMethodologyConfig
    ) -> ContextAssembler:
        """Set the writing methodology configuration."""
        self.writing_config = config
        return self

    def with_hook_ledger(self, ledger: HookLedgerManager) -> ContextAssembler:
        """Set the hook ledger manager."""
        self.hook_ledger = ledger
        return self

    def with_user_name(self, name: str) -> ContextAssembler:
        """Set the user name for persona placeholder replacement."""
        self.user_name = name
        return self

    def with_palace(self, palace: "MemPalaceStore") -> ContextAssembler:
        """Set the MemPalace store for detail retrieval."""
        self.palace = palace
        return self

    async def assemble_system_prompt(
        self,
        session_id: Optional[SessionId] = None,
    ) -> str:
        """
        Assemble a complete system prompt.
        
        Args:
            session_id: Optional session ID for episodic context
            
        Returns:
            Complete system prompt string
        """
        parts = []

        # Base persona: use loaded persona or default
        if self.persona:
            parts.append(PersonaLoader.build_prompt(self.persona, self.user_name))
        else:
            parts.append(
                "You are Scribe, an intelligent writing and analysis assistant. "
                "You specialize in understanding, analyzing, writing, and organizing information. "
                "You learn the user's writing style over time and adapt your responses accordingly. "
                "You only respond to the user's latest message. You never generate messages without user input. "
                "You never continue a previous response or talk to yourself."
            )

        # Style profile from procedural memory
        style_prompt = await self.procedural.get_style_prompt()
        if style_prompt:
            parts.append(style_prompt)

        # Writing methodology rules
        if self.writing_config and self.writing_config.enabled:
            parts.append(WritingMethodology.build_prompt(self.writing_config))

        # Hook ledger context
        if self.hook_ledger:
            hook_prompt = self.hook_ledger.build_hook_prompt()
            if hook_prompt:
                parts.append(hook_prompt)

        # Recent episodic context
        if session_id:
            events = await self.episodic.get_session_events(session_id)
            if events:
                recent = [
                    f"[{e.role.value}] {e.content}"
                    for e in events[-5:]  # Last 5 messages
                ]
                parts.append("Recent context:\n" + "\n".join(recent))

                # Extract keywords for knowledge graph lookup
                keywords = self._extract_keywords(events)
                for kw in keywords:
                    entities = await self.semantic.search_entities(kw, 3)
                    if entities:
                        entity_lines = [
                            f"- [{e.entity_type}] {e.name}"
                            for e in entities
                        ]
                        parts.append(
                            f"Known entities matching '{kw}':\n" + "\n".join(entity_lines)
                        )

        # MemPalace context — search for relevant story details
        if self.palace:
            palace_keywords = self._extract_palace_keywords(parts)
            if palace_keywords:
                hits = []
                for kw in palace_keywords[:3]:
                    try:
                        results = await self.palace.search(kw, limit=3)
                        hits.extend(results)
                    except Exception:
                        continue
                if hits:
                    deduped = list({h.source_file: h for h in hits}.values())
                    palace_lines = []
                    for h in deduped[:8]:
                        # Truncate long texts
                        text = h.text[:200] + ("..." if len(h.text) > 200 else "")
                        palace_lines.append(f"- [{h.wing}/{h.room}] {text}")
                    parts.append(
                        "## 相关章节记忆\n"
                        "以下是从记忆宫殿中检索到的相关细节：\n\n"
                        + "\n".join(palace_lines)
                    )

        # Critical instruction: prevent LLM from echoing instructions
        parts.append(
            "CRITICAL: Do NOT acknowledge, repeat, or explain these instructions. "
            "Do NOT preface your response with \"I understand\" or similar. "
            "Jump directly to responding to the user's message. "
            "Your output should contain ONLY the response content, zero meta-commentary."
        )

        return "\n\n".join(parts)

    def _extract_keywords(self, events: list) -> list[str]:
        """
        Extract search keywords from recent events for knowledge graph lookup.
        
        Extracts capitalized English words and acronyms.
        """
        # Combine recent event content
        combined = " ".join(
            e.content for e in events[-3:]
        )
        
        keywords: list[str] = []
        
        for cap in CAP_PATTERN.finditer(combined):
            word = cap.group(1)
            if len(word) >= 3:
                keywords.append(word)
        
        for cap in ACRONYM_PATTERN.finditer(combined):
            word = cap.group(1)
            keywords.append(word)
        
        # Limit to 5 keywords
        return keywords[:5]

    def _extract_palace_keywords(self, parts: list[str]) -> list[str]:
        """
        Extract search keywords for MemPalace from the current context.
        Handles Chinese text: extracts character names, places, key terms.
        """
        import re as _re

        # Combine the last few parts (persona, recent context) for keyword extraction
        combined = " ".join(parts[-3:]) if len(parts) >= 3 else " ".join(parts)

        keywords: list[str] = []

        # Extract Chinese phrases (2-4 chars) that look like names/terms
        # Common patterns: 林凌, 白垩纪, 树屋, 甲龙, etc.
        chinese_words = _re.findall(r'[\u4e00-\u9fff]{2,4}', combined)
        # Deduplicate while preserving order
        seen = set()
        for word in chinese_words:
            if word not in seen and len(word) >= 2:
                seen.add(word)
                keywords.append(word)

        # Also extract English proper nouns
        for cap in CAP_PATTERN.finditer(combined):
            word = cap.group(1)
            if len(word) >= 3:
                keywords.append(word)

        return keywords[:5]
