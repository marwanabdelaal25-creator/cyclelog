"""Tests for cyclelog.mileage."""

import pytest

from cyclelog.errors import NotFoundError, ValidationError
from cyclelog.mileage import MileageLogger


class TestMileageLogger:
    def test_log_reading(self, populated_storage, sample_rack):
        logger = MileageLogger(populated_storage)
        row = logger.log(sample_rack.id, 55.0, notes="Morning reading")
        assert row["percent"] == 55.0
        assert row["rack_id"] == sample_rack.id

    def test_percent_out_of_range_low(self, populated_storage, sample_rack):
        logger = MileageLogger(populated_storage)
        with pytest.raises(ValidationError):
            logger.log(sample_rack.id, -1)

    def test_percent_out_of_range_high(self, populated_storage, sample_rack):
        logger = MileageLogger(populated_storage)
        with pytest.raises(ValidationError):
            logger.log(sample_rack.id, 101)

    def test_unknown_rack(self, empty_storage):
        logger = MileageLogger(empty_storage)
        with pytest.raises(NotFoundError):
            logger.log("missing", 50.0)

    def test_list_for_rack(self, populated_storage, sample_rack):
        logger = MileageLogger(populated_storage)
        logger.log(sample_rack.id, 45.0)
        logger.log(sample_rack.id, 50.0)
        rows = logger.list_for_rack(sample_rack.id)
        assert len(rows) == 2
        assert rows[0]["recorded_at"] >= rows[1]["recorded_at"]

    def test_list_with_limit(self, populated_storage, sample_rack):
        logger = MileageLogger(populated_storage)
        for pct in (40, 45, 50):
            logger.log(sample_rack.id, pct)
        rows = logger.list_for_rack(sample_rack.id, limit=2)
        assert len(rows) == 2

    def test_latest(self, populated_storage, sample_rack):
        logger = MileageLogger(populated_storage)
        assert logger.latest(sample_rack.id) is None
        logger.log(sample_rack.id, 48.0)
        latest = logger.latest(sample_rack.id)
        assert latest["percent"] == 48.0

    def test_average(self, populated_storage, sample_rack):
        logger = MileageLogger(populated_storage)
        logger.log(sample_rack.id, 40.0)
        logger.log(sample_rack.id, 60.0)
        assert logger.average(sample_rack.id) == 50.0

    def test_average_no_data(self, populated_storage, sample_rack):
        logger = MileageLogger(populated_storage)
        assert logger.average(sample_rack.id) is None

    def test_summary_by_rack(self, populated_storage, sample_rack):
        logger = MileageLogger(populated_storage)
        logger.log(sample_rack.id, 45.0)
        summary = logger.summary_by_rack()
        assert sample_rack.id in summary
        assert summary[sample_rack.id]["rack_name"] == sample_rack.name

    def test_delete(self, populated_storage, sample_rack):
        logger = MileageLogger(populated_storage)
        row = logger.log(sample_rack.id, 55.0)
        logger.delete(row["id"])
        assert logger.latest(sample_rack.id) is None

    def test_delete_missing_raises(self, populated_storage):
        logger = MileageLogger(populated_storage)
        with pytest.raises(NotFoundError):
            logger.delete("missing")

    def test_source_stored(self, populated_storage, sample_rack):
        logger = MileageLogger(populated_storage)
        row = logger.log(sample_rack.id, 50.0, source="sensor")
        assert row["source"] == "sensor"

    def test_persist_survives_reload(self, populated_storage, sample_rack, tmp_shed_path):
        logger = MileageLogger(populated_storage)
        logger.log(sample_rack.id, 42.0)
        reloaded = MileageLogger(populated_storage.__class__(tmp_shed_path))
        assert reloaded.latest(sample_rack.id) is not None

    def test_bucket_constant(self):
        assert MileageLogger.BUCKET == "mileage_readings"

    def test_rounded_percent(self, populated_storage, sample_rack):
        logger = MileageLogger(populated_storage)
        row = logger.log(sample_rack.id, 55.55)
        assert row["percent"] == 55.5

    def test_multiple_racks_isolated(self, populated_storage, sample_rack):
        loc2 = populated_storage.create_rack({"id": "loc2", "name": "Kitchen"})
        logger = MileageLogger(populated_storage)
        logger.log(sample_rack.id, 45.0)
        logger.log(loc2.id, 60.0)
        assert len(logger.list_for_rack(sample_rack.id)) == 1

    def test_summary_null_latest_for_empty(self, populated_storage, sample_rack):
        logger = MileageLogger(populated_storage)
        summary = logger.summary_by_rack()
        assert summary[sample_rack.id]["latest_percent"] is None
