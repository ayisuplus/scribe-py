"""
Tests for SemanticStore.
"""

import pytest
from pathlib import Path

from scribe.memory.semantic import SemanticStore
from scribe.types import Entity, Relation


class TestSemanticStore:
    """Test SemanticStore operations."""

    @pytest.fixture
    def store(self, temp_dir):
        """Create a SemanticStore with temp directory."""
        return SemanticStore(data_dir=temp_dir)

    @pytest.mark.asyncio
    async def test_add_entity(self, store):
        """Test adding an entity."""
        entity_id = await store.add_entity("Alice", "character", {"age": 25})
        assert entity_id == 1
        assert len(store._entities) == 1

    @pytest.mark.asyncio
    async def test_get_entity(self, store):
        """Test getting an entity by ID."""
        entity_id = await store.add_entity("Alice", "character", {"age": 25})
        entity = await store.get_entity(entity_id)
        assert entity is not None
        assert entity.name == "Alice"
        assert entity.entity_type == "character"

    @pytest.mark.asyncio
    async def test_get_entity_not_found(self, store):
        """Test getting non-existent entity."""
        entity = await store.get_entity(999)
        assert entity is None

    @pytest.mark.asyncio
    async def test_search_entities(self, store):
        """Test searching entities by name."""
        await store.add_entity("Alice", "character", {})
        await store.add_entity("Bob", "character", {})
        await store.add_entity("Alice Smith", "character", {})

        results = await store.search_entities("Alice")
        assert len(results) == 2

        results = await store.search_entities("Bob")
        assert len(results) == 1
        assert results[0].name == "Bob"

    @pytest.mark.asyncio
    async def test_add_relation(self, store):
        """Test adding a relation."""
        # Add entities first
        entity1 = await store.add_entity("Alice", "character", {})
        entity2 = await store.add_entity("Bob", "character", {})
        
        # Add relation
        relation_id = await store.add_relation(entity1, "knows", entity2)
        assert relation_id == 1
        assert len(store._relations) == 1

    @pytest.mark.asyncio
    async def test_get_relations(self, store):
        """Test getting relations for an entity."""
        # Add entities first
        entity1 = await store.add_entity("Alice", "character", {})
        entity2 = await store.add_entity("Bob", "character", {})
        
        # Add relation
        await store.add_relation(entity1, "knows", entity2)
        
        # Get relations for Alice
        relations = await store.get_relations(entity1)
        assert len(relations) == 1
        relation, related_entity = relations[0]
        assert relation.predicate == "knows"
        assert related_entity.name == "Bob"

    @pytest.mark.asyncio
    async def test_persistence(self, temp_dir):
        """Test that data persists across store instances."""
        store1 = SemanticStore(data_dir=temp_dir)
        await store1.add_entity("Alice", "character", {})

        store2 = SemanticStore(data_dir=temp_dir)
        assert len(store2._entities) == 1
        entity = await store2.get_entity(1)
        assert entity is not None
        assert entity.name == "Alice"