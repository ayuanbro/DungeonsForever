#!/usr/bin/env python3
"""Archived entrypoint; execution intentionally disabled."""
import sys
from pathlib import Path

def main(argv=None):
    target = Path(__file__).resolve().parents[2] / "df-data-pipeline/_temp/fc_update.py"
    print("This pipeline is archived and disabled. Use: python -B \"%s\" --check --offline" % target, file=sys.stderr)
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
