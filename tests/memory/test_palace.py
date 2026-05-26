"""
Tests for MemPalaceStore and PalaceSearchTool.
Mocks the mempalace package — no real ChromaDB needed.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from scribe.types import PalaceHit, PalaceStatus


class TestMemPalaceStore:
    """Test MemPalaceStore search/mine/status."""

    @pytest.fixture
    def mock_palace(self):
        """Create a MemPalaceStore with mocked internals."""
        from scribe.memory.palace import MemPalaceStore
        store = MemPalaceStore(palace_path="/tmp/test_palace")
        return store

    @pytest.mark.asyncio
    async def test_search_returns_hits(self, mock_palace):
        """Test search returns PalaceHit objects."""
        mock_results = [
            PalaceHit(
                text="林凌在树屋中休息",
                wing="变身就变身",
                room="第一卷",
                source_file="第03章.md",
                similarity=0.85,
            )
        ]
        with patch.object(mock_palace, "_search_sync", return_value=mock_results):
            hits = await mock_palace.search("林凌", limit=3)
            assert len(hits) == 1
            assert hits[0].text == "林凌在树屋中休息"
            assert hits[0].wing == "变身就变身"

    @pytest.mark.asyncio
    async def test_search_empty(self, mock_palace):
        """Test search with no results."""
        with patch.object(mock_palace, "_search_sync", return_value=[]):
            hits = await mock_palace.search("不存在的查询")
            assert len(hits) == 0

    @pytest.mark.asyncio
    async def test_mine_calls_sync(self, mock_palace):
        """Test mine delegates to sync method."""
        with patch.object(mock_palace, "_mine_sync", return_value=True):
            result = await mock_palace.mine(
                content="新章节内容",
                wing="变身就变身",
                room="第一卷",
                title="第十一章",
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_status_returns_palace_status(self, mock_palace):
        """Test status returns PalaceStatus."""
        mock_status = PalaceStatus(
            wings={"变身就变身": ["第一卷", "第二卷"]},
            total_drawers=22,
        )
        with patch.object(mock_palace, "_status_sync", return_value=mock_status):
            status = await mock_palace.status()
            assert status.total_drawers == 22
            assert "变身就变身" in status.wings


class TestPalaceSearchTool:
    """Test PalaceSearchTool execute."""

    @pytest.fixture
    def mock_store(self):
        from scribe.memory.palace import MemPalaceStore
        return MagicMock(spec=MemPalaceStore)

    @pytest.fixture
    def tool(self, mock_store):
        from scribe.tools.palace_search import PalaceSearchTool
        return PalaceSearchTool(mock_store)

    def test_name(self, tool):
        assert tool.name() == "palace_search"

    def test_description(self, tool):
        assert "memory palace" in tool.description().lower()

    def test_parameters_requires_query(self, tool):
        params = tool.parameters()
        assert "query" in params["required"]

    @pytest.mark.asyncio
    async def test_execute_returns_results(self, tool, mock_store):
        """Test execute returns formatted results."""
        mock_store.search = AsyncMock(return_value=[
            PalaceHit(
                text="林凌制作了石矛",
                wing="变身就变身",
                room="第一卷",
                source_file="第03章.md",
                similarity=0.9,
            )
        ])
        ctx = MagicMock()
        result = await tool.execute({"query": "石矛"}, ctx)
        assert not result.is_error
        assert "石矛" in result.content
        assert "林凌" in result.content

    @pytest.mark.asyncio
    async def test_execute_no_results(self, tool, mock_store):
        """Test execute with no results."""
        mock_store.search = AsyncMock(return_value=[])
        ctx = MagicMock()
        result = await tool.execute({"query": "不存在"}, ctx)
        assert not result.is_error
        assert "No results" in result.content

    @pytest.mark.asyncio
    async def test_execute_empty_query(self, tool, mock_store):
        """Test execute with empty query returns error."""
        ctx = MagicMock()
        result = await tool.execute({"query": ""}, ctx)
        assert result.is_error

    @pytest.mark.asyncio
    async def test_execute_with_filters(self, tool, mock_store):
        """Test execute passes wing/room filters."""
        mock_store.search = AsyncMock(return_value=[])
        ctx = MagicMock()
        await tool.execute(
            {"query": "test", "wing": "my_wing", "room": "my_room", "results": 3},
            ctx,
        )
        mock_store.search.assert_called_once_with(
            query="test", wing="my_wing", room="my_room", limit=3
        )


class TestPalaceTypes:
    """Test PalaceHit and PalaceStatus dataclasses."""

    def test_palace_hit(self):
        hit = PalaceHit(
            text="test text",
            wing="wing1",
            room="room1",
            source_file="file.md",
            similarity=0.95,
        )
        assert hit.text == "test text"
        assert hit.similarity == 0.95

    def test_palace_status(self):
        status = PalaceStatus(
            wings={"proj": ["ch1", "ch2"]},
            total_drawers=10,
        )
        assert status.total_drawers == 10
        assert len(status.wings["proj"]) == 2
