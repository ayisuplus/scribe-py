"""
Council Wizard - interactive wizard for writer council management.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scribe.bookshelf import Book, Bookshelf
    from scribe.llm.base import LlmDriver


class ScopeMode(str, Enum):
    """Scope parsing modes."""

    CHAPTER = "chapter"
    PART = "part"
    FULL = "full"
    OUTLINE = "outline"


@dataclass
class WritingScope:
    """Parsed writing scope."""

    mode: ScopeMode
    description: str
    target: str | None = None


class ScopeParser:
    """Parse writing scope from text."""

    def parse(self, text: str) -> WritingScope:
        """Parse scope from text like '第3章' or '大纲'."""
        text = text.strip()

        if "章" in text:
            return WritingScope(
                mode=ScopeMode.CHAPTER,
                description=f"Write chapter: {text}",
                target=text,
            )

        if text in ("大纲", "outline", "summary"):
            return WritingScope(
                mode=ScopeMode.OUTLINE,
                description="Generate outline",
                target=text,
            )

        if text in ("整本", "全书", "full"):
            return WritingScope(
                mode=ScopeMode.FULL,
                description="Full book scope",
                target=text,
            )

        return WritingScope(
            mode=ScopeMode.CHAPTER,
            description=f"Write: {text}",
            target=text,
        )


class CouncilWizard:
    """
    Interactive wizard for running the writer council.

    The full implementation would:
    1. Select relevant writers for the book
    2. Run council discussion
    3. Generate consensus output
    """

    def __init__(self, llm: LlmDriver, bookshelf: Bookshelf) -> None:
        self._llm = llm
        self._bookshelf = bookshelf

    async def run(self, book: Book) -> str:
        """Run the council wizard."""
        return f"Writer Council for: {book.name}\nCouncil wizard is not fully implemented yet.\n"