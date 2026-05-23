"""
Semantic memory store for entities and relations.

Ports scribe-memory/src/semantic.rs to Python with JSON file storage.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

from scribe.types import Entity, Relation


class SemanticStore:
    """
    Stores entities and relations in a knowledge graph.
    
    Uses JSON file backend for persistence.
    """
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._lock = asyncio.Lock()
        self._entities_file = data_dir / "semantic_entities.json"
        self._relations_file = data_dir / "semantic_relations.json"
        self._next_entity_id = 1
        self._next_relation_id = 1
        self._entities: dict[int, Entity] = {}
        self._relations: dict[int, Relation] = {}
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load entities and relations from disk."""
        # Load entities
        if self._entities_file.exists():
            try:
                content = self._entities_file.read_text(encoding="utf-8")
                data = json.loads(content)
                for e_data in data:
                    entity = Entity(
                        id=e_data["id"],
                        name=e_data["name"],
                        entity_type=e_data["entity_type"],
                        properties=e_data.get("properties", {}),
                    )
                    self._entities[entity.id] = entity
                    if entity.id >= self._next_entity_id:
                        self._next_entity_id = entity.id + 1
            except Exception:
                pass

        # Load relations
        if self._relations_file.exists():
            try:
                content = self._relations_file.read_text(encoding="utf-8")
                data = json.loads(content)
                for r_data in data:
                    relation = Relation(
                        id=r_data["id"],
                        subject_id=r_data["subject_id"],
                        predicate=r_data["predicate"],
                        object_id=r_data["object_id"],
                    )
                    self._relations[relation.id] = relation
                    if relation.id >= self._next_relation_id:
                        self._next_relation_id = relation.id + 1
            except Exception:
                pass

    async def _save_to_disk(self) -> None:
        """Save entities and relations to disk."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        entities_data = [
            {
                "id": e.id,
                "name": e.name,
                "entity_type": e.entity_type,
                "properties": e.properties,
            }
            for e in self._entities.values()
        ]
        self._entities_file.write_text(
            json.dumps(entities_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        
        relations_data = [
            {
                "id": r.id,
                "subject_id": r.subject_id,
                "predicate": r.predicate,
                "object_id": r.object_id,
            }
            for r in self._relations.values()
        ]
        self._relations_file.write_text(
            json.dumps(relations_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    async def add_entity(
        self,
        name: str,
        entity_type: str,
        properties: Optional[dict] = None,
    ) -> int:
        """
        Add a new entity and return its ID.
        """
        async with self._lock:
            entity_id = self._next_entity_id
            self._next_entity_id += 1
            
            entity = Entity(
                id=entity_id,
                name=name,
                entity_type=entity_type,
                properties=properties or {},
            )
            self._entities[entity_id] = entity
            await self._save_to_disk()
            return entity_id

    async def add_relation(
        self,
        subject_id: int,
        predicate: str,
        object_id: int,
    ) -> int:
        """
        Add a new relation and return its ID.
        """
        async with self._lock:
            relation_id = self._next_relation_id
            self._next_relation_id += 1
            
            relation = Relation(
                id=relation_id,
                subject_id=subject_id,
                predicate=predicate,
                object_id=object_id,
            )
            self._relations[relation_id] = relation
            await self._save_to_disk()
            return relation_id

    async def get_entity(self, entity_id: int) -> Optional[Entity]:
        """Get an entity by ID."""
        return self._entities.get(entity_id)

    async def search_entities(self, query: str, limit: int = 10) -> list[Entity]:
        """
        Search entities by name (case-insensitive substring match).
        """
        query_lower = query.lower()
        results = [
            e for e in self._entities.values()
            if query_lower in e.name.lower()
        ]
        return results[:limit]

    async def get_relations(self, entity_id: int) -> list[tuple[Relation, Entity]]:
        """
        Get all relations involving an entity.
        
        Returns tuples of (Relation, RelatedEntity).
        """
        results: list[tuple[Relation, Entity]] = []
        
        for relation in self._relations.values():
            if relation.subject_id == entity_id:
                if relation.object_id in self._entities:
                    results.append((relation, self._entities[relation.object_id]))
            elif relation.object_id == entity_id:
                if relation.subject_id in self._entities:
                    results.append((relation, self._entities[relation.subject_id]))
        
        return results
