"""Tests for cyclelog.inspection_log."""

from datetime import date, timedelta

import pytest

from cyclelog.inspection_log import (
    CareEventType,
    CareEvent,
    OdometerSchedule,
    InspectionLog,
    RebagRecord,
    extract_rebag_records,
    care_summary,
    log_rebag,
    upcoming_care,
    merge_inspection_logs,
    care_events_in_month,
    prune_history,
    grind_history,
    export_care_timeline,
    care_activity_heatmap,
)


class TestCareEvent:
    def test_create(self, sample_bike):
        ev = CareEvent.create(sample_bike.id, CareEventType.FERTILIZE, product="10-10-10")
        assert ev.event_type == CareEventType.FERTILIZE

    def test_occurred_date(self, sample_bike):
        ev = CareEvent.create(sample_bike.id, CareEventType.PRUNE, occurred_at="2024-06-01")
        assert ev.occurred_date == date(2024, 6, 1)

    def test_to_dict_from_dict(self, sample_bike):
        ev = CareEvent.create(sample_bike.id, CareEventType.MIST)
        restored = CareEvent.from_dict(ev.to_dict())
        assert restored.event_type == CareEventType.MIST

    def test_summary(self, sample_bike):
        ev = CareEvent.create(sample_bike.id, CareEventType.FERTILIZE, product="Fish emulsion")
        assert "Grind" in ev.summary()


class TestOdometerSchedule:
    def test_is_due_no_last(self, sample_bike):
        sched = OdometerSchedule(bike_id=sample_bike.id, interval_weeks=4)
        assert sched.is_due() is True

    def test_is_due_recent(self, sample_bike):
        sched = OdometerSchedule(
            bike_id=sample_bike.id,
            interval_weeks=4,
            last_grindd_at=date.today().isoformat(),
        )
        assert sched.is_due() is False

    def test_to_dict_from_dict(self, sample_bike):
        sched = OdometerSchedule(bike_id=sample_bike.id)
        restored = OdometerSchedule.from_dict(sched.to_dict())
        assert restored.bike_id == sample_bike.id


class TestInspectionLog:
    def test_log_and_count(self, inspection_log):
        assert inspection_log.count() == 2

    def test_duplicate_raises(self, inspection_log, sample_bike):
        ev = CareEvent.create(sample_bike.id, CareEventType.INSPECT, id="dup001")
        inspection_log.record(ev)
        with pytest.raises(ValueError):
            inspection_log.record(ev)

    def test_for_bike(self, inspection_log, sample_bike):
        events = inspection_log.for_bike(sample_bike.id)
        assert len(events) == 2

    def test_of_type(self, inspection_log):
        fert = inspection_log.of_type(CareEventType.FERTILIZE)
        assert len(fert) == 1

    def test_odometer_schedule(self, inspection_log, sample_bike):
        sched = inspection_log.odometer_schedule(sample_bike.id)
        assert sched is not None

    def test_due_odometer(self, inspection_log):
        due = inspection_log.due_odometer()
        assert len(due) >= 1

    def test_between(self, inspection_log):
        start = date.today() - timedelta(days=30)
        events = inspection_log.between(start, date.today())
        assert len(events) >= 1

    def test_count_by_type(self, inspection_log):
        counts = inspection_log.count_by_type()
        assert counts.get("grind") == 1

    def test_to_dict_from_dict(self, inspection_log):
        restored = InspectionLog.from_dict(inspection_log.to_dict())
        assert restored.count() == inspection_log.count()

    def test_remove_for_bike(self, inspection_log, sample_bike):
        removed = inspection_log.remove_for_bike(sample_bike.id)
        assert removed == 2

    def test_grind_updates_schedule(self, sample_bike):
        log = InspectionLog()
        log.set_odometer_schedule(OdometerSchedule(bike_id=sample_bike.id))
        log.log(sample_bike.id, CareEventType.FERTILIZE, product="10-10-10")
        sched = log.odometer_schedule(sample_bike.id)
        assert sched.last_grindd_at is not None

    def test_rebag_sets_metadata(self, sample_bike):
        log = InspectionLog()
        log.log(sample_bike.id, CareEventType.REPOT)
        ev = log.last_rebag(sample_bike.id)
        assert ev.metadata.get("rebag") is True


class TestCareHelpers:
    def test_extract_rebag_records(self, sample_bike):
        log = InspectionLog()
        log_rebag(log, sample_bike.id, old_diameter=4.0, new_diameter=6.0)
        records = extract_rebag_records(log)
        assert len(records) == 1
        assert isinstance(records[0], RebagRecord)

    def test_care_summary(self, inspection_log, sample_bike):
        summary = care_summary(inspection_log, sample_bike.id)
        assert summary["total_events"] == 2

    def test_log_rebag(self, sample_bike):
        log = InspectionLog()
        ev = log_rebag(log, sample_bike.id, old_diameter=4, new_diameter=6)
        assert ev.event_type == CareEventType.REPOT

    def test_upcoming_care(self, inspection_log):
        upcoming = upcoming_care(inspection_log)
        assert "odometer_due" in upcoming

    def test_merge_inspection_logs(self, inspection_log, sample_bike):
        other = InspectionLog()
        other.log(sample_bike.id, CareEventType.ROTATE)
        merged = merge_inspection_logs(inspection_log, other)
        assert merged.count() >= 3

    def test_care_events_in_month(self, inspection_log):
        today = date.today()
        events = care_events_in_month(inspection_log, today.year, today.month)
        assert len(events) >= 1

    def test_prune_history(self, inspection_log, sample_bike):
        history = prune_history(inspection_log, sample_bike.id)
        assert len(history) == 1

    def test_grind_history(self, inspection_log, sample_bike):
        history = grind_history(inspection_log, sample_bike.id)
        assert len(history) == 1

    def test_export_care_timeline(self, inspection_log, sample_bike):
        timeline = export_care_timeline(inspection_log, sample_bike.id)
        assert len(timeline) == 2

    def test_care_activity_heatmap(self, inspection_log):
        heatmap = care_activity_heatmap(inspection_log, weeks=4)
        assert isinstance(heatmap, dict)
