"""
Palace search tool — query MemPalace for story details, scenes, characters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scribe.memory.palace import MemPalaceStore
    from scribe.tools.base import ToolContext

from scribe.tools.base import Tool
from scribe.types import ToolResult


class PalaceSearchTool(Tool):
    """
    Search the memory palace for story details, scenes, characters, and events.
    """

    def __init__(self, palace: MemPalaceStore):
        self._palace = palace

    def name(self) -> str:
        return "palace_search"

    def description(self) -> str:
        return (
            "Search the memory palace for story details, scenes, characters, and events. "
            "Use this when you need to recall specific details from previous chapters."
        )

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keywords (character names, events, locations)",
                },
                "wing": {
                    "type": "string",
                    "description": "Limit to a specific project/story",
                },
                "room": {
                    "type": "string",
                    "description": "Limit to a specific section/volume",
                },
                "results": {
                    "type": "integer",
                    "description": "Number of results to return (default 5)",
                },
            },
            "required": ["query"],
        }

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        query = params.get("query", "")
        if not query:
            return ToolResult(content="Error: query is required", is_error=True)

        wing = params.get("wing")
        room = params.get("room")
        limit = params.get("results", 5)

        try:
            hits = await self._palace.search(
                query=query, wing=wing, room=room, limit=limit
            )
        except Exception as e:
            return ToolResult(content=f"Palace search error: {e}", is_error=True)

        if not hits:
            return ToolResult(content=f'No results found for: "{query}"')

        lines = [f'Results for: "{query}"\n']
        for i, hit in enumerate(hits, 1):
            lines.append(f"[{i}] {hit.wing} / {hit.room}")
            lines.append(f"    Source: {hit.source_file}")
            lines.append(f"    Similarity: {hit.similarity}")
            lines.append("")
            for text_line in hit.text.strip().split("\n")[:10]:
                lines.append(f"    {text_line}")
            lines.append(f"    {'─' * 40}")
            lines.append("")

        return ToolResult(content="\n".join(lines))
