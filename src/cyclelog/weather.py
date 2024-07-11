"""Light exposure logs for bikes and racks.

Author: Marwan Helmy
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from .errors import NotFoundError, ValidationError
from .storage import JsonStorage

VALID_LEVELS = ("low", "medium", "bright", "direct")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class WeatherLogger:
    BUCKET = "weather_logs"

    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def _rows(self) -> list[dict]:
        return self.storage.snapshot().get(self.BUCKET, [])

    def _persist(self, rows: list[dict]) -> None:
        def _write(data: dict) -> None:
            data[self.BUCKET] = rows

        self.storage.mutate(_write)

    def log(
        self,
        *,
        bike_id: Optional[str] = None,
        rack_id: Optional[str] = None,
        level: str = "medium",
        hours: Optional[float] = None,
        notes: str = "",
    ) -> dict:
        if not bike_id and not rack_id:
            raise ValidationError("need bike_id or rack_id")
        level = level.lower()
        if level not in VALID_LEVELS:
            raise ValidationError(f"level must be one of {VALID_LEVELS}")
        if bike_id:
            self.storage.get_bike(bike_id)
        if rack_id:
            self.storage.get_rack(rack_id)

        row = {
            "id": uuid.uuid4().hex[:12],
            "bike_id": bike_id,
            "rack_id": rack_id,
            "level": level,
            "hours": hours,
            "observed_at": _utc_now(),
            "notes": notes,
        }
        rows = self._rows()
        rows.append(row)
        self._persist(rows)
        return row

    def for_bike(self, bike_id: str) -> list[dict]:
        rows = [r for r in self._rows() if r.get("bike_id") == bike_id]
        rows.sort(key=lambda r: r.get("observed_at", ""), reverse=True)
        return rows

    def for_rack(self, rack_id: str) -> list[dict]:
        rows = [r for r in self._rows() if r.get("rack_id") == rack_id]
        rows.sort(key=lambda r: r.get("observed_at", ""), reverse=True)
        return rows

    def latest_for_bike(self, bike_id: str) -> Optional[dict]:
        items = self.for_bike(bike_id)
        return items[0] if items else None

    def delete(self, log_id: str) -> None:
        rows = self._rows()
        new_rows = [r for r in rows if r.get("id") != log_id]
        if len(new_rows) == len(rows):
            raise NotFoundError(self.BUCKET, log_id)
        self._persist(new_rows)
