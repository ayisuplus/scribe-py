"""
Tests for ToolRegistry.
"""

import pytest
from pathlib import Path

from scribe.tools.registry import ToolRegistry
from scribe.tools.base import Tool, ToolContext, ToolResult


class DummyTool(Tool):
    """A minimal tool for testing."""

    def name(self) -> str:
        return "dummy"

    def description(self) -> str:
        return "A dummy tool for testing."

    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult:
        return ToolResult(content="OK", is_error=False)


class TestToolRegistry:
    def test_register_and_get(self):
        reg = ToolRegistry()
        tool = DummyTool()
        reg.register(tool)
        assert reg.get("dummy") is tool
        assert reg.get("nonexistent") is None

    def test_list(self):
        reg = ToolRegistry()
        reg.register(DummyTool())
        listed = reg.list()
        assert len(listed) == 1
        assert listed[0] == ("dummy", "A dummy tool for testing.")

    def test_definitions(self):
        reg = ToolRegistry()
        reg.register(DummyTool())
        defs = reg.definitions()
        assert len(defs) == 1
        assert defs[0].function.name == "dummy"
        assert defs[0].function.description == "A dummy tool for testing."
        assert defs[0].tool_type == "function"


class TestFileWriteToolSecurity:
    @pytest.mark.asyncio
    async def test_reject_absolute_path(self):
        from scribe.tools.file_write import FileWriteTool
        tool = FileWriteTool()
        ctx = ToolContext(working_dir=Path.cwd())
        result = await tool.execute(
            {"path": "/etc/passwd", "content": "bad"},
            ctx,
        )
        assert result.is_error
        assert ("Absolute paths" in result.content or "not allowed" in result.content)

    @pytest.mark.asyncio
    async def test_reject_path_traversal(self):
        from scribe.tools.file_write import FileWriteTool
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FileWriteTool()
            ctx = ToolContext(working_dir=Path(tmpdir))
            result = await tool.execute(
                {"path": "../escape.txt", "content": "bad"},
                ctx,
            )
            assert result.is_error
            assert "traversal" in result.content.lower() or "outside" in result.content.lower()

    @pytest.mark.asyncio
    async def test_write_relative_path_success(self):
        from scribe.tools.file_write import FileWriteTool
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FileWriteTool()
            ctx = ToolContext(working_dir=Path(tmpdir))
            result = await tool.execute(
                {"path": "test_output.txt", "content": "hello world"},
                ctx,
            )
            assert not result.is_error
            assert (Path(tmpdir) / "test_output.txt").read_text(encoding="utf-8") == "hello world"


class TestFileReadTool:
    @pytest.mark.asyncio
    async def test_read_file_relative(self):
        from scribe.tools.file_read import FileReadTool
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_read.txt"
            test_file.write_text("test content", encoding="utf-8")
            tool = FileReadTool()
            ctx = ToolContext(working_dir=Path(tmpdir))
            result = await tool.execute({"path": "test_read.txt"}, ctx)
            assert not result.is_error
            assert "test content" in result.content

    @pytest.mark.asyncio
    async def test_reject_absolute_path(self):
        from scribe.tools.file_read import FileReadTool
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            abs_file = Path(tmpdir) / "abs_file.txt"
            abs_file.write_text("test", encoding="utf-8")
            tool = FileReadTool()
            ctx = ToolContext(working_dir=Path(tmpdir))
            result = await tool.execute({"path": str(abs_file)}, ctx)
            assert result.is_error
            assert "Absolute paths are not allowed" in result.content

    @pytest.mark.asyncio
    async def test_reject_path_traversal(self):
        from scribe.tools.file_read import FileReadTool
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FileReadTool()
            ctx = ToolContext(working_dir=Path(tmpdir))
            result = await tool.execute({"path": "../escape.txt"}, ctx)
            assert result.is_error
            assert ("traversal" in result.content.lower() or "outside" in result.content.lower())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])