"""
Writer data model and registry.

Writers are distillations of real authors' styles - extracted from their works
and converted into Scribe personas.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path


class WriterGenre(str, Enum):
    """Genre categories for writers."""

    FICTION = "fiction"
    NONFICTION = "non-fiction"
    ESSAY = "essay"
    SCRIPT = "script"
    POETRY = "poetry"
    JOURNALISM = "journalism"
    ACADEMIC = "academic"
    TECHNICAL = "technical"


@dataclass
class Writer:
    """
    A distilled writer persona.

    Attributes:
        id: Unique identifier (slugified name)
        name: Display name (e.g., "Paul Auster")
        real_name: Real author's name (e.g., "Paul Auster")
        genre: Primary genre
        description: Brief description of the writer's style
        identity: The identity.md content (core persona)
        ishiki: The ishiki.md content (speaking style)
        mental_models: Key thinking patterns (extracted from their works)
        expression_dna: Writing style markers
        source_count: Number of sources used in distillation
        distilled_at: When this writer was distilled
        updated_at: Last update timestamp
    """

    id: str
    name: str
    real_name: str = ""
    genre: str = "fiction"
    description: str = ""
    identity: str = ""
    ishiki: str = ""
    mental_models: list[str] = field(default_factory=list)
    expression_dna: list[str] = field(default_factory=list)
    source_count: int = 0
    distilled_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Writer:
        """Deserialize from dictionary."""
        return cls(
            id=d["id"],
            name=d["name"],
            real_name=d.get("real_name", ""),
            genre=d.get("genre", "fiction"),
            description=d.get("description", ""),
            identity=d.get("identity", ""),
            ishiki=d.get("ishiki", ""),
            mental_models=d.get("mental_models", []),
            expression_dna=d.get("expression_dna", []),
            source_count=d.get("source_count", 0),
            distilled_at=d.get("distilled_at", ""),
            updated_at=d.get("updated_at", ""),
        )

    def to_markdown(self) -> str:
        """Convert to markdown format (identity + ishiki)."""
        parts = [f"# {self.name}\n"]
        if self.description:
            parts.append(f"{self.description}\n")
        if self.mental_models:
            parts.append("## 思维模型\n")
            for model in self.mental_models:
                parts.append(f"- {model}\n")
        parts.append("\n## 身份设定\n")
        parts.append(self.identity)
        parts.append("\n## 说话风格\n")
        parts.append(self.ishiki)
        return "\n".join(parts)


class WriterRegistry:
    """
    Manages available writers.

    Storage structure:
        ~/.scribe/writers/
        ├── registry.json      # Writer list + metadata
        └── writers/
            ├── {writer_id}/
            │   ├── writer.json    # Full writer data
            │   ├── identity.md    # Persona identity
            │   ├── ishiki.md      # Speaking style
            │   └── research/      # Distillation research
            └── ...
    """

    WRITERS_DIR = Path.home() / ".scribe" / "writers"
    REGISTRY_FILE = WRITERS_DIR / "registry.json"

    def __init__(self) -> None:
        self._writers: dict[str, Writer] = {}
        self._load_registry()

    def _load_registry(self) -> None:
        """Load writer registry from disk."""
        if not self.REGISTRY_FILE.exists():
            return

        try:
            data = json.loads(self.REGISTRY_FILE.read_text(encoding="utf-8"))
            writers_list = data.get("writers", [])
            for w in writers_list:
                writer = Writer.from_dict(w)
                self._writers[writer.id] = writer
        except Exception:
            pass

    def _save_registry(self) -> None:
        """Save writer registry to disk."""
        self.WRITERS_DIR.mkdir(parents=True, exist_ok=True)
        writers_list = [w.to_dict() for w in self._writers.values()]
        data = {
            "writers": writers_list,
            "updated": datetime.now(UTC).isoformat(),
        }
        self.REGISTRY_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def list_writers(self) -> list[Writer]:
        """List all available writers."""
        return sorted(self._writers.values(), key=lambda w: w.name)

    def get_writer(self, writer_id: str) -> Writer | None:
        """Get a writer by ID."""
        return self._writers.get(writer_id)

    def add_writer(self, writer: Writer) -> None:
        """Add a new writer."""
        self._writers[writer.id] = writer
        self._save_registry()

    def remove_writer(self, writer_id: str) -> bool:
        """Remove a writer. Returns True if removed."""
        if writer_id not in self._writers:
            return False

        del self._writers[writer_id]
        self._save_registry()

        # Remove writer files
        writer_dir = self.WRITERS_DIR / "writers" / writer_id
        if writer_dir.exists():
            import shutil

            shutil.rmtree(writer_dir)

        return True

    def create_writer_dir(self, writer: Writer) -> Path:
        """Create directory structure for a writer."""
        writer_dir = self.WRITERS_DIR / "writers" / writer.id
        writer_dir.mkdir(parents=True, exist_ok=True)

        # Write identity.md
        identity_path = writer_dir / "identity.md"
        identity_path.write_text(writer.identity, encoding="utf-8")

        # Write ishiki.md
        ishiki_path = writer_dir / "ishiki.md"
        ishiki_path.write_text(writer.ishiki, encoding="utf-8")

        # Write full writer.json
        writer_json = writer_dir / "writer.json"
        writer_json.write_text(
            json.dumps(writer.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Create research directory
        (writer_dir / "research").mkdir(exist_ok=True)

        return writer_dir

    def get_writer_dir(self, writer_id: str) -> Path | None:
        """Get the directory for a writer."""
        writer_dir = self.WRITERS_DIR / "writers" / writer_id
        return writer_dir if writer_dir.exists() else None