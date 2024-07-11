"""Allow `python -m cyclelog` invocation."""

from cyclelog.cli import main

__doc__ = """
Entry point for the cyclelog CLI.

Examples:
  python -m cyclelog init
  python -m cyclelog bike-add "Monstera" --make monstera-deliciosa
  python -m cyclelog service <bike-id> --amount 250ml
  python -m cyclelog schedule --week
  python -m cyclelog export shed.json

Environment:
  CYCLELOG_HOME  Directory for default shed.json (default: ~/.cyclelog/)
"""

if __name__ == "__main__":
    raise SystemExit(main())
