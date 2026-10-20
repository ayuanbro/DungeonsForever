"""Prepare, validate and publish the complete profession batch inside this checkout."""
import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid
import fc_pipeline_common as common
from fc_pipeline_paths import CSV_INPUTS

HERE, PACKAGE, REPO = common.HERE, common.PACKAGE, common.REPO
BASE_FILES = tuple('Data_%s.lua' % n for n in (
    'Professions', 'ProfRecipes', 'ProfLeveling', 'ProfGathering', 'ProfVendors', 'ProfTrainers'))
SHARED_FILES = ('Data_ProfItems.lua', 'Data_ProfSpecializations.lua')
DATA_DIR, OFFICIAL = HERE / '_fc/data', REPO / 'Core/Data'


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--check', '--dry-run', action='store_true', help='check without publishing (default)')
    mode.add_argument('--apply', action='store_true', help='publish to official Core/Data as one batch')
    p.add_argument('--offline', action='store_true', help='replay caches without network access')
    p.add_argument('--stage-dir', type=Path, help='retain a validated preview batch inside the repository')
    p.add_argument('--package-zip', type=Path, help='build an installation ZIP from the validated preview without publishing')
    scope = p.add_mutually_exclusive_group()
    scope.add_argument('--specializations-only', action='store_true')
    scope.add_argument('--from-csv', type=Path, help='rebuild only items Lua from a 19-column CSV')
    for option, default in {
        'data-dir': DATA_DIR, 'cache-dir': HERE / '_fc/cache', 'i18n-dir': HERE / '_fc/i18n',
        'maintenance': HERE / '_fc/maintenance/professions.json',
        **{key.replace('_', '-'): value for key, value in CSV_INPUTS.items()},
        'trainer-csv': DATA_DIR / 'trainer-recipe-specializations.csv',
        'output-csv': DATA_DIR / 'DataProfItems.csv', 'items-lua': OFFICIAL / SHARED_FILES[0],
        'specialization-output-lua': OFFICIAL / SHARED_FILES[1],
        'specialization-cache-root': HERE / '_fc/cache/specializations',
    }.items():
        p.add_argument('--' + option, type=Path, default=default)
    for option in ('specialization-data-dir', 'specialization-cache-dir', 'db2-dir', 'baseline-csv'):
        p.add_argument('--' + option, type=Path)
    p.add_argument('--specialization-build')
    p.add_argument('--verified-at', default='')
    for option in ('refresh-trainers', 'refresh-catalog', 'skip-recipe-catalog'):
        p.add_argument('--' + option, action='store_true')
    return p


def preflight(args):
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, common.require_repo_path(value))
    common.require_repo_path(OFFICIAL)
    common.require_repo_path(HERE)
    kinds = {'trainer_csv': '.csv', 'output_csv': '.csv', 'items_lua': '.lua',
             'specialization_output_lua': '.lua'}
    if args.from_csv:
        kinds = {'items_lua': '.lua'}
    elif args.specializations_only:
        kinds = {key: value for key, value in kinds.items() if key not in ('output_csv', 'items_lua')}
    source_keys = ('from_csv',) if args.from_csv else ('prices_csv', 'item_csv', 'recipe_items_csv')
    if not (args.from_csv or args.specializations_only):
        source_keys += ('vendors_csv', 'npcs_csv')
    sources = [getattr(args, key) for key in source_keys]
    for source in sources:
        if source.suffix.lower() != '.csv' or not source.is_file():
            raise common.PipelineError('CSV input is missing or not a CSV: %s' % source)
    destinations = []
    for key, suffix in kinds.items():
        path = getattr(args, key)
        if path.suffix.lower() != suffix:
            raise common.PipelineError('%s must end in %s' % (key, suffix))
        role = {'items_lua': SHARED_FILES[0], 'specialization_output_lua': SHARED_FILES[1]}.get(key)
        if path.is_relative_to(OFFICIAL) and path != OFFICIAL / (role or '__not_owned__'):
            raise common.PipelineError('output belongs to another official dataset: %s' % path)
        if path.is_relative_to(PACKAGE / 'Core/Data') and path.name != role:
            raise common.PipelineError('output belongs to another sample dataset: %s' % path)
        if path.is_relative_to(args.cache_dir) or path.is_relative_to(args.specialization_cache_root):
            raise common.PipelineError('final data output cannot overwrite cache/state: %s' % path)
        if path.is_relative_to(HERE / '_fc/maintenance'):
            raise common.PipelineError('output cannot overwrite maintenance inputs: %s' % path)
        protected = (REPO / 'Core', REPO / 'Locales', REPO / 'Libs', REPO / 'Media', REPO / 'tests',
                     REPO / 'df-prof-pipeline-v1.0')
        if any(path.is_relative_to(root) for root in protected) and path not in (OFFICIAL / SHARED_FILES[0], OFFICIAL / SHARED_FILES[1]):
            raise common.PipelineError('output would overwrite a non-owned runtime or archived file: %s' % path)
        if path.is_relative_to(PACKAGE) and not (path.is_relative_to(HERE / '_fc/data') or path.is_relative_to(PACKAGE / 'Core/Data')):
            raise common.PipelineError('output would overwrite a pipeline input or implementation: %s' % path)
        if path.is_relative_to(OFFICIAL) and path not in (OFFICIAL / SHARED_FILES[0], OFFICIAL / SHARED_FILES[1]):
            raise common.PipelineError('custom output would overwrite another official dataset: %s' % path)
        for other in destinations:
            if path == other or (path.exists() and other.exists() and os.path.samefile(path, other)):
                raise common.PipelineError('final data outputs must be distinct: %s' % path)
        destinations.append(path)
    for source in (*sources, args.maintenance):
        if source in destinations:
            raise common.PipelineError('output would overwrite an input: %s' % source)
    if args.apply and (args.stage_dir or args.package_zip):
        raise common.PipelineError('preview staging and packaging require check mode without --apply')
    if args.package_zip and (args.from_csv or args.specializations_only):
        raise common.PipelineError('installation packaging requires a complete profession check')
    for artifact in (args.stage_dir, args.package_zip):
        if artifact is None:
            continue
        allowed = (REPO / '.pipeline-runtime', REPO / 'dist', HERE / '_fc/reports')
        if not any(artifact.is_relative_to(directory) and artifact != directory for directory in allowed):
            raise common.PipelineError('preview artifacts must be under .pipeline-runtime, dist or _fc/reports')
        if artifact.exists():
            raise common.PipelineError('preview artifact already exists; choose a new destination: %s' % artifact)
    if args.package_zip and args.package_zip.suffix.lower() != '.zip':
        raise common.PipelineError('--package-zip must end in .zip')
    if args.stage_dir and args.package_zip and args.package_zip.is_relative_to(args.stage_dir):
        raise common.PipelineError('ZIP output must be separate from the retained preview directory')
    if not args.specializations_only and not args.from_csv:
        if args.items_lua != OFFICIAL / SHARED_FILES[0] or args.specialization_output_lua != OFFICIAL / SHARED_FILES[1]:
            raise common.PipelineError('full update must publish shared Lua to official Core/Data')
    common.lua_runtime()
    if not args.specializations_only and not args.from_csv:
        try:
            from opencc import OpenCC
            OpenCC('s2t')
        except ImportError as error:
            raise common.PipelineError('zhTW generation requires OpenCC in .pipeline-runtime/lib') from error


def watched_files(args):
    files = set()
    for directory, pattern in ((REPO / 'Core', '*.lua'), (REPO / 'Locales', '*.lua'),
                               (args.data_dir, '*'), (args.i18n_dir, '*'), (HERE / '_fc/maintenance', '*'),
                               (HERE / '_fc/inputs', '*')):
        if directory.exists():
            files.update(p for p in directory.rglob(pattern) if p.is_file())
    files.update(p for p in HERE.glob('*.py') if p.is_file())
    for directory in (HERE / 'tools', HERE / 'questie'):
        files.update(p for p in directory.glob('*') if p.is_file())
    for path in (HERE / '_wago_AreaTable_zh.csv', REPO / 'DungeonsForever.toc', args.maintenance):
        if path.is_file():
            files.add(path)
    for key in ('vendors_csv', 'npcs_csv', 'prices_csv', 'item_csv', 'recipe_items_csv',
                'trainer_csv', 'from_csv', 'baseline_csv'):
        path = getattr(args, key, None)
        if path and path.is_file():
            files.add(path)
    observed = {path: common.fingerprint(path) for path in files}
    targets = [OFFICIAL / name for name in BASE_FILES + SHARED_FILES]
    targets += [OFFICIAL / locale / name for locale in ('enUS', 'zhTW') for name in BASE_FILES]
    targets += [getattr(args, key) for key in ('trainer_csv',
                                              'output_csv', 'items_lua', 'specialization_output_lua')]
    targets += [HERE / '_fc/cache/.pipeline-state/current.json', args.specialization_cache_root / 'current.json']
    targets += [HERE / '_fc/data' / name for name in ('recipe-item-link-audit.csv', 'recipe-item-link-audit-summary.json',
                                                    'recipe-item-web-link-audit.json')]
    for path in targets:
        observed.setdefault(path, common.fingerprint(path))
    return observed


def run_step(script, arguments, environment):
    command = [sys.executable, '-B', str(HERE / script), *map(str, arguments)]
    print('  ' + subprocess.list2cmdline(command), flush=True)
    result = subprocess.run(command, cwd=REPO, env=environment)
    if result.returncode:
        raise common.PipelineError('%s failed (exit=%s)' % (script, result.returncode))


def freeze_directory(source, destination, expected, pattern='*'):
    destination.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.glob(pattern)):
        if not path.is_file():
            continue
        common.require_repo_path(path)
        content = path.read_bytes()
        expected.setdefault(path, common.sha(content))
        if expected[path] != common.sha(content):
            raise common.PipelineError('input changed before freezing: %s' % path)
        (destination / path.name).write_bytes(content)


def freeze_file(source, target, expected):
    common.require_repo_path(source)
    content = source.read_bytes()
    expected.setdefault(source, common.sha(content))
    if common.sha(content) != expected[source]:
        raise common.PipelineError('input changed before freezing: %s' % source)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


def special_options(args, data_dir=None):
    import fc_refresh_specializations as refresh
    forwarded = ['--apply' if args.apply else '--check']
    for flag in ('offline', 'refresh_trainers', 'refresh_catalog'):
        if getattr(args, flag):
            forwarded.append('--' + flag.replace('_', '-'))
    if args.skip_recipe_catalog:
        forwarded.append('--skip-catalog')
    for key, flag in {
        'prices_csv': '--prices-csv', 'item_csv': '--item-csv', 'recipe_items_csv': '--recipe-items-csv',
        'trainer_csv': '--trainer-csv', 'specialization_output_lua': '--output-lua',
        'specialization_cache_root': '--cache-root', 'specialization_cache_dir': '--wowhead-cache-dir',
        'specialization_build': '--build', 'db2_dir': '--db2-dir', 'baseline_csv': '--baseline-csv',
    }.items():
        value = getattr(args, key)
        if value is not None:
            forwarded.extend([flag, str(value)])
    default_catalog = args.data_dir / 'catalog'
    source_dir = data_dir or args.specialization_data_dir or (default_catalog if default_catalog.is_dir() else args.data_dir)
    forwarded.extend(['--data-dir', str(source_dir)])
    options = refresh.parse_args(forwarded)
    if data_dir and not args.specialization_data_dir:
        options.provenance_paths = {str(p): str(args.data_dir / p.name) for p in data_dir.glob('*.json')}
    return options


def item_options(args, overrides=None):
    return argparse.Namespace(from_csv=args.from_csv, vendors_csv=args.vendors_csv, npcs_csv=args.npcs_csv,
                              prices_csv=args.prices_csv, output_csv=args.output_csv, items_lua=args.items_lua,
                              vendors_lua=OFFICIAL / 'Data_ProfVendors.lua', verified_at=args.verified_at,
                              dry_run=True, input_overrides=overrides or {})


def merge_batch(target, additions, expected, observations):
    for path, content in additions.items():
        if path in target and path != OFFICIAL / 'Data_ProfVendors.lua':
            raise common.PipelineError('steps have overlapping output ownership: %s' % path)
        target[path] = content
    for path, digest in observations.items():
        if path in expected and expected[path] != digest:
            raise common.PipelineError('steps observed different input versions: %s' % path)
        expected[path] = digest


def identities(value):
    if isinstance(value, dict):
        return set(value)
    if isinstance(value, list) and value and all(isinstance(row, (dict, list)) for row in value):
        result = []
        for row in value:
            identifier = None
            if isinstance(row, list):
                for index in (0, 1):
                    if len(row) > index and isinstance(row[index], (int, float)) and row[index] > 0:
                        identifier = (index, row[index])
                        break
            else:
                for key in (1, 'id', 'spell', 'item_id', 'npc_id'):
                    if isinstance(row.get(key), (int, float)) and row[key] > 0:
                        identifier = (key, row[key])
                        break
            result.append(identifier)
        return set(result) if all(item is not None for item in result) else None
    return None


def recipe_collection_records(value, collection):
    from fc_maintenance import SCHEMAS
    rows = value.values() if isinstance(value, dict) else value if isinstance(value, list) else []
    return [{name: raw.get(i) if isinstance(raw, dict) else raw[i - 1] if i <= len(raw) else None
             for i, name in enumerate(SCHEMAS[collection], 1)} for raw in rows]


def recipe_collection_keys(value, collection):
    from fc_maintenance import stable_key
    return {stable_key(collection, row) for row in recipe_collection_records(value, collection)}


def missing_records(before, after, path=''):
    missing = []
    parts = path.strip('/').split('/')
    if len(parts) == 3 and parts[0] == 'ProfLeveling' and parts[-1] == 'steps':
        def spells(value):
            rows = value.values() if isinstance(value, dict) else value if isinstance(value, list) else []
            return {row.get(3) if isinstance(row, dict) else row[2] for row in rows}
        return [path + '/spell:%s' % spell for spell in sorted(spells(before) - spells(after))]
    if len(parts) == 3 and parts[0] == 'ProfRecipes':
        from fc_maintenance import SCHEMAS
        collection = parts[-1]
        if collection in SCHEMAS:
            return [path + '/' + key for key in sorted(recipe_collection_keys(before, collection) - recipe_collection_keys(after, collection))]
    # Sparse Lua tuples can become dense when the NPC CSV fills a missing field.
    if isinstance(before, dict) and isinstance(after, list):
        after = {i + 1: value for i, value in enumerate(after)}
    elif isinstance(before, list) and isinstance(after, dict):
        before = {i + 1: value for i, value in enumerate(before)}
    a, b = identities(before), identities(after)
    if a is not None:
        missing.extend('%s/%s' % (path, k) for k in sorted(a - (b or set()), key=str))
    if isinstance(before, dict) and isinstance(after, dict):
        for key in before.keys() & after.keys():
            missing.extend(missing_records(before[key], after[key], '%s/%s' % (path, key)))
    return missing


def numeric_structure(value):
    if isinstance(value, dict):
        return {k: numeric_structure(v) for k, v in value.items()}
    if isinstance(value, list):
        return [numeric_structure(v) for v in value]
    return '<text>' if isinstance(value, str) else value


def shared_retention_view(before, after, key, report):
    if key != 'ProfSpecializations':
        return before
    view = dict(before)
    removed = []
    for approval in report.get('approvedRemovals', []):
        spell = approval['spell']
        if spell in view and spell not in after:
            del view[spell]
            removed.append(spell)
    if removed:
        report['approvedSpecializationRemovals'] = removed
    return view


def retention_view(old, new, approvals, report, catalog_identities=None):
    """Exclude only explicitly approved missing recipe identities from retention checks."""
    result = copy.deepcopy(old)
    target_build = new.get('ProfData', {}).get('build')
    used = []
    for approval in approvals:
        if approval.get('target_build') != target_build:
            continue
        if (approval.get('namespace'), approval.get('collection')) != ('ProfRecipes', 'rows'):
            raise common.PipelineError('unsupported approved removal scope')
        slug, spell, item = (approval.get(k) for k in ('profession', 'spell', 'item'))
        def values(namespace):
            rows = namespace.get('ProfRecipes', {}).get(slug, {}).get('rows', [])
            return list(rows.values()) if isinstance(rows, dict) else list(rows)
        def matches(row):
            return ((row.get(1), row.get(2)) if isinstance(row, dict) else tuple(row[:2])) == (spell, item)
        if any(matches(row) for row in values(new)):
            continue
        rows = values(result)
        removed = [row for row in rows if matches(row)]
        if len(removed) > 1:
            raise common.PipelineError('approved removal matches duplicate recipe records')
        if removed:
            result['ProfRecipes'][slug]['rows'] = [row for row in rows if not matches(row)]
            used.append(approval)
    if used:
        report['approvedRemovals'] = used
    # rinfo is a fallback for the chosen leveling guide, not another recipe
    # catalogue. Retire an unused fallback only if its exact main-recipe
    # identity is still present and every new guide spell remains resolvable.
    retired = []
    guide_updates = []
    for slug, route in result.get('ProfLeveling', {}).items():
        replacement = new.get('ProfLeveling', {}).get(slug, {})
        rows = replacement.get('steps', [])
        rows = rows.values() if isinstance(rows, dict) else rows
        referenced = {r.get(3) if isinstance(r, dict) else r[2] for r in rows}
        available = set(replacement.get('rinfo', {}))
        from fc_maintenance import stable_key
        collection_ids = {collection: {(stable_key(collection, row), row.get('spell')) for row in recipe_collection_records(
            new.get('ProfRecipes', {}).get(slug, {}).get(collection, []), collection)}
            for collection in ('rows', 'enchants', 'crafted')}
        primary = set()
        for spell, entries in (catalog_identities or {}).items():
            for profession, collection, key in entries:
                if profession == slug and (key, int(spell)) in collection_ids[collection]:
                    primary.add(int(spell))
        if referenced <= available | primary:
            previous_steps = route.get('steps', [])
            previous_steps = list(previous_steps.values()) if isinstance(previous_steps, dict) else previous_steps
            kept_steps = []
            for row in previous_steps:
                spell = row.get(3) if isinstance(row, dict) else row[2]
                if spell not in referenced and spell in available | primary:
                    guide_updates.append({'profession': slug, 'spell': spell,
                                          'reason': 'guide changed; previous recipe still resolves in runtime data'})
                else:
                    kept_steps.append(row)
            if 'steps' in route:
                route['steps'] = kept_steps
        for spell in set(route.get('rinfo', {})) - available:
            if spell not in referenced and spell in primary and referenced <= available | primary:
                del route['rinfo'][spell]
                retired.append({'profession': slug, 'spell': spell,
                                'reason': 'guide no longer references this spell; exact main recipe retained'})
    if retired:
        report['retiredRouteFallbacks'] = retired
    if guide_updates:
        report['updatedGuideSpells'] = guide_updates
    return result


def validate_batch(outputs, before, report, full=True, approved_removals=(), catalog_identities=None):
    for path, content in outputs.items():
        if path.suffix == '.lua':
            common.raw_namespace([(path.name, content)])
    if not full:
        pairs = [(p, b) for p, b in outputs.items() if p.suffix == '.lua' and p in before]
        missing = []
        for path, content in pairs:
            old = common.load_namespace([(path.name, before[path])])
            new = common.load_namespace([(path.name, content)])
            for key in ('ProfItems', 'ProfSpecializations'):
                if key in old:
                    missing.extend(missing_records(old[key], new.get(key, {}), key))
        if missing:
            report['missingRecords'] = missing
            raise common.PipelineError('existing records would disappear: ' + '; '.join(missing[:12]))
        return
    base = [(name, outputs[OFFICIAL / name]) for name in BASE_FILES]
    old = common.load_namespace([(name, before[OFFICIAL / name]) for name in BASE_FILES])
    new = common.load_namespace(base)
    missing = missing_records(retention_view(old, new, approved_removals, report, catalog_identities), new)
    if missing:
        report['missingRecords'] = missing
        raise common.PipelineError('existing profession records would disappear: ' + '; '.join(missing[:12]))
    for name, key in zip(SHARED_FILES, ('ProfItems', 'ProfSpecializations')):
        path = OFFICIAL / name
        old_shared = common.load_namespace([(name, before[path])]).get(key, {})
        new_shared = common.load_namespace([(name, outputs[path])]).get(key, {})
        missing = missing_records(shared_retention_view(old_shared, new_shared, key, report), new_shared, key)
        if missing:
            report['missingRecords'] = missing
            raise common.PipelineError('existing shared records would disappear: ' + '; '.join(missing[:12]))
    for locale in ('zhTW', 'enUS'):
        localized = common.load_namespace(base + [(locale + '/' + n, outputs[OFFICIAL / locale / n]) for n in BASE_FILES], locale)
        if numeric_structure(new) != numeric_structure(localized):
            raise common.PipelineError('%s profession structure differs from base data' % locale)
    data_paths = []
    for line in (REPO / 'DungeonsForever.toc').read_text(encoding='utf-8-sig').splitlines():
        relative = line.split('[', 1)[0].strip().replace('\\', '/')
        if relative.startswith('Core/Data/') and Path(relative).name.startswith('Data_Prof'):
            data_paths.append(REPO / relative)
    for locale in ('zhCN', 'zhTW', 'enUS'):
        locale_sources = [(str(p.relative_to(REPO)), p.read_bytes())
                          for p in (REPO / 'Locales/zhCN.lua', REPO / 'Locales/zhTW.lua', REPO / 'Locales/enUS.lua')]
        selected = locale_sources + [(str(p.relative_to(REPO)), outputs.get(p, before.get(p))) for p in data_paths]
        if any(b is None for _, b in selected):
            raise common.PipelineError('TOC profession data is missing')
        ns = common.load_namespace(selected, locale)
        for key in ('ProfRecipes', 'ProfItems', 'ProfSpecializations', 'ProfSpecializationQuests', 'ProfFishingRoutes'):
            if key not in ns:
                raise common.PipelineError('%s missing after %s TOC load' % (key, locale))
    report['validatedLocales'] = ['zhCN', 'zhTW', 'enUS']


def prepare_full(args, report, expected, stage, before):
    import fc_gen, fc_locales, fc_refresh_specializations as refresh, fc_prof_items as items
    data, i18n = stage / 'data', stage / 'i18n'
    freeze_directory(args.data_dir, data, expected, '*.json')
    freeze_directory(args.i18n_dir, i18n, expected, '*.json')
    for source, target in ((args.i18n_dir / 'zh.json', data / 'zh.json'),
                           (HERE / 'questie/questie_forever.json', data / 'questie/questie_forever.json'),
                           (HERE / '_wago_AreaTable_zh.csv', data / '_wago_AreaTable_zh.csv')):
        if source.exists():
            freeze_file(source, target, expected)
    maintenance = stage / 'maintenance/professions.json'
    locale_maintenance = stage / 'maintenance/locales.json'
    freeze_file(args.maintenance, maintenance, expected)
    report['_approved_removals'] = json.loads(maintenance.read_bytes()).get('approved_removals', [])
    freeze_file(HERE / '_fc/maintenance/locales.json', locale_maintenance, expected)
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1',
               DF_PIPELINE_CACHE_DIR=str(args.cache_dir), DF_PIPELINE_DATA_DIR=str(data),
               DF_PIPELINE_I18N_DIR=str(i18n), DF_PIPELINE_REPORT_DIR=str(stage / 'reports'))
    run_step('fc_fetch.py', ['--offline'] if args.offline else ['--force'], env)
    for path in args.cache_dir.glob('*'):
        if path.is_file():
            expected[path] = common.fingerprint(path)
    run_step('fc_parse.py', [], env)
    run_step('fc_zones.py', ['--offline'] if args.offline else [], env)
    run_step('fc_fields.py', ['--strict', '--source-only'], env)
    run_step('fc_i18n.py', ['--audit'], env)
    print('  Generate preserved base professions', flush=True)
    rendered = fc_gen.render_data(data, maintenance_path=maintenance)
    if set(rendered) != set(BASE_FILES):
        raise common.PipelineError('base generator violated the six-file ownership manifest')
    outputs = {OFFICIAL / n: b for n, b in rendered.items()}
    report['baseSemanticChanges'] = [n for n in BASE_FILES if common.load_namespace([(n, before[OFFICIAL / n])]) != common.load_namespace([(n, rendered[n])])]
    catalog = stage / 'effective-catalog'
    if args.specialization_data_dir:
        freeze_directory(args.specialization_data_dir, catalog, expected, '*.json')
        catalog_final = args.specialization_data_dir
    else:
        catalog.mkdir()
        catalog_final = args.data_dir / 'catalog'
        for name, content in fc_gen.render_catalog(data, maintenance_path=maintenance).items():
            (catalog / name).write_bytes(content)
            outputs[catalog_final / name] = content
    from fc_maintenance import stable_key
    catalog_identities = {}
    for path in catalog.glob('prof_*.json'):
        source = json.loads(path.read_bytes())
        for collection in ('rows', 'enchants', 'crafted'):
            for row in source.get(collection) or []:
                if isinstance(row.get('spell'), int) and row['spell'] > 0:
                    catalog_identities.setdefault(row['spell'], []).append(
                        (path.stem[len('prof_'):], collection, stable_key(collection, row)))
    report['_catalog_identities'] = catalog_identities
    options = special_options(args, catalog)
    options.provenance_paths = {str(p): str(catalog_final / p.name) for p in catalog.glob('*.json')}
    prepared, seen = refresh.prepare_batch(options, report.setdefault('specializations', {}))
    merge_batch(outputs, prepared, expected, seen)
    prepared, seen = items.build_batch(item_options(args, outputs))
    merge_batch(outputs, prepared, expected, seen)
    baseline = stage / 'official-baseline'
    for path, content in before.items():
        if path.name in BASE_FILES:
            target = baseline / path.relative_to(OFFICIAL)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    languages = fc_locales.render_locales({n: outputs[OFFICIAL / n] for n in BASE_FILES}, baseline,
                                         maintenance_path=locale_maintenance)
    if set(languages) != {locale + '/' + n for locale in ('enUS', 'zhTW') for n in BASE_FILES}:
        raise common.PipelineError('language generator violated the ownership manifest')
    outputs.update({OFFICIAL / n: b for n, b in languages.items()})
    for path in data.glob('*.json'):
        if path.name in ('index.json', 'item_ids.json', 'zone_ids.json') or path.name.startswith('prof_'):
            outputs[args.data_dir / path.name] = path.read_bytes()
    return outputs


def execute(args, report):
    preflight(args)
    expected = watched_files(args)
    before = {p: p.read_bytes() for p in OFFICIAL.rglob('*.lua')}
    runs = common.require_repo_path(args.cache_dir / 'runs')
    runs.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='unified-', dir=runs) as temporary:
        stage = common.require_repo_path(temporary)
        if args.from_csv:
            import fc_prof_items as items
            outputs, seen = items.build_batch(item_options(args))
            merge_batch({}, {}, expected, seen)
        elif args.specializations_only:
            import fc_refresh_specializations as refresh
            outputs, seen = refresh.prepare_batch(special_options(args), report.setdefault('specializations', {}))
            merge_batch({}, {}, expected, seen)
        else:
            outputs = prepare_full(args, report, expected, stage, before)
        for path in outputs:
            common.require_repo_path(path)
            # Any pre-existing output was recorded before work started. A new
            # target must still be absent, not adopted midway through a run.
            expected.setdefault(path, None)
        print('  Validate staged Lua, record preservation and three-language TOC order', flush=True)
        approvals = report.pop('_approved_removals', [])
        catalog_identities = report.pop('_catalog_identities', {})
        validate_batch(outputs, before, report, not (args.from_csv or args.specializations_only), approvals, catalog_identities)
        common.ensure_unchanged(expected)
        changed = {p: b for p, b in outputs.items() if common.fingerprint(p) != common.sha(b)}
        report['changedFiles'] = [{'path': str(p.relative_to(REPO)).replace('\\', '/'), 'sha256': common.sha(b), 'bytes': len(b)} for p, b in changed.items()]
        state = {'schemaVersion': 1, 'scope': 'items' if args.from_csv else 'specializations' if args.specializations_only else 'professions',
                 'outputs': {str(p.relative_to(REPO)).replace('\\', '/'): common.sha(b) for p, b in outputs.items()}}
        if args.apply:
            marker = HERE / '_fc/cache/.pipeline-state/current.json'
            outputs[marker] = common.json_bytes(state)
            common.publish_batch(outputs, expected)
            report['status'] = 'updated' if changed else 'unchanged'
        else:
            report['status'] = 'checked'
            try:
                if args.stage_dir:
                    retain_preview(args.stage_dir, outputs, expected, report)
                if args.package_zip:
                    import fc_package
                    report['package'] = fc_package.build_install_zip(args.package_zip, outputs, expected)
                common.ensure_unchanged(expected)
            except (OSError, ValueError, RuntimeError) as error:
                package = report.get('package')
                if package and common.fingerprint(args.package_zip) == package['sha256']:
                    args.package_zip.unlink()
                    package['removedAfterFailure'] = True
                if report.get('previewDirectory'):
                    marker = args.stage_dir / 'preview-manifest.json'
                    manifest = json.loads(marker.read_bytes())
                    manifest.update(status='invalidated-preview', error=str(error))
                    marker.write_bytes(common.json_bytes(manifest))
                raise


def retain_preview(destination, outputs, expected, report):
    destination = common.require_repo_path(destination)
    if destination.exists():
        raise common.PipelineError('preview directory already exists: %s' % destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.preview-', dir=destination.parent) as temporary:
        stage = common.require_repo_path(temporary)
        manifest = {'schemaVersion': 1, 'status': 'validated-preview', 'published': False,
                    'files': {}, 'inputs': {p.relative_to(REPO).as_posix(): digest for p, digest in expected.items()}}
        for path, content in outputs.items():
            relative = path.relative_to(REPO)
            target = common.require_repo_path(stage / relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            manifest['files'][relative.as_posix()] = {'sha256': common.sha(content), 'bytes': len(content)}
        (stage / 'preview-manifest.json').write_bytes(common.json_bytes(manifest))
        # Windows scanners may briefly retain a handle after validating a large
        # staged Lua tree. Retry only this final rename, without publishing a
        # partial preview or replacing a destination created by another writer.
        for attempt in range(5):
            common.ensure_unchanged(expected)
            if destination.exists():
                raise common.PipelineError('preview directory already exists: %s' % destination)
            try:
                stage.rename(destination)
                break
            except PermissionError:
                if os.name != 'nt' or attempt == 4:
                    raise
                time.sleep(.025 * (attempt + 1))
    report['previewDirectory'] = destination.relative_to(REPO).as_posix()


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    args = parser().parse_args(argv)
    report = {'schemaVersion': 1, 'mode': 'apply' if args.apply else 'check', 'offline': args.offline,
              'startedAt': datetime.now(timezone.utc).isoformat()}
    try:
        preflight(args)
        with common.update_lock():
            execute(args, report)
        print('[OK] %s; %d changed files%s' % (report['status'], len(report.get('changedFiles', [])), '' if args.apply else '; no publication'), flush=True)
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        report['status'], report['error'] = 'failed', str(error)
        if hasattr(error, 'invalidated'):
            report['invalidatedTranslations'] = error.invalidated
        print('[FAIL] %s' % error, file=sys.stderr, flush=True)
        return 1
    finally:
        report['finishedAt'] = datetime.now(timezone.utc).isoformat()
        try:
            for value in vars(args).values():
                if isinstance(value, Path):
                    common.require_repo_path(value)
            directory = common.require_repo_path(HERE / '_fc/reports/unified')
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / ('run-' + uuid.uuid4().hex + '.json')
            path.write_bytes(common.json_bytes(report))
            print('Report: %s' % path, flush=True)
        except (OSError, ValueError):
            pass
