"""Tests for cyclelog.rack."""

import pytest

from cyclelog.errors import NotFoundError
from cyclelog.rack import (
    WindowDirection,
    Rack,
    RackRegistry,
    RackClimateProfile,
    default_racks,
    compare_light,
    suggest_bikes_for_rack,
    rack_report,
    reassign_bike,
    estimate_daily_light_hours,
    rank_racks_for_make,
    build_rack_map,
    bikes_without_rack,
    rack_capacity_report,
    RoomSnapshot,
    RoomHistory,
    sync_rack_bike_ids,
    format_rack_tree,
)
from cyclelog.make import MakeCatalog


class TestWindowDirection:
    def test_str(self):
        assert str(WindowDirection.SOUTH) == "south"


class TestRack:
    def test_create(self, sample_rack):
        assert sample_rack.name == "Living Room"

    def test_add_remove_bike(self, sample_rack):
        sample_rack.add_bike("bike001")
        assert "bike001" in sample_rack.bike_ids
        assert sample_rack.remove_bike("bike001") is True

    def test_effective_light_south(self):
        loc = Rack.create(
            "Bright Room",
            light_level="medium",
            window_direction=WindowDirection.SOUTH,
        )
        assert compare_light(loc.effective_light(), "medium") >= 0

    def test_label(self, sample_rack):
        assert "Living Room" in sample_rack.label()

    def test_to_dict_from_dict(self, sample_rack):
        restored = Rack.from_dict(sample_rack.to_dict())
        assert restored.name == sample_rack.name

    def test_summary(self, sample_rack):
        summary = sample_rack.summary()
        assert "Living Room" in summary


class TestRackRegistry:
    def test_add_and_get(self, rack_registry, sample_rack):
        assert rack_registry.get(sample_rack.id) is not None

    def test_duplicate_id_raises(self, sample_rack):
        reg = RackRegistry()
        reg.add(sample_rack)
        with pytest.raises(ValueError):
            reg.add(sample_rack)

    def test_get_by_name(self, rack_registry, sample_rack):
        assert rack_registry.get_by_name("Living Room") is not None

    def test_require_raises(self):
        reg = RackRegistry()
        with pytest.raises(NotFoundError):
            reg.require("missing")

    def test_remove(self, rack_registry, sample_rack):
        assert rack_registry.remove(sample_rack.id) is True

    def test_assign_unassign_bike(self, rack_registry, sample_rack):
        rack_registry.assign_bike(sample_rack.id, "bike001")
        assert "bike001" in rack_registry.get(sample_rack.id).bike_ids
        rack_registry.unassign_bike("bike001")
        assert "bike001" not in rack_registry.get(sample_rack.id).bike_ids

    def test_find_by_light(self, rack_registry):
        found = rack_registry.find_by_light("bright_indirect")
        assert len(found) >= 1

    def test_find_by_zone(self, rack_registry, sample_rack):
        found = rack_registry.find_by_zone("main")
        assert sample_rack in found

    def test_total_bikes_assigned(self, rack_registry, sample_rack):
        sample_rack.add_bike("p1")
        rack_registry._racks[sample_rack.id] = sample_rack
        assert rack_registry.total_bikes_assigned() >= 1

    def test_racks_needing_humidifier(self, rack_registry):
        low = rack_registry.racks_needing_humidifier(threshold=50)
        assert isinstance(low, list)

    def test_merge(self, rack_registry, sample_rack):
        other = RackRegistry()
        other.add(Rack.create("Kitchen", id="loc002"))
        merged = rack_registry.merge(other)
        assert merged.count() == 2


class TestClimateProfile:
    def test_from_rack(self, sample_rack):
        profile = RackClimateProfile.from_rack(sample_rack)
        assert profile.rack_id == sample_rack.id

    def test_service_factor_high_mileage(self):
        profile = RackClimateProfile(
            rack_id="loc1",
            avg_mileage=70.0,
        )
        assert profile.service_factor() > 1.0

    def test_service_factor_draft(self, sample_rack):
        sample_rack.notes = "drafty window"
        profile = RackClimateProfile.from_rack(sample_rack)
        assert profile.draft_risk is True


class TestRackHelpers:
    def test_default_racks(self):
        reg = default_racks()
        assert reg.count() >= 4

    def test_compare_light(self):
        assert compare_light("low", "full_sun") == -1
        assert compare_light("full_sun", "low") == 1
        assert compare_light("medium", "medium") == 0

    def test_suggest_bikes_for_rack(self, sample_rack):
        keys = suggest_bikes_for_rack(sample_rack)
        assert isinstance(keys, list)

    def test_rack_report(self, rack_registry):
        report = rack_report(rack_registry)
        assert "rack_count" in report

    def test_reassign_bike(self, rack_registry, sample_rack):
        kitchen = Rack.create("Kitchen", id="loc_k")
        rack_registry.add(kitchen)
        reassign_bike(rack_registry, "bike001", sample_rack.id, kitchen.id)
        assert "bike001" in kitchen.bike_ids

    def test_estimate_daily_light_hours(self, sample_rack):
        hours = estimate_daily_light_hours(sample_rack, month=7)
        assert hours > 0

    def test_rank_racks_for_make(self, rack_registry, sample_make):
        ranked = rank_racks_for_make(rack_registry, sample_make)
        assert len(ranked) >= 1

    def test_build_rack_map(self, rack_registry):
        mapping = build_rack_map(rack_registry)
        assert "living room" in mapping

    def test_bikes_without_rack(self, rack_registry):
        missing = bikes_without_rack(rack_registry, ["bike001", "bike999"])
        assert "bike999" in missing

    def test_rack_capacity_report(self, rack_registry, sample_rack):
        sample_rack.bike_ids = ["p1", "p2"]
        report = rack_capacity_report(rack_registry, max_per_room=1)
        assert len(report["crowded"]) >= 1

    def test_room_history(self):
        hist = RoomHistory()
        snap = RoomSnapshot(rack_id="loc1", recorded_at="2024-06-01", mileage_pct=50)
        hist.record(snap)
        assert len(hist.for_rack("loc1")) == 1
        assert hist.avg_mileage("loc1") == 50.0

    def test_sync_rack_bike_ids(self, rack_registry, sample_bike):
        sync_rack_bike_ids(rack_registry, [sample_bike])
        loc = rack_registry.get(sample_bike.rack_id)
        assert sample_bike.id in loc.bike_ids

    def test_format_rack_tree(self, rack_registry):
        text = format_rack_tree(rack_registry)
        assert "Living Room" in text
