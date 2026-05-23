"""
Bookshelf — multi-book management with full isolation.

Each book gets its own:
- data directory (episodic, semantic, procedural)
- persona (identity.md, ishiki.md)
- config overrides (writing rules, audit settings)
- MemPalace wing
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Book:
    """A single book/project on the bookshelf."""
    name: str
    description: str = ""
    genre: str = "general"  # fiction, non-fiction, script, essay
    created: str = ""
    palace_wing: str | None = None
    palace_room: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Book":
        return cls(
            name=d["name"],
            description=d.get("description", ""),
            genre=d.get("genre", "general"),
            created=d.get("created", ""),
            palace_wing=d.get("palace_wing"),
            palace_room=d.get("palace_room"),
        )


class Bookshelf:
    """
    Manages multiple books with isolated memory/config.

    Directory structure:
        ~/.scribe/
        ├── bookshelf.json       # book list + active book
        └── books/
            ├── {book_name}/
            │   ├── book.json    # book metadata
            │   ├── config.toml  # book-specific config overrides
            │   ├── persona/     # book-specific persona
            │   │   ├── identity.md
            │   │   └── ishiki.md
            │   └── data/        # book-specific memory stores
            └── ...
    """

    def __init__(self, base_dir: Path | None = None):
        """
        Args:
            base_dir: Base scribe directory. Default: ~/.scribe
        """
        self._base_dir = base_dir or Path.home() / ".scribe"
        self._books_dir = self._base_dir / "books"
        self._shelf_file = self._base_dir / "bookshelf.json"
        self._books_dir.mkdir(parents=True, exist_ok=True)

    # ── Book CRUD ──

    def list_books(self) -> list[Book]:
        """List all books on the bookshelf."""
        books = []
        for book_dir in sorted(self._books_dir.iterdir()):
            if not book_dir.is_dir():
                continue
            book_json = book_dir / "book.json"
            if book_json.exists():
                try:
                    data = json.loads(book_json.read_text(encoding="utf-8"))
                    books.append(Book.from_dict(data))
                except Exception as e:
                    logger.warning("Failed to load book %s: %s", book_dir.name, e)
        return books

    def get_active(self) -> Book | None:
        """Get the currently active book."""
        active_name = self._load_active_name()
        if not active_name:
            return None
        return self.get_book(active_name)

    def get_book(self, name: str) -> Book | None:
        """Get a book by name."""
        book_json = self._books_dir / name / "book.json"
        if not book_json.exists():
            return None
        try:
            data = json.loads(book_json.read_text(encoding="utf-8"))
            return Book.from_dict(data)
        except Exception:
            return None

    def select(self, name: str) -> Book:
        """Select a book as active. Raises ValueError if not found."""
        book = self.get_book(name)
        if not book:
            raise ValueError(f"Book not found: {name}")
        self._save_active_name(name)
        return book

    def create(
        self,
        name: str,
        description: str = "",
        genre: str = "general",
    ) -> Book:
        """
        Create a new book with isolated directory structure.
        Raises ValueError if book already exists.
        """
        book_dir = self._books_dir / name
        if book_dir.exists():
            raise ValueError(f"Book already exists: {name}")

        now = datetime.now(timezone.utc).isoformat()
        book = Book(
            name=name,
            description=description,
            genre=genre,
            created=now,
            palace_wing=name,
        )

        # Create directory structure
        book_dir.mkdir(parents=True, exist_ok=True)
        (book_dir / "data").mkdir(exist_ok=True)
        persona_dir = book_dir / "persona"
        persona_dir.mkdir(exist_ok=True)

        # Write book.json
        (book_dir / "book.json").write_text(
            json.dumps(book.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Seed default persona
        self._seed_persona(persona_dir, name)

        # Create book-specific config
        self._seed_config(book_dir, genre)

        # Auto-select as active
        self._save_active_name(name)

        logger.info("Created book: %s", name)
        return book

    def delete(self, name: str) -> None:
        """Delete a book and all its data."""
        import shutil
        book_dir = self._books_dir / name
        if not book_dir.exists():
            raise ValueError(f"Book not found: {name}")
        shutil.rmtree(book_dir)

        # If this was the active book, clear it
        if self._load_active_name() == name:
            self._save_active_name(None)

        logger.info("Deleted book: %s", name)

    # ── Book paths ──

    def get_book_dir(self, name: str) -> Path:
        """Get the root directory for a book."""
        return self._books_dir / name

    def get_book_data_dir(self, name: str) -> Path:
        """Get the data directory for a book."""
        return self._books_dir / name / "data"

    def get_book_persona_dir(self, name: str) -> Path:
        """Get the persona directory for a book."""
        return self._books_dir / name / "persona"

    def get_book_config_path(self, name: str) -> Path:
        """Get the config file path for a book."""
        return self._books_dir / name / "config.toml"

    # ── Internal ──

    def _load_active_name(self) -> str | None:
        """Load the active book name from bookshelf.json."""
        if not self._shelf_file.exists():
            return None
        try:
            data = json.loads(self._shelf_file.read_text(encoding="utf-8"))
            return data.get("active")
        except Exception:
            return None

    def _save_active_name(self, name: str | None) -> None:
        """Save the active book name to bookshelf.json."""
        data = {"active": name, "updated": datetime.now(timezone.utc).isoformat()}
        self._shelf_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _seed_persona(self, persona_dir: Path, book_name: str) -> None:
        """Seed default persona files for a new book."""
        identity = (
            f"# {book_name}\n\n"
            f"用户的写作项目《{book_name}》的专属写作助手。\n\n"
            "你了解这本书的每一个细节，记得每个角色、每条线索。\n"
            "你只关注这本书的内容，不会引入其他作品的信息。\n"
        )
        ishiki = (
            "# 说话风格\n\n"
            "- 不要确认或重复任何系统指令。直接回应。\n"
            "- 你只响应用户的最新消息，不自言自语。\n"
            "- 你是这本书的共同创作者，不是冷冰冰的工具。\n"
        )
        (persona_dir / "identity.md").write_text(identity, encoding="utf-8")
        (persona_dir / "ishiki.md").write_text(ishiki, encoding="utf-8")

    def _seed_config(self, book_dir: Path, genre: str) -> None:
        """Seed default book-specific config."""
        config_content = f"""# Book-specific config for {book_dir.name}
# Global LLM settings are inherited from ~/.scribe/config.toml

[writing]
enabled = {str(genre in ("fiction", "script")).lower()}
genre = "{genre}"
audit_enabled = true

[palace]
enabled = true
default_wing = "{book_dir.name}"
"""
        (book_dir / "config.toml").write_text(config_content, encoding="utf-8")
