"""
Persona loader for markdown-based persona configuration.

Loads persona configuration from markdown template files.
"""

from __future__ import annotations

from pathlib import Path

from scribe.types import PersonaConfig


class PersonaLoader:
    """
    Loads persona configuration from markdown template files.

    Expected directory structure:
        persona_dir/
            identity.md    (required)
            ishiki.md      (required)
    """

    @staticmethod
    def load(persona_dir: Path) -> PersonaConfig:
        """
        Load persona from a directory of markdown files.

        Args:
            persona_dir: Directory containing identity.md and ishiki.md

        Returns:
            PersonaConfig with loaded content

        Raises:
            FileNotFoundError: If required files are missing
        """
        identity_path = persona_dir / "identity.md"
        ishiki_path = persona_dir / "ishiki.md"

        if not identity_path.exists():
            raise FileNotFoundError(f"Required file not found: {identity_path}")
        if not ishiki_path.exists():
            raise FileNotFoundError(f"Required file not found: {ishiki_path}")

        identity = identity_path.read_text(encoding="utf-8")
        ishiki = ishiki_path.read_text(encoding="utf-8")

        return PersonaConfig(
            identity=identity,
            ishiki=ishiki,
            name=persona_dir.name,
        )

    @staticmethod
    def build_prompt(config: PersonaConfig, user_name: str) -> str:
        """
        Build the system prompt fragment from a persona config.

        Args:
            config: The loaded persona configuration
            user_name: The name to substitute for {{user_name}}

        Returns:
            Combined prompt string
        """
        parts = []

        # Identity - replace {{user_name}} placeholder
        identity = config.identity.replace("{{user_name}}", user_name)
        parts.append(identity)

        # Ishiki (speaking style)
        parts.append(config.ishiki)

        return "\n\n".join(parts)
