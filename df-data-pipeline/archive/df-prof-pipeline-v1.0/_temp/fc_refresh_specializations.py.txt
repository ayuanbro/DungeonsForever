#!/usr/bin/env python3
"""Repeatable specialization update: collect, audit, then publish one output batch.

Defaults to checking. --apply publishes; --offline replays the last successful
snapshot. Network page caches and immutable DB2 snapshots can accumulate on a
failed/check run, while published CSV/Lua/audit files retain the previous batch.
"""
import argparse
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from fc_prof_items import DataError
from fc_prof_specializations import alias, publish
from fc_recipe_item_audit import validated_tables

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
REPO = PACKAGE.parent
LOCK_PATH = HERE / "_fc/cache/specializations/.update-state/update.lock"
RUN_LOG_PATH = None


def stamp():
    return datetime.now(timezone.utc).isoformat()


def sha(content):
    return hashlib.sha256(content).hexdigest()


def fingerprint(path):
    return sha(path.read_bytes()) if path.is_file() else None


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


@contextmanager
def update_lock():
    """One updater per checkout, even when callers choose different cache roots."""
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("a+b") as stream:
        stream.seek(0, os.SEEK_END)
        if not stream.tell():
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise DataError("another specialization update is running") from error
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def run_command(command):
    display = subprocess.list2cmdline([str(arg) for arg in command])
    print("  " + display, flush=True)
    environment = dict(os.environ, PYTHONIOENCODING="utf-8")
    with RUN_LOG_PATH.open("a", encoding="utf-8") if RUN_LOG_PATH else nullcontext() as log:
        if log:
            log.write("\n" + display + "\n")
            log.flush()
        with subprocess.Popen([str(arg) for arg in command], cwd=REPO, env=environment,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              encoding="utf-8", errors="replace") as process:
            for line in process.stdout:
                print(line, end="", flush=True)
                if log:
                    log.write(line)
                    log.flush()
            code = process.wait()
    if code:
        raise DataError("%s failed (exit=%d)" % (Path(command[0]).name, code))


def child(script, *arguments):
    run_command([sys.executable, HERE / script, *arguments])


def collect_pages(cache_dir, refresh):
    from fc_specialization_fetch import collect_trainers
    return collect_trainers(cache_dir, refresh=refresh)


def freeze_files(paths, destination, replacements):
    """Copy a validated batch's inputs so later steps see identical bytes."""
    destination.mkdir(parents=True, exist_ok=True)
    observed = {}
    for path in sorted(paths):
        content = path.read_bytes()
        observed[path] = sha(content)
        copied = destination / path.name
        copied.write_bytes(content)
        replacements[str(copied)] = str(path)
    ensure_unchanged(observed)


def snapshot_identity(manifest):
    # Fetch timestamps do not create duplicate copies of identical DB2 content.
    return sha(json_bytes({
        "build": manifest["build"], "hotfixBuild": manifest.get("hotfixBuild"),
        "hotfixSHA256": manifest.get("hotfixSHA256"),
        "tables": {name: {"sha256": row["sha256"], "rows": row["rows"]}
                   for name, row in manifest["tables"].items()},
    }))


def checked_snapshot(directory, snapshots):
    build, tables, manifest = validated_tables(directory, snapshots)
    if "schemaVersion" in manifest:
        if (manifest["schemaVersion"] != 1 or
                str(manifest.get("hotfixBuild")) != build.rsplit(".", 1)[1] or
                manifest.get("useHotfixes") is not True or
                not re.fullmatch(r"[a-fA-F0-9]{64}", str(manifest.get("hotfixSHA256", "")))):
            raise DataError("DB2 snapshot has inconsistent or missing hotfix identity")
    return build, tables, manifest


def archive_snapshot(source, cache_root):
    if not source.resolve().is_relative_to((cache_root / "runs").resolve()):
        raise DataError("only an owned staging snapshot may be archived")
    _, _, manifest = checked_snapshot(source, {})
    identity = snapshot_identity(manifest)
    destination = cache_root / "db2" / manifest["build"] / identity
    if destination.exists():
        _, _, existing = checked_snapshot(destination, {})
        if snapshot_identity(existing) != identity:
            raise DataError("existing DB2 snapshot has a different identity")
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Both directories are on the configured cache filesystem. This is an
        # immutable cache publication, independent of final CSV/Lua publication.
        source.rename(destination)
    return destination, identity


def save_baseline(path, cache_root, inputs):
    if path is None or not path.exists():
        return None
    content = path.read_bytes()
    inputs[path] = sha(content)
    destination = cache_root / "baselines" / (sha(content) + ".csv")
    if destination.exists():
        if destination.read_bytes() != content:
            raise DataError("baseline cache content hash mismatch")
    else:
        publish({destination: content})
    inputs[destination] = sha(content)
    return destination


def stable_paths(value, replacements):
    """Keep provenance paths stable after private staging files are removed."""
    if isinstance(value, dict):
        return {key: stable_paths(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [stable_paths(item, replacements) for item in value]
    if isinstance(value, str):
        return replacements.get(value, value)
    return value


def ensure_unchanged(expected):
    for path, digest in expected.items():
        if fingerprint(path) != digest:
            raise DataError("file changed during update: %s" % path)


def offline_snapshot(args, cache_root, outputs):
    if args.db2_dir:
        directory = args.db2_dir.resolve()
        checked_snapshot(directory, {})
        return directory
    state_path = cache_root / "current.json"
    if not state_path.exists():
        raise DataError("offline update needs a successful online --apply first, or explicit --db2-dir")
    state = json.loads(state_path.read_bytes())
    if state.get("schemaVersion") != 1:
        raise DataError("unsupported update state schema")
    for name in ("prices", "items", "recipe_items"):
        expected = state["outputs"][name]
        if fingerprint(outputs[name]) != expected["sha256"]:
            raise DataError("offline %s differs from the published snapshot; refresh online or supply --db2-dir" % name)
    directory = Path(state["db2Snapshot"]["path"]).resolve()
    if fingerprint(directory / "manifest.json") != state["db2Snapshot"]["manifestSHA256"]:
        raise DataError("offline snapshot manifest differs from published state")
    checked_snapshot(directory, {})
    return directory


def comparison_baseline(state_path, recipe_path, fallback, explicit, expected):
    """Retain the comparison from the last data change on identical replays."""
    if explicit or not state_path.exists():
        return fallback
    state = json.loads(state_path.read_bytes())
    if (state.get("schemaVersion") != 1 or "comparisonBaseline" not in state or
            state.get("outputs", {}).get("recipe_items", {}).get("sha256") != fingerprint(recipe_path)):
        return fallback
    previous = state["comparisonBaseline"]
    if previous is None:
        return None
    path = Path(previous["path"]).resolve()
    if fingerprint(path) != previous["sha256"]:
        raise DataError("saved comparison baseline is missing or changed")
    expected[path] = previous["sha256"]
    return path


def execute(args, report):
    cache_root = args.cache_root.resolve()
    data_dir = args.data_dir.resolve()
    wowhead_cache = (args.wowhead_cache_dir or cache_root / "wowhead-forever").resolve()
    outputs = {
        "prices": args.prices_csv.resolve(), "items": args.item_csv.resolve(),
        "recipe_items": args.recipe_items_csv.resolve(), "trainers": args.trainer_csv.resolve(),
        "lua": args.output_lua.resolve(), "audit_csv": args.audit_csv.resolve(),
        "audit_json": args.audit_json.resolve(), "web_audit_json": args.web_audit_json.resolve(),
    }
    sources = sorted(data_dir.glob("prof_*.json"))
    if (data_dir / "enchant_ids.json").exists():
        sources.append(data_dir / "enchant_ids.json")
    if not sources:
        raise DataError("no profession catalog in %s" % data_dir)
    for index, destination in enumerate(outputs.values()):
        if destination.exists() and not destination.is_file():
            raise DataError("output is not a file: %s" % destination)
        if destination.is_relative_to(cache_root) or destination.is_relative_to(wowhead_cache):
            raise DataError("published output must be outside cache directories")
        if any(alias(destination, path) for path in list(outputs.values())[:index] + sources):
            raise DataError("output paths must be distinct and must not overwrite source catalogs")
    if args.offline and (args.refresh_trainers or args.refresh_catalog):
        raise DataError("offline mode cannot refresh network caches")
    if not args.offline and args.db2_dir:
        raise DataError("--db2-dir is an offline override; online runs export a fresh DB2 snapshot")
    if args.skip_catalog and args.refresh_catalog:
        raise DataError("--skip-catalog cannot be combined with --refresh-catalog")
    if args.baseline_csv and not args.baseline_csv.is_file():
        raise DataError("explicit --baseline-csv must be an existing file")
    if args.baseline_csv and any(
            alias(args.baseline_csv.resolve(), path) for name, path in outputs.items()
            if name != "recipe_items"):
        raise DataError("output must not overwrite an explicit comparison baseline")
    expected = {path: fingerprint(path) for path in outputs.values()}
    state_path = cache_root / "current.json"
    expected[state_path] = fingerprint(state_path)
    baseline = save_baseline((args.baseline_csv.resolve() if args.baseline_csv else outputs["recipe_items"]),
                             cache_root, expected)
    run_root = cache_root / "runs"
    run_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="stage-", dir=run_root) as temporary:
        stage = Path(temporary).resolve()
        if not stage.is_relative_to(run_root.resolve()):
            raise DataError("staging directory escaped the configured run directory")
        staged = {name: stage / name / path.name for name, path in outputs.items()}
        replacements = {str(staged[name]): str(path) for name, path in outputs.items()}
        for path in staged.values():
            path.parent.mkdir(parents=True, exist_ok=True)
        catalog_dir = stage / "catalog"
        catalog_dir.mkdir()
        for path in sources:
            content = path.read_bytes()
            expected[path] = sha(content)
            (catalog_dir / path.name).write_bytes(content)
        if args.offline:
            db2 = offline_snapshot(args, cache_root, outputs)
            for name in ("prices", "items", "recipe_items"):
                staged[name].write_bytes(outputs[name].read_bytes())
        else:
            exporter = REPO / "scripts/export_buyprice/export-item-buy-prices.ps1"
            command = [args.powershell, "-NoProfile", "-ExecutionPolicy", "Bypass",
                       "-File", exporter, "-OutputPath", staged["prices"],
                       "-ItemOutputPath", staged["items"], "-RecipeItemOutputPath", staged["recipe_items"],
                       "-LearningSnapshotPath", stage / "db2", "-BaseUrl", args.base_url]
            if args.tool_directory:
                command.extend(["-ToolDirectory", args.tool_directory.resolve()])
            run_command(command)
            db2, _ = archive_snapshot(stage / "db2", cache_root)
        if any(path.is_relative_to(db2) for path in outputs.values()):
            raise DataError("output must not overwrite a DB2 snapshot")
        snapshot_hashes = {}
        _, _, manifest = checked_snapshot(db2, snapshot_hashes)
        if any(alias(path, source) for path in outputs.values() for source in snapshot_hashes):
            raise DataError("output must not alias a DB2 snapshot file")
        expected.update(snapshot_hashes)
        if args.build and manifest["build"] != args.build:
            raise DataError("exported snapshot does not match the requested --build")
        report["targetBuild"] = manifest["build"]
        report["snapshotFormat"] = "versioned" if "schemaVersion" in manifest else "legacy_hotfix_unverified"
        baseline = comparison_baseline(state_path, staged["recipe_items"], baseline,
                                       bool(args.baseline_csv), expected)
        if args.offline and outputs["trainers"].exists():
            staged["trainers"].write_bytes(outputs["trainers"].read_bytes())
        catalog = None
        if not args.skip_catalog:
            from fc_recipe_catalog_fetch import collect_catalog
            catalog = collect_catalog(cache_root / "wuxianwow", offline=args.offline,
                                      refresh=args.refresh_catalog)
            report["catalogCacheState"] = catalog["cacheState"]
            source_path = Path(catalog["path"])
            freeze_files([source_path, source_path.with_name("source.json")], stage / "external-catalog",
                         replacements)
            catalog = dict(catalog, path=str(stage / "external-catalog" / source_path.name))
        if not args.offline:
            collected = collect_pages(wowhead_cache, args.refresh_trainers)
            report["webCollection"] = collected.get("coverage", {})
        frozen_pages = stage / "wowhead"
        freeze_files(wowhead_cache.glob("*.json"), frozen_pages, replacements)
        # Online collection has already succeeded. An empty staged trainer CSV
        # makes this a fresh snapshot, while offline runs merge previous evidence.
        child("fc_prof_specializations.py", "--recipe-items-csv", staged["recipe_items"],
              "--trainer-csv", staged["trainers"], "--output-lua", staged["lua"],
              "--data-dir", catalog_dir, "--cache-dir", frozen_pages,
              "--build", manifest["build"], "--offline")
        audit_flags = []
        if baseline:
            audit_flags += ["--baseline-csv", baseline, "--include-current-unmapped"]
        if catalog:
            audit_flags += ["--recipe-catalog-json", catalog["path"]]
        child("fc_recipe_item_audit.py", "--recipe-items-csv", staged["recipe_items"],
              "--item-csv", staged["items"], "--prices-csv", staged["prices"],
              "--db2-dir", db2, "--output-csv", staged["audit_csv"],
              "--summary-json", staged["audit_json"], *audit_flags)
        child("fc_recipe_item_web_audit.py", "--recipe-items-csv", staged["recipe_items"],
              "--db2-dir", db2, "--cache-dir", frozen_pages,
              "--output-json", staged["web_audit_json"])
        replacements[str(frozen_pages)] = str(wowhead_cache)
        replacements.update({str(catalog_dir / path.name): str(path) for path in sources})
        content = {name: path.read_bytes() for name, path in staged.items()}
        for name in ("audit_json", "web_audit_json"):
            content[name] = json_bytes(stable_paths(json.loads(content[name]), replacements))
        summary = json.loads(content["audit_json"])
        report["audit"] = {key: summary[key] for key in (
            "items", "mappingResolved", "stillUnmapped", "stillUnmappedClassifications")}
        state = {
            "schemaVersion": 1, "targetBuild": manifest["build"],
            "hotfixBuild": manifest.get("hotfixBuild"),
            "comparisonBaseline": {"path": str(baseline), "sha256": fingerprint(baseline)}
            if baseline else None,
            "db2Snapshot": {"path": str(db2), "manifestSHA256": fingerprint(db2 / "manifest.json"),
                            "contentKey": snapshot_identity(manifest)},
            "outputs": {name: {"path": str(path), "sha256": sha(content[name])}
                        for name, path in outputs.items()},
        }
        changes = {name: path for name, path in outputs.items() if expected[path] != sha(content[name])}
        report["changedOutputs"] = list(changes)
        report["outputs"] = state["outputs"]
        ensure_unchanged(expected)
        if args.apply:
            batch = {outputs[name]: content[name] for name in changes}
            state_content = json_bytes(state)
            if fingerprint(state_path) != sha(state_content):
                batch[state_path] = state_content
            if batch:
                publish(batch)
            report["status"] = "updated" if changes else "unchanged"
        else:
            report["status"] = "checked"


def main(argv=None):
    global RUN_LOG_PATH
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--check", "--dry-run", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--refresh-trainers", action="store_true")
    parser.add_argument("--refresh-catalog", action="store_true")
    parser.add_argument("--skip-catalog", action="store_true", help="omit the optional wuxianwow comparison")
    parser.add_argument("--cache-root", type=Path, default=HERE / "_fc/cache/specializations")
    parser.add_argument("--wowhead-cache-dir", type=Path)
    parser.add_argument("--data-dir", type=Path, default=HERE / "_fc/data")
    parser.add_argument("--build", help="require this exact target build; never relabel source evidence")
    parser.add_argument("--db2-dir", type=Path, help="explicit existing DB2 snapshot for offline replay")
    parser.add_argument("--baseline-csv", type=Path, help="default: previous published recipe item CSV")
    parser.add_argument("--tool-directory", type=Path)
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--powershell", default="powershell.exe")
    defaults = {
        "prices-csv": REPO / "scripts/export_buyprice/output/item-buy-prices.csv",
        "item-csv": REPO / "scripts/export_buyprice/output/item.csv",
        "recipe-items-csv": REPO / "scripts/export_buyprice/output/recipe-item-specializations.csv",
        "trainer-csv": HERE / "_fc/data/trainer-recipe-specializations.csv",
        "output-lua": PACKAGE / "Core/Data/Data_ProfSpecializations.lua",
        "audit-csv": HERE / "_fc/data/recipe-item-link-audit.csv",
        "audit-json": HERE / "_fc/data/recipe-item-link-audit-summary.json",
        "web-audit-json": HERE / "_fc/data/recipe-item-web-link-audit.json",
    }
    for option, default in defaults.items():
        parser.add_argument("--" + option, type=Path, default=default)
    args = parser.parse_args(argv)
    report = {"schemaVersion": 1, "startedAt": stamp(), "mode": "apply" if args.apply else "check",
              "offline": args.offline, "status": "failed"}
    try:
        with update_lock():
            run_root = args.cache_root.resolve() / "runs"
            run_root.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(prefix="update-", suffix=".log", dir=run_root,
                                             delete=False) as log:
                RUN_LOG_PATH = Path(log.name)
            report["logPath"] = str(RUN_LOG_PATH)
            try:
                execute(args, report)
            except Exception as error:
                report["error"] = str(error)
                raise
            finally:
                report["finishedAt"] = stamp()
                # Diagnostic state is a cache artifact, never the commit marker.
                report_path = args.cache_root.resolve() / "runs/last-run.json"
                try:
                    publish({report_path: json_bytes(report)})
                except Exception as error:
                    print("could not save run report: %s" % error, file=sys.stderr)
                RUN_LOG_PATH = None
        print("[%s] %s" % (report["status"].upper(), json.dumps(report.get("audit", {}), ensure_ascii=False)))
        print("  changed outputs: %s" % (", ".join(report["changedOutputs"]) or "none"))
        return 0
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print("fc_refresh_specializations: %s" % error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
