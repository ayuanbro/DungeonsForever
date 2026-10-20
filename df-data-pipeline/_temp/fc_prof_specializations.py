#!/usr/bin/env python3
"""Export source-backed recipe learning requirements, independently of recipe UI data.

Online runs collect Wowhead Forever trainer evidence. Offline runs replay the
normalized trainer CSV and validated page cache. Unknown never means unrestricted.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
from urllib.parse import urlsplit

from fc_pipeline_paths import CSV_INPUTS
from fc_prof_items import DataError, lua, read_csv

from fc_pipeline_common import HERE, PACKAGE, REPO, publish_batch, require_repo_path
ITEM_FIELDS = (
    'RecipeItemID', 'RecipeSpellID', 'RequiredAbility', 'Status', 'Reason',
    'LearningPath', 'Build', 'HotfixBuild', 'Source',
)
TRAINER_FIELDS = (
    'RecipeSpellID', 'RequiredAbility', 'Status', 'Reason', 'SkillLineID',
    'LearnedAt', 'NPCIDs', 'TrainerObserved', 'SpecializationObserved',
    'TargetBuild', 'SourceEnvironment', 'SourceURL', 'SourcePatch', 'SourceBuild',
    'SourceFetchedAt', 'SourceSHA256', 'TrainerSourceURL',
    'TrainerSourceFetchedAt', 'TrainerSourceSHA256', 'TrainerSourcePatch',
    'TrainerSourceBuild', 'Evidence',
)
STATUSES = {'confirmed', 'pending', 'conflict'}
BUILD = re.compile(r'1\.60\.\d+\.\d+\Z')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def number(value, label, optional=False, minimum=1):
    if value is None or value == '':
        if optional:
            return None
        raise DataError('%s is required' % label)
    if isinstance(value, bool) or not re.fullmatch(r'\d+', str(value)):
        raise DataError('%s must be an integer' % label)
    result = int(value)
    if result < minimum:
        raise DataError('%s must be >= %d' % (label, minimum))
    return result


def boolean(value, label):
    if value is True or value == 'true':
        return True
    if value is False or value == 'false':
        return False
    raise DataError('%s must be true or false' % label)


def snapshot(path, snapshots):
    content = path.read_bytes()
    snapshots[path] = digest(content)
    return content


def catalog(data_dir, snapshots):
    """Use existing explicit spell IDs, including the established enchant ID map."""
    result, sources, unresolved = set(), [], 0
    enchant_path = data_dir / 'enchant_ids.json'
    enchants = json.loads(snapshot(enchant_path, snapshots)) if enchant_path.exists() else {}
    files = sorted(data_dir.glob('prof_*.json'))
    if not files:
        raise DataError('no prof_*.json recipe catalog in %s' % data_dir)
    for path in files:
        data = json.loads(snapshot(path, snapshots))
        sources.append({'file': path.name, 'build': data.get('build', ''),
                        'sha256': snapshots[path]})
        for collection in ('rows', 'enchants', 'crafted'):
            for row in data.get(collection) or []:
                spell = row.get('spell')
                if not spell and collection == 'enchants':
                    spell = (enchants.get(row.get('name')) or {}).get('spell')
                if spell:
                    result.add(number(spell, '%s.%s.spell' % (path.name, collection)))
                else:
                    unresolved += 1
        leveling = data.get('leveling') or {}
        for spell in (leveling.get('recipes') or {}):
            result.add(number(spell, '%s.leveling.recipes' % path.name))
        for step in leveling.get('steps') or []:
            if step.get('spell'):
                result.add(number(step['spell'], '%s.leveling.steps' % path.name))
    if enchant_path.exists():
        sources.append({'file': enchant_path.name, 'sha256': snapshots[enchant_path]})
    return result, sources, unresolved


def item_rows(path, snapshots, explicit_build=''):
    snapshot(path, snapshots)
    _, rows = read_csv(path, ITEM_FIELDS)
    builds, hotfixes = set(), set()
    for row in rows:
        row['RecipeItemID'] = number(row['RecipeItemID'], 'RecipeItemID')
        row['RecipeSpellID'] = number(row['RecipeSpellID'], 'RecipeSpellID', True)
        row['RequiredAbility'] = number(row['RequiredAbility'], 'RequiredAbility', True, 0)
        if row['Status'] not in STATUSES:
            raise DataError('invalid item Status %r' % row['Status'])
        if not BUILD.fullmatch(row['Build']):
            raise DataError('item Build must be a full Forever build')
        if row['HotfixBuild'] != row['Build'].rsplit('.', 1)[1]:
            raise DataError('item HotfixBuild does not match Build')
        builds.add(row['Build'])
        hotfixes.add(row['HotfixBuild'])
        if row['Status'] == 'confirmed' and not (
                row['RecipeSpellID'] and row['RequiredAbility'] and row['LearningPath']):
            raise DataError('confirmed item requirement lacks teaching evidence')
        if not row['Source']:
            raise DataError('item Source is required')
    if len(builds) > 1 or len(hotfixes) > 1:
        raise DataError('mixed client builds in recipe item CSV')
    if explicit_build and not BUILD.fullmatch(explicit_build):
        raise DataError('--build must be a full Forever build')
    if builds and explicit_build and explicit_build not in builds:
        raise DataError('--build conflicts with recipe item CSV')
    target = next(iter(builds), explicit_build)
    if not target:
        raise DataError('empty item CSV requires --build')
    return rows, target, next(iter(hotfixes), target.rsplit('.', 1)[1])


def normalize_trainer(raw, target):
    row = {field: raw.get(field, '') for field in TRAINER_FIELDS}
    row['RecipeSpellID'] = number(row['RecipeSpellID'], 'RecipeSpellID')
    row['RequiredAbility'] = number(row['RequiredAbility'], 'RequiredAbility', True, 0)
    row['SkillLineID'] = number(row['SkillLineID'], 'SkillLineID', True)
    row['LearnedAt'] = number(row['LearnedAt'], 'LearnedAt', True, 0)
    row['TrainerObserved'] = boolean(row['TrainerObserved'], 'TrainerObserved')
    row['SpecializationObserved'] = boolean(row['SpecializationObserved'], 'SpecializationObserved')
    npc_ids = row['NPCIDs']
    if isinstance(npc_ids, str):
        npc_ids = json.loads(npc_ids) if npc_ids else []
    if not isinstance(npc_ids, list):
        raise DataError('NPCIDs must be a JSON array')
    row['NPCIDs'] = sorted({number(value, 'NPCID') for value in npc_ids})
    if row['Status'] not in STATUSES:
        raise DataError('invalid trainer Status %r' % row['Status'])
    if row['TargetBuild'] and not BUILD.fullmatch(row['TargetBuild']):
        raise DataError('invalid persisted TargetBuild')
    row['TargetBuild'] = target
    if row['SourceEnvironment'] != 'forever':
        raise DataError('trainer evidence must belong to Forever')
    if row['SourceURL']:
        url = urlsplit(row['SourceURL'])
        if url.scheme != 'https' or url.netloc != 'www.wowhead.com' or not url.path.startswith('/forever/'):
            raise DataError('trainer SourceURL must be a Wowhead Forever URL')
        if not re.fullmatch(r'[0-9a-f]{64}', row['SourceSHA256']):
            raise DataError('web evidence requires SourceSHA256')
        try:
            stamp = datetime.fromisoformat(row['SourceFetchedAt'].replace('Z', '+00:00'))
            if stamp.tzinfo is None:
                raise ValueError('timezone missing')
        except (ValueError, AttributeError):
            raise DataError('web evidence requires an ISO SourceFetchedAt with timezone')
        if not re.fullmatch(r'1\.60\.\d+', row['SourcePatch']):
            raise DataError('web evidence must identify the Forever source patch')
    elif row['TrainerObserved'] or row['SpecializationObserved'] or row['RequiredAbility']:
        raise DataError('observed trainer evidence requires SourceURL')
    if row['TrainerSourceURL']:
        trainer_url = urlsplit(row['TrainerSourceURL'])
        if (trainer_url.scheme != 'https' or trainer_url.netloc != 'www.wowhead.com' or
                not trainer_url.path.startswith('/forever/')):
            raise DataError('TrainerSourceURL must be a Wowhead Forever URL')
        if not re.fullmatch(r'[0-9a-f]{64}', row['TrainerSourceSHA256']):
            raise DataError('trainer relationship evidence requires TrainerSourceSHA256')
        if not re.fullmatch(r'1\.60\.\d+', row['TrainerSourcePatch']):
            raise DataError('trainer relationship requires a Forever TrainerSourcePatch')
        if row['TrainerSourceBuild'] and (
                not BUILD.fullmatch(row['TrainerSourceBuild']) or
                row['TrainerSourceBuild'].rsplit('.', 1)[0] != row['TrainerSourcePatch']):
            raise DataError('TrainerSourceBuild does not match TrainerSourcePatch')
        try:
            stamp = datetime.fromisoformat(row['TrainerSourceFetchedAt'].replace('Z', '+00:00'))
            if stamp.tzinfo is None:
                raise ValueError('timezone missing')
        except (ValueError, AttributeError):
            raise DataError('trainer relationship requires a timezone-aware TrainerSourceFetchedAt')
    elif any(row[field] for field in (
            'TrainerSourceSHA256', 'TrainerSourceFetchedAt', 'TrainerSourcePatch', 'TrainerSourceBuild')):
        raise DataError('trainer relationship metadata requires TrainerSourceURL')
    if row['SourceBuild'] and not BUILD.fullmatch(row['SourceBuild']):
        raise DataError('invalid SourceBuild')
    if row['SourceBuild'] and row['SourceBuild'].rsplit('.', 1)[0] != row['SourcePatch']:
        raise DataError('SourceBuild does not match SourcePatch')
    if (row['Status'] == 'pending' and row['Reason'] in (
            'source_patch_mismatch', 'source_build_mismatch',
            'trainer_source_patch_mismatch', 'trainer_source_build_mismatch') and
            row['RequiredAbility'] and row['TrainerObserved'] and row['SpecializationObserved'] and
            row['SourcePatch'] == target.rsplit('.', 1)[0] and
            (not row['SourceBuild'] or row['SourceBuild'] == target) and
            (not row['TrainerSourceURL'] or row['TrainerSourcePatch'] == row['SourcePatch']) and
            (not row['TrainerSourceBuild'] or row['TrainerSourceBuild'] == target)):
        row['Status'], row['Reason'] = 'confirmed', 'explicit_specialization_and_trainer'
    if row['Status'] == 'confirmed' and not (
            row['RequiredAbility'] and row['TrainerObserved'] and
            row['SpecializationObserved'] and row['Evidence'] and row['SourceURL']):
        raise DataError('confirmed trainer requirement lacks explicit specialization/trainer evidence')
    if row['NPCIDs'] and not row['TrainerObserved']:
        raise DataError('NPCIDs require observed trainer relationship')
    if row['Status'] == 'confirmed':
        if row['SourcePatch'] != target.rsplit('.', 1)[0]:
            row['Status'], row['Reason'] = 'pending', 'source_patch_mismatch'
        elif row['SourceBuild'] and row['SourceBuild'] != target:
            row['Status'], row['Reason'] = 'pending', 'source_build_mismatch'
        elif row['TrainerSourceURL'] and row['TrainerSourcePatch'] != row['SourcePatch']:
            row['Status'], row['Reason'] = 'pending', 'trainer_source_patch_mismatch'
        elif row['TrainerSourceBuild'] and row['TrainerSourceBuild'] != target:
            row['Status'], row['Reason'] = 'pending', 'trainer_source_build_mismatch'
    return row


def load_trainers(path, target, snapshots):
    if not path.exists():
        return []
    snapshot(path, snapshots)
    _, rows = read_csv(path, TRAINER_FIELDS)
    return [normalize_trainer(row, target) for row in rows]


def merge_trainer_snapshots(previous, fetched, target):
    """Offline replay keeps evidence for pages missing from the cache."""
    result = {}
    for raw in list(previous) + list(fetched):
        row = normalize_trainer(raw, target)
        if not row['SourceURL']:
            continue
        key = (row['RecipeSpellID'], row['SourceURL'])
        old = result.get(key)
        stamp = datetime.fromisoformat(row['SourceFetchedAt'].replace('Z', '+00:00'))
        old_stamp = datetime.fromisoformat(old['SourceFetchedAt'].replace('Z', '+00:00')) if old else None
        if old is None or stamp > old_stamp:
            result[key] = row
        elif stamp == old_stamp and row != old:
            relationship_fields = {
                'TrainerSourceURL', 'TrainerSourceFetchedAt', 'TrainerSourceSHA256',
                'TrainerSourcePatch', 'TrainerSourceBuild', 'TrainerObserved', 'NPCIDs',
                'Status', 'Reason', 'Evidence',
            }
            if any(row[field] != old[field] for field in TRAINER_FIELDS
                   if field not in relationship_fields):
                raise DataError('conflicting source snapshots for %s' % row['SourceURL'])
            old_relation, new_relation = old['TrainerSourceURL'], row['TrainerSourceURL']
            if old_relation and not new_relation:
                # A missing offline page cannot erase a recorded NPC relationship.
                continue
            if new_relation and not old_relation:
                result[key] = row
                continue
            if new_relation and old_relation == new_relation:
                old_time = datetime.fromisoformat(old['TrainerSourceFetchedAt'].replace('Z', '+00:00'))
                new_time = datetime.fromisoformat(row['TrainerSourceFetchedAt'].replace('Z', '+00:00'))
                if new_time > old_time:
                    result[key] = row
                    continue
                if new_time < old_time:
                    continue
            raise DataError('conflicting trainer relationship snapshots for %s' % row['SourceURL'])
    return sorted(result.values(), key=lambda row: (row['RecipeSpellID'], row['SourceURL']))


def trainer_snapshot(rows, recipes, target):
    records = list(rows)
    observed = {row['RecipeSpellID'] for row in records}
    for spell in sorted(recipes - observed):
        records.append(normalize_trainer({
            'RecipeSpellID': spell, 'Status': 'pending',
            'Reason': 'no_trainer_learning_evidence', 'NPCIDs': [],
            'TrainerObserved': False, 'SpecializationObserved': False,
            'SourceEnvironment': 'forever',
        }, target))
    return sorted(records, key=lambda row: (row['RecipeSpellID'], row['SourceURL']))


def csv_bytes(rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, TRAINER_FIELDS, lineterminator='\n')
    writer.writeheader()
    for source in rows:
        row = dict(source)
        row['NPCIDs'] = json.dumps(row['NPCIDs'], separators=(',', ':'))
        for field in ('TrainerObserved', 'SpecializationObserved'):
            row[field] = 'true' if row[field] else 'false'
        writer.writerow({key: '' if row[key] is None else row[key] for key in TRAINER_FIELDS})
    return stream.getvalue().encode('utf-8-sig')


def requirement_map(items, trainers, recipes):
    entries = defaultdict(list)
    unmapped = []
    for row in items:
        evidence = {
            'kind': 'item', 'itemID': row['RecipeItemID'],
            'requiredAbility': row['RequiredAbility'], 'status': row['Status'],
            'reason': row['Reason'], 'learningPath': row['LearningPath'],
            'source': row['Source'], 'sourceBuild': row['Build'],
            'hotfixBuild': row['HotfixBuild'],
        }
        if row['RecipeSpellID']:
            entries[row['RecipeSpellID']].append(evidence)
        else:
            unmapped.append(evidence)
    for row in trainers:
        entries[row['RecipeSpellID']].append({
            'kind': 'trainer' if row['TrainerObserved'] else 'unverified_trainer',
            'requiredAbility': row['RequiredAbility'], 'status': row['Status'],
            'reason': row['Reason'], 'skillLineID': row['SkillLineID'],
            'learnedAt': row['LearnedAt'], 'npcIDs': row['NPCIDs'],
            'trainerObserved': row['TrainerObserved'],
            'specializationObserved': row['SpecializationObserved'],
            'sourceURL': row['SourceURL'], 'sourceEnvironment': row['SourceEnvironment'],
            'sourcePatch': row['SourcePatch'], 'sourceBuild': row['SourceBuild'],
            'sourceFetchedAt': row['SourceFetchedAt'], 'sourceSHA256': row['SourceSHA256'],
            'trainerSourceURL': row['TrainerSourceURL'],
            'trainerSourceFetchedAt': row['TrainerSourceFetchedAt'],
            'trainerSourceSHA256': row['TrainerSourceSHA256'],
            'trainerSourcePatch': row['TrainerSourcePatch'],
            'trainerSourceBuild': row['TrainerSourceBuild'],
            'evidence': row['Evidence'],
        })
    result = {}
    for spell in sorted(set(entries) | recipes):
        unique = {json.dumps(row, sort_keys=True, ensure_ascii=False): row for row in entries[spell]}
        routes = [unique[key] for key in sorted(unique)]
        # A different scroll or a different trainer may be an alternative route.
        groups = defaultdict(list)
        for route in routes:
            if route['kind'] == 'item':
                key = ('item', route['itemID'])
                groups[key].append(route)
            elif route['kind'] == 'trainer':
                for npc in route['npcIDs'] or [0]:
                    groups[('trainer', npc)].append(route)
        conflicts = []
        for group in groups.values():
            abilities = {route['requiredAbility'] for route in group
                         if route['status'] == 'confirmed' and route['requiredAbility']}
            if len(abilities) > 1:
                conflicts.extend(group)
        for route in conflicts:
            route['status'] = 'conflict'
            route['reason'] = 'contradictory_requirements_for_same_learning_route'
        statuses = {route['status'] for route in routes}
        status = 'conflict' if 'conflict' in statuses else (
            'confirmed' if 'confirmed' in statuses else 'pending')
        result[spell] = {
            'status': status, 'hasPending': not routes or 'pending' in statuses,
            'routes': routes,
        }
    return result, unmapped


def alias(left, right):
    return left.resolve() == right.resolve() or (
        left.exists() and right.exists() and os.path.samefile(left, right))


def validate_paths(inputs, outputs, data_dir, cache_dir):
    if alias(outputs[0], outputs[1]):
        raise DataError('trainer CSV and Lua output paths must be distinct')
    for destination in outputs:
        for source in inputs:
            if alias(destination, source):
                raise DataError('output must not overwrite input %s' % source)
        if destination.is_relative_to(cache_dir):
            raise DataError('final output must not be placed inside page cache')
    if outputs[0].suffix.lower() != '.csv' or outputs[1].suffix.lower() != '.lua':
        raise DataError('outputs must be a .csv and a .lua')


def publish(outputs):
    """Compatibility helper for the shared repository-local publisher."""
    return publish_batch(outputs)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe-items-csv', type=Path,
                        default=CSV_INPUTS['recipe_items_csv'])
    parser.add_argument('--trainer-csv', type=Path,
                        default=HERE / '_fc/data/trainer-recipe-specializations.csv')
    parser.add_argument('--output-lua', type=Path, default=PACKAGE / 'Core/Data/Data_ProfSpecializations.lua')
    parser.add_argument('--data-dir', type=Path, default=HERE / '_fc/data')
    parser.add_argument('--cache-dir', type=Path, default=HERE / '_fc/cache/specializations/wowhead-forever')
    parser.add_argument('--build', default='', help='full target build; required for an empty item CSV')
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--refresh-trainers', action='store_true')
    parser.add_argument('--dry-run', '--check', action='store_true', dest='dry_run',
                        help='do not publish CSV/Lua; network cache and cooldown may be updated')
    args = parser.parse_args(argv)
    try:
        for path in (args.trainer_csv, args.output_lua, args.cache_dir):
            require_repo_path(path)
        from fc_specialization_fetch import collect_trainers, FetchError
        if args.offline and args.refresh_trainers:
            raise DataError('--offline and --refresh-trainers cannot be combined')
        inputs = {}
        item_path, trainer_path, output_path, data_dir, cache_dir = [
            path.resolve() for path in (args.recipe_items_csv, args.trainer_csv,
                                       args.output_lua, args.data_dir, args.cache_dir)]
        recipes, catalog_sources, unresolved = catalog(data_dir, inputs)
        items, target, hotfix = item_rows(item_path, inputs, args.build)
        recipes.update(row['RecipeSpellID'] for row in items if row['RecipeSpellID'])
        validate_paths(list(inputs), [trainer_path, output_path], data_dir, cache_dir)
        # Guard against concurrent replacement throughout collection and publishing.
        old_trainer_digest = digest(trainer_path.read_bytes()) if trainer_path.exists() else None
        old_lua_digest = digest(output_path.read_bytes()) if output_path.exists() else None
        previous = load_trainers(trainer_path, target, inputs) if args.offline else []
        fetched = collect_trainers(cache_dir, offline=args.offline, refresh=args.refresh_trainers)
        trainers = merge_trainer_snapshots(previous, fetched['records'], target)
        recipes.update(row['RecipeSpellID'] for row in trainers)
        trainers = trainer_snapshot(trainers, recipes, target)
        trainer_content = csv_bytes(trainers)
        requirements, unmapped = requirement_map(items, trainers, recipes)
        counts = Counter(row['status'] for row in requirements.values())
        stats = {key: counts[key] for key in ('confirmed', 'pending', 'conflict')}
        stats.update(recipes=len(requirements), itemEvidence=len(items),
                     trainerEvidence=sum(row['TrainerObserved'] for row in trainers),
                     unmappedItems=len(unmapped), catalogWithoutSpellID=unresolved)
        metadata = {
            'schemaVersion': 1, 'targetBuild': target, 'hotfixBuild': hotfix,
            'coverage': 'observed-only',
            'statusMeaning': 'confirmed means explicit evidence for at least one learning route; not all routes',
            'pendingLabel': '待确认', 'stats': stats,
            'sources': {
                'recipeItems': {'file': item_path.name, 'sha256': inputs[item_path]},
                'trainers': {'file': trainer_path.name, 'sha256': digest(trainer_content)},
                'catalog': catalog_sources,
            },
            'unmappedItems': unmapped,
        }
        lines = ['local _, ns = ...', 'ns.ProfSpecializationsMeta = ' + lua(metadata),
                 'ns.ProfSpecializations = {']
        lines += ['    [%d] = %s,' % (spell, lua(value)) for spell, value in requirements.items()]
        lines.append('}')
        lua_content = ('\n'.join(lines) + '\n').encode('utf-8')
        for path, expected in inputs.items():
            if digest(path.read_bytes()) != expected:
                raise DataError('input changed during generation: %s' % path)
        for path, expected in ((trainer_path, old_trainer_digest), (output_path, old_lua_digest)):
            current = digest(path.read_bytes()) if path.exists() else None
            if current != expected:
                raise DataError('output changed during generation: %s' % path)
        if not args.dry_run:
            publish({trainer_path: trainer_content, output_path: lua_content})
        print('[%s] %s' % ('CHECK' if args.dry_run else 'OK', json.dumps(stats, ensure_ascii=False)))
        print('  targetBuild=%s; web SourceBuild remains unknown unless explicitly supplied' % target)
        print('  collection: %s' % json.dumps(fetched.get('coverage', {}), ensure_ascii=False))
        print('  %s (%d bytes)' % (trainer_path, len(trainer_content)))
        print('  %s (%d bytes)' % (output_path, len(lua_content)))
        return 0
    except (OSError, ValueError, csv.Error, ImportError) as error:
        print('fc_prof_specializations: %s' % error, file=sys.stderr)
        return 1
    except Exception as error:
        # FetchError is loaded lazily so --help and offline diagnostics are cheap.
        if isinstance(error, FetchError):
            print('fc_prof_specializations: %s' % error, file=sys.stderr)
            return 1
        raise


if __name__ == '__main__':
    sys.exit(main())
