"""Tests for cyclelog.storage."""

import json

import pytest

from cyclelog.errors import NotFoundError, StorageError, ValidationError
from cyclelog.rack import Rack
from cyclelog.bike import Bike, HealthStatus
from cyclelog.make import MakeProfile
from cyclelog.storage import JsonStorage, DEFAULT_CELLAR, SCHEMA_VERSION


class TestJsonStorageInit:
    def test_creates_empty_shed(self, tmp_shed_path):
        storage = JsonStorage(tmp_shed_path)
        assert tmp_shed_path.exists()

    def test_loads_existing(self, populated_storage, tmp_shed_path):
        storage2 = JsonStorage(tmp_shed_path)
        assert len(storage2.list_bikes()) >= 2


class TestBikes:
    def test_create_and_list(self, empty_storage, sample_bike):
        created = empty_storage.create_bike(sample_bike)
        assert created.name == sample_bike.name

    def test_get_bike(self, populated_storage, sample_bike):
        bike = populated_storage.get_bike(sample_bike.id)
        assert bike.id == sample_bike.id

    def test_get_bike_not_found(self, empty_storage):
        with pytest.raises(NotFoundError):
            empty_storage.get_bike("missing")

    def test_update_bike(self, populated_storage, sample_bike):
        updated = populated_storage.update_bike(sample_bike.id, {"nickname": "NewNick"})
        assert updated.nickname == "NewNick"

    def test_delete_bike(self, populated_storage, sample_bike):
        populated_storage.delete_bike(sample_bike.id)
        with pytest.raises(NotFoundError):
            populated_storage.get_bike(sample_bike.id)

    def test_list_bikes_active_only(self, populated_storage, sample_bike):
        populated_storage.update_bike(sample_bike.id, {"archived": True})
        active = populated_storage.list_bikes(active_only=True)
        assert all(not p.archived for p in active)

    def test_duplicate_bike_raises(self, populated_storage, sample_bike):
        with pytest.raises(ValidationError):
            populated_storage.create_bike(sample_bike.to_dict())


class TestMake:
    def test_create_make(self, empty_storage, sample_make):
        created = empty_storage.create_make(sample_make)
        assert created.key == sample_make.key

    def test_get_make(self, populated_storage, sample_make):
        sp = populated_storage.get_make(sample_make.key)
        assert sp.common_name == sample_make.common_name

    def test_delete_make(self, populated_storage, sample_make):
        populated_storage.delete_make(sample_make.key)
        with pytest.raises(NotFoundError):
            populated_storage.get_make(sample_make.key)


class TestRacks:
    def test_create_rack(self, empty_storage, sample_rack):
        created = empty_storage.create_rack(sample_rack)
        assert created.name == sample_rack.name

    def test_get_rack(self, populated_storage, sample_rack):
        loc = populated_storage.get_rack(sample_rack.id)
        assert loc.id == sample_rack.id

    def test_update_rack(self, populated_storage, sample_rack):
        updated = populated_storage.update_rack(sample_rack.id, {"notes": "Updated"})
        assert updated.notes == "Updated"


class TestService:
    def test_create_service_event(self, populated_storage, sample_bike):
        event = populated_storage.create_service_event({
            "id": "we_new",
            "bike_id": sample_bike.id,
            "amount_ml": 300,
        })
        assert event["bike_id"] == sample_bike.id

    def test_list_service_events_filtered(self, populated_storage, sample_bike):
        events = populated_storage.list_service_events(bike_id=sample_bike.id)
        assert len(events) >= 1

    def test_delete_service_event(self, populated_storage):
        events = populated_storage.list_service_events()
        eid = events[0]["id"]
        populated_storage.delete_service_event(eid)
        with pytest.raises(NotFoundError):
            populated_storage.get_service_event(eid)


class TestTagsAndNotes:
    def test_create_tag(self, empty_storage):
        tag = empty_storage.create_tag({"id": "tag_new", "name": "test"})
        assert tag["name"] == "test"

    def test_create_note(self, populated_storage, sample_bike):
        note = populated_storage.create_note({
            "id": "note_new",
            "bike_id": sample_bike.id,
            "body": "Test note",
        })
        assert note["body"] == "Test note"

    def test_list_notes_filtered(self, populated_storage, sample_bike):
        notes = populated_storage.list_notes(bike_id=sample_bike.id)
        assert len(notes) >= 1


class TestAuditAndPlugins:
    def test_append_audit(self, empty_storage):
        entry = empty_storage.append_audit({"action": "create", "entity": "bike"})
        assert "timestamp" in entry

    def test_upsert_plugin(self, empty_storage):
        plugin = empty_storage.upsert_plugin({"id": "p1", "name": "Test Plugin"})
        assert plugin["name"] == "Test Plugin"
        updated = empty_storage.upsert_plugin({"id": "p1", "name": "Updated"})
        assert updated["name"] == "Updated"


class TestRecurringAndCollections:
    def test_create_recurring(self, empty_storage):
        task = empty_storage.create_recurring({"id": "r1", "title": "Weekly mist"})
        assert task["title"] == "Weekly mist"

    def test_create_collection(self, empty_storage):
        coll = empty_storage.create_collection({"id": "c1", "name": "Favorites"})
        assert coll["name"] == "Favorites"


class TestStorageCore:
    def test_snapshot(self, populated_storage):
        snap = populated_storage.snapshot()
        assert "bikes" in snap

    def test_replace_all(self, empty_storage, sample_bike):
        empty_storage.replace_all({
            **DEFAULT_CELLAR,
            "bikes": [sample_bike.to_dict()],
        })
        assert len(empty_storage.list_bikes()) == 1

    def test_mutate(self, empty_storage):
        def add_tag(data):
            data["tags"].append({"id": "t1", "name": "test"})
        empty_storage.mutate(add_tag)
        assert len(empty_storage.list_tags()) == 1

    def test_load_corrupt_json(self, tmp_shed_path):
        tmp_shed_path.write_text("{not json", encoding="utf-8")
        with pytest.raises(StorageError):
            JsonStorage(tmp_shed_path)

    def test_schema_version_in_default(self):
        assert DEFAULT_CELLAR["schema_version"] == SCHEMA_VERSION
