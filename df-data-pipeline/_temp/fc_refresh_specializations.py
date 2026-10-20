#!/usr/bin/env python3
"""Repeatable specialization update: collect, audit, then publish one output batch.

Existing client CSVs and DB2 snapshots are read-only inputs in every mode.
Online mode only refreshes independent web evidence; --offline replays page
caches. --apply publishes the derived trainer CSV, Lua, audits and state as one
batch. This module never runs a client exporter or starts a database service.
"""
import argparse
import csv
import io
from contextlib import nullcontext
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from fc_prof_items import DataError, PRICE_FIELDS
from fc_prof_specializations import alias, publish, ITEM_FIELDS as RECIPE_ITEM_FIELDS
from fc_recipe_item_audit import validated_tables
from fc_pipeline_paths import CSV_INPUTS
from fc_pipeline_common import (
    HERE, PACKAGE, REPO, fingerprint, publish_batch, require_repo_path, sha,
    update_lock,
)

LOCK_PATH = HERE / "_fc/cache/.pipeline-state/update.lock"
RUN_LOG_PATH = None


def stamp():
    return datetime.now(timezone.utc).isoformat()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


LOCAL_CHILDREN = frozenset(('fc_prof_specializations.py', 'fc_recipe_item_audit.py',
                            'fc_recipe_item_web_audit.py'))


def child(script, *arguments):
    if script not in LOCAL_CHILDREN:
        raise DataError('unsupported specialization step: %s' % script)
    command = [sys.executable, '-B', HERE / script, *arguments]
    display = subprocess.list2cmdline([str(arg) for arg in command])
    print('  ' + display, flush=True)
    environment = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
    with require_repo_path(RUN_LOG_PATH).open('a', encoding='utf-8') if RUN_LOG_PATH else nullcontext() as log:
        if log:
            log.write('\n' + display + '\n')
            log.flush()
        with subprocess.Popen([str(arg) for arg in command], cwd=REPO, env=environment,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              encoding='utf-8', errors='replace') as process:
            for line in process.stdout:
                print(line, end='', flush=True)
                if log:
                    log.write(line)
                    log.flush()
            code = process.wait()
    if code:
        raise DataError('%s failed (exit=%d)' % (script, code))


def collect_pages(cache_dir, refresh):
    from fc_specialization_fetch import collect_trainers
    return collect_trainers(cache_dir, refresh=refresh)


def freeze_files(paths, destination, replacements):
    """Copy a validated batch's inputs so later steps see identical bytes."""
    destination = require_repo_path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    observed = {}
    for path in sorted(paths):
        content = path.read_bytes()
        observed[path] = sha(content)
        copied = require_repo_path(destination / path.name)
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


def save_baseline(path, cache_root, inputs):
    if path is None or not path.exists():
        return None
    content = path.read_bytes()
    inputs.setdefault(path, sha(content))
    if inputs[path] != sha(content):
        raise DataError('comparison input changed during update: %s' % path)
    destination = require_repo_path(cache_root / "baselines" / (sha(content) + ".csv"))
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


def _state_csvs(state):
    version = state.get('schemaVersion')
    if version == 1:
        return state.get('outputs', {})
    if version == 2:
        return state.get('inputs', {})
    raise DataError('unsupported specialization state schema')


def select_snapshot(args, cache_root, inputs, expected):
    """Select an existing snapshot independently of web online/offline mode."""
    if args.db2_dir:
        directory = require_repo_path(args.db2_dir)
    else:
        state_path = require_repo_path(cache_root / 'current.json')
        if not state_path.is_file():
            raise DataError('an existing DB2 snapshot is required: supply --db2-dir or a validated current.json')
        content = state_path.read_bytes()
        if sha(content) != expected[state_path]:
            raise DataError('specialization state changed while selecting the snapshot')
        state = json.loads(content)
        recorded = _state_csvs(state)
        for name, path in inputs.items():
            if recorded.get(name, {}).get('sha256') != expected[path]:
                raise DataError('%s CSV differs from the selected source snapshot; supply the matching --db2-dir' % name)
        record = state.get('db2Snapshot', {})
        directory = require_repo_path(record.get('path', ''))
        if fingerprint(directory / 'manifest.json') != record.get('manifestSHA256'):
            raise DataError('DB2 snapshot manifest differs from the recorded source snapshot')
    if not directory.is_dir() or not (directory / 'manifest.json').is_file():
        raise DataError('DB2 snapshot is missing manifest.json: %s' % directory)
    return directory


def _client_rows(content, required, label):
    reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig'), newline=''))
    fields = reader.fieldnames or []
    if len(fields) != len(set(fields)) or not set(required).issubset(fields):
        raise DataError('%s CSV has duplicate or missing columns' % label)
    rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise DataError('%s CSV contains a malformed row' % label)
    return rows


def validate_client_snapshot(content, manifest, directory):
    """Bind raw Item bytes and derived CSV build/ID coverage to the snapshot."""
    item_record = manifest.get('tables', {}).get('item', {})
    if item_record.get('sha256') != sha(content['items']):
        raise DataError('Item CSV does not match the DB2 snapshot raw Item hash')
    items = _client_rows(content['items'], ('ID', 'ClassID', 'SubclassID'), 'items')
    prices = _client_rows(content['prices'], PRICE_FIELDS, 'prices')
    recipes = _client_rows(content['recipe_items'], RECIPE_ITEM_FIELDS, 'recipe_items')
    sparse_path = require_repo_path(directory / 'itemsparse.csv')
    sparse_record = manifest.get('tables', {}).get('itemsparse', {})
    if not sparse_path.is_file():
        raise DataError('DB2 snapshot is missing raw ItemSparse evidence')
    sparse_content = sparse_path.read_bytes()
    if sparse_record.get('sha256') != sha(sparse_content):
        raise DataError('DB2 ItemSparse hash does not match its source manifest')
    sparse = _client_rows(sparse_content, ('ID', 'Display_lang', 'BuyPrice', 'VendorStackCount',
                                         'RequiredAbility'), 'snapshot ItemSparse')
    sparse_by_id = {row['ID']: row for row in sparse}
    def identifier(row, field):
        value = row[field]
        if not re.fullmatch(r'[1-9][0-9]*', value):
            raise DataError('%s must be a positive integer' % field)
        return int(value)
    item_ids = [identifier(row, 'ID') for row in items]
    price_ids = [identifier(row, 'ItemID') for row in prices]
    if len(set(item_ids)) != len(item_ids) or len(set(price_ids)) != len(price_ids):
        raise DataError('client CSV contains duplicate item IDs')
    if set(item_ids) != set(price_ids):
        raise DataError('price CSV does not cover the same Item IDs as the DB2 snapshot')
    recipe_ids = {identifier(row, 'RecipeItemID') for row in recipes}
    if recipe_ids != {identifier(row, 'ID') for row in items if row['ClassID'] == '9'}:
        raise DataError('recipe CSV does not cover the snapshot recipe-item IDs')
    hotfix = str(manifest.get('hotfixBuild', manifest['build'].rsplit('.', 1)[1]))
    for label, rows in (('prices', prices), ('recipe_items', recipes)):
        if any(row['Build'] != manifest['build'] or row['HotfixBuild'] != hotfix for row in rows):
            raise DataError('%s CSV build or hotfix does not match the DB2 snapshot' % label)
    for row in prices:
        source = sparse_by_id.get(row['ItemID'])
        wanted = {'Name_enUS': '', 'BuyPriceCopper': '', 'VendorStackCount': '',
                  'PriceStatus': 'missing_item_sparse'}
        if source:
            amount = int(source['BuyPrice'])
            wanted = {'Name_enUS': source['Display_lang'], 'BuyPriceCopper': str(amount),
                      'VendorStackCount': str(int(source['VendorStackCount'])),
                      'PriceStatus': 'zero' if amount == 0 else 'priced'}
        if any(row[field] != value for field, value in wanted.items()):
            raise DataError('price CSV item %s differs from snapshot ItemSparse evidence' % row['ItemID'])
    for row in recipes:
        source = sparse_by_id.get(row['RecipeItemID'], {})
        if int(row['RequiredAbility'] or '0') != int(source.get('RequiredAbility', '0')):
            raise DataError('recipe CSV item %s has a different snapshot RequiredAbility' % row['RecipeItemID'])


def comparison_baseline(state_path, recipe_path, fallback, explicit, expected):
    """Retain the comparison from the last data change on identical replays."""
    if explicit or not state_path.exists():
        return fallback
    state = json.loads(state_path.read_bytes())
    if ("comparisonBaseline" not in state or
            _state_csvs(state).get("recipe_items", {}).get("sha256") != fingerprint(recipe_path)):
        return fallback
    previous = state["comparisonBaseline"]
    if previous is None:
        return None
    path = Path(previous["path"]).resolve()
    if fingerprint(path) != previous["sha256"]:
        raise DataError("saved comparison baseline is missing or changed")
    expected[path] = previous["sha256"]
    return path


def validate_write_paths(args):
    """Validate local inputs and every writable destination before web requests."""
    for name in ('cache_root', 'wowhead_cache_dir', 'prices_csv', 'item_csv',
                 'recipe_items_csv', 'trainer_csv', 'output_lua', 'audit_csv',
                 'audit_json', 'web_audit_json', 'data_dir', 'db2_dir', 'baseline_csv'):
        value = getattr(args, name, None)
        if value is not None:
            require_repo_path(value)
    require_repo_path(args.cache_root / 'current.json')


def prepare_batch(args, report):
    """Return derived output bytes and observed hashes; client CSVs stay read-only.

    Web caches and diagnostic logs may change. The caller owns the checkout
    lock and the single publication of trainer data, Lua, audits and state.
    """
    validate_write_paths(args)
    cache_root = require_repo_path(args.cache_root)
    data_dir = require_repo_path(args.data_dir)
    wowhead_cache = require_repo_path(args.wowhead_cache_dir or cache_root / 'wowhead-forever')
    inputs = {'prices': require_repo_path(args.prices_csv), 'items': require_repo_path(args.item_csv),
              'recipe_items': require_repo_path(args.recipe_items_csv)}
    outputs = {'trainers': require_repo_path(args.trainer_csv), 'lua': require_repo_path(args.output_lua),
               'audit_csv': require_repo_path(args.audit_csv), 'audit_json': require_repo_path(args.audit_json),
               'web_audit_json': require_repo_path(args.web_audit_json)}
    sources = sorted(data_dir.glob('prof_*.json'))
    if (data_dir / 'enchant_ids.json').exists():
        sources.append(data_dir / 'enchant_ids.json')
    if not sources:
        raise DataError('no profession catalog in %s' % data_dir)
    for name, path in inputs.items():
        if not path.is_file():
            raise DataError('missing read-only %s CSV: %s' % (name, path))
        if any(alias(path, other) for key, other in inputs.items() if key != name):
            raise DataError('client CSV inputs must be distinct')
    for index, destination in enumerate(outputs.values()):
        if destination.exists() and not destination.is_file():
            raise DataError('output is not a file: %s' % destination)
        if destination.is_relative_to(cache_root) or destination.is_relative_to(wowhead_cache):
            raise DataError('published output must be outside cache directories')
        if any(alias(destination, path) for path in list(outputs.values())[:index] + sources + list(inputs.values())):
            raise DataError('outputs must be distinct and must not overwrite read-only inputs')
    if args.offline and (args.refresh_trainers or args.refresh_catalog):
        raise DataError('offline mode cannot refresh network caches')
    if args.skip_catalog and args.refresh_catalog:
        raise DataError('--skip-catalog cannot be combined with --refresh-catalog')
    if args.baseline_csv and not args.baseline_csv.is_file():
        raise DataError('explicit --baseline-csv must be an existing file')
    if args.baseline_csv and any(alias(args.baseline_csv.resolve(), path) for path in outputs.values()):
        raise DataError('output must not overwrite an explicit comparison baseline')
    expected = {path: fingerprint(path) for path in list(outputs.values()) + list(inputs.values())}
    state_path = require_repo_path(cache_root / 'current.json')
    expected[state_path] = fingerprint(state_path)
    client_content = {name: path.read_bytes() for name, path in inputs.items()}
    if any(sha(client_content[name]) != expected[path] for name, path in inputs.items()):
        raise DataError('client CSV changed while freezing input bytes')
    db2 = select_snapshot(args, cache_root, inputs, expected)
    snapshot_hashes = {}
    _, _, manifest = checked_snapshot(db2, snapshot_hashes)
    if any(path.is_relative_to(db2) for path in outputs.values()) or any(
            alias(path, source) for path in outputs.values() for source in snapshot_hashes):
        raise DataError('output must not overwrite a DB2 snapshot')
    expected.update(snapshot_hashes)
    validate_client_snapshot(client_content, manifest, db2)
    if args.build and manifest['build'] != args.build:
        raise DataError('source snapshot does not match the requested --build')
    report['targetBuild'] = manifest['build']
    report['snapshotFormat'] = 'versioned' if 'schemaVersion' in manifest else 'legacy_hotfix_unverified'
    report['inputs'] = {name: {'path': str(path), 'sha256': expected[path]} for name, path in inputs.items()}
    baseline = save_baseline(args.baseline_csv.resolve() if args.baseline_csv else inputs['recipe_items'],
                             cache_root, expected)
    baseline = comparison_baseline(state_path, inputs['recipe_items'], baseline, bool(args.baseline_csv), expected)
    run_root = require_repo_path(cache_root / 'runs')
    run_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='stage-', dir=run_root) as temporary:
        stage = require_repo_path(temporary)
        staged = {name: require_repo_path(stage / name / path.name) for name, path in outputs.items()}
        frozen_csv = {name: require_repo_path(stage / 'inputs' / name / path.name) for name, path in inputs.items()}
        replacements = dict(getattr(args, 'provenance_paths', {}) or {})
        replacements.update({str(staged[name]): str(path) for name, path in outputs.items()})
        replacements.update({str(frozen_csv[name]): str(path) for name, path in inputs.items()})
        for path in list(staged.values()) + list(frozen_csv.values()):
            path.parent.mkdir(parents=True, exist_ok=True)
        for name, path in frozen_csv.items():
            path.write_bytes(client_content[name])
        catalog_dir = require_repo_path(stage / 'catalog')
        catalog_dir.mkdir()
        for path in sources:
            content = path.read_bytes()
            expected[path] = sha(content)
            require_repo_path(catalog_dir / path.name).write_bytes(content)
        if args.offline and outputs['trainers'].exists():
            staged['trainers'].write_bytes(outputs['trainers'].read_bytes())
        catalog = None
        if not args.skip_catalog:
            from fc_recipe_catalog_fetch import collect_catalog
            catalog = collect_catalog(cache_root / 'wuxianwow', offline=args.offline,
                                      refresh=args.refresh_catalog)
            report['catalogCacheState'] = catalog['cacheState']
            source_path = Path(catalog['path'])
            freeze_files([source_path, source_path.with_name('source.json')], stage / 'external-catalog', replacements)
            catalog = dict(catalog, path=str(stage / 'external-catalog' / source_path.name))
        if not args.offline:
            collected = collect_pages(wowhead_cache, args.refresh_trainers)
            report['webCollection'] = collected.get('coverage', {})
        frozen_pages = stage / 'wowhead'
        freeze_files(wowhead_cache.glob('*.json'), frozen_pages, replacements)
        child('fc_prof_specializations.py', '--recipe-items-csv', frozen_csv['recipe_items'],
              '--trainer-csv', staged['trainers'], '--output-lua', staged['lua'],
              '--data-dir', catalog_dir, '--cache-dir', frozen_pages,
              '--build', manifest['build'], '--offline')
        audit_flags = []
        if baseline:
            audit_flags += ['--baseline-csv', baseline, '--include-current-unmapped']
        if catalog:
            audit_flags += ['--recipe-catalog-json', catalog['path']]
        child('fc_recipe_item_audit.py', '--recipe-items-csv', frozen_csv['recipe_items'],
              '--item-csv', frozen_csv['items'], '--prices-csv', frozen_csv['prices'],
              '--db2-dir', db2, '--output-csv', staged['audit_csv'],
              '--summary-json', staged['audit_json'], *audit_flags)
        child('fc_recipe_item_web_audit.py', '--recipe-items-csv', frozen_csv['recipe_items'],
              '--db2-dir', db2, '--cache-dir', frozen_pages, '--output-json', staged['web_audit_json'])
        replacements[str(frozen_pages)] = str(wowhead_cache)
        replacements.update({str(catalog_dir / path.name): replacements.get(str(path), str(path)) for path in sources})
        content = {name: path.read_bytes() for name, path in staged.items()}
        for name in ('audit_json', 'web_audit_json'):
            content[name] = json_bytes(stable_paths(json.loads(content[name]), replacements))
        summary = json.loads(content['audit_json'])
        report['audit'] = {key: summary[key] for key in (
            'items', 'mappingResolved', 'stillUnmapped', 'stillUnmappedClassifications')}
        state = {'schemaVersion': 2, 'targetBuild': manifest['build'],
                 'hotfixBuild': manifest.get('hotfixBuild'), 'inputs': report['inputs'],
                 'comparisonBaseline': {'path': str(baseline), 'sha256': fingerprint(baseline)} if baseline else None,
                 'db2Snapshot': {'path': str(db2), 'manifestSHA256': fingerprint(db2 / 'manifest.json'),
                                 'contentKey': snapshot_identity(manifest)},
                 'outputs': {name: {'path': str(path), 'sha256': sha(content[name])} for name, path in outputs.items()}}
        report['changedOutputs'] = [name for name, path in outputs.items() if expected[path] != sha(content[name])]
        report['outputs'] = state['outputs']
        ensure_unchanged(expected)
        batch = {outputs[name]: content[name] for name in outputs}
        batch[state_path] = json_bytes(state)
        report['status'] = 'prepared'
        return batch, expected


def execute(args, report):
    batch, expected = prepare_batch(args, report)
    if args.apply:
        publish_batch(batch, expected)
        report["status"] = "updated" if report["changedOutputs"] else "unchanged"
    else:
        report["status"] = "checked"


def parse_args(argv=None):
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
    parser.add_argument("--db2-dir", type=Path, help="existing DB2 source snapshot for online or offline audit")
    parser.add_argument("--baseline-csv", type=Path, help="default: previous published recipe item CSV")
    defaults = {
        "prices-csv": CSV_INPUTS["prices_csv"],
        "item-csv": CSV_INPUTS["item_csv"],
        "recipe-items-csv": CSV_INPUTS["recipe_items_csv"],
        "trainer-csv": HERE / "_fc/data/trainer-recipe-specializations.csv",
        "output-lua": PACKAGE / "Core/Data/Data_ProfSpecializations.lua",
        "audit-csv": HERE / "_fc/data/recipe-item-link-audit.csv",
        "audit-json": HERE / "_fc/data/recipe-item-link-audit-summary.json",
        "web-audit-json": HERE / "_fc/data/recipe-item-web-link-audit.json",
    }
    for option, default in defaults.items():
        parser.add_argument("--" + option, type=Path, default=default)
    return parser.parse_args(argv)


def main(argv=None):
    global RUN_LOG_PATH
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    report = {"schemaVersion": 1, "startedAt": stamp(), "mode": "apply" if args.apply else "check",
              "offline": args.offline, "status": "failed"}
    try:
        validate_write_paths(args)
        with update_lock(LOCK_PATH):
            run_root = require_repo_path(args.cache_root.resolve() / "runs")
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
