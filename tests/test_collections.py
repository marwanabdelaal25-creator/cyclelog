"""Tests for cyclelog.collections."""

import pytest

from cyclelog.errors import NotFoundError, ValidationError
from cyclelog.collections import CollectionManager


class TestCollectionManager:
    def test_create(self, populated_storage, sample_bike):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Kitchen Herbs", bike_ids=[sample_bike.id])
        assert coll["name"] == "Kitchen Herbs"
        assert sample_bike.id in coll["bike_ids"]

    def test_create_empty_name_raises(self, empty_storage):
        mgr = CollectionManager(empty_storage)
        with pytest.raises(ValidationError):
            mgr.create("  ")

    def test_create_invalid_bike_raises(self, empty_storage):
        mgr = CollectionManager(empty_storage)
        with pytest.raises(NotFoundError):
            mgr.create("Bad", bike_ids=["missing"])

    def test_list_all(self, populated_storage, sample_bike):
        mgr = CollectionManager(populated_storage)
        mgr.create("Group A", bike_ids=[sample_bike.id])
        assert len(mgr.list_all()) == 1

    def test_get(self, populated_storage, sample_bike):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Favorites")
        found = mgr.get(coll["id"])
        assert found["name"] == "Favorites"

    def test_get_not_found(self, empty_storage):
        mgr = CollectionManager(empty_storage)
        with pytest.raises(NotFoundError):
            mgr.get("missing")

    def test_add_bike(self, populated_storage, sample_bike, sample_bike2):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Group")
        updated = mgr.add_bike(coll["id"], sample_bike.id)
        updated = mgr.add_bike(coll["id"], sample_bike2.id)
        assert len(updated["bike_ids"]) == 2

    def test_add_bike_dedupes(self, populated_storage, sample_bike):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Group", bike_ids=[sample_bike.id])
        updated = mgr.add_bike(coll["id"], sample_bike.id)
        assert updated["bike_ids"].count(sample_bike.id) == 1

    def test_remove_bike(self, populated_storage, sample_bike):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Group", bike_ids=[sample_bike.id])
        updated = mgr.remove_bike(coll["id"], sample_bike.id)
        assert sample_bike.id not in updated["bike_ids"]

    def test_rename(self, populated_storage):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Old Name")
        updated = mgr.rename(coll["id"], "New Name")
        assert updated["name"] == "New Name"

    def test_rename_blank_raises(self, populated_storage):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Name")
        with pytest.raises(ValidationError):
            mgr.rename(coll["id"], "  ")

    def test_delete(self, populated_storage):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Temp")
        mgr.delete(coll["id"])
        assert mgr.list_all() == []

    def test_bikes_in(self, populated_storage, sample_bike):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Group", bike_ids=[sample_bike.id])
        bikes = mgr.bikes_in(coll["id"])
        assert len(bikes) == 1

    def test_bikes_in_skips_stale(self, populated_storage):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Group")
        populated_storage.update_collection(coll["id"], {"bike_ids": ["stale_id"]})
        assert mgr.bikes_in(coll["id"]) == []

    def test_collections_for_bike(self, populated_storage, sample_bike):
        mgr = CollectionManager(populated_storage)
        mgr.create("A", bike_ids=[sample_bike.id])
        mgr.create("B", bike_ids=[sample_bike.id])
        cols = mgr.collections_for_bike(sample_bike.id)
        assert len(cols) == 2

    def test_merge(self, populated_storage, sample_bike, sample_bike2):
        mgr = CollectionManager(populated_storage)
        t = mgr.create("Target", bike_ids=[sample_bike.id])
        s = mgr.create("Source", bike_ids=[sample_bike2.id])
        merged = mgr.merge(t["id"], s["id"])
        assert sample_bike2.id in merged["bike_ids"]
        assert len(mgr.list_all()) == 1

    def test_merge_dedupes_overlap(self, populated_storage, sample_bike):
        mgr = CollectionManager(populated_storage)
        t = mgr.create("Target", bike_ids=[sample_bike.id])
        s = mgr.create("Source", bike_ids=[sample_bike.id])
        merged = mgr.merge(t["id"], s["id"])
        assert merged["bike_ids"].count(sample_bike.id) == 1

    def test_description_stored(self, populated_storage):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Herbs", description="Kitchen window")
        assert coll["description"] == "Kitchen window"

    def test_add_unknown_bike_raises(self, populated_storage):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Group")
        with pytest.raises(NotFoundError):
            mgr.add_bike(coll["id"], "missing")
