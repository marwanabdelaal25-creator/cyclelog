"""Upcoming service reminders sorted by urgency.

Author: Marwan Helmy
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from .bike import Bike, parse_iso
from .seasons import SeasonCalendar, effective_service_interval
from .storage import JsonStorage


@dataclass
class ServiceReminder:
    bike_id: str
    bike_name: str
    due_at: datetime
    days_overdue: float
    urgency: str  # overdue | due_today | upcoming
    rack_id: Optional[str] = None

    @property
    def sort_key(self) -> tuple:
        return (self.days_overdue * -1, self.due_at)


class ReminderEngine:
    def __init__(self, storage: JsonStorage, seasons: Optional[SeasonCalendar] = None):
        self.storage = storage
        self.seasons = seasons or SeasonCalendar()

    def _due_date(self, bike: Bike, ref: datetime) -> datetime:
        interval = effective_service_interval(
            bike.service_interval_days,
            self.seasons.multiplier_for(ref),
        )
        last = parse_iso(bike.last_serviced_at)
        if last is None:
            acquired = parse_iso(bike.acquired_at) or ref
            return acquired + timedelta(days=interval)
        return last + timedelta(days=interval)

    def compute_for_bike(self, bike: Bike, ref: Optional[datetime] = None) -> ServiceReminder:
        ref = ref or datetime.now(timezone.utc)
        due = self._due_date(bike, ref)
        delta_days = (ref - due).total_seconds() / 86400.0
        if delta_days > 0.01:
            urgency = "overdue"
        elif delta_days > -1:
            urgency = "due_today"
        else:
            urgency = "upcoming"
        return ServiceReminder(
            bike_id=bike.id,
            bike_name=bike.name,
            due_at=due,
            days_overdue=round(delta_days, 2),
            urgency=urgency,
            rack_id=bike.rack_id,
        )

    def upcoming(
        self,
        *,
        within_days: int = 14,
        include_overdue: bool = True,
        active_only: bool = True,
    ) -> list[ServiceReminder]:
        ref = datetime.now(timezone.utc)
        reminders = []
        for bike in self.storage.list_bikes(active_only=active_only):
            rem = self.compute_for_bike(bike, ref)
            if rem.urgency == "overdue" and not include_overdue:
                continue
            if rem.urgency != "overdue":
                days_until = (rem.due_at - ref).total_seconds() / 86400.0
                if days_until > within_days:
                    continue
            reminders.append(rem)
        reminders.sort(key=lambda r: r.sort_key, reverse=True)
        return reminders

    def overdue_only(self) -> list[ServiceReminder]:
        return [r for r in self.upcoming(within_days=9999) if r.urgency == "overdue"]

    def summary_text(self) -> str:
        items = self.upcoming(within_days=7)
        if not items:
            return "All caught up for the next week."
        lines = []
        for r in items[:20]:
            if r.urgency == "overdue":
                lines.append(f"!! {r.bike_name} ({r.days_overdue:.1f}d overdue)")
            elif r.urgency == "due_today":
                lines.append(f"-> {r.bike_name} (due today)")
            else:
                lines.append(f"   {r.bike_name} (due {r.due_at.date()})")
        return "\n".join(lines)
