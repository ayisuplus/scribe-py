"""Tests for Scribe startup onboarding."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from scribe.cli.onboarding import build_quickstart_lines, run_onboarding


def test_build_quickstart_lines_names_current_book_and_intent():
    """Quickstart output should anchor the user in their active writing flow."""
    book = SimpleNamespace(name="Novel", genre="fiction")

    lines = build_quickstart_lines(book, "draft")

    assert any("Quickstart" in line for line in lines)
    assert any("Novel" in line for line in lines)
    assert any("/help" in line for line in lines)
    assert any("/council" in line for line in lines)


def test_run_onboarding_creates_first_book_and_collects_intent():
    """First startup should create a book and select an initial writing intent."""
    bookshelf = MagicMock()
    bookshelf.list_books.return_value = []
    book = SimpleNamespace(name="Novel", genre="fiction")
    bookshelf.create.return_value = book

    with patch("scribe.cli.onboarding.click.prompt") as prompt:
        prompt.side_effect = ["Novel", "A haunted city", "fiction", "1"]

        result = run_onboarding(bookshelf)

    bookshelf.create.assert_called_once_with(
        "Novel",
        description="A haunted city",
        genre="fiction",
    )
    assert result.book is book
    assert result.intent == "draft"
    assert any("Quickstart" in line for line in result.startup_lines)


def test_run_onboarding_selects_existing_book():
    """Startup should let users pick an existing book without recreating it."""
    book = SimpleNamespace(name="Novel", genre="fiction")
    bookshelf = MagicMock()
    bookshelf.list_books.return_value = [book]

    with patch("scribe.cli.onboarding.click.prompt") as prompt:
        prompt.side_effect = ["1", "2"]

        result = run_onboarding(bookshelf)

    bookshelf.select.assert_called_once_with("Novel")
    bookshelf.create.assert_not_called()
    assert result.book is book
    assert result.intent == "world"
