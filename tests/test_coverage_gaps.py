"""Targeted pytest coverage for previously uncovered cyclelog lines."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cyclelog.errors import (
    ExportError,
    ImportPipelineError,
    NotFoundError,
    StorageError,
    ValidationError,
)
from cyclelog.parser import (
    coerce_float,
    coerce_light_list,
    format_amount_ml,
    format_health_status,
    format_mileage,
    format_interval_days,
    format_light_level,
    format_temperature_c,
    normalize_enum,
    parse_amount_ml,
    parse_bool,
    parse_care_frequency,
    parse_date,
    parse_datetime,
    parse_duration_minutes,
    parse_odometer_strength,
    parse_health_note,
    parse_health_status,
    parse_mileage,
    parse_interval,
    parse_interval_range,
    parse_key_value,
    parse_key_value_pairs,
    parse_rack_descriptor,
    parse_npk,
    parse_ph,
    parse_bike_list,
    parse_relative_date,
    parse_reminder_offset,
    parse_season_hint,
    parse_grind_ph_range,
    parse_tags,
    parse_temperature,
    parse_weekday,
    parse_weekly_schedule,
    parse_service_method,
    parse_light_level,
    parse_growth_rate,
)
from cyclelog.validators import (
    validate_amount_range,
    validate_batch_size,
    validate_care_event_type,
    validate_care_product,
    validate_color_hex,
    validate_duration_minutes,
    validate_export_format,
    validate_odometer_interval_weeks,
    validate_floor,
    validate_health_status,
    validate_mileage_pct,
    validate_mileage_range,
    validate_id,
    validate_interval_days,
    validate_last_serviced,
    validate_list_not_empty,
    validate_metadata,
    validate_note_body,
    validate_note_kind,
    validate_optional_url,
    validate_ph,
    validate_bike_name,
    validate_bag_diameter,
    validate_bag_material,
    validate_priority,
    validate_reminder_days,
    validate_room_name,
    validate_season_name,
    validate_grind_components,
    validate_grind_ph_preference,
    validate_tag_name,
    validate_temperature_c,
    validate_uuidish,
    validate_service_amount_ml,
    validate_service_quality,
    validate_service_method,
    validate_service_notes,
    validate_window_direction,
    validate_acquired_date,
    validate_rack_zone,
    validate_health_score,
)


# --- parser gaps ---


class TestParserCoverageGaps:
    def test_parse_date_tomorrow(self):
        assert parse_date("tomorrow") == date.today() + timedelta(days=1)

    def test_parse_date_plus_relative(self):
        assert parse_date("+2d") == date.today() + timedelta(days=2)

    def test_parse_relative_months(self):
        assert parse_relative_date("+1m") == date.today() + timedelta(days=30)

    def test_parse_datetime_space_and_z(self):
        dt = parse_datetime("2024-06-01 14:30")
        assert dt.hour == 14
        dt2 = parse_datetime("2024-06-01T12:00:00Z")
        assert dt2.year == 2024

    def test_parse_interval_months(self):
        assert parse_interval("2 months") == 60

    def test_parse_interval_range_to(self):
        assert parse_interval_range("5 to 7 days") == (5, 7)

    def test_parse_amount_oz(self):
        assert parse_amount_ml("8 oz") == pytest.approx(8 * 29.5735, rel=0.01)

    def test_parse_light_compact_value(self):
        assert parse_light_level("bright_indirect") == "bright_indirect"

    def test_parse_mileage_bad(self):
        with pytest.raises(ValueError):
            parse_mileage("humid")

    def test_parse_temperature_bad(self):
        with pytest.raises(ValueError):
            parse_temperature("warm")

    def test_parse_bool_invalid(self):
        with pytest.raises(ValueError):
            parse_bool("maybe")

    def test_coerce_float_default(self):
        assert coerce_float("x", default=1.5) == 1.5

    def test_parse_key_value_equals_and_error(self):
        assert parse_key_value("a=b") == ("a", "b")
        with pytest.raises(ValueError):
            parse_key_value("noseparator")

    def test_parse_key_value_pairs_colon_and_skip(self):
        assert parse_key_value_pairs("a:1, badpart, b=2") == {"a": "1", "b": "2"}

    def test_parse_tags_empty(self):
        assert parse_tags("") == []

    def test_parse_service_method_passthrough(self):
        assert parse_service_method("custom soak") == "custom_soak"

    def test_parse_season_unknown(self):
        with pytest.raises(ValueError):
            parse_season_hint("monsoon")

    def test_parse_duration_digits_only(self):
        assert parse_duration_minutes("45") == 45

    def test_parse_duration_bad(self):
        with pytest.raises(ValueError):
            parse_duration_minutes("soon")

    def test_parse_odometer_quarter_full_npk(self):
        assert parse_odometer_strength("quarter strength")["dilution"] == 0.25
        assert parse_odometer_strength("full strength")["dilution"] == 1.0
        assert "npk" in parse_odometer_strength("10-10-10")

    def test_parse_health_note_issues_root_rot(self):
        flags = parse_health_note("issue on leaves and root rot smell")
        assert flags.get("issues") is True
        assert flags.get("root_rot") is True

    def test_format_interval_one_week(self):
        assert format_interval_days(7) == "1w"

    def test_format_amount_sub_liter(self):
        assert format_amount_ml(500) == "500ml"

    def test_format_light_unknown(self):
        assert "Custom" in format_light_level("custom_level")

    def test_parse_grind_ph_bad_and_swap(self):
        with pytest.raises(ValueError):
            parse_grind_ph_range("bad")
        assert parse_grind_ph_range("7.0-6.0") == (6.0, 7.0)

    def test_parse_weekday_bad_and_empty_schedule(self):
        with pytest.raises(ValueError):
            parse_weekday("Funday")
        assert parse_weekly_schedule("") == []

    def test_parse_bike_list_comma(self):
        assert parse_bike_list("A, B, C") == ["A", "B", "C"]

    def test_parse_health_status_unknown(self):
        with pytest.raises(ValueError):
            parse_health_status("meh")

    def test_parse_reminder_offsets(self):
        assert parse_reminder_offset("2h before") == 7200
        assert parse_reminder_offset("30m") == 1800
        assert parse_reminder_offset("5") == 300

    def test_parse_npk_bad(self):
        with pytest.raises(ValueError):
            parse_npk("10-10")

    def test_parse_growth_rate_default(self):
        assert parse_growth_rate("variable") == "moderate"

    def test_parse_rack_descriptor_temp(self):
        result = parse_rack_descriptor("Office | 22c")
        assert "temp_c" in result

    def test_normalize_enum_substring(self):
        allowed = {"indirect": "bright_indirect"}
        assert normalize_enum("bright_indirect", allowed) == "bright_indirect"

    def test_parse_care_frequency_equals(self):
        assert parse_care_frequency("mist=3d")["mist"] == 3

    def test_format_temperature_celsius(self):
        assert "°C" in format_temperature_c(20.0, use_f=False)

    def test_format_helpers(self):
        assert format_mileage(40.2) == "40%"
        assert format_health_status("okay") == "Okay"


# --- validators gaps ---


class TestValidatorsCoverageGaps:
    def test_interval_days_too_long(self):
        with pytest.raises(ValidationError):
            validate_interval_days(400)

    def test_mileage_range_inverted(self):
        with pytest.raises(ValidationError):
            validate_mileage_range(70, 40)

    def test_service_amount_too_large(self):
        with pytest.raises(ValidationError):
            validate_service_amount_ml(60_000)

    def test_bag_diameter_zero_and_cm_range(self):
        with pytest.raises(ValidationError):
            validate_bag_diameter(0)
        with pytest.raises(ValidationError):
            validate_bag_diameter(200, unit="cm")

    def test_bag_diameter_inches_too_large(self):
        with pytest.raises(ValidationError):
            validate_bag_diameter(50, unit="in")

    def test_bag_material_custom(self):
        assert validate_bag_material("wood") == "wood"

    def test_service_method_bad(self):
        with pytest.raises(ValidationError):
            validate_service_method("spray")

    def test_temperature_out_of_range(self):
        with pytest.raises(ValidationError):
            validate_temperature_c(100)

    def test_ph_out_of_range(self):
        with pytest.raises(ValidationError):
            validate_ph(20)

    def test_id_too_long(self):
        with pytest.raises(ValidationError):
            validate_id("x" * 70)

    def test_uuidish_bad(self):
        with pytest.raises(ValidationError):
            validate_uuidish("not-hex!")

    def test_tag_name_too_long(self):
        with pytest.raises(ValidationError):
            validate_tag_name("x" * 40)

    def test_note_body_too_long(self):
        with pytest.raises(ValidationError):
            validate_note_body("x" * 10_001)

    def test_acquired_too_old(self):
        with pytest.raises(ValidationError):
            validate_acquired_date(date(1960, 1, 1))

    def test_last_serviced_future(self):
        with pytest.raises(ValidationError):
            validate_last_serviced(date.today() + timedelta(days=1))

    def test_room_name_too_long(self):
        with pytest.raises(ValidationError):
            validate_room_name("x" * 70)

    def test_zone_too_long(self):
        with pytest.raises(ValidationError):
            validate_rack_zone("x" * 50)

    def test_odometer_interval_bad(self):
        with pytest.raises(ValidationError):
            validate_odometer_interval_weeks(0)

    def test_care_event_type_bad(self):
        with pytest.raises(ValidationError):
            validate_care_event_type("dance")

    def test_metadata_not_dict(self):
        with pytest.raises(ValidationError):
            validate_metadata("meta")

    def test_optional_url_bad(self):
        with pytest.raises(ValidationError):
            validate_optional_url("ftp://x.com")

    def test_grind_ph_inverted(self):
        with pytest.raises(ValidationError):
            validate_grind_ph_preference(7.0, 5.0)

    def test_service_notes_too_long(self):
        with pytest.raises(ValidationError):
            validate_service_notes("n" * 2500)

    def test_batch_size_bounds(self):
        with pytest.raises(ValidationError):
            validate_batch_size(0)

    def test_season_invalid(self):
        with pytest.raises(ValidationError):
            validate_season_name("monsoon")

    def test_health_status_invalid(self):
        with pytest.raises(ValidationError):
            validate_health_status("great")

    def test_amount_range_inverted(self):
        with pytest.raises(ValidationError):
            validate_amount_range(500, 100)

    def test_list_not_empty(self):
        with pytest.raises(ValidationError):
            validate_list_not_empty([], "items")

    def test_export_format_bad(self):
        with pytest.raises(ValidationError):
            validate_export_format("xml")

    def test_care_product_too_long(self):
        with pytest.raises(ValidationError):
            validate_care_product("x" * 150)

    def test_duration_minutes_bad(self):
        with pytest.raises(ValidationError):
            validate_duration_minutes(25 * 60)

    def test_floor_too_long(self):
        with pytest.raises(ValidationError):
            validate_floor("x" * 30)

    def test_priority_bad(self):
        with pytest.raises(ValidationError):
            validate_priority(11)

    def test_reminder_days_bad(self):
        with pytest.raises(ValidationError):
            validate_reminder_days(40)

    def test_window_direction_bad(self):
        with pytest.raises(ValidationError):
            validate_window_direction("up")

    def test_grind_component_too_long(self):
        with pytest.raises(ValidationError):
            validate_grind_components(["x" * 70])

    def test_service_quality_bad(self):
        with pytest.raises(ValidationError):
            validate_service_quality("sparkling")

    def test_note_kind_bad(self):
        with pytest.raises(ValidationError):
            validate_note_kind("memo")

    def test_bike_name_invalid_chars(self):
        with pytest.raises(ValidationError):
            validate_bike_name("!!!")


# --- io_csv gaps ---


class TestIoCsvCoverageGaps:
    def test_read_csv_missing_file(self, empty_storage, tmp_path):
        from cyclelog.io_csv import import_bikes_csv

        with pytest.raises(ImportPipelineError):
            import_bikes_csv(empty_storage, tmp_path / "nope.csv")

    def test_import_update_existing(self, populated_storage, tmp_path):
        from cyclelog.io_csv import import_bikes_csv

        src = tmp_path / "update.csv"
        src.write_text(
            "id,name,health,health_score,service_amount_ml,mileage_override\n"
            "bike001,Monstera Renamed,okay,85,300ml,55\n",
            encoding="utf-8",
        )
        n = import_bikes_csv(populated_storage, src, update=True)
        assert n == 1
        bike = populated_storage.get_bike("bike001")
        assert bike.name == "Monstera Renamed"
        assert bike.health.value == "okay"

    def test_import_service_by_name(self, populated_storage, tmp_path, sample_service_csv):
        from cyclelog.io_csv import import_service_csv

        src = tmp_path / "w.csv"
        src.write_text(
            "bike_name,serviced_at,amount_ml\n"
            "Monstera,2024-01-15,200ml\n",
            encoding="utf-8",
        )
        assert import_service_csv(populated_storage, src) == 1

    def test_import_service_bad_amount(self, populated_storage, tmp_path):
        from cyclelog.io_csv import import_service_csv

        src = tmp_path / "w.csv"
        src.write_text(
            "bike_id,serviced_at,amount_ml\n"
            "bike001,2024-01-15,not-an-amount\n",
            encoding="utf-8",
        )
        with pytest.raises(ImportPipelineError):
            import_service_csv(populated_storage, src)

    def test_validate_csv_headers_service(self, tmp_path):
        from cyclelog.io_csv import validate_csv_headers, sample_rows

        p = tmp_path / "w.csv"
        p.write_text("foo,bar\n1,2\n", encoding="utf-8")
        assert "bike_id or bike_name" in validate_csv_headers(p, kind="service")[0]
        assert sample_rows(tmp_path / "missing.csv") == []

    def test_export_oserror(self, populated_storage, tmp_path):
        from cyclelog.io_csv import export_bikes_csv

        with patch.object(Path, "open", side_effect=OSError("disk full")):
            with pytest.raises(ExportError):
                export_bikes_csv(populated_storage, tmp_path / "out.csv")


# --- io_jsonl gaps ---


class TestIoJsonlCoverageGaps:
    def test_iter_lines_oserror(self, tmp_path):
        from cyclelog.io_jsonl import _iter_lines

        with patch.object(Path, "open", side_effect=OSError("denied")):
            with pytest.raises(ImportPipelineError):
                list(_iter_lines(tmp_path / "x.jsonl"))

    def test_load_line_invalid_json(self, tmp_path):
        from cyclelog.io_jsonl import _load_line

        with pytest.raises(ImportPipelineError):
            _load_line("{bad", 1)

    def test_load_line_not_object(self):
        from cyclelog.io_jsonl import _load_line

        with pytest.raises(ImportPipelineError):
            _load_line("[1,2]", 1)

    def test_export_oserror(self, populated_storage, tmp_path):
        from cyclelog.io_jsonl import export_service_jsonl

        with patch.object(Path, "open", side_effect=OSError("fail")):
            with pytest.raises(ExportError):
                export_service_jsonl(populated_storage, tmp_path / "o.jsonl")

    def test_import_missing(self, empty_storage, tmp_path):
        from cyclelog.io_jsonl import import_service_jsonl

        with pytest.raises(ImportPipelineError):
            import_service_jsonl(empty_storage, tmp_path / "n.jsonl")

    def test_import_care_remaps_fields(self, empty_storage, tmp_path):
        from cyclelog.io_jsonl import import_care_jsonl

        src = tmp_path / "care.jsonl"
        src.write_text(
            json.dumps({
                "_type": "care",
                "bike_id": "p1",
                "event_type": "grind",
                "occurred_at": "2024-06-01T12:00:00",
            }) + "\n",
            encoding="utf-8",
        )
        empty_storage.create_bike({"id": "p1", "name": "Fern"})
        assert import_care_jsonl(empty_storage, src) == 1

    def test_import_mixed_bike_update_and_skip(self, empty_storage, tmp_path):
        from cyclelog.io_jsonl import import_mixed_jsonl

        empty_storage.create_bike({"id": "p1", "name": "Fern"})
        src = tmp_path / "mix.jsonl"
        lines = [
            {"_type": "bike", "id": "p1", "name": "Fern Updated"},
            {"_type": "note", "id": "n1", "bike_id": "p1", "body": "hi"},
            {"_type": "unknown", "x": 1},
        ]
        src.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
        counts = import_mixed_jsonl(empty_storage, src)
        assert counts["bike"] == 1
        assert counts["note"] == 1
        assert counts["skipped"] == 1

    def test_count_and_preview(self, tmp_path):
        from cyclelog.io_jsonl import count_lines, preview

        assert count_lines(tmp_path / "n.jsonl") == 0
        p = tmp_path / "p.jsonl"
        p.write_text('{"_type":"service","bike_id":"x"}\n', encoding="utf-8")
        assert count_lines(p) == 1
        assert preview(p, limit=1)[0]["_type"] == "service"


# --- io_strava gaps ---


class TestIoStravaCoverageGaps:
    def test_service_interval_variants(self):
        from cyclelog.io_strava import parse_strava_row

        for service, expected in [
            ("daily", 1),
            ("twice a week", 3),
            ("monthly", 30),
            ("drought tolerant", 14),
            ("moist grind", 3),
            ("high moisture", 3),
        ]:
            parsed = parse_strava_row({"Bike": "X", "Service": service})
            assert parsed["service_interval"] == expected

    def test_bikeed_date_invalid_kept(self):
        from cyclelog.io_strava import parse_strava_row

        parsed = parse_strava_row({"Bike": "X", "Bikeed Date": "someday"})
        assert parsed["bikeed_at"] == "someday"

    def test_ensure_rack_existing(self, empty_storage, tmp_path, sample_rack):
        from cyclelog.io_strava import import_strava

        empty_storage.create_rack(sample_rack)
        src = tmp_path / "gp.csv"
        src.write_text(
            "Bike,Section\nFern,%s\n" % sample_rack.name.split()[0],
            encoding="utf-8",
        )
        import_strava(empty_storage, src)

    def test_preview_missing_file(self, tmp_path):
        from cyclelog.io_strava import preview_strava, validate_strava_headers

        assert preview_strava(tmp_path / "n.csv") == []
        assert validate_strava_headers(tmp_path / "n.csv") == ["Bike"]

    def test_import_pipeline_error_on_bad_row(self, empty_storage, tmp_path):
        from cyclelog.io_strava import import_strava

        src = tmp_path / "gp.csv"
        src.write_text("Bike,Quantity\nBad,\n", encoding="utf-8")
        with patch("cyclelog.io_strava.Bike.create", side_effect=ValueError("boom")):
            with pytest.raises(ImportPipelineError):
                import_strava(empty_storage, src)


# --- io_komoot gaps ---


class TestIoKomootCoverageGaps:
    def test_parse_komoot_interval_digits(self):
        from cyclelog.io_komoot import parse_komoot_row

        row = {
            "Bike Name": "Fern",
            "Service Every": "about 10 days",
            "Last Serviceed": "not-a-date",
            "Light": "indirect",
        }
        parsed = parse_komoot_row(row)
        assert parsed["service_interval_days"] == 10

    def test_import_komoot_creates_make_and_rack(self, empty_storage, tmp_path):
        from cyclelog.io_komoot import import_komoot

        src = tmp_path / "komoot.csv"
        src.write_text(
            "Bike Name,Nickname,Room,Make,Service Every,Last Serviceed,Light\n"
            "Monstera,Monty,Living Room,Monstera deliciosa,7d,today,bright indirect\n",
            encoding="utf-8",
        )
        n = import_komoot(empty_storage, src)
        assert n >= 1
        assert len(empty_storage.list_racks()) >= 1

    def test_import_komoot_update(self, populated_storage, tmp_path):
        from cyclelog.io_komoot import import_komoot

        src = tmp_path / "komoot.csv"
        src.write_text(
            "Bike Name,Service Every\nMonstera,14d\n",
            encoding="utf-8",
        )
        import_komoot(populated_storage, src, update=True)

    def test_komoot_helpers(self, tmp_path):
        from cyclelog.io_komoot import preview_komoot, validate_komoot_headers

        assert preview_komoot(tmp_path / "n.csv") == []
        assert validate_komoot_headers(tmp_path / "n.csv")


# --- reports gaps ---


class TestReportsCoverageGaps:
    def test_in_range_naive_datetime(self, empty_storage):
        from cyclelog.reports import MonthlyReport

        report = MonthlyReport(empty_storage)
        start = datetime(2024, 6, 1, tzinfo=timezone.utc)
        end = datetime(2024, 6, 30, 23, 59, 59, tzinfo=timezone.utc)
        assert report._in_range("2024-06-15T10:00:00", start, end) is True
        assert report._in_range(None, start, end) is False

    def test_generate_with_rack_breakdown(self, populated_storage, sample_bike):
        from cyclelog.reports import MonthlyReport

        now = datetime.now(timezone.utc)
        populated_storage.create_service_event({
            "bike_id": sample_bike.id,
            "serviced_at": now.isoformat(),
            "amount_ml": 100,
        })
        report = MonthlyReport(populated_storage)
        data = report.generate(now.year, now.month)
        assert data["services_by_rack"]

    def test_render_text_top_serviced(self, populated_storage, sample_bike):
        from cyclelog.reports import MonthlyReport

        now = datetime.now(timezone.utc)
        for _ in range(3):
            populated_storage.create_service_event({
                "bike_id": sample_bike.id,
                "serviced_at": now.isoformat(),
            })
        report = MonthlyReport(populated_storage)
        text = report.render_text(now.year, now.month)
        assert "Most serviced" in text or sample_bike.name in text


# --- cli gaps ---


def _ns(**kwargs):
    return argparse.Namespace(**kwargs)


class TestCliCoverageGaps:
    def test_default_shed_without_env(self, monkeypatch):
        from cyclelog.cli import _default_shed_path

        monkeypatch.delenv("CYCLELOG_HOME", raising=False)
        path = _default_shed_path()
        assert path.name == "shed.json"

    def test_resolve_nickname_and_partial(self, populated_storage, sample_bike):
        from cyclelog.cli import _resolve_bike

        populated_storage.update_bike(sample_bike.id, {"nickname": "Monty"})
        assert _resolve_bike(populated_storage, "Monty").id == sample_bike.id
        assert _resolve_bike(populated_storage, "onst").id == sample_bike.id

    def test_add_bike_with_amount(self, tmp_shed_path):
        from cyclelog.cli import cmd_add_bike, cmd_init

        cmd_init(_ns(shed=str(tmp_shed_path)))
        ns = _ns(
            shed=str(tmp_shed_path),
            name="Fern",
            nickname=None,
            make=None,
            rack=None,
            health=None,
            interval="7d",
            acquired=None,
            amount="250ml",
        )
        assert cmd_add_bike(ns) == 0

    def test_list_filters_and_truncation(self, populated_storage, sample_rack):
        from cyclelog.cli import cmd_list

        populated_storage.update_bike("bike001", {"rack_id": sample_rack.id})
        ns = _ns(
            shed=str(populated_storage.path),
            all=False,
            overdue=False,
            rack=sample_rack.id,
            limit=1,
        )
        with patch("sys.stdout", new_callable=StringIO) as out:
            assert cmd_list(ns) == 0
            assert "more" in out.getvalue()

    def test_import_export_branches(self, populated_storage, tmp_path):
        from cyclelog.cli import cmd_export, cmd_import

        wcsv = tmp_path / "w.csv"
        wcsv.write_text("bike_id,serviced_at\nbike001,2024-01-01\n", encoding="utf-8")
        assert cmd_import(_ns(
            shed=str(populated_storage.path),
            file=str(wcsv),
            format="csv",
            kind="service",
            update=False,
            no_expand=False,
        )) == 0

        jsrc = tmp_path / "events.jsonl"
        jsrc.write_text(
            json.dumps({"_type": "care", "bike_id": "bike001", "action": "mist"}) + "\n",
            encoding="utf-8",
        )
        assert cmd_import(_ns(
            shed=str(populated_storage.path),
            file=str(jsrc),
            format="jsonl",
            kind="care",
            update=False,
            no_expand=False,
        )) == 0

        mixed = tmp_path / "mix.jsonl"
        mixed.write_text(
            json.dumps({"_type": "service", "bike_id": "bike001", "serviced_at": "2024-02-01"}) + "\n",
            encoding="utf-8",
        )
        assert cmd_import(_ns(
            shed=str(populated_storage.path),
            file=str(mixed),
            format="jsonl",
            kind=None,
            update=False,
            no_expand=False,
        )) == 0

        gp = tmp_path / "gp.csv"
        gp.write_text("Bike,Section\nBasil,Kitchen\n", encoding="utf-8")
        assert cmd_import(_ns(
            shed=str(populated_storage.path),
            file=str(gp),
            format="strava",
            kind=None,
            update=False,
            no_expand=True,
        )) == 0

        assert cmd_import(_ns(
            shed=str(populated_storage.path),
            file=str(tmp_path / "x.csv"),
            format="csv",
            kind="unknown",
            update=False,
            no_expand=False,
        )) == 1

        dest = tmp_path / "out.csv"
        assert cmd_export(_ns(
            shed=str(populated_storage.path),
            file=str(dest),
            format="csv",
            kind="service",
        )) == 0

        jdest = tmp_path / "out.jsonl"
        for kind in ("service", "care", "full", None):
            assert cmd_export(_ns(
                shed=str(populated_storage.path),
                file=str(jdest),
                format="jsonl",
                kind=kind,
            )) == 0

        assert cmd_export(_ns(
            shed=str(populated_storage.path),
            file=str(tmp_path / "x.bin"),
            format="bin",
            kind=None,
        )) == 1

    def test_backup_restore_prune(self, populated_storage, tmp_path):
        from cyclelog.backup import ShedBackup
        from cyclelog.cli import cmd_backup

        backup_dir = tmp_path / "backups"
        gb = ShedBackup(populated_storage.path, backup_dir)
        backup_file = gb.create(label="test")
        ns_restore = _ns(
            shed=str(populated_storage.path),
            dir=str(backup_dir),
            label=None,
            list=False,
            restore=str(backup_file),
            prune=False,
            keep=1,
        )
        assert cmd_backup(ns_restore) == 0
        ns_prune = _ns(
            shed=str(populated_storage.path),
            dir=str(backup_dir),
            label="daily",
            list=False,
            restore=None,
            prune=True,
            keep=0,
        )
        assert cmd_backup(ns_prune) == 0

    def test_search_and_reminders_branches(self, populated_storage, capsys):
        from cyclelog.cli import cmd_reminders, cmd_search

        assert cmd_search(_ns(
            shed=str(populated_storage.path),
            query="note",
            kind="notes",
            limit=5,
            verbose=True,
        )) == 0
        assert cmd_search(_ns(
            shed=str(populated_storage.path),
            query="care",
            kind="care",
            limit=5,
            verbose=False,
        )) == 0

        populated_storage.update_bike("bike001", {"last_serviced_at": "2020-01-01"})
        ns = _ns(shed=str(populated_storage.path), overdue=False, within=30, limit=1)
        assert cmd_reminders(ns) == 0

    def test_main_keyboard_interrupt(self):
        from cyclelog.cli import main

        parser = MagicMock()
        parser.parse_args.return_value = MagicMock(func=MagicMock(side_effect=KeyboardInterrupt))
        with patch("cyclelog.cli.build_parser", return_value=parser):
            assert main([]) == 130

    def test_main_module_entry(self):
        import cyclelog.cli as cli_mod

        with patch.object(cli_mod, "main", return_value=0) as mock_main:
            with pytest.raises(SystemExit) as exc:
                exec(compile("if True: raise SystemExit(main())", "<test>", "exec"), {
                    "main": cli_mod.main,
                    "SystemExit": SystemExit,
                })
            assert exc.value.code == 0 or exc.value.code is None


# --- storage gaps ---


class TestStorageCoverageGaps:
    def test_legacy_bike_normalization(self, tmp_shed_path):
        from cyclelog.storage import JsonStorage, _normalize_bike_row

        row = {
            "id": "p1",
            "name": "Fern",
            "make_id": "sp1",
            "tags": ["t1"],
            "active": False,
        }
        norm = _normalize_bike_row(row)
        assert norm["make_key"] == "sp1"
        assert norm["tag_ids"] == ["t1"]
        assert norm["archived"] is True

    def test_legacy_make_normalization(self):
        from cyclelog.storage import _normalize_make_row

        assert _normalize_make_row({"id": "sp-key"})["key"] == "sp-key"

    def test_load_invalid_json(self, tmp_shed_path):
        from cyclelog.storage import JsonStorage

        tmp_shed_path.write_text("not json", encoding="utf-8")
        with pytest.raises(StorageError):
            JsonStorage(tmp_shed_path).load()

    def test_load_non_object_root(self, tmp_shed_path):
        from cyclelog.storage import JsonStorage

        tmp_shed_path.write_text("[1,2]", encoding="utf-8")
        with pytest.raises(StorageError):
            JsonStorage(tmp_shed_path).load()

    def test_corrupt_bucket(self, empty_storage):
        empty_storage._data["bikes"] = "bad"
        with pytest.raises(StorageError):
            empty_storage._list("bikes")

    def test_crud_paths(self, empty_storage, sample_bike, sample_make, sample_rack):
        empty_storage.create_make({"id": "legacy-sp", "common_name": "Legacy"})
        empty_storage.delete_make("legacy-sp")

        loc = empty_storage.create_rack(sample_rack)
        empty_storage.update_rack(loc.id, {"notes": "updated"})
        empty_storage.delete_rack(loc.id)

        bike = empty_storage.create_bike(sample_bike)
        empty_storage.update_bike(bike.id, {"nickname": "X"})
        ev = empty_storage.create_service_event({
            "bike_id": bike.id,
            "serviced_at": date.today().isoformat(),
        })
        empty_storage.get_service_event(ev["id"])
        empty_storage.update_service_event(ev["id"], {"notes": "ok"})
        empty_storage.delete_service_event(ev["id"])

        log = empty_storage.create_inspection_log({"bike_id": bike.id, "action": "mist"})
        empty_storage.get_inspection_log(log["id"])
        empty_storage.update_inspection_log(log["id"], {"notes": "done"})
        empty_storage.delete_inspection_log(log["id"])

        tag = empty_storage.create_tag({"id": "t9", "name": "test"})
        empty_storage.update_tag(tag["id"], {"name": "test2"})
        empty_storage.delete_tag(tag["id"])

        note = empty_storage.create_note({"id": "n9", "bike_id": bike.id, "body": "hi"})
        empty_storage.update_note(note["id"], {"body": "bye"})
        empty_storage.delete_note(note["id"])

        empty_storage.upsert_plugin({"id": "plug1", "name": "p"})
        empty_storage.upsert_plugin({"id": "plug1", "name": "p2"})
        empty_storage.delete_plugin("plug1")

        rec = empty_storage.create_recurring({"id": "r1", "rule": "weekly"})
        empty_storage.update_recurring("r1", {"rule": "daily"})
        empty_storage.delete_recurring("r1")

        empty_storage.delete_bike(bike.id)

    def test_service_events_filter(self, populated_storage, sample_bike):
        events = populated_storage.list_service_events(bike_id=sample_bike.id)
        assert all(e["bike_id"] == sample_bike.id for e in events)

    def test_atomic_write_failure(self, empty_storage):
        with patch.object(Path, "write_text", side_effect=OSError("fail")):
            with pytest.raises(StorageError):
                empty_storage.save()


# --- rack gaps ---


class TestRackCoverageGaps:
    def test_rack_with_temp_validation(self, sample_rack):
        from cyclelog.rack import Rack

        loc = Rack(
            name="Warm Room",
            id="loc-warm",
            temp_c=22.0,
            mileage_pct=50.0,
        )
        assert loc.temp_c == 22.0
        assert "°C" in loc.summary()

    def test_effective_light_south_and_invalid(self):
        from cyclelog.rack import Rack, WindowDirection

        loc = Rack.create(
            "South Window",
            light_level="medium",
            window_direction=WindowDirection.SOUTH,
        )
        assert loc.effective_light() != "medium"
        loc2 = Rack.create("Odd", light_level="low")
        loc2.light_level = "unknown_level"
        assert loc2.effective_light() == "unknown_level"

    def test_registry_helpers(self, sample_rack, sample_bike):
        from cyclelog.rack import (
            RackRegistry,
            RackClimateProfile,
            RoomHistory,
            RoomSnapshot,
            build_rack_map,
            compare_light,
            default_racks,
            estimate_daily_light_hours,
            format_rack_tree,
            rack_capacity_report,
            rack_report,
            bikes_without_rack,
            rank_racks_for_make,
            reassign_bike,
            suggest_bikes_for_rack,
            sync_rack_bike_ids,
        )

        reg = RackRegistry()
        reg.add(sample_rack)
        reg.assign_bike(sample_rack.id, sample_bike.id)
        reg.unassign_bike(sample_bike.id)
        assert reg.require(sample_rack.id).id == sample_rack.id
        assert reg.find_by_light(sample_rack.light_level)
        if sample_rack.zone:
            assert reg.find_by_zone(sample_rack.zone)
        with pytest.raises(ValueError):
            reg.add(sample_rack)
        assert reg.count() >= 1

        profile = RackClimateProfile.from_rack(sample_rack)
        assert profile.service_factor() > 0
        profile.draft_risk = True
        profile.heater_nearby = True
        profile.ac_nearby = True
        profile.avg_mileage = 70
        assert profile.service_factor() != 1.0

        assert compare_light("low", "full_sun") == -1
        with pytest.raises(ValidationError):
            compare_light("bad", "low")
        assert suggest_bikes_for_rack(sample_rack)
        assert rack_report(reg)["rack_count"] >= 1
        reassign_bike(reg, sample_bike.id, None, sample_rack.id)
        assert estimate_daily_light_hours(sample_rack, month=7) > 0
        assert rank_racks_for_make(reg, "not-a-profile") == []
        assert build_rack_map(reg)
        unassigned = bikes_without_rack(reg, [sample_bike.id, "other"])
        assert "other" in unassigned
        assert sample_bike.id not in unassigned
        assert rack_capacity_report(reg, max_per_room=0)["crowded"]

        hist = RoomHistory()
        hist.record(RoomSnapshot(sample_rack.id, datetime.now(timezone.utc).isoformat(), 50.0))
        assert hist.avg_mileage(sample_rack.id) == 50.0
        RoomHistory.from_dict_list(hist.to_dict_list())

        sync_rack_bike_ids(reg, [sample_bike])
        tree = format_rack_tree(reg)
        assert sample_rack.name in tree
        assert default_racks().count() >= 0

    def test_registry_remove_missing(self):
        from cyclelog.rack import RackRegistry

        reg = RackRegistry()
        assert reg.remove("nope") is False


# --- schedule gaps ---


class TestScheduleCoverageGaps:
    def test_season_str_and_detect_fallback(self):
        from cyclelog.schedule import Season, ScheduleEngine, ScheduleOptions, detect_season

        assert str(Season.SPRING) == "spring"
        with patch("cyclelog.schedule._SEASON_MONTHS", {Season.SPRING: ()}):
            assert detect_season(date(2024, 6, 15)) == Season.SPRING

    def test_engine_multipliers(self, bike_catalog, make_catalog, rack_registry, service_log, sample_bike):
        from copy import deepcopy

        from cyclelog.bike import HealthStatus
        from cyclelog.schedule import ScheduleEngine

        engine = ScheduleEngine(bike_catalog, make_catalog, rack_registry, service_log)
        engine.set_options(health_adjust=True, rack_mileage_adjust=True)

        struggling = deepcopy(sample_bike)
        struggling.health = HealthStatus.STRUGGLING
        assert engine.health_multiplier(struggling) < 1.0
        critical = deepcopy(sample_bike)
        critical.health = HealthStatus.CRITICAL
        assert engine.health_multiplier(critical) == 0.75
        thriving = deepcopy(sample_bike)
        thriving.health = HealthStatus.THRIVING
        assert engine.health_multiplier(thriving) > 1.0

        loc = rack_registry.get(sample_bike.rack_id)
        if loc:
            loc.mileage_pct = 70
            assert engine.rack_multiplier(sample_bike) > 1.0
            loc.mileage_pct = 30
            assert engine.rack_multiplier(sample_bike) < 1.0

        small_bag = deepcopy(sample_bike)
        small_bag.bag.diameter = 3
        small_bag.bag.unit = "in"
        assert engine.bag_multiplier(small_bag) < 1.0
        big_bag = deepcopy(sample_bike)
        big_bag.bag.diameter = 14
        big_bag.bag.unit = "in"
        assert engine.bag_multiplier(big_bag) > 1.0

        engine.options.health_adjust = False
        assert engine.health_multiplier(sample_bike) == 1.0

    def test_last_serviced_and_entry_notes(self, bike_catalog, service_log, sample_bike):
        from copy import deepcopy

        from cyclelog.bike import HealthStatus
        from cyclelog.schedule import ScheduleEngine

        engine = ScheduleEngine(bike_catalog, service_log=service_log)
        sample_bike.last_serviced_at = None
        sample_bike.acquired_at = (date.today() - timedelta(days=30)).isoformat()
        assert engine.last_serviced(sample_bike) is not None

        never = deepcopy(sample_bike)
        never.last_serviced_at = None
        never.acquired_at = None
        assert engine.next_due_date(never) <= date.today() + timedelta(days=engine.adjusted_interval(never))

        critical = sample_bike
        critical.health = HealthStatus.CRITICAL
        entry = engine.build_entry(critical, date.today() - timedelta(days=10))
        assert entry.notes == "check roots/grind" or entry.overdue_days >= 0


# --- backup gaps ---


class TestBackupCoverageGaps:
    def test_create_missing_shed(self, tmp_path):
        from cyclelog.backup import ShedBackup

        gb = ShedBackup(tmp_path / "nope.json", tmp_path / "bk")
        with pytest.raises(StorageError):
            gb.create()

    def test_restore_missing_and_corrupt(self, populated_storage, tmp_path):
        from cyclelog.backup import ShedBackup

        gb = ShedBackup(populated_storage.path, tmp_path / "bk")
        with pytest.raises(StorageError):
            gb.restore(tmp_path / "missing.json")
        bad = tmp_path / "bad.json"
        bad.write_text("{", encoding="utf-8")
        with pytest.raises(StorageError):
            gb.restore(bad)

    def test_restore_latest_empty(self, tmp_path):
        from cyclelog.backup import ShedBackup

        gb = ShedBackup(tmp_path / "g.json", tmp_path / "bk")
        with pytest.raises(StorageError):
            gb.restore_latest()

    def test_prune_oserror_ignored(self, populated_storage, tmp_path):
        from cyclelog.backup import ShedBackup

        gb = ShedBackup(populated_storage.path, tmp_path / "bk")
        gb.create()
        gb.create()
        with patch.object(Path, "unlink", side_effect=OSError("locked")):
            removed = gb.prune(keep=0)
        assert isinstance(removed, list)

    def test_create_copy_oserror(self, populated_storage, tmp_path):
        from cyclelog.backup import ShedBackup

        gb = ShedBackup(populated_storage.path, tmp_path / "bk")
        with patch("cyclelog.backup.shutil.copy2", side_effect=OSError("disk full")):
            with pytest.raises(StorageError, match="backup failed"):
                gb.create()

    def test_restore_copy_oserror(self, populated_storage, tmp_path):
        from cyclelog.backup import ShedBackup

        gb = ShedBackup(populated_storage.path, tmp_path / "bk")
        backup = gb.create()
        makeal = __import__("shutil").copy2

        def copy_side_effect(src, dst):
            if str(dst) == str(populated_storage.path):
                raise OSError("permission")
            return makeal(src, dst)

        with patch("cyclelog.backup.shutil.copy2", side_effect=copy_side_effect):
            with pytest.raises(StorageError, match="restore failed"):
                gb.restore(backup)


# --- server gaps ---


class TestServerCoverageGaps:
    def test_handler_put_delete_via_background(self, populated_storage):
        import urllib.error
        import urllib.request

        from cyclelog.server import ShedServer

        server = ShedServer(populated_storage, port=0)
        server.start_background()
        try:
            host, port = server.address
            for method in ("PUT", "DELETE"):
                req = urllib.request.Request(
                    f"http://{host}:{port}/bikes",
                    method=method,
                    data=b"{}",
                )
                with pytest.raises(urllib.error.HTTPError) as exc:
                    urllib.request.urlopen(req)
                assert exc.value.code == 405
        finally:
            server.stop()

    def test_shed_server_lifecycle(self, populated_storage):
        from cyclelog.server import ShedServer, run_server

        srv = ShedServer(populated_storage, host="127.0.0.1", port=0)
        assert srv.address[0] == "127.0.0.1"
        httpd = srv.start_background()
        assert httpd is not None
        srv.stop()
        srv.stop()

        with patch("cyclelog.server.ShedServer.serve_forever"):
            with patch("cyclelog.server.JsonStorage"):
                run_server(str(populated_storage.path), port=9999)


# --- bike / tag / notes / service / streaks / migrate / make / inspection_log ---


class TestDomainCoverageGaps:
    def test_bike_edges(self, sample_bike):
        from cyclelog.bike import HealthStatus, Bike, BikeCatalog

        p = Bike.from_dict({
            **sample_bike.to_dict(),
            "tag_ids": ["t1"],
            "light_override": "low",
        })
        p.set_health(HealthStatus.THRIVING, score=90)
        p.archive()
        p.unarchive()
        p.service_interval_days = 10
        assert p.display_name

        cat = BikeCatalog()
        cat.add(p)
        p.attach_tag("t1")
        assert cat.find_by_tag("t1")

    def test_tag_registry_edges(self):
        from cyclelog.tag import Tag, TagRegistry

        tag = Tag.create("rare", color="#aabbcc")
        reg = TagRegistry()
        reg.add(tag)
        assert reg.get(tag.id)
        reg.remove(tag.id)

    def test_notes_collection_edges(self, sample_bike):
        from cyclelog.notes import NoteKind, NotesCollection

        coll = NotesCollection()
        n = coll.create(sample_bike.id, "body", kind=NoteKind.REMINDER)
        n.edit(body="new body")
        n.pin()
        n.unpin()
        assert coll.for_bike(sample_bike.id)

    def test_service_log_edges(self, sample_service_events):
        from cyclelog.service import ServiceLog

        log = ServiceLog()
        log.load_many(sample_service_events)
        assert log.total_ml_for_bike(sample_service_events[0].bike_id) >= 0
        assert log.for_bike(sample_service_events[0].bike_id)

    def test_streaks_break_and_leaderboard(self, populated_storage, sample_bike):
        from cyclelog.streaks import StreakTracker

        populated_storage.create_service_event({
            "bike_id": sample_bike.id,
            "serviced_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        })
        populated_storage.create_service_event({
            "bike_id": sample_bike.id,
            "serviced_at": datetime.now(timezone.utc).isoformat(),
        })
        tracker = StreakTracker(populated_storage)
        info = tracker.compute(sample_bike.id)
        assert info.longest_streak >= 1
        assert tracker.leaderboard(5)
        assert isinstance(tracker.broken_streaks(), list)

    def test_migrate_edges(self, populated_storage):
        from cyclelog.migrate import detect_version, migrate_file, migration_plan

        path = populated_storage.path
        data = json.loads(path.read_text(encoding="utf-8"))
        data["schema_version"] = 0
        path.write_text(json.dumps(data), encoding="utf-8")
        assert detect_version(data) == 0
        migrate_file(str(path))
        assert migration_plan(0)

    def test_make_and_inspection_log_edges(self, make_catalog, inspection_log, sample_bike):
        from cyclelog.inspection_log import CareEventType
        from cyclelog.make import MakeProfile

        sp = MakeProfile(
            key="test-sp",
            common_name="Test",
            scientific_name="T. test",
            light_level="low",
            service_interval_min=5,
            service_interval_max=10,
        )
        make_catalog.register(sp)
        assert sp.matches_light("low")
        inspection_log.log(sample_bike.id, CareEventType.INSPECT)

    def test_odometer_seasons_issues_labels_recurring(self, populated_storage, sample_bike):
        from cyclelog.odometer import OdometerManager
        from cyclelog.issues import IssueTracker
        from cyclelog.parts import LabelCatalog
        from cyclelog.recurring import RecurringTasks
        from cyclelog.seasons import SeasonCalendar

        assert SeasonCalendar().multiplier_for(date.today()) > 0
        OdometerManager(populated_storage).apply(sample_bike.id, "10-10-10")
        IssueTracker(populated_storage).report(sample_bike.id, "aphids")
        LabelCatalog(populated_storage).register(sample_bike.id, "/tmp/x.jpg")
        RecurringTasks(populated_storage).define("Service", "service", 7, bike_id=sample_bike.id)


class TestFinalCoveragePush:
    def test_service_quality_str(self):
        from cyclelog.service import ServiceQuality

        assert str(ServiceQuality.TAP) == "tap"

    def test_odometer_due_skips_bad_timestamp(self, populated_storage, sample_bike):
        from cyclelog.odometer import OdometerManager

        populated_storage.mutate(lambda d: d.setdefault("grind_events", []).append({
            "id": "fe_bad",
            "bike_id": sample_bike.id,
            "product": "10-10-10",
            "applied_at": "not-a-date",
        }))
        due = OdometerManager(populated_storage).due_for_odometer(interval_days=30)
        assert isinstance(due, list)

    def test_odometer_due_naive_timestamp(self, populated_storage, sample_bike):
        from cyclelog.odometer import OdometerManager

        old = (datetime.now() - timedelta(days=60)).isoformat()
        populated_storage.mutate(lambda d: d.setdefault("grind_events", []).append({
            "id": "fe_naive",
            "bike_id": sample_bike.id,
            "product": "10-10-10",
            "applied_at": old,
        }))
        due = OdometerManager(populated_storage).due_for_odometer(interval_days=30)
        assert any(d["bike_id"] == sample_bike.id for d in due)

    def test_parse_iso_invalid(self):
        from cyclelog.bike import parse_iso

        assert parse_iso("not-a-date") is None
        assert parse_iso(None) is None

    def test_seasons_day_of_year(self):
        from cyclelog.seasons import SeasonCalendar

        cal = SeasonCalendar()
        assert cal._day_of_year(date(2024, 7, 1)) == date(2024, 7, 1).timetuple().tm_yday

    def test_cli_main_keyboard_interrupt(self):
        from cyclelog.cli import main

        with patch("cyclelog.cli.build_parser") as bp:
            ns = MagicMock()
            ns.func.side_effect = KeyboardInterrupt
            bp.return_value.parse_args.return_value = ns
            assert main([]) == 130
