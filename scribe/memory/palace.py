"""
MemPalace integration — 4th memory layer for detail retrieval.

Directly imports the mempalace Python package (not CLI subprocess).
Uses ChromaDB collection API for search, miner API for auto-archival.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path

from scribe.types import PalaceHit, PalaceStatus

logger = logging.getLogger(__name__)


class MemPalaceStore:
    """
    MemPalace integration for scribe.

    Provides:
    - search(): Query drawers by keyword (vector + BM25 hybrid)
    - mine(): Archive new content into the palace
    - status(): Get palace overview
    """

    def __init__(self, palace_path: str | Path | None = None):
        """
        Args:
            palace_path: Path to palace directory.
                         Default: from MempalaceConfig (~/.mempalace/palace)
        """
        self._palace_path: str | None = str(palace_path) if palace_path else None
        self._collection = None  # lazy init

    def _get_collection(self):
        """Lazy-init the ChromaDB collection."""
        if self._collection is not None:
            return self._collection

        from mempalace.palace import get_collection

        path = self._palace_path
        if path is None:
            from mempalace.config import MempalaceConfig
            path = MempalaceConfig().palace_path

        self._collection = get_collection(path, create=False)
        return self._collection

    def _resolve_path(self) -> str:
        """Get the palace path, resolving from config if needed."""
        if self._palace_path:
            return self._palace_path
        from mempalace.config import MempalaceConfig
        return MempalaceConfig().palace_path

    async def search(
        self,
        query: str,
        wing: str | None = None,
        room: str | None = None,
        limit: int = 5,
    ) -> list[PalaceHit]:
        """Search drawers by keyword. Returns matching drawer summaries."""
        return await asyncio.to_thread(
            self._search_sync, query, wing, room, limit
        )

    def _search_sync(
        self, query: str, wing: str | None, room: str | None, limit: int
    ) -> list[PalaceHit]:
        from mempalace.searcher import build_where_filter, _first_or_empty, _hybrid_rank

        col = self._get_collection()
        where = build_where_filter(wing, room)

        kwargs = {
            "query_texts": [query],
            "n_results": limit,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        try:
            results = col.query(**kwargs)
        except Exception as e:
            logger.warning("MemPalace search error: %s", e)
            return []

        docs = _first_or_empty(results, "documents")
        metas = _first_or_empty(results, "metadatas")
        dists = _first_or_empty(results, "distances")

        if not docs:
            return []

        hits = [
            {"text": doc or "", "distance": float(dist), "metadata": meta or {}}
            for doc, meta, dist in zip(docs, metas, dists)
        ]
        hits = _hybrid_rank(hits, query)

        return [
            PalaceHit(
                text=hit["text"],
                wing=hit["metadata"].get("wing", ""),
                room=hit["metadata"].get("room", ""),
                source_file=Path(hit["metadata"].get("source_file", "")).name,
                similarity=round(max(0.0, 1 - hit["distance"]), 3),
            )
            for hit in hits
        ]

    async def mine(
        self,
        content: str,
        wing: str,
        room: str,
        title: str,
    ) -> bool:
        """
        Mine content into the palace as a new drawer.
        Writes to a temp file, then mines it.
        Returns True on success.
        """
        return await asyncio.to_thread(
            self._mine_sync, content, wing, room, title
        )

    def _mine_sync(
        self, content: str, wing: str, room: str, title: str
    ) -> bool:
        from mempalace.miner import mine

        palace_path = self._resolve_path()

        # Write content to a temp .md file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", prefix="scribe_", delete=False, encoding="utf-8"
        ) as f:
            f.write(f"# {title}\n\n{content}\n")
            temp_path = f.name

        try:
            mine(
                project_dir=str(Path(temp_path).parent),
                palace_path=palace_path,
                wing_override=wing,
                files=[temp_path],
            )
            logger.info("Mined '%s' into %s/%s", title, wing, room)
            return True
        except Exception as e:
            logger.warning("MemPalace mine error: %s", e)
            return False
        finally:
            Path(temp_path).unlink(missing_ok=True)

    async def wake_up(self) -> str:
        """Get L0+L1 wake-up context."""
        return await asyncio.to_thread(self._wake_up_sync)

    def _wake_up_sync(self) -> str:
        import io
        import sys

        from mempalace.cli import cmd_wakeup

        # Capture stdout from cmd_wakeup
        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        try:
            # Build a mock args object
            class Args:
                palace = self._palace_path
                compact = False

            cmd_wakeup(Args())
            return buffer.getvalue()
        except Exception as e:
            logger.warning("MemPalace wake-up error: %s", e)
            return ""
        finally:
            sys.stdout = old_stdout

    async def status(self) -> PalaceStatus:
        """Get palace status (wings, rooms, drawer counts)."""
        return await asyncio.to_thread(self._status_sync)

    def _status_sync(self) -> PalaceStatus:
        import io
        import re
        import sys

        from mempalace.cli import cmd_status

        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        try:
            class Args:
                palace = self._palace_path

            cmd_status(Args())
            output = buffer.getvalue()

            # Parse the status output
            wings: dict[str, list[str]] = {}
            current_wing = ""
            total = 0

            for line in output.split("\n"):
                line = line.strip()
                wing_match = re.match(r"WING:\s*(.+)", line)
                if wing_match:
                    current_wing = wing_match.group(1).strip()
                    wings[current_wing] = []
                    continue

                room_match = re.match(r"ROOM:\s*(\S+)\s+(\d+)\s+drawers", line)
                if room_match:
                    room_name = room_match.group(1)
                    count = int(room_match.group(2))
                    total += count
                    if current_wing:
                        wings[current_wing].append(room_name)
                    continue

            return PalaceStatus(wings=wings, total_drawers=total)
        except Exception as e:
            logger.warning("MemPalace status error: %s", e)
            return PalaceStatus(wings={}, total_drawers=0)
        finally:
            sys.stdout = old_stdout
