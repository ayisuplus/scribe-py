"""
Procedural memory store for skills and style profiles.

Ports scribe-memory/src/procedural.rs to Python with JSON file storage.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from scribe.types import StyleProfile


class ProceduralStore:
    """
    Stores style profiles and generates style prompts.

    Uses JSON file backend for persistence.
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._lock = asyncio.Lock()
        self._style_file = data_dir / "procedural_styles.json"
        self._styles: list[tuple[StyleProfile, datetime]] = []  # (profile, timestamp)
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load style profiles from disk."""
        if not self._style_file.exists():
            return

        try:
            content = self._style_file.read_text(encoding="utf-8")
            data = json.loads(content)
            for item in data:
                profile_data = item["profile"]
                timestamp_str = item["updated_at"]
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

                from scribe.types import (
                    EllipsisStyle,
                    PunctuationStyle,
                    QuoteStyle,
                    Tone,
                )

                tone = Tone(profile_data.get("tone", "casual"))
                punctuation_data = profile_data.get("punctuation_style", {})
                punctuation = PunctuationStyle(
                    use_oxford_comma=punctuation_data.get("use_oxford_comma", False),
                    ellipsis_style=EllipsisStyle(
                        punctuation_data.get("ellipsis_style", "threedots")
                    ),
                    quote_style=QuoteStyle(
                        punctuation_data.get("quote_style", "double")
                    ),
                )

                profile = StyleProfile(
                    tone=tone,
                    avg_sentence_length=profile_data.get("avg_sentence_length", 20.0),
                    preferred_structures=profile_data.get("preferred_structures", []),
                    vocabulary_patterns=profile_data.get("vocabulary_patterns", []),
                    punctuation_style=punctuation,
                    paragraph_density=profile_data.get("paragraph_density", 3.0),
                    transition_words=profile_data.get("transition_words", []),
                )
                self._styles.append((profile, timestamp))
        except Exception:
            pass

    async def _save_to_disk(self) -> None:
        """Save style profiles to disk."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

        data = [
            {
                "profile": {
                    "tone": p.tone.value,
                    "avg_sentence_length": p.avg_sentence_length,
                    "preferred_structures": p.preferred_structures,
                    "vocabulary_patterns": p.vocabulary_patterns,
                    "punctuation_style": {
                        "use_oxford_comma": p.punctuation_style.use_oxford_comma,
                        "ellipsis_style": p.punctuation_style.ellipsis_style.value,
                        "quote_style": p.punctuation_style.quote_style.value,
                    },
                    "paragraph_density": p.paragraph_density,
                    "transition_words": p.transition_words,
                },
                "updated_at": ts.isoformat(),
            }
            for p, ts in self._styles
        ]

        self._style_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    async def update_style(self, profile: StyleProfile) -> None:
        """
        Add a new style profile entry.
        """
        async with self._lock:
            now = datetime.now(UTC)
            self._styles.append((profile, now))
            await self._save_to_disk()

    async def get_latest_style(self) -> StyleProfile | None:
        """
        Get the most recent style profile.
        """
        if not self._styles:
            return None

        # Sort by timestamp and get the most recent
        sorted_styles = sorted(self._styles, key=lambda x: x[1], reverse=True)
        return sorted_styles[0][0]

    async def get_style_prompt(self) -> str:
        """
        Generate a style description prompt from the latest profile.
        """
        profile = await self.get_latest_style()
        if profile is None:
            return ""

        parts = ["Write in the following style:"]
        parts.append(f"- Tone: {profile.tone.value}")
        parts.append(
            f"- Average sentence length: {profile.avg_sentence_length:.0f} words"
        )

        if profile.preferred_structures:
            parts.append(
                f"- Preferred structures: {', '.join(profile.preferred_structures)}"
            )

        if profile.transition_words:
            parts.append(f"- Common transitions: {', '.join(profile.transition_words)}")

        parts.append(
            f"- Paragraph density: {profile.paragraph_density:.1f} sentences per paragraph"
        )

        return "\n".join(parts)
