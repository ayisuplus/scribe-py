# Bookshelf Feature — Design Spec

**Date:** 2026-05-23
**Status:** Approved
**Scope:** Add bookshelf to scribe-py for multi-book isolation

## Goal

作家经常同时写好几本书。每本书需要完全隔离的记忆、配置、人设。开始对话时选择要写哪本书，或创建新书。

## Architecture

```
~/.scribe/
├── config.toml              # 全局配置 (LLM keys, providers)
├── bookshelf.json           # 书籍列表 + 当前活跃书
└── books/
    ├── 变身就变身/
    │   ├── book.json        # name, created, description, genre
    │   ├── config.toml      # 书级别配置覆盖 (写作规则/审计)
    │   ├── persona/         # 书级别人设
    │   │   ├── identity.md
    │   │   └── ishiki.md
    │   ├── data/
    │   │   ├── episodic_*.json
    │   │   ├── semantic_entities.json
    │   │   ├── semantic_relations.json
    │   │   └── skills/
    │   └── chapters/        # 章节文件 (可选)
    └── 她的生活/
        └── ...
```

## Data Model

### book.json
```json
{
  "name": "变身就变身",
  "description": "穿越/荒野求生/性别转换",
  "genre": "fiction",
  "created": "2026-05-23T10:00:00Z",
  "palace_wing": "变身就变身_小说",
  "palace_room": null
}
```

### bookshelf.json
```json
{
  "books": ["变身就变身", "她的生活"],
  "active": "变身就变身"
}
```

## Components

### 1. `scribe/bookshelf.py` — Bookshelf + Book

```python
@dataclass
class Book:
    name: str
    description: str = ""
    genre: str = "general"
    created: str = ""
    palace_wing: str | None = None
    palace_room: str | None = None

class Bookshelf:
    """Manages multiple books with isolated memory/config."""

    def __init__(self, base_dir: Path | None = None):
        """base_dir: ~/.scribe by default"""
        ...

    def list_books(self) -> list[Book]:
        """List all books."""
        ...

    def get_active(self) -> Book | None:
        """Get the currently active book."""
        ...

    def select(self, name: str) -> Book:
        """Select a book as active. Raises if not found."""
        ...

    def create(self, name: str, description: str = "", genre: str = "general") -> Book:
        """Create a new book with isolated directory structure."""
        ...

    def delete(self, name: str) -> None:
        """Delete a book and all its data."""
        ...

    def get_book_dir(self, name: str) -> Path:
        """Get the data directory for a book."""
        ...

    def get_book_config(self, name: str) -> KernelConfig:
        """Load book-specific config (merged with global)."""
        ...
```

### 2. CLI Changes — `scribe/cli/main.py`

```python
@cli.command()
def run(...):
    # Before starting, check bookshelf
    bookshelf = Bookshelf()
    books = bookshelf.list_books()

    if not books:
        # First time: create a book
        click.echo("No books found. Let's create one!")
        name = click.prompt("Book name")
        book = bookshelf.create(name)
    else:
        # Show book list
        for i, b in enumerate(books, 1):
            click.echo(f"  {i}. {b.name} ({b.genre})")
        click.echo(f"  N. New book")
        choice = click.prompt("Which book?", type=str)

        if choice.lower() == 'n':
            name = click.prompt("Book name")
            book = bookshelf.create(name)
        else:
            book = books[int(choice) - 1]

    bookshelf.select(book.name)
    # Now create ScribeState with book context
    state = await ScribeState.init(book=book)
```

### 3. ScribeState Changes

```python
class ScribeState:
    @classmethod
    async def init(cls, book: Book | None = None) -> "ScribeState":
        self = cls()
        self._book = book

        if book:
            # Book-specific data directory
            data_dir = self._config.data_dir / "books" / book.name
            self._book_dir = data_dir
            data_dir.mkdir(parents=True, exist_ok=True)

            # Load book-specific config if exists
            book_config = data_dir.parent / "config.toml"  # Actually: book_dir/config.toml
            if book_config.exists():
                # Merge with global config
                ...

            # Book-specific persona
            persona_dir = data_dir / "persona"
            ...

        # Initialize memory stores with book-scoped data_dir
        self._episodic = EpisodicStore(data_dir / "data")
        self._semantic = SemanticStore(data_dir / "data")
        ...
```

### 4. AgentLoop Changes

```python
# Session ID prefixed with book name
session_id = f"{book.name}_{session_id}"

# MemPalace wing = book name (or book.palace_wing)
agent.with_palace(palace, wing=book.palace_wing or book.name)
```

### 5. MemPalace Integration

When creating a book, optionally create a MemPalace wing:
```python
def create(self, name, ...):
    # Create book directory
    ...
    # MemPalace wing is the book name
    book.palace_wing = name
```

## User Flow

```
$ scribe run

  📚 书架
  ─────────────────
  1. 变身就变身 (fiction)
  2. 她的生活 (fiction)
  N. 新建书籍

  选择: 1

  📖 正在打开: 变身就变身
  已加载 12 个会话, 45 个实体, 3 个技能

  你: 写第十一章：夺巢
  [自动搜索 MemPalace 变身就变身 wing...]
  [注入前10章摘要...]
  [生成...审计...返回]

  你: /switch
  📚 书架
  选择: 2
  📖 正在打开: 她的生活
```

## Files Changed

| File | Change |
|------|--------|
| `scribe/bookshelf.py` | NEW — Book dataclass + Bookshelf manager |
| `scribe/cli/main.py` | Book selection prompt before run |
| `scribe/api/state.py` | ScribeState.init(book=...) scoping |
| `scribe/kernel/config.py` | Book config loading/merging |
| `scribe/__init__.py` | Export Book, Bookshelf |
| `tests/test_bookshelf.py` | NEW — tests |

## Testing

- Test Bookshelf.create builds correct directory structure
- Test Bookshelf.select sets active book
- Test Bookshelf.list_books returns all books
- Test ScribeState with book uses book-scoped data_dir
- Test session IDs are book-prefixed
- Test MemPalace wing is set from book
