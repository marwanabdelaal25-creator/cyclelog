#!/usr/bin/env python3
"""Weekly service workflow — service overdue and due-today bikes.

Author: Marwan Helmy
Run: python examples/weekly_service.py
     CYCLELOG_HOME=~/.cyclelog python examples/weekly_service.py
"""

from __future__ import annotations

import os
from pathlib import Path

from cyclelog.reminders import ReminderEngine
from cyclelog.storage import JsonStorage
from cyclelog.service import ServiceEvent


def shed_path() -> Path:
    home = os.environ.get("CYCLELOG_HOME")
    base = Path(home) if home else Path.home() / ".cyclelog"
    return base / "shed.json"


def main() -> None:
    storage = JsonStorage(shed_path())
    engine = ReminderEngine(storage)
    due = [r for r in engine.upcoming(within_days=0, include_overdue=True) if r.urgency != "upcoming"]

    if not due:
        print("All caught up — nothing due today or overdue.")
        return

    print(f"Service {len(due)} bike(s):\n")
    for rem in due:
        bike = storage.get_bike(rem.bike_id)
        amount = bike.service_amount_ml
        flag = "OVERDUE" if rem.urgency == "overdue" else "TODAY"
        print(f"  [{flag}] {rem.bike_name} (due {rem.due_at.date()})")

        if amount is None:
            print("    skipped — no default amount; set service_amount_ml on bike")
            continue

        event = ServiceEvent.create(bike_id=bike.id, amount_ml=amount, notes="weekly script")
        storage.create_service_event(event.to_dict())
        print(f"    logged: {event.summary()}")

    print("\nDone. Run `cyclelog reminders --within 7` to preview the week ahead.")


if __name__ == "__main__":
    main()
