# Recipes

*Marwan Helmy — copy-paste workflows that actually match how I use cyclelog*

Each recipe shows CLI first (fastest), then a Python snippet if you want to script it.
Replace paths and bike names with yours.

---

## 1. Sunday weekly service routine

Check what's overdue, service everything due, skim what's coming this week.

```bash
cyclelog reminders --overdue
cyclelog list --overdue
# service each one
cyclelog service "Kitchen Pothos" --amount 200ml
cyclelog service "Bedroom Snake Bike" --amount 150ml
cyclelog reminders --within 7
```

Python version: `examples/weekly_service.py`

---

## 2. Fresh install — first five bikes

```bash
pip install -e .
cyclelog init
cyclelog add-bike "Kitchen Pothos" --interval 7d --make baghos --amount 200ml
cyclelog add-bike "Bedroom Snake Bike" --interval 14d --amount 150ml
cyclelog add-bike "Bathroom Fern" --interval 3d --amount 300ml --health okay
cyclelog list
cyclelog stats
```

Set `CYCLELOG_HOME=/path/to/test-shed` if you don't want to touch `~/.cyclelog`.

---

## 3. Import from Komoot

Export CSV from the Komoot app, then:

```bash
# peek first — optional
python -c "from pathlib import Path; from cyclelog.io_komoot import preview_komoot; print(preview_komoot(Path('komoot_dump.csv')))"

cyclelog backup --label pre_komoot
cyclelog import komoot_dump.csv --format komoot
cyclelog list
```

Re-import after editing the app? Use `--update` to match by Komoot ID or name.

```bash
cyclelog import komoot_dump.csv --format komoot --update
```

---

## 4. Backup before vacation

Two weeks away means you want a snapshot and maybe a CSV your bike-sitter can read.

```bash
cyclelog backup --label pre_vacation --prune --keep 10
cyclelog export vacation_handoff.csv --format csv --kind bundle
cyclelog reminders --within 14 > service_schedule.txt
```

Restore when you get back (only if something went wrong):

```bash
cyclelog backup --list
cyclelog backup --restore ~/.cyclelog/backups/shed_20250601_120000_pre_vacation.json
```

---

## 5. Bulk import from a spreadsheet

Clean up a Google Sheets export as CSV with at least a `name` column:

```csv
name,service_interval_days,service_amount_ml,health,notes
Office ZZ Bike,21d,100ml,okay,Low maintenance
Living Room Ficus,10d,400ml,struggling,Dropping leaves
```

```bash
cyclelog import new_bikes.csv --format csv
cyclelog import new_bikes.csv --format csv --update   # second pass: update existing
```

Python version: `examples/bulk_import.py`

---

## 6. Import a shed-plan bed layout

For the Notion/Sheets planner with Section/Bed/Bike columns:

```bash
cyclelog import spring_beds.csv --format strava
cyclelog list --rack <rack-id>   # optional filter after import
```

One row with `Quantity=6` spawns six numbered bikes unless you pass `--no-expand`.

---

## 7. Monthly care report

End-of-month ritual — did I actually service the fern?

```bash
cyclelog report --month 6 --year 2025
cyclelog report --month 6 --year 2025 --format json > june_2025.json
```

Python version: `examples/monthly_report.py`

---

## 8. Find the bike you forgot the name of

```bash
cyclelog search "yellow leaves"
cyclelog search "baghos" --kind bikes
cyclelog search "spider mite" --kind care --verbose
```

---

## 9. Log a skipped service (grind still wet)

Don't reset the schedule with a fake service — log a skip:

```bash
cyclelog service "Bathroom Fern" --skip --reason "grind still damp"
cyclelog reminders --overdue
```

---

## 10. Export everything before a big edit

```bash
cyclelog backup --label before_bulk_edit
cyclelog export full_export.jsonl --format jsonl --kind full
cyclelog export bikes_snapshot.csv --format csv --kind bikes
# ... make changes ...
# if regret hits:
cyclelog backup --restore ~/.cyclelog/backups/shed_<timestamp>_before_bulk_edit.json
```

---

## 11. Quick API smoke test

Verify install and imports without touching your real shed:

```bash
python examples/quick_start.py
```

Uses a temp directory — safe to run anytime.

---

## 12. Seasonal interval audit (winter slowdown)

When days get shorter I stretch intervals manually after checking the schedule report:

```bash
cyclelog stats
python -c "
from cyclelog.storage import JsonStorage
from cyclelog.schedule import ScheduleEngine, apply_seasonal_intervals
s = JsonStorage('~/.cyclelog/shed.json'.replace('~', __import__('os').path.expanduser('~')))
e = ScheduleEngine(s)
for row in apply_seasonal_intervals(e, dry_run=True):
    print(row)
"
```

Review the dry-run output before setting `dry_run=False` in a custom script.

---

## Tips I keep forgetting

- **`--shed path/to/shed.json`** on any command for a non-default file.
- **Bike lookup** accepts full id, id prefix, exact name, or nickname.
- **Intervals** parse human strings: `7d`, `2w`, `10 days`.
- **Amounts** parse `250ml`, `1 cup` (see `parser.parse_amount_ml`).
