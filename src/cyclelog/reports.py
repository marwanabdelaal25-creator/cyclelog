"""Monthly care summary reports.

Author: Marwan Helmy
"""

from __future__ import annotations

from calendar import monthrange
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

from .bike import parse_iso
from .storage import JsonStorage


class MonthlyReport:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def _month_bounds(self, year: int, month: int) -> tuple[datetime, datetime]:
        start = datetime(year, month, 1, tzinfo=timezone.utc)
        last_day = monthrange(year, month)[1]
        end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
        return start, end

    def _in_range(self, ts: Optional[str], start: datetime, end: datetime) -> bool:
        dt = parse_iso(ts)
        if dt is None:
            return False
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return start <= dt <= end

    def generate(self, year: int, month: int) -> dict[str, Any]:
        start, end = self._month_bounds(year, month)
        service = [
            e for e in self.storage.list_service_events()
            if self._in_range(e.get("serviced_at"), start, end)
        ]
        care = [
            c for c in self.storage.list_inspection_logs()
            if self._in_range(c.get("logged_at"), start, end)
        ]
        issues = [
            p for p in self.storage.snapshot().get("issue_reports", [])
            if self._in_range(p.get("reported_at"), start, end)
        ]
        fert = [
            f for f in self.storage.snapshot().get("grind_events", [])
            if self._in_range(f.get("applied_at"), start, end)
        ]

        bikes_serviced = Counter(e.get("bike_id") for e in service)
        care_actions = Counter(c.get("action", "unknown") for c in care)

        by_rack: dict[str, int] = defaultdict(int)
        bike_map = {p.id: p for p in self.storage.list_bikes(active_only=False)}
        for pid in bikes_serviced:
            loc = bike_map.get(pid)
            if loc and loc.rack_id:
                by_rack[loc.rack_id] += bikes_serviced[pid]

        return {
            "year": year,
            "month": month,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "totals": {
                "services": len(service),
                "inspection_logs": len(care),
                "issue_reports": len(issues),
                "grind_events": len(fert),
                "unique_bikes_serviced": len(bikes_serviced),
            },
            "top_serviced_bikes": bikes_serviced.most_common(5),
            "care_action_breakdown": dict(care_actions),
            "services_by_rack": dict(by_rack),
            "issue_reports": issues,
        }

    def render_text(self, year: int, month: int) -> str:
        report = self.generate(year, month)
        t = report["totals"]
        lines = [
            f"Cyclelog report {year}-{month:02d}",
            f"  Services: {t['services']} ({t['unique_bikes_serviced']} bikes)",
            f"  Care logs: {t['inspection_logs']}",
            f"  Issue incidents: {t['issue_reports']}",
            f"  Odometer: {t['grind_events']}",
        ]
        if report["top_serviced_bikes"]:
            lines.append("  Most serviced:")
            for pid, count in report["top_serviced_bikes"]:
                name = bike_map_name(self.storage, pid)
                lines.append(f"    - {name}: {count}x")
        return "\n".join(lines)


def bike_map_name(storage: JsonStorage, bike_id: str) -> str:
    try:
        return storage.get_bike(bike_id).name
    except Exception:
        return bike_id
