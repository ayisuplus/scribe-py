"""Startup onboarding for first-run Scribe sessions."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from scribe.bookshelf import Book, Bookshelf


INTENTS = {
    "1": ("draft", "start drafting"),
    "2": ("world", "organize setting"),
    "3": ("council", "run writer council"),
    "4": ("import", "import existing draft"),
    "5": ("chat", "chat freely"),
}


@dataclass(frozen=True)
class OnboardingResult:
    """Result of startup guidance."""

    book: Book | None
    intent: str
    startup_lines: list[str]


def build_quickstart_lines(book: Book | None, intent: str) -> list[str]:
    """Build compact guidance shown when the TUI starts."""
    name = book.name if book else "no active book"
    genre = f" ({book.genre})" if book and book.genre else ""
    intent_label = INTENTS.get(intent, (intent, intent))[1]

    return [
        "Quickstart",
        f"  Book: {name}{genre}",
        f"  Intent: {intent_label}",
        "  Try: write chapter 1 opening in 800 words",
        "  Commands: /help  /council  /writers  /status  /quit",
    ]


def run_onboarding(bookshelf: Bookshelf) -> OnboardingResult:
    """Guide user through book selection and first writing intent."""
    book = _choose_book(bookshelf)
    intent = _choose_intent()
    return OnboardingResult(
        book=book,
        intent=intent,
        startup_lines=build_quickstart_lines(book, intent),
    )


def _choose_book(bookshelf: Bookshelf) -> Book | None:
    books = bookshelf.list_books()

    if not books:
        click.echo("\n  Quickstart: create first book\n")
        name = click.prompt("  Book name")
        description = click.prompt("  Description", default="", show_default=False)
        genre = click.prompt("  Genre", default="fiction", show_default=True)
        try:
            return bookshelf.create(name, description=description, genre=genre)
        except Exception as e:
            click.echo(f"  Failed to create book: {e}", err=True)
            sys.exit(1)

    click.echo("\n  Books")
    for i, book in enumerate(books, 1):
        click.echo(f"  {i}. {book.name} ({book.genre})")
    click.echo("  N. New book")

    while True:
        choice = click.prompt("  Choose", type=str).strip()
        if choice.lower() == "n":
            name = click.prompt("  Book name")
            description = click.prompt("  Description", default="", show_default=False)
            genre = click.prompt("  Genre", default="fiction", show_default=True)
            try:
                return bookshelf.create(name, description=description, genre=genre)
            except Exception as e:
                click.echo(f"  Failed to create book: {e}", err=True)
                continue
        try:
            index = int(choice) - 1
        except ValueError:
            click.echo("  Invalid choice.")
            continue
        if 0 <= index < len(books):
            selected = books[index]
            bookshelf.select(selected.name)
            return selected
        click.echo("  Invalid choice.")


def _choose_intent() -> str:
    click.echo("\n  What next?")
    click.echo("  1. Start drafting")
    click.echo("  2. Organize setting")
    click.echo("  3. Writer council")
    click.echo("  4. Import existing draft")
    click.echo("  5. Chat freely")

    while True:
        choice = click.prompt("  Choose", default="1", show_default=True).strip()
        if choice in INTENTS:
            return INTENTS[choice][0]
        click.echo("  Invalid choice.")
