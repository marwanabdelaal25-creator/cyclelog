"""Aggregate shed statistics.

Author: Marwan Helmy
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .bike import parse_iso
from .reminders import ReminderEngine
from .storage import JsonStorage


class ShedStats:
    def __init__(self, storage: JsonStorage):
        self.storage = storage
        self.reminders = ReminderEngine(storage)

    def snapshot(self) -> dict[str, Any]:
        bikes = self.storage.list_bikes(active_only=True)
        all_bikes = self.storage.list_bikes(active_only=False)
        service = self.storage.list_service_events()
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        serviced_last_7 = sum(
            1 for e in service
            if (dt := parse_iso(e.get("serviced_at"))) and dt >= week_ago
        )
        serviced_last_30 = sum(
            1 for e in service
            if (dt := parse_iso(e.get("serviced_at"))) and dt >= month_ago
        )

        overdue = self.reminders.overdue_only()
        make_count = len(self.storage.list_make())
        racks_count = len(self.storage.list_racks())
        tags_count = len(self.storage.list_tags())

        inactive = len(all_bikes) - len(bikes)
        avg_interval = 0.0
        if bikes:
            avg_interval = sum(p.service_interval_days for p in bikes) / len(bikes)

        return {
            "generated_at": now.isoformat(),
            "bikes_active": len(bikes),
            "bikes_inactive": inactive,
            "bikes_total": len(all_bikes),
            "make_count": make_count,
            "racks_count": racks_count,
            "tags_count": tags_count,
            "service_events_total": len(service),
            "serviced_last_7_days": serviced_last_7,
            "serviced_last_30_days": serviced_last_30,
            "overdue_count": len(overdue),
            "due_today_count": sum(
                1 for r in self.reminders.upcoming(within_days=0, include_overdue=False)
                if r.urgency == "due_today"
            ),
            "avg_service_interval_days": round(avg_interval, 1),
            "inspection_logs_total": len(self.storage.list_inspection_logs()),
            "notes_total": len(self.storage.list_notes()),
            "collections_total": len(self.storage.list_collections()),
        }

    def render_text(self) -> str:
        s = self.snapshot()
        return (
            f"Shed stats @ {s['generated_at'][:10]}\n"
            f"  Active bikes: {s['bikes_active']} / {s['bikes_total']}\n"
            f"  Overdue: {s['overdue_count']}\n"
            f"  Serviceed (7d / 30d): {s['serviced_last_7_days']} / {s['serviced_last_30_days']}\n"
            f"  Make: {s['make_count']}  Racks: {s['racks_count']}"
        )
