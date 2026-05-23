"""
Tests for Bookshelf — multi-book management.
"""

import json
import pytest
from pathlib import Path

from scribe.bookshelf import Book, Bookshelf


class TestBook:
    """Test Book dataclass."""

    def test_book_creation(self):
        book = Book(name="测试书", description="测试", genre="fiction")
        assert book.name == "测试书"
        assert book.genre == "fiction"

    def test_book_to_dict(self):
        book = Book(name="测试书", genre="fiction")
        d = book.to_dict()
        assert d["name"] == "测试书"
        assert d["genre"] == "fiction"

    def test_book_from_dict(self):
        d = {"name": "测试书", "genre": "fiction", "description": "desc"}
        book = Book.from_dict(d)
        assert book.name == "测试书"
        assert book.description == "desc"

    def test_book_from_dict_minimal(self):
        d = {"name": "最小书"}
        book = Book.from_dict(d)
        assert book.name == "最小书"
        assert book.genre == "general"


class TestBookshelf:
    """Test Bookshelf CRUD operations."""

    @pytest.fixture
    def bookshelf(self, tmp_path):
        """Create a Bookshelf with a temp directory."""
        return Bookshelf(base_dir=tmp_path)

    def test_list_books_empty(self, bookshelf):
        """Empty bookshelf returns no books."""
        assert bookshelf.list_books() == []

    def test_create_book(self, bookshelf):
        """Create a book and verify structure."""
        book = bookshelf.create("测试书", description="一本测试书", genre="fiction")
        assert book.name == "测试书"
        assert book.genre == "fiction"

        # Verify directory structure
        book_dir = bookshelf.get_book_dir("测试书")
        assert book_dir.exists()
        assert (book_dir / "book.json").exists()
        assert (book_dir / "data").is_dir()
        assert (book_dir / "persona" / "identity.md").exists()
        assert (book_dir / "persona" / "ishiki.md").exists()
        assert (book_dir / "config.toml").exists()

    def test_create_book_duplicate_raises(self, bookshelf):
        """Creating a duplicate book raises ValueError."""
        bookshelf.create("测试书")
        with pytest.raises(ValueError, match="already exists"):
            bookshelf.create("测试书")

    def test_list_books(self, bookshelf):
        """List returns all created books."""
        bookshelf.create("书一")
        bookshelf.create("书二")
        books = bookshelf.list_books()
        names = [b.name for b in books]
        assert "书一" in names
        assert "书二" in names

    def test_get_book(self, bookshelf):
        """Get a book by name."""
        bookshelf.create("测试书")
        book = bookshelf.get_book("测试书")
        assert book is not None
        assert book.name == "测试书"

    def test_get_book_not_found(self, bookshelf):
        """Get a non-existent book returns None."""
        assert bookshelf.get_book("不存在") is None

    def test_select_book(self, bookshelf):
        """Select sets the active book."""
        bookshelf.create("书一")
        bookshelf.create("书二")

        selected = bookshelf.select("书一")
        assert selected.name == "书一"
        assert bookshelf.get_active().name == "书一"

        bookshelf.select("书二")
        assert bookshelf.get_active().name == "书二"

    def test_select_nonexistent_raises(self, bookshelf):
        """Select a non-existent book raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            bookshelf.select("不存在")

    def test_delete_book(self, bookshelf):
        """Delete removes the book and its data."""
        bookshelf.create("要删的书")
        assert bookshelf.get_book("要删的书") is not None

        bookshelf.delete("要删的书")
        assert bookshelf.get_book("要删的书") is None
        assert not bookshelf.get_book_dir("要删的书").exists()

    def test_delete_clears_active(self, bookshelf):
        """Deleting the active book clears the active selection."""
        bookshelf.create("活跃书")
        bookshelf.select("活跃书")
        assert bookshelf.get_active().name == "活跃书"

        bookshelf.delete("活跃书")
        assert bookshelf.get_active() is None

    def test_delete_nonexistent_raises(self, bookshelf):
        """Delete a non-existent book raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            bookshelf.delete("不存在")

    def test_auto_select_on_create(self, bookshelf):
        """Creating a book auto-selects it as active."""
        bookshelf.create("新书")
        assert bookshelf.get_active().name == "新书"

    def test_book_config_toml(self, bookshelf):
        """Book config.toml has correct content."""
        bookshelf.create("测试书", genre="fiction")
        config_path = bookshelf.get_book_config_path("测试书")
        content = config_path.read_text(encoding="utf-8")
        assert "测试书" in content
        assert "fiction" in content

    def test_book_persona_content(self, bookshelf):
        """Book persona files have book-specific content."""
        bookshelf.create("我的小说")
        persona_dir = bookshelf.get_book_persona_dir("我的小说")
        identity = (persona_dir / "identity.md").read_text(encoding="utf-8")
        assert "我的小说" in identity
