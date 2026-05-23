"""
Tool registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scribe.tools.base import Tool
from scribe.types import ToolDefinition, FunctionDefinition

from scribe.types import ToolDefinition


class ToolRegistry:
    """
    Registry for available tools.
    Thread-safe (read-mostly) access via a dict.
    """

    def __init__(self) -> None:
        self._tools: dict[str, "Tool"] = {}

    def register(self, tool: "Tool") -> None:
        """Register a tool instance."""
        self._tools[tool.name()] = tool

    def get(self, name: str) -> "Tool | None":
        """Get a tool by name."""
        return self._tools.get(name)

    def list(self) -> list[tuple[str, str]]:
        """List all (name, description) pairs."""
        return [(t.name(), t.description()) for t in self._tools.values()]

    def definitions(self) -> list[ToolDefinition]:
        """Return tool definitions for LLM function-calling."""
        return [
            ToolDefinition(
                tool_type="function",
                function=FunctionDefinition(
                    name=t.name(),
                    description=t.description(),
                    parameters=t.parameters(),
                ),
            )
            for t in self._tools.values()
        ]