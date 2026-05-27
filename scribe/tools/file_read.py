"""
File read tool.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scribe.tools.base import ToolContext

from scribe.tools.base import Tool
from scribe.types import ToolResult


class FileReadTool(Tool):
    """
    Read the contents of a local file (text, Markdown, or other text formats).
    File size limit: 5 MB.
    """

    MAX_BYTES = 5 * 1024 * 1024  # 5 MB

    def name(self) -> str:
        return "file_read"

    def description(self) -> str:
        return (
            "Read the contents of a local file (text, Markdown, or other text formats)."
        )

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read",
                }
            },
            "required": ["path"],
        }

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        path_str = params.get("path")
        if not path_str:
            return ToolResult(content="Missing 'path' parameter", is_error=True)

        # Absolute paths are not allowed for security
        if Path(path_str).is_absolute():
            return ToolResult(
                content="Absolute paths are not allowed. Use a relative path within the working directory.",
                is_error=True,
            )

        full_path = ctx.working_dir / path_str

        try:
            canonical = full_path.resolve()
        except OSError:
            return ToolResult(content=f"File not found: {path_str}", is_error=True)

        # Sandbox: ensure canonical path is within working_dir
        try:
            sandbox = ctx.working_dir.resolve()
        except OSError as e:
            return ToolResult(
                content=f"Cannot resolve working directory: {e}", is_error=True
            )

        if not str(canonical).startswith(str(sandbox)):
            return ToolResult(
                content="Access denied — path resolves outside the working directory.",
                is_error=True,
            )

        # File size check
        try:
            size = os.path.getsize(canonical)
        except OSError:
            return ToolResult(content=f"Cannot access file: {path_str}", is_error=True)

        if size > self.MAX_BYTES:
            return ToolResult(
                content=f"File too large ({size} bytes). Maximum 5 MB.",
                is_error=True,
            )

        try:
            content = canonical.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return ToolResult(content="File is not valid UTF-8 text.", is_error=True)
        except OSError as e:
            return ToolResult(content=f"Error reading file: {e}", is_error=True)

        return ToolResult(content=content, is_error=False)
