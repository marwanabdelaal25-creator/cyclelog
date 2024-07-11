# cyclelog

A bicycle maintenance + ride log I built because I kept rebuilding the
same drivetrain twice in a season, couldn't remember when I last bled the
brakes, and refused to pay for yet another app subscription just to know
my chain was due for a wax.

Everything lives in one JSON file (`shed.json`) on disk. Log services,
track mileage per bike, stash the brand/spec of each frame, and grep for
"bottom bracket" at 11pm in the garage without an internet connection.

## What it does

- Track bikes (road, gravel, MTB, the beater commuter) with purchase date,
  make/brand and which rack they hang on
- Log service events (drivetrain clean, brake bleed, cable replace, bearing
  service) with labour hours and parts cost
- Record odometer readings and watch mileage accumulate between services
- Inspection logs + issue reports when something creaks or shifts badly
- Weekly/seasonal service stats, streaks, and a maintenance calendar
- Import ride history from Strava and Komoot CSV exports
- Reminders before a bike is overdue for its next service

## What it doesn't do

- Live Strava/Garmin API sync. That needs OAuth trust I don't extend to a
  weekend side project. Export a CSV and import it.
- Power-meter analytics or training-load math. Use intervals.icu for that.
- Bike-shop multi-customer invoicing. This is my shed, not a POS.

## Quick start

```bash
pip install .
cyclelog init ~/cycling/shed.json
cyclelog add-bike "Allez Sprint" --make specialized --rack wall-a --interval 8w
cyclelog service "Allez Sprint" --method top_service --notes "new chain + cassette"
cyclelog reminders --within 21
cyclelog stats
```

## Author

Marwan Helmy — marwanabdelaal25@gmail.com

MIT licensed. Personal project, started summer 2024.
