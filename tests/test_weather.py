"""Tests for cyclelog.weather."""

import pytest

from cyclelog.errors import NotFoundError, ValidationError
from cyclelog.weather import WeatherLogger, VALID_LEVELS


class TestWeatherLogger:
    def test_log_with_bike(self, populated_storage, sample_bike):
        logger = WeatherLogger(populated_storage)
        row = logger.log(bike_id=sample_bike.id, level="bright", hours=6.0)
        assert row["bike_id"] == sample_bike.id

    def test_log_with_rack(self, populated_storage, sample_rack):
        logger = WeatherLogger(populated_storage)
        row = logger.log(rack_id=sample_rack.id, level="medium")
        assert row["rack_id"] == sample_rack.id

    def test_neither_id_raises(self, populated_storage):
        logger = WeatherLogger(populated_storage)
        with pytest.raises(ValidationError):
            logger.log(level="medium")

    def test_invalid_level_raises(self, populated_storage, sample_bike):
        logger = WeatherLogger(populated_storage)
        with pytest.raises(ValidationError):
            logger.log(bike_id=sample_bike.id, level="supernova")

    def test_level_normalized(self, populated_storage, sample_bike):
        logger = WeatherLogger(populated_storage)
        row = logger.log(bike_id=sample_bike.id, level="MEDIUM")
        assert row["level"] == "medium"

    def test_unknown_bike_raises(self, empty_storage):
        logger = WeatherLogger(empty_storage)
        with pytest.raises(NotFoundError):
            logger.log(bike_id="missing", level="low")

    def test_for_bike(self, populated_storage, sample_bike):
        logger = WeatherLogger(populated_storage)
        logger.log(bike_id=sample_bike.id, level="low")
        logger.log(bike_id=sample_bike.id, level="medium")
        rows = logger.for_bike(sample_bike.id)
        assert len(rows) == 2

    def test_for_rack(self, populated_storage, sample_rack):
        logger = WeatherLogger(populated_storage)
        logger.log(rack_id=sample_rack.id, level="bright")
        rows = logger.for_rack(sample_rack.id)
        assert len(rows) == 1

    def test_latest_for_bike(self, populated_storage, sample_bike):
        logger = WeatherLogger(populated_storage)
        assert logger.latest_for_bike(sample_bike.id) is None
        logger.log(bike_id=sample_bike.id, level="low")
        assert logger.latest_for_bike(sample_bike.id) is not None

    def test_delete(self, populated_storage, sample_bike):
        logger = WeatherLogger(populated_storage)
        row = logger.log(bike_id=sample_bike.id, level="low")
        logger.delete(row["id"])
        assert logger.latest_for_bike(sample_bike.id) is None

    def test_delete_missing_raises(self, populated_storage):
        logger = WeatherLogger(populated_storage)
        with pytest.raises(NotFoundError):
            logger.delete("missing")

    @pytest.mark.parametrize("level", list(VALID_LEVELS))
    def test_all_valid_levels(self, populated_storage, sample_bike, level):
        logger = WeatherLogger(populated_storage)
        row = logger.log(bike_id=sample_bike.id, level=level)
        assert row["level"] == level

    def test_hours_optional(self, populated_storage, sample_bike):
        logger = WeatherLogger(populated_storage)
        row = logger.log(bike_id=sample_bike.id, level="medium")
        assert row.get("hours") is None

    def test_notes_persisted(self, populated_storage, sample_bike):
        logger = WeatherLogger(populated_storage)
        row = logger.log(bike_id=sample_bike.id, level="low", notes="Cloudy day")
        assert row["notes"] == "Cloudy day"

    def test_both_ids(self, populated_storage, sample_bike, sample_rack):
        logger = WeatherLogger(populated_storage)
        row = logger.log(
            bike_id=sample_bike.id,
            rack_id=sample_rack.id,
            level="direct",
        )
        assert row["bike_id"] == sample_bike.id

    def test_rack_only_excluded_from_for_bike(self, populated_storage, sample_rack):
        logger = WeatherLogger(populated_storage)
        logger.log(rack_id=sample_rack.id, level="medium")
        assert logger.for_bike("any") == []

    def test_observed_at_present(self, populated_storage, sample_bike):
        logger = WeatherLogger(populated_storage)
        row = logger.log(bike_id=sample_bike.id, level="low")
        assert "observed_at" in row

    def test_valid_levels_constant(self):
        assert "medium" in VALID_LEVELS
        assert "direct" in VALID_LEVELS
