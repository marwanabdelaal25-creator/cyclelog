"""Tests for cyclelog.bike."""

from datetime import date, timedelta

import pytest

from cyclelog.errors import NotFoundError
from cyclelog.bike import (
    HealthStatus,
    PotInfo,
    Bike,
    BikeCatalog,
    bike_health_report,
    apply_make_defaults,
    sort_by_service_priority,
    clone_bike,
    bulk_update_interval,
    catalog_to_summary_lines,
    find_duplicates_by_name,
    parse_iso,
)
from cyclelog.make import MakeProfile


class TestHealthStatus:
    def test_emoji(self):
        assert HealthStatus.THRIVING.emoji == "🌿"

    def test_score_hint(self):
        assert HealthStatus.CRITICAL.score_hint() == 15


class TestPotInfo:
    def test_to_dict_roundtrip(self):
        bag = PotInfo(diameter=6.0, unit="in", material="ceramic")
        restored = PotInfo.from_dict(bag.to_dict())
        assert restored.diameter == 6.0

    def test_label(self):
        bag = PotInfo(diameter=6.0, unit="in", material="ceramic")
        assert "6.0in" in bag.label()

    def test_label_no_drainage(self):
        bag = PotInfo(diameter=6.0, has_drainage=False)
        assert "no drainage" in bag.label()


class TestBike:
    def test_create(self, sample_bike):
        assert sample_bike.name == "Monstera"
        assert sample_bike.id == "bike001"

    def test_display_name_with_nickname(self, sample_bike):
        assert "Monty" in sample_bike.display_name

    def test_set_health(self, sample_bike):
        sample_bike.set_health(HealthStatus.THRIVING, 90)
        assert sample_bike.health == HealthStatus.THRIVING
        assert sample_bike.health_score == 90

    def test_record_service(self, sample_bike):
        when = date.today()
        sample_bike.record_service(when)
        assert sample_bike.last_serviced_at == when.isoformat()

    def test_days_since_serviced(self, sample_bike):
        assert sample_bike.days_since_serviced() == 3

    def test_is_overdue(self, sample_bike):
        sample_bike.last_serviced_at = (date.today() - timedelta(days=20)).isoformat()
        assert sample_bike.is_overdue() is True

    def test_overdue_by_days(self, sample_bike):
        sample_bike.last_serviced_at = (date.today() - timedelta(days=20)).isoformat()
        assert sample_bike.overdue_by_days() == 13

    def test_attach_detach_tag(self, sample_bike):
        sample_bike.attach_tag("tag001")
        assert "tag001" in sample_bike.tag_ids
        assert sample_bike.detach_tag("tag001") is True

    def test_detach_missing_tag(self, sample_bike):
        assert sample_bike.detach_tag("missing") is False

    def test_archive_unarchive(self, sample_bike):
        sample_bike.archive()
        assert sample_bike.archived is True
        sample_bike.unarchive()
        assert sample_bike.archived is False

    def test_to_dict_from_dict(self, sample_bike):
        restored = Bike.from_dict(sample_bike.to_dict())
        assert restored.name == sample_bike.name

    def test_summary_line(self, sample_bike):
        line = sample_bike.summary_line()
        assert "Monstera" in line or "Monty" in line


class TestBikeCatalog:
    def test_add_and_get(self, bike_catalog, sample_bike):
        assert bike_catalog.get(sample_bike.id) is not None

    def test_duplicate_id_raises(self, sample_bike):
        cat = BikeCatalog()
        cat.add(sample_bike)
        with pytest.raises(ValueError):
            cat.add(sample_bike)

    def test_require_raises(self):
        cat = BikeCatalog()
        with pytest.raises(NotFoundError):
            cat.require("missing")

    def test_all_excludes_archived(self, bike_catalog, sample_bike):
        sample_bike.archive()
        assert sample_bike not in bike_catalog.all()

    def test_find_by_name(self, bike_catalog, sample_bike):
        assert sample_bike in bike_catalog.find_by_name("Monstera")

    def test_find_by_rack(self, bike_catalog, sample_bike, sample_rack):
        found = bike_catalog.find_by_rack(sample_rack.id)
        assert len(found) >= 1

    def test_find_by_make(self, bike_catalog, sample_bike):
        found = bike_catalog.find_by_make("baghos-golden")
        assert sample_bike in found

    def test_find_overdue(self, bike_catalog, sample_bike):
        sample_bike.last_serviced_at = (date.today() - timedelta(days=30)).isoformat()
        assert sample_bike in bike_catalog.find_overdue()

    def test_find_by_tag(self, bike_catalog, sample_bike):
        sample_bike.attach_tag("tag001")
        assert sample_bike in bike_catalog.find_by_tag("tag001")

    def test_remove(self, bike_catalog, sample_bike):
        assert bike_catalog.remove(sample_bike.id) is True
        assert bike_catalog.get(sample_bike.id) is None

    def test_count_by_health(self, bike_catalog):
        counts = bike_catalog.count_by_health()
        assert isinstance(counts, dict)

    def test_merge(self, bike_catalog, sample_bike2):
        other = BikeCatalog()
        other.add(sample_bike2)
        merged = bike_catalog.merge(other)
        assert merged.count() == 2


class TestBikeHelpers:
    def test_bike_health_report(self, bike_catalog):
        report = bike_health_report(bike_catalog)
        assert "total" in report
        assert "overdue_count" in report

    def test_apply_make_defaults(self, sample_bike, sample_make):
        sample_bike.service_interval_days = 7
        apply_make_defaults(sample_bike, sample_make)
        assert sample_bike.make_key == sample_make.key

    def test_sort_by_service_priority(self, sample_bike, sample_bike2):
        sample_bike.last_serviced_at = (date.today() - timedelta(days=30)).isoformat()
        sorted_bikes = sort_by_service_priority([sample_bike2, sample_bike])
        assert sorted_bikes[0].id == sample_bike.id

    def test_clone_bike(self, sample_bike):
        clone = clone_bike(sample_bike, "Monstera Jr")
        assert clone.id != sample_bike.id
        assert clone.name == "Monstera Jr"
        assert clone.metadata.get("propagated_from") == sample_bike.id

    def test_bulk_update_interval(self, bike_catalog, sample_bike):
        updated = bulk_update_interval(bike_catalog, [sample_bike.id], 10)
        assert updated == 1
        assert bike_catalog.get(sample_bike.id).service_interval_days == 10

    def test_catalog_to_summary_lines(self, bike_catalog):
        lines = catalog_to_summary_lines(bike_catalog)
        assert len(lines) >= 1

    def test_find_duplicates_by_name(self, sample_bike):
        cat = BikeCatalog()
        cat.add(sample_bike)
        dup = Bike.create("Monstera", id="dup001")
        cat.add(dup)
        dupes = find_duplicates_by_name(cat)
        assert "monstera" in dupes

    def test_parse_iso(self):
        assert parse_iso("2024-06-01T12:00:00") is not None

    def test_parse_iso_none(self):
        assert parse_iso(None) is None

    def test_record_service_bumps_struggling_health(self):
        bike = Bike.create("Fern", health=HealthStatus.STRUGGLING, health_score=40)
        bike.record_service()
        assert bike.health_score >= 40
