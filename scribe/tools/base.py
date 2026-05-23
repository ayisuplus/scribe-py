"""
Tool abstract base class.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scribe.types import ToolResult


@dataclass
class ToolContext:
    """Execution context passed to tools."""
    working_dir: Path


class Tool(ABC):
    """
    Abstract tool interface.
    Tools are async and thread-safe (Send + Sync).
    """

    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier."""
        ...

    @abstractmethod
    def description(self) -> str:
        """Human-readable description for LLM."""
        ...

    @abstractmethod
    def parameters(self) -> dict:
        """JSON Schema for tool parameters."""
        ...

    @abstractmethod
    async def execute(
        self, params: dict, ctx: ToolContext
    ) -> ToolResult:
        """
        Execute the tool with the given JSON parameters.
        Returns a ToolResult with content and is_error flag.
        """
        ...