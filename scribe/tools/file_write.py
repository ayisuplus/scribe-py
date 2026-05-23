"""
File write tool.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scribe.tools.base import ToolContext

from scribe.tools.base import Tool
from scribe.types import ToolResult


class FileWriteTool(Tool):
    """
    Write content to a local file. Creates the file if it doesn't exist.
    Rejects absolute paths and path traversal attempts.
    """

    def name(self) -> str:
        return "file_write"

    def description(self) -> str:
        return "Write content to a local file. Creates the file if it doesn't exist."

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to write (relative to working directory)",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["path", "content"],
        }

    async def execute(self, params: dict, ctx: "ToolContext") -> ToolResult:
        path_str = params.get("path")
        content = params.get("content")
        if not path_str:
            return ToolResult(content="Missing 'path' parameter", is_error=True)
        if content is None:
            return ToolResult(content="Missing 'content' parameter", is_error=True)

        # Reject absolute paths
        if Path(path_str).is_absolute():
            return ToolResult(
                content="Absolute paths are not allowed. Use a relative path within the working directory.",
                is_error=True,
            )

        # Resolve relative to working_dir
        resolved = ctx.working_dir / path_str

        # Sandbox: canonicalize both
        try:
            sandbox = ctx.working_dir.resolve()
        except OSError as e:
            return ToolResult(
                content=f"Error resolving working directory: {e}", is_error=True
            )

        parent = resolved.parent
        if parent == resolved:
            # resolved is a directory, not a file — not allowed
            return ToolResult(
                content="Path resolves to a directory. Provide a file name.", is_error=True
            )

        try:
            parent.mkdir(parents=True, exist_ok=True)
            canonical_parent = parent.resolve()
        except OSError as e:
            return ToolResult(content=f"Error resolving path: {e}", is_error=True)

        # Detect path traversal
        if not str(canonical_parent).startswith(str(sandbox)):
            return ToolResult(
                content="Path traversal detected — writing outside the working directory is not allowed.",
                is_error=True,
            )

        try:
            resolved.write_text(content, encoding="utf-8")
        except OSError as e:
            return ToolResult(content=f"Error writing file: {e}", is_error=True)

        return ToolResult(
            content=f"File written successfully: {resolved}", is_error=False
        )