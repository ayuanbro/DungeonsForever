"""Run with ``python -m data_pipeline.professions --help``."""
from __future__ import annotations

import argparse
import json
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
        action.add_argument("--retry-failed", action="store_true", help="With --resume, retry blocked/error/missing (including HTTP404) responses")
        action.add_argument("--refresh-web", action="store_true", help="With --resume, refresh every same-build web entity, including verified pages and historical404 gaps")
        action.add_argument("--web-interval", type=float, default=1.0, help="Global minimum seconds between entity requests")
        action.add_argument("--web-transport", choices=("auto", "browser", "browser-fetch"), default="auto",
                            help="auto: HTTP then JS-browser fallback; browser: native browser from the first request")
        action.add_argument("--host-recoveries", type=int, choices=range(4), default=2,
                            help="Bounded host cooldown/probe episodes; zero keeps stop-on-circuit behavior")
        action.add_argument("--host-cooldown", type=float, default=120,
                            help="Minimum cooldown seconds before a single recovery probe")
        action.add_argument("--browser-assets", choices=("all", "light"), default="all",
                            help="Experimental light mode blocks images/fonts/media but disables HTTP cache")
        action.add_argument("--retry-current-http", type=int, choices=(403, 429, 202),
                            help="With --resume, retry only current full-run sourceBlocked responses with this HTTP code")
    for name in ("build", "check"):
        action = sub.add_parser(name)
        action.add_argument("--raw", required=True, type=Path)
        action.add_argument("--output", required=True, type=Path)
        action.add_argument("--report", required=True, type=Path)
    for name in ("reparse", "reuse-verified"):
        offline = sub.add_parser(name, help="Offline raw-response processing; no network requests")
        offline.add_argument("--raw", required=True, type=Path)
        offline.add_argument("--report", required=True, type=Path)
    status = sub.add_parser("status", help="Read acquisition and reuse counters without networking")
    status.add_argument("--raw", required=True, type=Path)
    comparison = sub.add_parser("compare", help="Gated online transport comparison after a completed full collection (Linux)")
    comparison.add_argument("--after-raw", type=Path, required=True)
    comparison.add_argument("--out", type=Path, required=True)
    comparison.add_argument("--limit", type=int, default=12)
    comparison.add_argument("--interval", type=float, default=2.0)
    comparison.add_argument("--rounds", type=int, default=2)
    args = parser.parse_args(argv)
    try:
        if args.command in ("fetch", "probe"):
            if args.web_limit is not None and args.web_limit < 0:
                raise SourceError("web limit must be nonnegative")
            from .fetch import fetch
            fetch(args.out, web_limit=args.web_limit, workers=args.workers, retries=args.retries, resume=args.resume,
                  retry_failed=args.retry_failed, refresh_web=args.refresh_web, web_interval=args.web_interval,
                  web_transport=args.web_transport, retry_current_http=args.retry_current_http,
                  host_recoveries=args.host_recoveries, host_cooldown=args.host_cooldown,
                  browser_assets=args.browser_assets)
        elif args.command == "status":
            manifest = json.loads((args.raw / "manifest.json").read_text(encoding="utf-8"))
            fields = ("id", "mode", "targetCount", "newlyRequested", "attempted", "notAttempted", "reused",
                      "covered", "uncovered", "statuses", "reusedStatuses", "effectiveStatuses", "skippedReasons",
                      "requestCoverageComplete", "acquisitionCoverageComplete", "closedAt")
            print(json.dumps({"build": manifest["build"], "fetchComplete": manifest.get("fetchComplete"),
                              "webRun": {key: manifest.get("webRun", {}).get(key) for key in fields}}, ensure_ascii=False, indent=2))
        elif args.command == "reuse-verified":
            from .reuse import reuse_verified
            result = reuse_verified(args.raw, args.report)
            print(json.dumps(result['summary'], ensure_ascii=False))
        elif args.command == "reparse":
            from .reparse import reparse
            result = reparse(args.raw, args.report)
            print(f"reparsed changes={len(result['changes'])} remainingErrors={len(result['remainingErrors'])}")
        elif args.command == "compare":
            from .compare_transport import compare
            compare(args.after_raw, args.out, limit=args.limit, interval=args.interval, rounds=args.rounds)
        else:
            from .build import build
            build(args.raw, args.output, args.report, check=args.command == "check")
    except (OSError, SourceError, ValueError) as error:
        print(f"{args.command}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
