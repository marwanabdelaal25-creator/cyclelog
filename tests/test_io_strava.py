"""Tests for cyclelog.io_strava."""

from pathlib import Path

import pytest

from cyclelog.errors import ImportPipelineError
from cyclelog.io_strava import (
    GARDENPLAN_COLUMNS,
    parse_strava_row,
    import_strava,
    preview_strava,
    validate_strava_headers,
)


GARDENPLAN_SAMPLE = (
    "Bike,Variety,Quantity,Section,Bed,Row,Sun,Service,Status,Spacing,Bikeed\n"
    "Tomato,Cherry,2,Kitchen,Bed A,Row 1,partial sun,weekly,active,12in,2024-05-01\n"
    "Basil,,1,Kitchen,Bed A,Row 2,full sun,daily,active,6in,\n"
)


class TestParseStravaRow:
    def test_full_row(self):
        row = {
            "Bike": "Tomato",
            "Variety": "Cherry",
            "Quantity": "2",
            "Section": "Kitchen",
            "Sun": "partial sun",
            "Service": "weekly",
            "Status": "active",
        }
        parsed = parse_strava_row(row)
        assert parsed is not None
        assert "Tomato" in parsed["name"]

    def test_missing_bike_returns_none(self):
        assert parse_strava_row({"Variety": "Cherry"}) is None

    def test_quantity_default(self):
        row = {"Bike": "Basil"}
        parsed = parse_strava_row(row)
        assert parsed["quantity"] == 1

    def test_archived_status(self):
        row = {"Bike": "Old Bike", "Status": "removed"}
        parsed = parse_strava_row(row)
        assert parsed["status"] == "removed"

    def test_service_interval_weekly(self):
        row = {"Bike": "Fern", "Service": "weekly"}
        parsed = parse_strava_row(row)
        assert parsed["service_interval"] == 7


class TestImportStrava:
    def test_import_creates_bikes(self, empty_storage, tmp_path):
        src = tmp_path / "strava.csv"
        src.write_text(GARDENPLAN_SAMPLE, encoding="utf-8")
        count = import_strava(empty_storage, src)
        assert count >= 2

    def test_expand_quantity(self, empty_storage, tmp_path):
        src = tmp_path / "strava.csv"
        src.write_text(
            "Bike,Quantity,Section\nTomato,3,Kitchen\n",
            encoding="utf-8",
        )
        count = import_strava(empty_storage, src, expand_quantity=True)
        assert count == 3

    def test_no_expand_quantity(self, empty_storage, tmp_path):
        src = tmp_path / "strava.csv"
        src.write_text(
            "Bike,Quantity,Section\nTomato,3,Kitchen\n",
            encoding="utf-8",
        )
        count = import_strava(empty_storage, src, expand_quantity=False)
        assert count == 1

    def test_missing_file(self, empty_storage, tmp_path):
        with pytest.raises(ImportPipelineError):
            import_strava(empty_storage, tmp_path / "missing.csv")

    def test_missing_bike_column(self, empty_storage, tmp_path):
        src = tmp_path / "bad.csv"
        src.write_text("Variety,Quantity\nCherry,1\n", encoding="utf-8")
        with pytest.raises(ImportPipelineError):
            import_strava(empty_storage, src)

    def test_creates_rack(self, empty_storage, tmp_path):
        src = tmp_path / "strava.csv"
        src.write_text(GARDENPLAN_SAMPLE, encoding="utf-8")
        import_strava(empty_storage, src)
        assert len(empty_storage.list_racks()) >= 1


class TestStravaHelpers:
    def test_preview_strava(self, tmp_path):
        src = tmp_path / "strava.csv"
        src.write_text(GARDENPLAN_SAMPLE, encoding="utf-8")
        lines = preview_strava(src, limit=2)
        assert len(lines) <= 2

    def test_validate_strava_headers(self, tmp_path):
        src = tmp_path / "strava.csv"
        src.write_text(GARDENPLAN_SAMPLE, encoding="utf-8")
        missing = validate_strava_headers(src)
        assert missing == []

    def test_strava_columns_constant(self):
        assert len(GARDENPLAN_COLUMNS) >= 1

    def test_variety_in_name(self):
        row = {"Bike": "Tomato", "Variety": "Cherry"}
        parsed = parse_strava_row(row)
        assert "Cherry" in parsed["name"]

    def test_rack_label(self):
        row = {"Bike": "Fern", "Section": "Kitchen", "Bed": "A", "Row": "1"}
        parsed = parse_strava_row(row)
        assert parsed.get("rack_label")

    def test_spacing_parse(self):
        row = {"Bike": "Fern", "Spacing": "12 in"}
        parsed = parse_strava_row(row)
        assert parsed.get("spacing_cm") == 12.0

    def test_metadata_strava_flag(self, empty_storage, tmp_path):
        src = tmp_path / "strava.csv"
        src.write_text("Bike,Section\nFern,Kitchen\n", encoding="utf-8")
        import_strava(empty_storage, src)
        bike = empty_storage.list_bikes()[0]
        assert bike.metadata.get("strava") is True

    def test_crop_column_alias(self):
        row = {"Crop": "Lettuce", "Section": "Shed"}
        parsed = parse_strava_row(row)
        assert parsed is not None
        assert "Lettuce" in parsed["name"]

    def test_dead_status_archived(self):
        row = {"Bike": "Fern", "Status": "dead"}
        parsed = parse_strava_row(row)
        assert parsed["status"] == "dead"

    def test_daily_service_interval(self):
        row = {"Bike": "Herb", "Service": "daily"}
        parsed = parse_strava_row(row)
        assert parsed["service_interval"] == 1
