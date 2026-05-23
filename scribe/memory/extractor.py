"""
Entity extractor for extracting named entities from text.

Ports scribe-memory/src/extractor.rs to Python.
Uses regex patterns to identify entities in text.
"""

from __future__ import annotations

import re
from typing import Optional

from scribe.memory.semantic import SemanticStore
from scribe.types import MemoryEvent


# Pre-compiled regex patterns
EN_PATTERN = re.compile(r"\b([A-Z][a-zA-Z]*[a-zA-Z]*)+\b")
ACRONYM_PATTERN = re.compile(r"\b([A-Z]{2,}(?:\.[A-Z]{2,})?)\b")
CN_NAME_PATTERN = re.compile(r"[「『]([\u4e00-\u9fff]{2,4})[」』]")
DOMAIN_PATTERN = re.compile(
    r"https?://(?:www\.)?([a-zA-Z0-9][-a-zA-Z0-9]*(?:\.[a-zA-Z]{2,})+)"
)

# Common English words to filter out
COMMON_WORDS: set[str] = {
    "the", "this", "that", "these", "those", "there", "their", "they", 
    "what", "when", "where", "which", "who", "how", "why", "and", "but", 
    "for", "not", "are", "was", "were", "been", "being", "have", "has", 
    "had", "does", "will", "would", "could", "should", "from", "with",
    "each", "every", "some", "any", "all", "both", "you", "we", "he", 
    "she", "it", "your", "our", "his", "her", "yes", "no", "just", "also", 
    "like", "make", "made", "get", "got", "one", "two", "first", "hello", 
    "hi", "okay", "ok", "thanks", "now", "then", "well", "see", "way",
    "back", "say", "said", "take", "know", "come", "look", "want", "give",
}


class EntityExtractor:
    """
    Extracts named entities from text using regex patterns.
    
    Recognizes:
    - English names (capitalized words)
    - Acronyms (ALL CAPS)
    - Chinese character names in quotes
    - Chinese org/place names with common suffixes
    - Domain names
    """

    @staticmethod
    async def extract_from_event(
        semantic: SemanticStore,
        event: MemoryEvent,
    ) -> int:
        """
        Extract entities from a single event.
        
        Args:
            semantic: The semantic store to add entities to
            event: The memory event to extract from
            
        Returns:
            Number of entities added
        """
        candidates = EntityExtractor.find_entities(event.content)
        added = 0
        
        for name, entity_type in candidates:
            existing = await semantic.search_entities(name, 1)
            if not existing:
                await semantic.add_entity(name, entity_type, {})
                added += 1
        
        return added

    @staticmethod
    async def extract_from_events(
        semantic: SemanticStore,
        events: list[MemoryEvent],
    ) -> int:
        """
        Extract entities from multiple events.
        
        Args:
            semantic: The semantic store to add entities to
            events: The memory events to extract from
            
        Returns:
            Total number of entities added
        """
        total = 0
        for event in events:
            total += await EntityExtractor.extract_from_event(semantic, event)
        return total

    @staticmethod
    def find_entities(text: str) -> list[tuple[str, str]]:
        """
        Find all named entities in text.
        
        Returns:
            List of (name, entity_type) tuples
        """
        entities: list[tuple[str, str]] = []
        seen: set[str] = set()

        # Match English names (capitalized words with at least one lowercase)
        for match in EN_PATTERN.finditer(text):
            name = match.group(1)
            has_lower = any(c.islower() for c in name)
            if has_lower and len(name) >= 3 and name not in COMMON_WORDS and name not in seen:
                seen.add(name)
                entity_type = _guess_entity_type(name)
                entities.append((name, entity_type))

        # Match all-caps acronyms
        for match in ACRONYM_PATTERN.finditer(text):
            name = match.group(1)
            if len(name) >= 2 and name not in seen:
                seen.add(name)
                entities.append((name, "acronym"))

        # Match Chinese names in quotes
        for match in CN_NAME_PATTERN.finditer(text):
            name = match.group(1)
            if name not in seen:
                seen.add(name)
                entities.append((name, "character"))

        # Match Chinese org/place names with suffix patterns
        suffixes = [
            ("公司", "organization"),
            ("集团", "organization"),
            ("大学", "institution"),
            ("学院", "institution"),
            ("研究院", "institution"),
            ("组织", "organization"),
            ("团队", "organization"),
            ("部门", "organization"),
            ("中心", "organization"),
            ("市", "location"),
            ("省", "location"),
            ("国", "location"),
        ]
        
        for suffix, entity_type in suffixes:
            # Build regex pattern for this suffix
            pattern = re.compile(rf"([\u4e00-\u9fff]{{2,6}}{re.escape(suffix)})")
            for match in pattern.finditer(text):
                name = match.group(1)
                if name not in seen:
                    seen.add(name)
                    guess = _guess_entity_type(name)
                    entities.append((name, guess))

        # Match domain names
        for match in DOMAIN_PATTERN.finditer(text):
            name = match.group(1)
            if name not in seen:
                seen.add(name)
                entities.append((name, "website"))

        return entities


def _guess_entity_type(name: str) -> str:
    """
    Guess the entity type based on suffix patterns.
    """
    if name.endswith("公司") or name.endswith("集团"):
        return "organization"
    elif name.endswith("大学") or name.endswith("学院") or name.endswith("研究院"):
        return "institution"
    elif name.endswith("市") or name.endswith("省") or name.endswith("国"):
        return "location"
    elif name.endswith("团队") or name.endswith("部门") or name.endswith("中心"):
        return "organization"
    elif all(c.isupper() or c.isdigit() for c in name):
        return "acronym"
    else:
        return "concept"
