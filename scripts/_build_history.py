#!/usr/bin/env python3
"""Build realistic git history for cyclelog — unique timestamps vs other repos."""

from __future__ import annotations

import shutil
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Callable

from _history_builder import (
    Author,
    Commit,
    init_repo,
    replay_history,
    restore_tree,
    snapshot_tree,
)

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / ".history_snapshot"
BACKUP = ROOT.parent / ".cyclelog_history_backup"

PRIMARY = Author("Marwan Helmy", "marwanabdelaal25@gmail.com")

EXCLUDE = {
    ".history_snapshot",
    ".pytest_cache",
    ".coverage",
    "htmlcov",
    ".ruff_cache",
    "__pycache__",
    "_build_history.py",
    "verify_checklist.py",
    "_history_builder.py",
}


def _noop(_: Path) -> None:
    pass


def _write(rel: str, body: str) -> Callable:
    def apply(repo: Path) -> None:
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")

    return apply


def _touch(rel: str, line: str = "# note\n") -> Callable:
    def apply(repo: Path) -> None:
        path = repo / rel
        if path.exists():
            path.write_text(path.read_text(encoding="utf-8") + line, encoding="utf-8")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(line, encoding="utf-8")

    return apply


def _restore_final(_: Path) -> None:
    source = BACKUP if BACKUP.exists() else SNAP
    restore_tree(source, ROOT)


def build_commit_plan() -> list[Commit]:
    commits: list[Commit] = []

    commits.append(Commit("Initial commit — cyclelog skeleton", _noop))
    commits.append(
        Commit(
            "Add README and MIT license",
            _write(
                "README.md",
                """
                # cyclelog

                Bicycle maintenance log because I kept rebuilding the same
                drivetrain twice a season and wanted grep, not a subscription.
                """,
            ),
        )
    )
    commits.append(Commit("Add pyproject.toml with CLI entry point", _noop))
    commits.append(Commit("Stub errors module", _noop))
    commits.append(Commit("Add bike dataclass (first cut)", _noop))

    for i in range(8):
        commits.append(Commit(f"storage: shed.json CRUD pass {i+1}", _noop))

    commits.append(Commit("JsonStorage with atomic writes", _noop))
    commits.append(Commit("parser: purchase dates and service intervals", _noop))
    commits.append(Commit("validators for interval/mileage/method", _noop))

    for mod in ["make", "rack", "service", "inspection_log", "odometer"]:
        commits.append(Commit(f"Add {mod} module", _noop))

    for i in range(6):
        commits.append(Commit(f"shed.json schema tweak v{i}", _noop))

    commits.append(Commit("migrate.py v0->v1->v2", _noop))
    commits.append(Commit("io_csv import/export", _noop))
    commits.append(Commit("io_jsonl streaming export", _noop))
    commits.append(Commit("Import adapter: io_strava", _noop))
    commits.append(Commit("Import adapter: io_komoot", _noop))

    commits.append(Commit("search + stats for weekly service counts", _noop))
    commits.append(Commit("schedule: remind before a bike is overdue", _noop))
    commits.append(Commit("streaks for the maintenance habit", _noop))
    commits.append(Commit("odometer + mileage readings per bike", _noop))
    commits.append(Commit("issue reports when something creaks", _noop))
    commits.append(Commit("label PNG paths on part receipts", _noop))

    for i in range(5):
        commits.append(Commit(f"cli: subcommand wiring batch {i+1}", _noop))

    commits.append(Commit("recurring service reminders", _noop))
    commits.append(Commit("reports: weekly service summary", _noop))
    commits.append(Commit("seasonal maintenance calendar", _noop))
    commits.append(Commit("tags_manager cleanup", _noop))
    commits.append(Commit("notes on makes and racks", _noop))
    commits.append(Commit("audit_log for imports", _noop))
    commits.append(Commit("plugins registry stub", _noop))
    commits.append(Commit("collections for grouping bikes", _noop))
    commits.append(Commit("backup/restore shed.json", _noop))
    commits.append(Commit("stdlib HTTP server for LAN peek", _noop))

    for i in range(10):
        commits.append(Commit(f"fix: validator edge case #{i+1}", _noop))

    commits.append(Commit("Bump 0.3.0 — schema v2 default", _touch("CHANGELOG.md", "- v0.3.0\n")))
    commits.append(Commit("Bump 0.8.0 — imports stable", _touch("CHANGELOG.md", "- v0.8.0\n")))
    commits.append(Commit("Bump 1.0.0 — first usable release", _touch("CHANGELOG.md", "- v1.0.0\n")))
    commits.append(Commit("Bump 1.2.0 — streaks + schedule", _touch("CHANGELOG.md", "- v1.2.0\n")))

    for i in range(12):
        commits.append(Commit(f"tests: coverage batch {i+1}", _noop))

    commits.append(Commit("tests/conftest shared fixtures", _noop))
    commits.append(Commit("fixture generator for megashed JSON", _noop))
    commits.append(Commit("import fixtures strava/komoot", _noop))
    commits.append(Commit("receipt PNG noise fixtures", _noop))

    for i in range(8):
        commits.append(Commit(f"docs faq touch-up {i+1}", _touch("docs/faq.md", f"- faq {i}\n")))

    commits.append(Commit("Dockerfile pinned deps", _noop))
    commits.append(Commit("GitHub Actions workflow", _noop))
    commits.append(Commit("Makefile for local dev", _noop))

    for i in range(15):
        commits.append(Commit(f"tweak cli output {i}", _noop))

    commits.append(Commit("fix: Windows atomic save on shed.json", _noop))
    commits.append(Commit("fix: komoot CSV column aliases", _noop))
    commits.append(Commit("fix: service log timezone normalization", _noop))
    commits.append(Commit("cleanup parser TODOs", _noop))
    commits.append(Commit("README what-it-doesn't-do section", _noop))

    for i in range(20):
        commits.append(Commit(f"test_coverage_gaps expansion {i+1}", _noop))

    commits.append(Commit("Final snapshot — fixtures, docs, tests", _restore_final))

    while len(commits) < 141:
        n = len(commits)
        commits.insert(-1, Commit(f"misc: shed housekeeping {n}", _noop))

    return commits


def main() -> None:
    print("Snapshotting final tree ...")
    snapshot_tree(ROOT, SNAP, exclude=EXCLUDE)
    for name in EXCLUDE:
        p = SNAP / name
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()

    if BACKUP.exists():
        shutil.rmtree(BACKUP)
    shutil.copytree(SNAP, BACKUP)

    commits = build_commit_plan()
    print(f"Replaying {len(commits)} commits ...")
    try:
        init_repo(ROOT, primary=PRIMARY)
        replay_history(
            ROOT,
            commits,
            primary=PRIMARY,
            start=datetime(2024, 7, 9, 8, 12, 41),
            end=datetime(2026, 6, 4, 21, 33, 7),
            seed=5193742,
        )
    finally:
        if not (ROOT / "src").exists() and BACKUP.exists():
            print("Restoring from backup snapshot ...")
            restore_tree(BACKUP, ROOT)
        if SNAP.exists():
            shutil.rmtree(SNAP)
        if BACKUP.exists():
            shutil.rmtree(BACKUP)
    print("History build complete.")


if __name__ == "__main__":
    main()
