"""
Memory search tool.
Queries all three memory layers (episodic, semantic, procedural).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scribe.tools.base import ToolContext
    from scribe.memory.episodic import EpisodicStore
    from scribe.memory.semantic import SemanticStore
    from scribe.memory.procedural import ProceduralStore

from scribe.tools.base import Tool
from scribe.types import ToolResult


class MemorySearchTool(Tool):
    """
    Search across all memory layers (episodic, semantic, procedural) for relevant information.
    """

    def __init__(
        self,
        episodic: "EpisodicStore | None" = None,
        semantic: "SemanticStore | None" = None,
        procedural: "ProceduralStore | None" = None,
    ):
        self._episodic = episodic
        self._semantic = semantic
        self._procedural = procedural

    def name(self) -> str:
        return "memory_search"

    def description(self) -> str:
        return "Search across all memory layers (episodic, semantic, procedural) for relevant information."

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"],
        }

    async def execute(self, params: dict, ctx: "ToolContext") -> ToolResult:
        query = params.get("query")
        if not query:
            return ToolResult(content="Missing 'query' parameter", is_error=True)

        parts: list[str] = []

        # Episodic: search event content
        if self._episodic:
            try:
                events = await self._episodic.search_by_content(query, limit=5)
                if events:
                    parts.append("=== Episodic Memory ===")
                    for e in events:
                        parts.append(f"[{e.role.value}] {e.content}")
            except Exception as e:
                parts.append(f"[Episodic search failed: {e}]")

        # Semantic: search entities
        if self._semantic:
            try:
                entities = await self._semantic.search_entities(query, limit=5)
                if entities:
                    parts.append("=== Semantic Memory (Knowledge Graph) ===")
                    for ent in entities:
                        parts.append(
                            f"[{ent.entity_type}] {ent.name} — props: {ent.properties}"
                        )
            except Exception as e:
                parts.append(f"[Semantic search failed: {e}]")

        # Procedural: style profile
        if self._procedural:
            try:
                profile = await self._procedural.get_latest_style()
                if profile:
                    parts.append("=== Procedural Memory (Style) ===")
                    parts.append(
                        f"Tone: {profile.tone}, "
                        f"Avg sentence length: {profile.avg_sentence_length:.0}, "
                        f"Paragraph density: {profile.paragraph_density:.1}"
                    )
                    if profile.transition_words:
                        parts.append(
                            f"Common transitions: {', '.join(profile.transition_words)}"
                        )
            except Exception as e:
                parts.append(f"[Procedural fetch failed: {e}]")

        if not parts:
            parts.append(f"No memory matches found for '{query}'.")

        return ToolResult(content="\n".join(parts), is_error=False)