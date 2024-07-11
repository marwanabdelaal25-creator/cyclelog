#!/usr/bin/env python3
"""Bulk import bikes from CSV (and optionally Komoot).

Author: Marwan Helmy
Run: python examples/bulk_import.py
     python examples/bulk_import.py path/to/bikes.csv
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from cyclelog import io_csv, io_komoot
from cyclelog.backup import ShedBackup
from cyclelog.storage import JsonStorage


def shed_path() -> Path:
    home = os.environ.get("CYCLELOG_HOME")
    base = Path(home) if home else Path.home() / ".cyclelog"
    return base / "shed.json"


def sample_csv(path: Path) -> None:
    path.write_text(
        "name,service_interval_days,service_amount_ml,health,notes\n"
        "Office ZZ Bike,21d,100ml,okay,Low maintenance\n"
        "Living Room Ficus,10d,400ml,struggling,Dropping leaves — check light\n"
        "Kitchen Pothos,7d,200ml,thriving,Trailing nicely\n",
        encoding="utf-8",
    )


def main() -> None:
    csv_file = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    use_temp_shed = csv_file is None

    if use_temp_shed:
        tmp = tempfile.mkdtemp(prefix="cyclelog_import_")
        path = Path(tmp) / "shed.json"
        csv_file = Path(tmp) / "bikes.csv"
        sample_csv(csv_file)
        print(f"Demo mode — shed: {path}")
    else:
        path = shed_path()
        if not csv_file.exists():
            print(f"File not found: {csv_file}", file=sys.stderr)
            sys.exit(1)

    storage = JsonStorage(path)
    backup_dir = path.parent / "backups"
    if path.exists() and path.stat().st_size > 50:
        snap = ShedBackup(path, backup_dir).create(label="pre_bulk_import")
        print(f"Backup: {snap}")

    missing = io_csv.validate_csv_headers(csv_file, "bikes")
    if missing:
        print(f"CSV missing columns: {missing}", file=sys.stderr)
        sys.exit(1)

    count = io_csv.import_bikes_csv(storage, csv_file, update=True)
    print(f"Imported {count} bike(s) from {csv_file.name}")

    for bike in storage.list_bikes():
        print(f"  - {bike.display_name}: every {bike.service_interval_days}d, {bike.health.value}")

    if csv_file.name.lower().find("komoot") >= 0:
        n = io_komoot.import_komoot(storage, csv_file, update=True)
        print(f"Komoot pass: {n} record(s)")


if __name__ == "__main__":
    main()
