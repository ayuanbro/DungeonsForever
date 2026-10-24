#!/usr/bin/env python3
"""Collect or strictly replay affiliations for every NPC in a vendor CSV.

This producer emits JSON and frozen evidence only. Import the result through
fc_update.py; neither collection nor replay modifies prices, locations or Lua.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sys

import gen_vendors as collector

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'df-data-pipeline/_temp'
INPUTS = TOOLS / '_fc/inputs'
sys.path.insert(0, str(TOOLS))
try:
    from fc_pipeline_paths import CSV_INPUTS
finally:
    sys.path.remove(str(TOOLS))
DEFAULT_VENDORS = CSV_INPUTS['vendors_csv']
DEFAULT_BUNDLE = INPUTS / 'vendors/faction-sources'
DEFAULT_INPUT = INPUTS / 'vendors/npc-factions.json'
LOCALES = ('enUS', 'zhCN', 'zhTW')


def digest(content):
    return hashlib.sha256(content).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def object_json(content, label):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError('%s has a duplicate JSON key: %s' % (label, key))
            result[key] = value
        return result
    value = json.loads(content, object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise ValueError('%s must be a JSON object' % label)
    return value


def scoped(path):
    result = Path(path).resolve()
    if not result.is_relative_to(ROOT):
        raise ValueError('all paths must stay inside the current repository: %s' % result)
    return result


def bundle_path(directory, relative):
    if not isinstance(relative, str) or not relative or '\\' in relative or ':' in relative \
            or any(part in ('', '.', '..') for part in relative.split('/')):
        raise ValueError('invalid evidence path')
    result = (directory / relative).resolve()
    if not result.is_relative_to(directory.resolve()) or result == directory.resolve():
        raise ValueError('evidence path escapes snapshot: %s' % relative)
    return scoped(result)


def rows(content):
    reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig'), newline=''))
    fields = reader.fieldnames or []
    if len(fields) != len(set(fields)):
        raise ValueError('CSV contains duplicate column names')
    result = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in result):
        raise ValueError('CSV contains malformed rows')
    return result


def positive(value):
    text = str(value)
    if not re.fullmatch(r'[1-9]\d*', text):
        raise ValueError('invalid positive ID: %r' % value)
    return int(text)


def targets(content):
    result = set()
    for row in rows(content):
        if 'npc_id' not in row:
            raise ValueError('vendor CSV must contain npc_id')
        result.add(positive(row['npc_id']))
    if not result:
        raise ValueError('vendor CSV contains no NPCs')
    return sorted(result)


def publish(outputs, expected=None):
    # Reuse the repository's transactional writer, without invoking any data
    # generator, client exporter or service from this producer.
    sys.path.insert(0, str(TOOLS))
    try:
        import fc_pipeline_common as common
        with common.update_lock():
            try:
                common.publish_batch(outputs, expected)
            except common.PipelineError as error:
                raise ValueError(str(error)) from error
    finally:
        sys.path.remove(str(TOOLS))


def frozen(directory):
    manifest_content = (directory / 'manifest.json').read_bytes()
    manifest = object_json(manifest_content, 'evidence manifest')
    if type(manifest.get('schemaVersion')) is not int or manifest['schemaVersion'] != 1 \
            or not isinstance(manifest.get('files'), dict):
        raise ValueError('unsupported affiliation evidence snapshot')
    files = {}
    for name, record in manifest['files'].items():
        if not isinstance(record, dict) or type(record.get('bytes')) is not int \
                or record['bytes'] < 0 or not isinstance(record.get('sha256'), str) \
                or not re.fullmatch(r'[0-9a-f]{64}', record['sha256']):
            raise ValueError('invalid evidence manifest record: %s' % name)
        content = bundle_path(directory, name).read_bytes()
        if digest(content) != record.get('sha256') or len(content) != record.get('bytes'):
            raise ValueError('evidence hash mismatch: %s' % name)
        files[name] = content
    return manifest, manifest_content, files


def capture(args, vendor_content, directory):
    """Freeze raw inputs; missing NPCs are explicit, never a hidden network read."""
    ids = targets(vendor_content)
    files = {'vendors.csv': vendor_content}
    statuses = {}
    locales = args.locales.split(',')
    if 'enUS' not in locales or set(locales) - set(LOCALES):
        raise ValueError('--locales must include enUS and only enUS,zhCN,zhTW')
    for locale in locales:
        provider = collector.NpcNether(
            proxy=args.proxy, refetch=args.refresh, locale='' if locale == 'enUS' else locale,
            cache_only=args.capture_cache, max_age_days=args.max_age, cache_dir=str(args.cache_dir))
        info = provider.npc_info(ids)
        for npc in ids:
            suffix = '' if locale == 'enUS' else '.' + locale
            path = args.cache_dir / ('%d%s.json' % (npc, suffix))
            record = info.get(npc, {})
            status = record.get('collectionStatus', 'ok' if path.is_file() else 'missing')
            statuses['%d:%s' % (npc, locale)] = {
                'status': status, 'diagnostics': record.get('diagnostics', [])}
            if status == 'ok' and path.is_file():
                files['nether/%d%s.json' % (npc, suffix)] = path.read_bytes()
    if args.client_dir:
        client_dir = scoped(args.client_dir)
        if client_dir == directory or directory.is_relative_to(client_dir):
            raise ValueError('client export must be separate from evidence destination')
        for path in sorted(client_dir.rglob('*')):
            if path.is_file():
                if path.is_symlink() or not path.resolve().is_relative_to(client_dir):
                    raise ValueError('client export contains a directory link')
                files['client/' + path.relative_to(client_dir).as_posix()] = path.read_bytes()
        if 'client/factions.csv' not in files:
            raise ValueError('client export must contain factions.csv')
    # These catalogs supply locale fallback by a confirmed Faction ID only.
    for locale, source in (('zhCN', ROOT / 'Core/Data/Data_Factions.lua'),
                           ('zhTW', ROOT / 'Core/Data/zhTW/Data_Factions.lua')):
        files['locales/' + locale + '.lua'] = source.read_bytes()
    manifest = {'schemaVersion': 1, 'targets': ids, 'collection': statuses,
                'files': {name: {'sha256': digest(content), 'bytes': len(content)}
                          for name, content in sorted(files.items())}}
    return manifest, encoded(manifest), files


def source(name, content, kind, **extra):
    return dict(type=kind, file='faction-sources/' + name, sha256=digest(content), **extra)


def client_records(files):
    by_id, by_name, ambiguous = {}, {}, set()
    client_files = {name for name in files if name.startswith('client/')}
    if client_files:
        if not {'client/factions.csv', 'client/manifest.json'} <= client_files:
            raise ValueError('client export must manifest factions.csv and raw evidence')
        client_manifest = object_json(files['client/manifest.json'], 'client manifest')
        declared = client_manifest.get('files')
        if not isinstance(declared, dict) or 'factions.csv' not in declared:
            raise ValueError('client export must manifest factions.csv and raw evidence')
        present = {name[len('client/'):] for name in files
                   if name.startswith('client/') and name != 'client/manifest.json'}
        if present != set(declared):
            raise ValueError('client export contains unmanifested or missing files')
        for relative, record in declared.items():
            # Validate paths even during in-memory capture, before publication.
            bundle_path(ROOT, relative)
            if not isinstance(record, dict) or type(record.get('bytes')) is not int:
                raise ValueError('invalid client export manifest record: %s' % relative)
            content = files.get('client/' + relative)
            if content is None or digest(content) != record.get('sha256') or len(content) != record.get('bytes'):
                raise ValueError('client export hash mismatch: %s' % relative)
    for row in rows(files.get('client/factions.csv', b'ID,Name_enUS\n')):
        fid = positive(row['ID'])
        names = {locale: row.get('Name_' + locale, '').strip() for locale in LOCALES}
        names = {locale: name for locale, name in names.items() if name}
        if not names.get('enUS'):
            raise ValueError('client Faction %d has no verified English name' % fid)
        if fid in by_id and by_id[fid] != names:
            raise ValueError('conflicting client names for Faction %d' % fid)
        by_id[fid] = names
        for name in names.values():
            if name in by_name and by_name[name] != fid:
                ambiguous.add(name)
            else:
                by_name[name] = fid
    for name in ambiguous:
        by_name.pop(name, None)
    bindings = {}
    for row in rows(files.get('client/npc-factions.csv', b'npc_id,faction_id,status\n')):
        npc = positive(row['npc_id'])
        if npc in bindings:
            raise ValueError('duplicate client NPC %d' % npc)
        status = row['status']
        if status not in ('resolved', 'missing-template', 'missing-faction', 'conflict', 'no-faction'):
            raise ValueError('unsupported client NPC status: %s' % status)
        fid = positive(row['faction_id']) if status == 'resolved' else None
        if fid is not None and fid not in by_id:
            raise ValueError('NPC %d refers to a missing client Faction' % npc)
        bindings[npc] = (status, fid)
    return by_id, by_name, bindings, ambiguous


def locale_catalog(content):
    # Parse only literal id/name fields from the existing generated catalog.
    # No Lua execution, side/group inference, or transliteration is involved.
    found = {}
    for match in re.finditer(r'\{\s*id\s*=\s*(\d+)\s*,\s*name\s*=\s*("(?:\\.|[^"\\])*")',
                             content.decode('utf-8-sig')):
        fid, name = int(match[1]), json.loads(match[2])
        if fid in found and found[fid] != name:
            raise ValueError('conflicting localized faction catalog')
        found[fid] = name
    return found


def build(manifest, manifest_content, files, vendor_content):
    ids = targets(vendor_content)
    if 'vendors.csv' not in files or not isinstance(manifest.get('collection', {}), dict):
        raise ValueError('evidence snapshot must contain vendors.csv and a collection object')
    frozen_ids = targets(files['vendors.csv'])
    if ids != frozen_ids or ids != manifest.get('targets'):
        raise ValueError('vendor NPC set differs from snapshot; collect a new snapshot')
    by_id, by_name, bindings, ambiguous = client_records(files)
    catalogs = {locale: locale_catalog(files.get('locales/' + locale + '.lua', b''))
                for locale in ('zhCN', 'zhTW')}
    result, ledger, conflicts = {}, {}, []
    for npc in ids:
        candidates, names, evidence, diagnostics = set(), {}, [], []
        binding = bindings.get(npc)
        if binding:
            status, fid = binding
            if status == 'conflict':
                diagnostics.append('client NPC has conflicting faction chains')
                conflicts.append(npc)
            if fid:
                candidates.add(fid)
                evidence.append(source('client/npc-factions.csv', files['client/npc-factions.csv'],
                                       'client-npc-faction-chain'))
        for locale in LOCALES:
            suffix = '' if locale == 'enUS' else '.' + locale
            key = 'nether/%d%s.json' % (npc, suffix)
            if key not in files:
                continue
            payload = object_json(files[key].decode('utf-8-sig'), 'raw NPC payload: ' + key)
            if not isinstance(payload.get('name'), str) or not payload['name'].strip() \
                    or not isinstance(payload.get('tooltip', ''), str):
                raise ValueError('invalid raw NPC payload: %s' % key)
            try:
                faction = collector.parse_npc_faction(payload.get('tooltip'))
            except ValueError as error:
                diagnostics.append(str(error))
                conflicts.append(npc)
                continue
            if not faction:
                continue
            names[locale] = faction['name']
            if faction.get('factionID'):
                candidates.add(positive(faction['factionID']))
            if faction['name'] in by_name:
                candidates.add(by_name[faction['name']])
            elif faction['name'] in ambiguous:
                diagnostics.append('ambiguous exact client faction name: ' + faction['name'])
            url = collector.NETHER_NPC_URL % npc
            if locale != 'enUS':
                url += '?locale=' + locale
            evidence.append(source(key, files[key], 'wowhead-npc-tooltip', locale=locale, url=url))
        if len(candidates) > 1:
            diagnostics.append('conflicting NPC affiliation IDs: ' + ','.join(map(str, sorted(candidates))))
            conflicts.append(npc)
        fid = next(iter(candidates)) if len(candidates) == 1 else None
        if fid in by_id:
            # Explicit localized tooltip names and decoded names must agree by
            # ID; locale wording may vary, so verified client spelling wins.
            names.update(by_id[fid])
            evidence.append(source('client/factions.csv', files['client/factions.csv'], 'client-faction-csv'))
        if fid:
            for locale, catalog in catalogs.items():
                if locale not in names and catalog.get(fid):
                    names[locale] = catalog[fid]
                    key = 'locales/' + locale + '.lua'
                    evidence.append(source(key, files[key], 'existing-localized-faction-catalog', locale=locale))
        collection = manifest.get('collection', {}).get('%d:enUS' % npc, {})
        if npc in conflicts:
            state = 'conflict'
        elif names.get('enUS') and evidence:
            record = {'names': names, 'sources': evidence}
            if fid:
                record['factionID'] = fid
            result[str(npc)] = record
            state = 'resolved-id' if fid else 'resolved-name'
        else:
            state = 'missing-payload' if ('nether/%d.json' % npc) not in files else 'no-affiliation'
        ledger[str(npc)] = {'status': state, 'diagnostics': diagnostics,
                            'collection': collection, 'clientStatus': binding[0] if binding else 'not-covered'}
    counts = {state: sum(value['status'] == state for value in ledger.values())
              for state in sorted({value['status'] for value in ledger.values()})}
    data = {'schemaVersion': 1, 'npcs': result,
            'sourceBundle': {'directory': 'faction-sources', 'manifestSHA256': digest(manifest_content)}}
    audit = {'schemaVersion': 1, 'targets': len(ids), 'resolved': len(result),
             'counts': counts, 'npcs': ledger, 'conflicts': sorted(set(conflicts)),
             'vendorNPCSetSHA256': digest(encoded(ids)),
             'evidenceManifestSHA256': digest(manifest_content), 'outputSHA256': digest(encoded(data))}
    return data, audit


def run(args):
    vendor_content = args.vendors_csv.read_bytes()
    source_expected = {args.vendors_csv: digest(vendor_content)}
    output_path = args.output_dir / 'npc-factions.json'
    expected = {output_path: digest(output_path.read_bytes()) if output_path.is_file() else None}
    capture_mode = args.collect or args.capture_cache
    directory = args.snapshot_dir or (args.output_dir / 'faction-sources' if capture_mode else DEFAULT_BUNDLE)
    directory = scoped(directory)
    if capture_mode:
        manifest, manifest_content, files = capture(args, vendor_content, directory)
    else:
        manifest, manifest_content, files = frozen(directory)
        source_expected[directory / 'manifest.json'] = digest(manifest_content)
        source_expected.update({bundle_path(directory, name): digest(content) for name, content in files.items()})
    if capture_mode:
        source_expected.update({args.cache_dir / name[len('nether/'):]: digest(content)
                                for name, content in files.items() if name.startswith('nether/')})
        if args.client_dir:
            source_expected.update({bundle_path(args.client_dir, name[len('client/'):]): digest(content)
                                    for name, content in files.items() if name.startswith('client/')})
        source_expected[ROOT / 'Core/Data/Data_Factions.lua'] = digest(files['locales/zhCN.lua'])
        source_expected[ROOT / 'Core/Data/zhTW/Data_Factions.lua'] = digest(files['locales/zhTW.lua'])
    expected.update(source_expected)
    data, audit = build(manifest, manifest_content, files, vendor_content)
    audit_path = args.output_dir / 'audit.json'
    outputs = {}

    def add(path, content):
        path = scoped(path)
        if path in source_expected and digest(content) != source_expected[path]:
            raise ValueError('output must not overwrite a source input: %s' % path)
        if path in outputs and outputs[path] != content:
            raise ValueError('conflicting publication destinations: %s' % path)
        outputs[path] = content

    add(audit_path, encoded(audit))
    collection_errors = capture_mode and any(
        not isinstance(row, dict) or row.get('status') == 'error'
        for row in manifest.get('collection', {}).values())
    incomplete_install = args.install_input and any(
        row['status'] == 'missing-payload' for row in audit['npcs'].values())
    if audit['conflicts'] or collection_errors or incomplete_install:
        publish(outputs, expected)
        reason = ('conflicting affiliations' if audit['conflicts'] else
                  'missing NPC evidence prevents input installation' if incomplete_install else 'collection failed')
        raise ValueError('%s; previous JSON kept; see %s' % (reason, audit_path))
    add(output_path, encoded(data))
    output_bundle = args.output_dir / 'faction-sources'
    for name, content in files.items():
        add(bundle_path(output_bundle, name), content)
    add(output_bundle / 'manifest.json', manifest_content)
    if capture_mode:
        for name, content in files.items():
            add(bundle_path(directory, name), content)
        add(directory / 'manifest.json', manifest_content)
    if args.install_input:
        canonical = DEFAULT_BUNDLE
        installed = {DEFAULT_INPUT: encoded(data), INPUTS / 'vendors/npc-factions-audit.json': encoded(audit),
                     canonical / 'manifest.json': manifest_content}
        installed.update({bundle_path(canonical, name): content for name, content in files.items()})
        manifest_path = INPUTS / 'manifest.json'
        old_manifest = manifest_path.read_bytes()
        input_manifest = object_json(old_manifest, 'pipeline input manifest')
        if not isinstance(input_manifest.get('files'), dict):
            raise ValueError('pipeline input manifest must contain files')
        expected[manifest_path] = digest(old_manifest)
        for path, producer in ((DEFAULT_INPUT, args.output_dir / 'npc-factions.json'),
                               (INPUTS / 'vendors/npc-factions-audit.json', audit_path),
                               (canonical / 'manifest.json', output_bundle / 'manifest.json')):
            content = installed[path]
            input_manifest['files'][path.relative_to(INPUTS).as_posix()] = {
                'originalFile': producer.relative_to(ROOT).as_posix(),
                'bytes': len(content), 'sha256': digest(content), 'kind': 'npc-affiliation-reproducible'}
        installed[manifest_path] = encoded(input_manifest)
        for path, content in installed.items():
            add(path, content)
    publish(outputs, expected)
    print(json.dumps({'targets': audit['targets'], 'resolved': audit['resolved'], 'counts': audit['counts'],
                      'output': str(args.output_dir / 'npc-factions.json')}, ensure_ascii=True))
    return audit


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--collect', action='store_true', help='refresh aged/missing Nether payloads and freeze inputs')
    mode.add_argument('--capture-cache', action='store_true', help='freeze existing raw cache/client export without network')
    mode.add_argument('--offline', action='store_true', help='verify and replay a frozen snapshot (default)')
    parser.add_argument('--vendors-csv', type=Path, default=DEFAULT_VENDORS)
    parser.add_argument('--snapshot-dir', type=Path)
    parser.add_argument('--client-dir', type=Path, help='export_npc_factions output, copied into new snapshots')
    parser.add_argument('--cache-dir', type=Path, default=ROOT / 'scripts/.cache/nether')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'scripts/out/vendor-factions')
    parser.add_argument('--locales', default='enUS', help='comma-separated Nether locales; client export supplies translations')
    parser.add_argument('--max-age', type=float, default=7)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--proxy', default=collector.PROXY)
    parser.add_argument('--install-input', action='store_true', help='transactionally import JSON/evidence into pipeline inputs; no Lua')
    args = parser.parse_args(argv)
    try:
        for key, value in vars(args).items():
            if isinstance(value, Path):
                setattr(args, key, scoped(value))
        if args.max_age < 0:
            raise ValueError('--max-age must not be negative')
        run(args)
        return 0
    except (OSError, ValueError, csv.Error) as error:
        print('update_vendor_factions: %s' % error, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
