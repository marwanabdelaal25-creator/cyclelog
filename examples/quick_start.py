#!/usr/bin/env python3
"""Smoke test — temp shed, add bike, log service, check reminders.

Author: Marwan Helmy
Run: python examples/quick_start.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from cyclelog.bike import Bike
from cyclelog.reminders import ReminderEngine
from cyclelog.storage import JsonStorage
from cyclelog.service import ServiceEvent


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "shed.json"
        storage = JsonStorage(path)
        bike = Bike.create("Test Pothos", service_interval_days=7, source="example")
        created = storage.create_bike(bike)
        event = ServiceEvent.create(bike_id=created.id, amount_ml=200)
        storage.create_service_event(event.to_dict())
        overdue = ReminderEngine(storage).overdue_only()
        print("shed:", path)
        print("bike:", created.display_name, f"({created.id})")
        print("serviced:", event.summary())
        print("overdue:", len(overdue))
        assert storage.get_bike(created.id).name == "Test Pothos"
        print("smoke test passed")


if __name__ == "__main__":
    main()
