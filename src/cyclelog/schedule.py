"""Service schedule engine with seasonal adjustments."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, timedelta
from enum import Enum
from typing import Any

from cyclelog.bike import Bike, BikeCatalog, HealthStatus
from cyclelog.make import MakeCatalog, MakeProfile
from cyclelog.rack import RackRegistry, Rack
from cyclelog.service import ServiceLog


class Season(str, Enum):
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"

    def __str__(self) -> str:
        return self.value


# northern hemisphere defaults — good enough for my use
_SEASON_MONTHS: dict[Season, tuple[int, ...]] = {
    Season.SPRING: (3, 4, 5),
    Season.SUMMER: (6, 7, 8),
    Season.FALL: (9, 10, 11),
    Season.WINTER: (12, 1, 2),
}

# multipliers applied to base interval
_SEASON_MULT: dict[Season, float] = {
    Season.SPRING: 1.0,
    Season.SUMMER: 0.85,
    Season.FALL: 1.05,
    Season.WINTER: 1.35,
}


def detect_season(d: date | None = None) -> Season:
    ref = d or date.today()
    m = ref.month
    for season, months in _SEASON_MONTHS.items():
        if m in months:
            return season
    return Season.SPRING  # shouldn't happen


@dataclass
class ScheduleEntry:
    bike_id: str
    bike_name: str
    next_due: str
    base_interval_days: int
    adjusted_interval_days: int
    season: str
    overdue: bool = False
    overdue_days: int = 0
    last_serviced_at: str | None = None
    rack_name: str | None = None
    health: str = "unknown"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScheduleEntry":
        return cls(**data)

    def days_until_due(self, today: date | None = None) -> int:
        ref = today or date.today()
        due = date.fromisoformat(self.next_due[:10])
        return (due - ref).days


@dataclass
class ScheduleOptions:
    season_override: Season | None = None
    health_adjust: bool = True
    rack_mileage_adjust: bool = True
    min_interval_days: int = 2
    max_interval_days: int = 60
    include_archived: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.season_override:
            d["season_override"] = self.season_override.value
        return d


class ScheduleEngine:
    """Compute next service dates with seasonal and contextual tweaks."""

    def __init__(
        self,
        bikes: BikeCatalog | None = None,
        make: MakeCatalog | None = None,
        racks: RackRegistry | None = None,
        service_log: ServiceLog | None = None,
    ) -> None:
        self.bikes = bikes or BikeCatalog()
        self.make = make or MakeCatalog.with_defaults()
        self.racks = racks or RackRegistry()
        self.service_log = service_log or ServiceLog()
        self.options = ScheduleOptions()

    def set_options(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            if hasattr(self.options, k):
                setattr(self.options, k, v)

    def base_interval(self, bike: Bike) -> int:
        if bike.make_key:
            try:
                profile = self.make.require(bike.make_key)
                return profile.service_interval_days
            except Exception:
                pass  # fall back — don't crash schedule over bad make key
        return bike.service_interval_days

    def season_multiplier(self, when: date | None = None) -> float:
        season = self.options.season_override or detect_season(when)
        return _SEASON_MULT[season]

    def health_multiplier(self, bike: Bike) -> float:
        if not self.options.health_adjust:
            return 1.0
        if bike.health == HealthStatus.STRUGGLING:
            return 0.9  # service a bit sooner when struggling
        if bike.health == HealthStatus.CRITICAL:
            return 0.75
        if bike.health == HealthStatus.THRIVING:
            return 1.05
        return 1.0

    def rack_multiplier(self, bike: Bike) -> float:
        if not self.options.rack_mileage_adjust or not bike.rack_id:
            return 1.0
        loc = self.racks.get(bike.rack_id)
        if loc is None or loc.mileage_pct is None:
            return 1.0
        # higher mileage -> stretch interval slightly
        if loc.mileage_pct >= 65:
            return 1.15
        if loc.mileage_pct <= 35:
            return 0.9
        return 1.0

    def bag_multiplier(self, bike: Bike) -> float:
        if bike.bag.diameter is None:
            return 1.0
        # tiny bags dry faster
        dia = bike.bag.diameter
        if bike.bag.unit == "cm":
            dia = dia / 2.54
        if dia <= 4:
            return 0.85
        if dia >= 12:
            return 1.2
        return 1.0

    def adjusted_interval(self, bike: Bike, when: date | None = None) -> int:
        base = self.base_interval(bike)
        mult = (
            self.season_multiplier(when)
            * self.health_multiplier(bike)
            * self.rack_multiplier(bike)
            * self.bag_multiplier(bike)
        )
        days = int(round(base * mult))
        days = max(self.options.min_interval_days, days)
        days = min(self.options.max_interval_days, days)
        return days

    def last_serviced(self, bike: Bike) -> date | None:
        if bike.last_serviced_at:
            return date.fromisoformat(bike.last_serviced_at[:10])
        ev = self.service_log.last_for_bike(bike.id)
        if ev:
            return ev.serviced_date
        if bike.acquired_at:
            return date.fromisoformat(bike.acquired_at[:10])
        return None

    def next_due_date(self, bike: Bike, when: date | None = None) -> date:
        ref = when or date.today()
        interval = self.adjusted_interval(bike, ref)
        last = self.last_serviced(bike)
        if last is None:
            return ref  # due now if never serviced
        return last + timedelta(days=interval)

    def build_entry(self, bike: Bike, when: date | None = None) -> ScheduleEntry:
        ref = when or date.today()
        season = self.options.season_override or detect_season(ref)
        base = self.base_interval(bike)
        adj = self.adjusted_interval(bike, ref)
        due = self.next_due_date(bike, ref)
        overdue = due < ref
        overdue_days = (ref - due).days if overdue else 0
        loc_name = None
        if bike.rack_id:
            loc = self.racks.get(bike.rack_id)
            loc_name = loc.name if loc else None
        last = self.last_serviced(bike)
        notes = ""
        if bike.health == HealthStatus.CRITICAL:
            notes = "check roots/grind"
        elif overdue_days > 7:
            notes = "seriously overdue"
        return ScheduleEntry(
            bike_id=bike.id,
            bike_name=bike.display_name,
            next_due=due.isoformat(),
            base_interval_days=base,
            adjusted_interval_days=adj,
            season=season.value,
            overdue=overdue,
            overdue_days=overdue_days,
            last_serviced_at=last.isoformat() if last else None,
            rack_name=loc_name,
            health=bike.health.value,
            notes=notes,
        )

    def week_schedule(self, start: date | None = None) -> list[ScheduleEntry]:
        ref = start or date.today()
        end = ref + timedelta(days=7)
        entries: list[ScheduleEntry] = []
        for bike in self.bikes.all(include_archived=self.options.include_archived):
            entry = self.build_entry(bike, ref)
            due = date.fromisoformat(entry.next_due[:10])
            if due <= end:
                entries.append(entry)
        return sorted(entries, key=lambda e: e.next_due)

    def overdue(self, when: date | None = None) -> list[ScheduleEntry]:
        ref = when or date.today()
        out: list[ScheduleEntry] = []
        for bike in self.bikes.all(include_archived=self.options.include_archived):
            entry = self.build_entry(bike, ref)
            if entry.overdue:
                out.append(entry)
        return sorted(out, key=lambda e: -e.overdue_days)

    def today(self, when: date | None = None) -> list[ScheduleEntry]:
        ref = when or date.today()
        out: list[ScheduleEntry] = []
        for bike in self.bikes.all(include_archived=self.options.include_archived):
            entry = self.build_entry(bike, ref)
            due = date.fromisoformat(entry.next_due[:10])
            if due <= ref:
                out.append(entry)
        return sorted(out, key=lambda e: e.bike_name.lower())

    def full_schedule(self, when: date | None = None) -> list[ScheduleEntry]:
        ref = when or date.today()
        return sorted(
            [
                self.build_entry(p, ref)
                for p in self.bikes.all(include_archived=self.options.include_archived)
            ],
            key=lambda e: e.next_due,
        )

    def preview_interval_change(
        self, bike: Bike, new_base_days: int, when: date | None = None
    ) -> dict[str, Any]:
        old = bike.service_interval_days
        bike.service_interval_days = new_base_days
        adj = self.adjusted_interval(bike, when)
        nxt = self.next_due_date(bike, when)
        bike.service_interval_days = old
        return {
            "bike_id": bike.id,
            "new_base_days": new_base_days,
            "adjusted_days": adj,
            "next_due": nxt.isoformat(),
        }

    def summarize_week(self, start: date | None = None) -> dict[str, Any]:
        entries = self.week_schedule(start)
        overdue = [e for e in entries if e.overdue]
        return {
            "start": (start or date.today()).isoformat(),
            "total_due": len(entries),
            "overdue_count": len(overdue),
            "by_day": self._group_by_day(entries),
        }

    def _group_by_day(self, entries: list[ScheduleEntry]) -> dict[str, list[str]]:
        buckets: dict[str, list[str]] = {}
        for e in entries:
            day = e.next_due[:10]
            buckets.setdefault(day, []).append(e.bike_name)
        return buckets

    def sync_bike_intervals_from_make(self) -> int:
        """Push make defaults onto bikes missing explicit intervals."""
        updated = 0
        for bike in self.bikes.all():
            if not bike.make_key:
                continue
            profile = self.make.get(bike.make_key)
            if profile is None:
                continue
            if bike.service_interval_days == 7:  # default sentinel — yeah it's hacky
                bike.service_interval_days = profile.service_interval_days
                bike.touch()
                updated += 1
        return updated


def compute_next_service(
    bike: Bike,
    make: MakeCatalog | None = None,
    when: date | None = None,
) -> date:
    """One-shot helper without standing up the full engine."""
    engine = ScheduleEngine(make=make or MakeCatalog.with_defaults())
    engine.bikes.add(bike)
    return engine.next_due_date(bike, when)


def month_calendar(
    engine: ScheduleEngine,
    year: int,
    month: int,
) -> dict[str, list[str]]:
    """Map ISO date strings to bike names due that day."""
    from calendar import monthrange

    _, last_day = monthrange(year, month)
    cal: dict[str, list[str]] = {}
    for day in range(1, last_day + 1):
        ref = date(year, month, day)
        for entry in engine.full_schedule(ref):
            due = entry.next_due[:10]
            if due == ref.isoformat():
                cal.setdefault(due, []).append(entry.bike_name)
    return cal


def format_schedule_text(entries: list[ScheduleEntry]) -> str:
    lines = ["Service schedule", "=" * 40]
    for e in entries:
        flag = " [OVERDUE %dd]" % e.overdue_days if e.overdue else ""
        lines.append(
            "{due}  {name}  ({interval}d, {season}){flag}".format(
                due=e.next_due[:10],
                name=e.bike_name,
                interval=e.adjusted_interval_days,
                season=e.season,
                flag=flag,
            )
        )
    return "\n".join(lines)


def group_by_rack(
    engine: ScheduleEngine,
    when: date | None = None,
) -> dict[str, list[ScheduleEntry]]:
    buckets: dict[str, list[ScheduleEntry]] = {}
    for entry in engine.today(when):
        key = entry.rack_name or "unassigned"
        buckets.setdefault(key, []).append(entry)
    return buckets


def estimate_weekly_service_ml(
    engine: ScheduleEngine,
    default_ml_per_bike: float = 250.0,
) -> float:
    """Rough weekly service volume based on due bikes and stored amounts."""
    total = 0.0
    for entry in engine.week_schedule():
        bike = engine.bikes.get(entry.bike_id)
        if bike and bike.service_amount_ml:
            total += bike.service_amount_ml
        else:
            total += default_ml_per_bike
    return total


def reschedule_after_service(
    engine: ScheduleEngine,
    bike: Bike,
    when: date | None = None,
) -> ScheduleEntry:
    """Rebuild entry assuming bike was just serviced."""
    ref = when or date.today()
    bike.record_service(ref)
    return engine.build_entry(bike, ref)


def compare_seasons(engine: ScheduleEngine, bike: Bike) -> dict[str, int]:
    """Show adjusted interval per season — educational."""
    makeal = engine.options.season_override
    out: dict[str, int] = {}
    for season in Season:
        engine.options.season_override = season
        out[season.value] = engine.adjusted_interval(bike)
    engine.options.season_override = makeal
    return out


@dataclass
class ScheduleReport:
    generated_at: str
    season: str
    due_today: int
    due_this_week: int
    overdue: int
    entries: list[ScheduleEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "season": self.season,
            "due_today": self.due_today,
            "due_this_week": self.due_this_week,
            "overdue": self.overdue,
            "entries": [e.to_dict() for e in self.entries],
        }


def build_schedule_report(engine: ScheduleEngine, when: date | None = None) -> ScheduleReport:
    from datetime import datetime

    ref = when or date.today()
    season = (engine.options.season_override or detect_season(ref)).value
    today_entries = engine.today(ref)
    week_entries = engine.week_schedule(ref)
    overdue_entries = engine.overdue(ref)
    return ScheduleReport(
        generated_at=datetime.utcnow().isoformat(),
        season=season,
        due_today=len(today_entries),
        due_this_week=len(week_entries),
        overdue=len(overdue_entries),
        entries=today_entries,
    )


def bikes_by_urgency(engine: ScheduleEngine, when: date | None = None) -> list[ScheduleEntry]:
    entries = engine.full_schedule(when)
    return sorted(
        entries,
        key=lambda e: (not e.overdue, e.days_until_due(when), e.bike_name.lower()),
    )


def next_n_days(engine: ScheduleEngine, n: int = 14, start: date | None = None) -> dict[str, list[ScheduleEntry]]:
    ref = start or date.today()
    end = ref + timedelta(days=n)
    buckets: dict[str, list[ScheduleEntry]] = {}
    for bike in engine.bikes.all(include_archived=engine.options.include_archived):
        entry = engine.build_entry(bike, ref)
        due = date.fromisoformat(entry.next_due[:10])
        if ref <= due <= end:
            buckets.setdefault(due.isoformat(), []).append(entry)
    return buckets


def interval_audit(engine: ScheduleEngine) -> list[dict[str, Any]]:
    """Compare each bike's configured interval vs make default."""
    rows: list[dict[str, Any]] = []
    for bike in engine.bikes.all():
        base = engine.base_interval(bike)
        configured = bike.service_interval_days
        rows.append({
            "bike_id": bike.id,
            "name": bike.display_name,
            "configured_days": configured,
            "make_default_days": base,
            "delta": configured - base,
        })
    return rows


def apply_seasonal_intervals(engine: ScheduleEngine, dry_run: bool = True) -> list[dict[str, Any]]:
    """Preview or apply seasonal interval adjustments to all bikes."""
    changes: list[dict[str, Any]] = []
    season = engine.options.season_override or detect_season()
    mult = engine.season_multiplier()
    for bike in engine.bikes.all():
        old = bike.service_interval_days
        new = max(engine.options.min_interval_days, int(round(old * mult)))
        changes.append({
            "bike_id": bike.id,
            "name": bike.display_name,
            "old_days": old,
            "new_days": new,
            "season": season.value,
        })
        if not dry_run and new != old:
            bike.service_interval_days = new
            bike.touch()
    return changes


def schedule_conflicts(entries: list[ScheduleEntry]) -> list[tuple[str, str]]:
    """Find bikes sharing same due date and rack — batch service hints."""
    by_day_loc: dict[tuple[str, str | None], list[str]] = {}
    for e in entries:
        key = (e.next_due[:10], e.rack_name)
        by_day_loc.setdefault(key, []).append(e.bike_name)
    pairs: list[tuple[str, str]] = []
    for (day, loc), names in by_day_loc.items():
        if len(names) > 1:
            pairs.append(("%s @ %s" % (day, loc or "?"), ", ".join(names)))
    return pairs


