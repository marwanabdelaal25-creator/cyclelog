# Data formats

*Marwan Helmy — what goes in, what comes out*

cyclelog speaks a few dialects. The source of truth is always `shed.json`; everything
else is a view or an import path into that file.

---

## shed.json schema

**Rack:** `~/.cyclelog/shed.json` (or `$CYCLELOG_HOME/shed.json`)

**Root object fields:**

| Field | Type | Notes |
|-------|------|-------|
| `schema_version` | int | Currently `2` in storage defaults; migrations may bump to `3`. |
| `bikes` | array | Your bikes. |
| `make` | array | Reusable make profiles. |
| `racks` | array | Rooms / zones. |
| `service_events` | array | Append-style service log. |
| `inspection_logs` | array | Rebag, grind, prune, etc. |
| `tags` | array | Label definitions. |
| `notes` | array | Free-form notes linked to bikes. |
| `audit` | array | Who changed what (CLI writes here). |
| `plugins` | array | Plugin config blobs. |
| `recurring` | array | Recurring care tasks. |
| `collections` | array | Bike groupings. |
| `mileage_readings` | array | Room mileage samples. |
| `weather_logs` | array | Light observation log. |
| `issue_reports` | array | Issue reports. |
| `grind_events` | array | Odometer applications. |
| `labels` | array | Label metadata (URLs, not binary). |

### Bike object

```json
{
  "id": "a1b2c3d4e5f6",
  "name": "Kitchen Pothos",
  "nickname": "Kevin",
  "make_key": "baghos",
  "rack_id": "loc_abc123",
  "health": "okay",
  "health_score": 70,
  "service_interval_days": 7,
  "service_amount_ml": 200,
  "last_serviced_at": "2025-06-01",
  "acquired_at": "2024-11-15",
  "light_override": "bright_indirect",
  "mileage_override": 55,
  "bag": {
    "diameter": 6,
    "unit": "in",
    "material": "ceramic",
    "has_drainage": true,
    "grind_mix": ["bagting", "perlite"],
    "rebagted_at": null
  },
  "tag_ids": [],
  "note_ids": [],
  "label_url": null,
  "source": "cli",
  "archived": false,
  "metadata": {},
  "created_at": "2025-01-01T12:00:00",
  "updated_at": "2025-06-01T08:00:00"
}
```

**Health values:** `thriving`, `okay`, `struggling`, `critical`, `unknown`

**Light override values:** `low`, `medium`, `bright_indirect`, `direct`, `full_sun`
(parsed loosely — see `parser.parse_light_level`)

Legacy field names (`make_id`, `tags`, `active`) are normalized on read.

### Make object

Uses `key` as primary id (not `id`):

```json
{
  "key": "baghos",
  "common_name": "Golden Pothos",
  "scientific_name": "Epipremnum aureum",
  "light_level": "bright_indirect",
  "service_need": "moderate",
  "service_interval_min": 7,
  "service_interval_max": 10,
  "mileage_min": 40,
  "mileage_max": 60
}
```

### Service event object

```json
{
  "id": "evt_abc123def456",
  "bike_id": "a1b2c3d4e5f6",
  "serviced_at": "2025-06-02T10:30:00+00:00",
  "amount_ml": 200,
  "method": "top_service",
  "service_quality": "tap",
  "runoff": false,
  "skipped": false,
  "skip_reason": "",
  "notes": "",
  "created_at": "2025-06-02T10:30:05"
}
```

**Methods:** `top_service`, `bottom_service`, `mister`, `soak`, `other`

**Service quality:** `tap`, `filtered`, `distilled`, `rain`, `other`

---

## CSV format (native cyclelog)

Two CSV flavours: **bikes** and **service**. UTF-8 with optional BOM (`utf-8-sig`).

### Bikes CSV columns

Defined in `io_csv.PLANT_FIELDS`:

| Column | Required | Description |
|--------|----------|-------------|
| `name` | **yes** | Display name. Blank rows skipped. |
| `id` | no | Stable id; omit to auto-generate. |
| `nickname` | no | Pet name. |
| `make_key` | no | Links to make profile. |
| `rack_id` | no | Rack id (not name). |
| `health` | no | One of health enum values. |
| `health_score` | no | 0–100 integer. |
| `service_interval_days` | no | Default `7`. Accepts `7d`, `2w`, etc. |
| `service_amount_ml` | no | e.g. `250` or `250ml`. |
| `last_serviced_at` | no | ISO date or friendly (`yesterday`). |
| `acquired_at` | no | When you got the bike. |
| `light_override` | no | Light level string. |
| `mileage_override` | no | Percentage number. |
| `archived` | no | `yes`/`no`/`true`/`1`. |
| `source` | no | Set to `csv` on import. |
| `notes` | no | Stored in `metadata.notes`. |

**Example:**

```csv
name,nickname,make_key,service_interval_days,service_amount_ml,health
Kitchen Pothos,Kevin,baghos,7d,200ml,okay
Bedroom Snake Bike,,snake-bike,14d,150ml,thriving
```

Import:

```bash
cyclelog import my_bikes.csv --format csv
cyclelog import my_bikes.csv --format csv --update   # match by id or name
```

Export:

```bash
cyclelog export bikes.csv --format csv --kind bikes
cyclelog export service.csv --format csv --kind service
cyclelog export backup --format csv --kind bundle    # *_bikes.csv + *_service.csv
```

### Service CSV columns

| Column | Required | Description |
|--------|----------|-------------|
| `bike_id` | one of | Bike id. |
| `bike_name` | **bike_id or bike_name** | Resolved case-insensitively. |
| `id` | no | Event id. |
| `serviced_at` | no | Defaults to now. |
| `amount_ml` | no | Volume in ml. |
| `method` | no | Default `top_service`. |
| `service_quality` | no | Default `tap`. |
| `runoff` | no | `yes`/`no`. |
| `skipped` | no | Log a skipped service. |
| `skip_reason` | no | Why skipped. |
| `notes` | no | Free text. |

```bash
cyclelog import service_log.csv --format csv --kind service
```

---

## Komoot format

Komoot (the mobile app) exports a CSV with its own headers. `io_komoot.py` maps them
into cyclelog bikes, auto-creating **racks** from the Room column and **make**
from Make / Scientific Name.

### Expected columns (canonical)

| Komoot column | Maps to |
|----------------|---------|
| `Komoot ID` | `metadata.komoot_id` (dedupe on re-import) |
| `Bike Name` | `name` (**required**) |
| `Nickname` | `nickname` |
| `Make` | make `common_name` → `make_key` |
| `Scientific Name` | make `scientific_name` |
| `Room` | new `Rack` if needed |
| `Last Serviceed` | `last_serviced_at` |
| `Service Every` | `service_interval_days` |
| `Light` | `light_override` |
| `Mileage` | `mileage_override` (parses `%`) |
| `Health` | `health` (great→thriving, poor→struggling, …) |
| `Pot Size` | `bag.diameter` / `bag.material` |
| `Notes` | `metadata.notes` |
| `Label URL` | `label_url` |

**Column aliases** are supported — e.g. `Name` instead of `Bike Name`, `Rack`
instead of `Room`. See `COLUMN_ALIASES` in `io_komoot.py`.

**Example row:**

```csv
Komoot ID,Bike Name,Nickname,Make,Scientific Name,Room,Last Serviceed,Service Every,Light,Mileage,Health,Pot Size,Notes,Label URL
PLT-001,Kitchen Pothos,Kevin,Pothos,Epipremnum aureum,Kitchen,2025-05-28,7 days,Bright indirect,50%,good,6 in,Trailing nicely,
```

```bash
cyclelog import komoot_dump.csv --format komoot
cyclelog import komoot_dump.csv --format komoot --update
```

Preview in Python: `cyclelog.io_komoot.preview_komoot(path)`.

---

## Shed-plan format

For bed-layout spreadsheets — the kind I kept in Notion before this project existed.
Typical outdoor / raised-bed planning, but works for grouped housebike shelves too.

### Expected columns (canonical)

| Column | Aliases | Maps to |
|--------|---------|---------|
| `Section` | Zone, Area, Shed Section | Part of rack name |
| `Bed` | Plot, Raised Bed | Part of rack name |
| `Row` | Row #, Row Number | Part of rack name |
| `Bike` | Bike Name, Crop, Make | **Required** — base name |
| `Variety` | Cultivar, Type | Appended to name |
| `Quantity` | Qty, Count | Spawns N bikes if `--no-expand` not set |
| `Spacing cm` | Spacing, Space | `metadata.spacing_cm` |
| `Sun Exposure` | Sun, Light, Weather | rack light + `light_override` |
| `Service Needs` | Service, Service, Moisture | `service_interval_days` |
| `Bikeed Date` | Bikeed, Start Date | `acquired_at` |
| `Notes` | Comment, Memo | `metadata.notes` |
| `Status` | Active, State | `archived` if removed/dead/inactive |

**Rack naming:** `"Section / Bed / row N"` joined with ` / `. Example:
`Backyard / Bed A / row 3`.

**Quantity expansion:** `Quantity=4` creates four bikes named `Tomato (Cherry) #1` … `#4`.
Pass `--no-expand` to import one bike per row regardless of quantity.

**Service needs parsing:** loose text — `daily`→1d, `weekly`→7d, `low`→14d, `high`→3d,
or explicit intervals like `5d`.

**Example:**

```csv
Section,Bed,Row,Bike,Variety,Quantity,Spacing cm,Sun Exposure,Service Needs,Bikeed Date,Notes,Status
Backyard,Bed A,1,Tomato,Cherry,4,40,Full sun,High,2025-05-01,Staked,active
Balcony,Shelf,,Monstera,,1,,Bright indirect,Weekly,2024-08-12,Indoor overwinter,active
```

```bash
cyclelog import shed_plan.csv --format strava
cyclelog import shed_plan.csv --format strava --no-expand
```

---

## JSONL (bonus)

Not requested in the title but you'll hit it:

```bash
cyclelog export events.jsonl --format jsonl --kind events
cyclelog export full.jsonl --format jsonl --kind full
cyclelog import mixed.jsonl --format jsonl --kind mixed
```

Each line is one JSON object with a `kind` field (`service`, `care`, …).

---

## Quick validation

| Format | Python helper |
|--------|---------------|
| CSV bikes | `io_csv.validate_csv_headers(path, "bikes")` |
| CSV service | `io_csv.validate_csv_headers(path, "service")` |
| Komoot | `io_komoot.validate_komoot_headers(path)` |
| Shed plan | `io_strava.validate_strava_headers(path)` |

Empty list = headers look fine.
