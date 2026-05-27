"""
Writer Router - routes writer requests to appropriate handlers.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scribe.council.registry import Writer


class WriterRouter:
    """
    Routes requests to writers and manages writer selection.

    This is a simplified version - the full implementation would include
    intelligent routing based on query type and writer expertise.
    """

    # Pre-defined writer genres (for backward compatibility)
    WRITER_GENRES: dict[str, set[str]] = {
        "hemingway": {"fiction", "non-fiction", "journalism"},
        "orwell": {"fiction", "essay", "journalism"},
        "woolf": {"fiction", "essay"},
        "faulkner": {"fiction"},
        "kafka": {"fiction"},
    }

    @classmethod
    def get_writer_for_genre(cls, genre: str) -> list[str]:
        """Get writers that match a genre."""
        return [
            writer_id
            for writer_id, genres in cls.WRITER_GENRES.items()
            if genre in genres
        ]

    @classmethod
    def get_all_writers(cls) -> list[str]:
        """Get all available writer IDs."""
        return list(cls.WRITER_GENRES.keys())