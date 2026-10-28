"""Run with ``python -m data_pipeline.professions --help``."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .model import SourceError


def main(argv=None):
    parser = argparse.ArgumentParser(description="Latest Forever learning-source pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("fetch", "probe"):
        action = sub.add_parser(name)
        action.add_argument("--out", required=True, type=Path)
        action.add_argument("--workers", type=int, default=2)
        action.add_argument("--retries", type=int, default=3)
        action.add_argument("--web-limit", type=int, default=8 if name == "probe" else None,
                            help="Explicit partial probe; unrequested entities remain notFetched gaps")
        action.add_argument("--resume", action="store_true", help="Resume only the same latest build, with checksums verified")
        action.add_argument("--retry-failed", action="store_true", help="With --resume, retry blocked/error responses in the same build")
        action.add_argument("--web-interval", type=float, default=1.0, help="Global minimum seconds between entity requests")
    for name in ("build", "check"):
        action = sub.add_parser(name)
        action.add_argument("--raw", required=True, type=Path)
        action.add_argument("--output", required=True, type=Path)
        action.add_argument("--report", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command in ("fetch", "probe"):
            if args.web_limit is not None and args.web_limit < 0:
                raise SourceError("web limit must be nonnegative")
            from .fetch import fetch
            fetch(args.out, web_limit=args.web_limit, workers=args.workers, retries=args.retries, resume=args.resume,
                  retry_failed=args.retry_failed, web_interval=args.web_interval)
        else:
            from .build import build
            build(args.raw, args.output, args.report, check=args.command == "check")
    except (OSError, SourceError, ValueError) as error:
        print(f"{args.command}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
