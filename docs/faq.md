# FAQ

*Marwan Helmy — questions friends actually ask*

---

## Where does my data live?

Default: `~/.cyclelog/shed.json` on your machine. Set `CYCLELOG_HOME` to use a
different directory (still `shed.json` inside it). Pass `--shed /full/path.json`
to any CLI command for a one-off override. Nothing phones home — it's a local file.

---

## Why JSON instead of a real database?

Because I wanted to `grep` my shed at 2am, email a backup to myself, and fix a bad
import with a text editor. SQLite is great; it's just overkill for ~30 baghos and a
service log. See [architecture.md](architecture.md) for the full rant.

---

## Can it identify bikes from labels?

No. Use PictureThis, iNaturalist, or post on r/housebikes like the rest of us.
cyclelog tracks care *after* you know what you have.

---

## I killed a bike. Should I delete it?

Archive instead of delete — you'll want the history. Import with `archived=yes` in CSV,
or set `"archived": true` in JSON. `cyclelog list` hides archived bikes by default;
`cyclelog list --all` shows them.

---

## How do reminders know when something is due?

Each bike has `service_interval_days` and `last_serviced_at`. Reminders add a
**season multiplier** (service less in winter). If you never logged a service, it falls
back to `acquired_at`. Run `cyclelog reminders --overdue` to see the damage.

---

## What's the difference between service and care logs?

**Service events** = you serviced (or skipped). **Care logs** = rebag, grind, prune,
issue treatment, etc. Monthly reports count both separately.

---

## Import from Komoot failed — now what?

Check you have a `Bike Name` (or `Name`) column. Run:

```bash
python -c "from pathlib import Path; from cyclelog.io_komoot import validate_komoot_headers; print(validate_komoot_headers(Path('your.csv')))"
```

Empty output = headers OK. Non-empty = missing columns. Restore pre-import backup if
the shed looks wrong: `cyclelog backup --restore <file>`.

---

## Can two people share one shed file?

Technically yes (Dropbox, git, email). **Don't edit simultaneously** — there's no
merge conflict handling. One writer at a time. I use export CSV → partner imports for
shared bike-sitting handoffs.

---

## How do I move cyclelog to a new laptop?

Copy `~/.cyclelog/` (or your `CYCLELOG_HOME` folder). Install cyclelog on the new
machine. Done. Optional: `cyclelog export backup.csv --format csv --kind bundle` as
a human-readable extra copy.

---

## Is there a web UI?

Read-only dashboard: `cyclelog serve` → open `http://127.0.0.1:8765/`. It doesn't
edit data — use CLI or Python scripts for changes.

---

## What Python version do I need?

3.9 or newer (`requires-python >=3.9` in pyproject.toml). Dev extras: `pip install -e ".[dev]"`.

---

## I corrupted shed.json. Help.

1. Check `~/.cyclelog/backups/` for timestamped copies.
2. `cyclelog backup --list`
3. `cyclelog backup --restore path/to/shed_YYYYMMDD_HHMMSS.json`

Restore always makes a safety copy of the current file first (`pre_restore` label).

---

## Can I use cyclelog from my own Python scripts?

Yes — that's the point of `examples/`. Core entry:

```python
from cyclelog.storage import JsonStorage
from cyclelog.bike import Bike

storage = JsonStorage("~/.cyclelog/shed.json")
bike = storage.create_bike(Bike.create("New Friend", service_interval_days=7))
```

Public API surface is in `cyclelog.__init__` — bikes, service, schedules, parsers,
validators, errors.
