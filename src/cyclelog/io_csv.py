"""CSV import/export for bikes and service logs.

Author: Marwan Helmy — started as a quick spreadsheet escape hatch.
"""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from typing import Any, Optional

from .errors import ExportError, ImportPipelineError, ValidationError, import_pipeline_error
from .parser import parse_date, parse_interval, parse_amount_ml
from .bike import HealthStatus, Bike
from .storage import JsonStorage
from .service import ServiceEvent

__author__ = "Marwan Helmy"

PLANT_FIELDS = [
    "id",
    "name",
    "nickname",
    "make_key",
    "rack_id",
    "health",
    "health_score",
    "service_interval_days",
    "service_amount_ml",
    "last_serviced_at",
    "acquired_at",
    "light_override",
    "mileage_override",
    "archived",
    "source",
    "notes",
]

WATERING_FIELDS = [
    "id",
    "bike_id",
    "bike_name",
    "serviced_at",
    "amount_ml",
    "method",
    "service_quality",
    "runoff",
    "skipped",
    "skip_reason",
    "notes",
]


def _read_csv_text(path: Path) -> str:
    if not path.exists():
        raise ImportPipelineError("csv", "file not found: %s" % path)
    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ImportPipelineError("csv", str(exc)) from exc


def _parse_bool(raw: Optional[str]) -> bool:
    if not raw:
        return False
    return raw.strip().lower() in ("1", "true", "yes", "y")


def _parse_health(raw: Optional[str]) -> HealthStatus:
    if not raw:
        return HealthStatus.UNKNOWN
    key = raw.strip().lower().replace(" ", "_")
    try:
        return HealthStatus(key)
    except ValueError:
        return HealthStatus.UNKNOWN


def _bike_lookup(storage: JsonStorage) -> tuple[dict[str, Bike], dict[str, Bike]]:
    by_id = {p.id: p for p in storage.list_bikes(active_only=False)}
    by_name: dict[str, Bike] = {}
    for p in by_id.values():
        by_name.setdefault(p.name.lower(), p)
        if p.nickname:
            by_name.setdefault(p.nickname.lower(), p)
    return by_id, by_name


def _resolve_bike_id(
    by_id: dict[str, Bike],
    by_name: dict[str, Bike],
    bike_id: Optional[str],
    bike_name: Optional[str],
) -> Optional[str]:
    if bike_id and bike_id in by_id:
        return bike_id
    if bike_name:
        hit = by_name.get(bike_name.strip().lower())
        if hit:
            return hit.id
    return bike_id


def export_bikes_csv(storage: JsonStorage, dest: Path) -> int:
    """Write all bikes (including archived) to a CSV file."""
    try:
        with dest.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=PLANT_FIELDS)
            writer.writeheader()
            count = 0
            for bike in storage.list_bikes(active_only=False):
                notes = str(bike.metadata.get("notes", ""))
                writer.writerow({
                    "id": bike.id,
                    "name": bike.name,
                    "nickname": bike.nickname or "",
                    "make_key": bike.make_key or "",
                    "rack_id": bike.rack_id or "",
                    "health": bike.health.value,
                    "health_score": bike.health_score,
                    "service_interval_days": bike.service_interval_days,
                    "service_amount_ml": bike.service_amount_ml or "",
                    "last_serviced_at": bike.last_serviced_at or "",
                    "acquired_at": bike.acquired_at or "",
                    "light_override": bike.light_override or "",
                    "mileage_override": bike.mileage_override or "",
                    "archived": "yes" if bike.archived else "no",
                    "source": bike.source,
                    "notes": notes.replace("\n", " "),
                })
                count += 1
        return count
    except OSError as exc:
        raise ExportError("csv", str(exc)) from exc


def export_service_csv(storage: JsonStorage, dest: Path) -> int:
    """Write service events with bike names for human-readable spreadsheets."""
    bike_names = {p.id: p.name for p in storage.list_bikes(active_only=False)}
    try:
        with dest.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=WATERING_FIELDS)
            writer.writeheader()
            count = 0
            for row in storage.list_service_events():
                writer.writerow({
                    "id": row.get("id", ""),
                    "bike_id": row.get("bike_id", ""),
                    "bike_name": bike_names.get(row.get("bike_id", ""), ""),
                    "serviced_at": row.get("serviced_at", ""),
                    "amount_ml": row.get("amount_ml") or "",
                    "method": row.get("method", "top_service"),
                    "service_quality": row.get("service_quality", "tap"),
                    "runoff": "yes" if row.get("runoff") else "no",
                    "skipped": "yes" if row.get("skipped") else "no",
                    "skip_reason": row.get("skip_reason", ""),
                    "notes": (row.get("notes") or "").replace("\n", " "),
                })
                count += 1
        return count
    except OSError as exc:
        raise ExportError("csv", str(exc)) from exc


def export_csv_bundle(storage: JsonStorage, dest: Path) -> tuple[int, int]:
    """Export bikes.csv and service.csv beside dest stem."""
    bikes_path = dest.with_name(dest.stem + "_bikes.csv")
    service_path = dest.with_name(dest.stem + "_service.csv")
    return export_bikes_csv(storage, bikes_path), export_service_csv(storage, service_path)


def import_bikes_csv(
    storage: JsonStorage,
    src: Path,
    *,
    update: bool = False,
) -> int:
    """Import bikes from CSV; skips blank name rows."""
    text = _read_csv_text(src)
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames or "name" not in reader.fieldnames:
        raise ImportPipelineError("csv", "missing required column: name")

    existing = {p.id: p for p in storage.list_bikes(active_only=False)}
    by_name = {p.name.lower(): p for p in existing.values()}
    count = 0

    for line_no, row in enumerate(reader, start=2):
        name = (row.get("name") or "").strip()
        if not name:
            continue
        pid = (row.get("id") or "").strip()
        bike: Bike | None = None
        if pid and pid in existing:
            bike = existing[pid]
        elif update:
            bike = by_name.get(name.lower())

        try:
            interval_raw = row.get("service_interval_days")
            interval = parse_interval(str(interval_raw)) if interval_raw else 7
            health = _parse_health(row.get("health"))
            metadata = {}
            notes = (row.get("notes") or "").strip()
            if notes:
                metadata["notes"] = notes

            if bike is None:
                bike = Bike.create(
                    name,
                    id=pid or None,
                    nickname=(row.get("nickname") or "").strip() or None,
                    make_key=(row.get("make_key") or "").strip() or None,
                    rack_id=(row.get("rack_id") or "").strip() or None,
                    health=health,
                    service_interval_days=interval,
                    last_serviced_at=(row.get("last_serviced_at") or "").strip() or None,
                    acquired_at=(row.get("acquired_at") or "").strip() or None,
                    light_override=(row.get("light_override") or "").strip() or None,
                    archived=_parse_bool(row.get("archived")),
                    source="csv",
                    metadata=metadata,
                )
                hs = row.get("health_score")
                if hs and str(hs).isdigit():
                    bike.health_score = int(hs)
                amt = row.get("service_amount_ml")
                if amt:
                    bike.service_amount_ml = parse_amount_ml(str(amt))
                hum = row.get("mileage_override")
                if hum:
                    bike.mileage_override = float(hum)
                created = storage.create_bike(bike)
                existing[created.id] = created
                by_name[created.name.lower()] = created
            else:
                patch: dict[str, Any] = {
                    "name": name,
                    "nickname": (row.get("nickname") or "").strip() or None,
                    "make_key": (row.get("make_key") or "").strip() or None,
                    "rack_id": (row.get("rack_id") or "").strip() or None,
                    "health": health.value,
                    "service_interval_days": interval,
                    "archived": _parse_bool(row.get("archived")),
                    "source": "csv",
                    "metadata": {**bike.metadata, **metadata},
                }
                lw = (row.get("last_serviced_at") or "").strip()
                if lw:
                    patch["last_serviced_at"] = lw
                updated = storage.update_bike(bike.id, patch)
                existing[updated.id] = updated
            count += 1
        except (ValidationError, ValueError) as exc:
            raise import_pipeline_error("csv", line_no, str(exc)) from exc

    return count


def import_service_csv(storage: JsonStorage, src: Path) -> int:
    """Import service events; resolves bike_name when bike_id missing."""
    text = _read_csv_text(src)
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise ImportPipelineError("csv", "empty or headerless file")

    by_id, by_name = _bike_lookup(storage)
    count = 0

    for line_no, row in enumerate(reader, start=2):
        bike_id = _resolve_bike_id(
            by_id,
            by_name,
            (row.get("bike_id") or "").strip() or None,
            (row.get("bike_name") or "").strip() or None,
        )
        if not bike_id:
            raise import_pipeline_error("csv", line_no, "bike_id or bike_name required")

        try:
            storage.get_bike(bike_id)
        except Exception:
            raise import_pipeline_error("csv", line_no, "unknown bike %s" % bike_id)

        serviced_at = (row.get("serviced_at") or "").strip()
        if serviced_at:
            try:
                serviced_at = parse_date(serviced_at).isoformat()
            except ValueError:
                pass  # keep raw ISO if already formatted

        amount_ml = None
        amt_raw = row.get("amount_ml")
        if amt_raw not in (None, ""):
            try:
                amount_ml = parse_amount_ml(str(amt_raw))
            except ValueError:
                raise import_pipeline_error("csv", line_no, "bad amount_ml: %s" % amt_raw)

        event = ServiceEvent.create(
            bike_id=bike_id,
            id=(row.get("id") or "").strip() or None,
            serviced_at=serviced_at or None,
            amount_ml=amount_ml,
            method=(row.get("method") or "top_service").strip(),
            runoff=_parse_bool(row.get("runoff")),
            skipped=_parse_bool(row.get("skipped")),
            skip_reason=(row.get("skip_reason") or "").strip(),
            notes=(row.get("notes") or "").strip(),
        )
        if row.get("service_quality"):
            event.service_quality = row["service_quality"].strip()  # type: ignore[assignment]
        storage.create_service_event(event.to_dict())
        count += 1

    return count


def validate_csv_headers(path: Path, kind: str = "bikes") -> list[str]:
    """Return missing required columns for bikes or service CSV."""
    if not path.exists():
        return ["name"] if kind == "bikes" else ["bike_id"]
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    headers = reader.fieldnames or []
    if kind == "bikes":
        required = ["name"]
    else:
        required = []  # bike_name OR bike_id
        if "bike_id" not in headers and "bike_name" not in headers:
            return ["bike_id or bike_name"]
        return []
    return [h for h in required if h not in headers]


def sample_rows(path: Path, n: int = 3) -> list[dict[str, str]]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    out: list[dict[str, str]] = []
    for i, row in enumerate(reader):
        if i >= n:
            break
        out.append({k: (v or "") for k, v in row.items()})
    return out
