"""Versioned, three-way preservation of the maintained profession catalogues.

The migration reads Lua once. Normal generation uses the checked-in JSON delta
and canonical trainer seed; no previous generated Lua is a generation input.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
DEFAULT_PATH = HERE / '_fc/maintenance/professions.json'
FILES = ('Data_Professions.lua', 'Data_ProfRecipes.lua', 'Data_ProfLeveling.lua',
         'Data_ProfGathering.lua', 'Data_ProfVendors.lua', 'Data_ProfTrainers.lua')
SCHEMAS = {
    'rows': ('spell', 'id', 'count', 'cat', 'kind', 'effect', 'learn', 'yellow',
             'green', 'grey', 'is_new', 'reagents', 'formula', 'source', 'was', 'set', 'armor'),
    'enchants': ('name', 'short', 'group', 'text', 'learn', 'yellow', 'green',
                 'grey', 'reagents', 'source', 'is_new', 'sod', 'bis', 'spell', 'created'),
    'crafted': ('spell', 'id', 'count', 'learn', 'yellow', 'green', 'grey',
                'reagents', 'taught_by', 'is_new'),
    'groups': ('key', 'label', 'icon', 'count'),
    'favor': ('id', 'skill', 'favor', 'recipe', 'makes'),
}
MISSING = {'$absent': True}


class MaintenanceError(ValueError):
    pass


def lua_runtime():
    from fc_pipeline_common import lua_runtime as create_runtime
    return create_runtime()


def lua_value(value):
    if hasattr(value, 'items'):
        return {key: lua_value(item) for key, item in value.items()}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise MaintenanceError('unsupported Lua value: %r' % (value,))


def load_sources(sources):
    """Read independent data files in memory, without evaluating external modules."""
    result = {}
    for name, content in sources.items():
        runtime = lua_runtime()
        namespace = runtime.table()
        text = content.decode('utf-8-sig') if isinstance(content, bytes) else content
        runtime.eval('function(src, ns) assert(loadstring(src))("DungeonsForever", ns) end')(text, namespace)
        if name == 'Data_ProfRecipes.lua':
            if namespace.EnsureProfRecipes is not None:
                namespace.EnsureProfRecipes()
            namespace.EnsureProfRecipes = None
        result[name] = lua_value(namespace)
    return result


def _array(table):
    if not table:
        return []
    if set(table) != set(range(1, len(table) + 1)):
        raise MaintenanceError('expected a contiguous Lua array')
    return [table[i] for i in range(1, len(table) + 1)]


def stable_key(collection, row):
    if collection == 'enchants':
        # Some maintained enchants intentionally lack a spell ID. The original
        # source name is stable across ID enrichment and is not localized.
        return 'name:' + str(row.get('name'))
    if collection == 'groups':
        return 'group:' + str(row.get('key'))
    if collection == 'favor':
        return 'item:' + str(row.get('id'))
    spell, item = row.get('spell'), row.get('id')
    if not spell and item:
        return 'item:' + str(item)
    return 'spell:%s/item:%s' % (spell, item)


def normalize(model):
    """Give recipe rows stable identities, retaining numeric keys everywhere else."""
    model = copy.deepcopy(model)
    recipes = model.get('Data_ProfRecipes.lua', {}).get('ProfRecipes', {})
    for slug, data in recipes.items():
        for collection, fields in SCHEMAS.items():
            if collection not in data:
                continue
            rows, order = {}, {}
            for i, raw in enumerate(_array(data[collection]), 1):
                row = {fields[k - 1]: v for k, v in raw.items()
                       if isinstance(k, int) and 1 <= k <= len(fields)}
                extra = {k: v for k, v in raw.items()
                         if not isinstance(k, int) or not 1 <= k <= len(fields)}
                if extra:
                    row['$extra'] = extra
                key = stable_key(collection, row)
                if key in rows:
                    raise MaintenanceError('duplicate stable key %s/%s/%s' % (slug, collection, key))
                rows[key], order[i] = row, key
            data[collection] = {'$rows': rows, '$order': order}
    return model


def denormalize(model):
    model = copy.deepcopy(model)
    recipes = model.get('Data_ProfRecipes.lua', {}).get('ProfRecipes', {})
    for slug, data in recipes.items():
        for collection, fields in SCHEMAS.items():
            if collection not in data:
                continue
            grouped = data[collection]
            order = _array(grouped['$order'])
            rows = grouped['$rows']
            if len(order) != len(set(order)) or set(order) != set(rows):
                raise MaintenanceError('invalid maintained order: %s/%s' % (slug, collection))
            output = {}
            for i, key in enumerate(order, 1):
                row = rows[key]
                raw = {k: row[field] for k, field in enumerate(fields, 1) if field in row}
                raw.update(row.get('$extra', {}))
                output[i] = raw
            data[collection] = output
    return model


def pack(value):
    """Lossless JSON encoding: Lua number keys must never become string keys."""
    if isinstance(value, dict):
        if all(isinstance(key, str) for key in value):
            return {key: pack(item) for key, item in sorted(value.items())}
        return {'$table': [[key, pack(item)] for key, item in sorted(
            value.items(), key=lambda pair: (isinstance(pair[0], str), str(pair[0])))]}
    return value


def unpack(value):
    if isinstance(value, dict) and set(value) == {'$table'}:
        return {key: unpack(item) for key, item in value['$table']}
    if isinstance(value, dict):
        return {key: unpack(item) for key, item in value.items()}
    return value


def make_changes(base, value, path=()):
    """Build field-level deltas; an absent table is an explicit add or removal."""
    if path and path[-1] == '$order':
        return [] if base == value else [{'path': list(path), 'base': pack(base), 'value': pack(value)}]
    if isinstance(base, dict) and isinstance(value, dict):
        changes = []
        for key in sorted(set(base) | set(value), key=lambda k: (isinstance(k, str), str(k))):
            if key not in base:
                changes.append({'path': [*path, key], 'base': MISSING, 'value': pack(value[key])})
            elif key not in value:
                changes.append({'path': [*path, key], 'base': pack(base[key]), 'value': MISSING})
            else:
                changes.extend(make_changes(base[key], value[key], (*path, key)))
        return changes
    if base != value:
        return [{'path': list(path), 'base': pack(base), 'value': pack(value)}]
    return []


def apply_changes(model, changes):
    """All-or-nothing three-way merge; stale assumptions never overwrite input."""
    result = copy.deepcopy(model)
    conflicts = []
    for change in changes:
        path = change['path']
        if not path:
            raise MaintenanceError('maintenance path must not replace the root')
        parent = result
        for part in path[:-1]:
            if not isinstance(parent, dict) or part not in parent:
                parent = None
                break
            parent = parent[part]
        key = path[-1]
        current = pack(parent[key]) if isinstance(parent, dict) and key in parent else MISSING
        if current == change['value']:
            continue
        if parent is None or current != change['base']:
            conflicts.append('/'.join(map(str, path)))
            continue
        if change['value'] == MISSING:
            parent.pop(key, None)
        else:
            parent[key] = unpack(change['value'])
    if conflicts:
        raise MaintenanceError('maintenance conflicts (%d): %s' % (len(conflicts), ', '.join(conflicts[:20])))
    return result


def read_manifest(path=None):
    path = Path(path or DEFAULT_PATH)
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('schema') != 1:
        raise MaintenanceError('unsupported profession maintenance schema')
    return value


def select_revision(manifest, input_sha):
    """Select a historical rule set only for an exact prepared-input identity."""
    if manifest.get('input_semantic_sha256') == input_sha:
        return manifest
    for entry in manifest.get('accepted_revisions', []):
        if entry['input_semantic_sha256'] == input_sha:
            revision = entry['manifest']
            if revision.get('input_semantic_sha256') != input_sha:
                raise MaintenanceError('historical revision input identity is inconsistent')
            return revision
    # Unknown input must still pass the current revision's three-way guards.
    return manifest


def prepared_input_sha(raw_sources):
    """Fingerprint the five prepared source namespaces before applying maintenance."""
    return semantic_sha(normalize(load_sources(raw_sources)))


def maintained_model(raw_sources, manifest):
    raw = load_sources(raw_sources)
    raw['Data_ProfTrainers.lua'] = unpack(manifest['trainer_seed'])
    return denormalize(apply_changes(normalize(raw), manifest['changes']))


def lua_literal(value):
    if value is None:
        return 'nil'
    if value is True:
        return 'true'
    if value is False:
        return 'false'
    if isinstance(value, str):
        escaped = []
        for char in value:
            if char in ('"', '\\'):
                escaped.append('\\' + char)
            elif ord(char) < 32:
                escaped.append('\\%03d' % ord(char))
            else:
                escaped.append(char)
        return '"' + ''.join(escaped) + '"'
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise MaintenanceError('Lua data cannot contain non-finite numbers')
        return str(value)
    if isinstance(value, dict):
        if not value:
            return '{}'
        # Retain holes: recipes use positional tuples with nil fields.
        if (all(isinstance(key, int) and not isinstance(key, bool) and key > 0 for key in value)
                and (max(value) <= 32 or set(value) == set(range(1, len(value) + 1)))):
            return '{ ' + ', '.join(lua_literal(value.get(i)) for i in range(1, max(value) + 1)) + ' }'
        return '{ ' + ', '.join('[%s]=%s' % (lua_literal(k), lua_literal(v))
                                for k, v in sorted(value.items(), key=lambda pair: (isinstance(pair[0], str), str(pair[0])))) + ' }'
    raise MaintenanceError('cannot serialize %s' % type(value))


def render_namespace(name, namespace):
    lines = ['local _, ns = ...', '']
    if name == 'Data_ProfRecipes.lua':
        keys = _array(namespace['ProfRecipeKeys'])
        recipes = namespace['ProfRecipes']
        if len(keys) != len(set(keys)) or set(keys) != set(recipes):
            raise MaintenanceError('recipe keys do not match the maintained partitions')
        lines += ['local PARTS = {}', 'local KEYS = %s' % lua_literal(namespace['ProfRecipeKeys']), '']
        for key in keys:
            lines.append('PARTS[%s] = function() return %s end' % (lua_literal(key), lua_literal(recipes[key])))
        lines += ['', 'ns.ProfRecipeKeys = KEYS', 'ns.ProfRecipes = setmetatable({}, {',
                  '    __index = function(t, k)', '        local f = PARTS[k]',
                  '        if not f then return nil end', '        PARTS[k] = nil',
                  '        local v = f()', '        rawset(t, k, v)', '        return v',
                  '    end,', '})', 'ns.EnsureProfRecipes = function(keys)',
                  '    local t = ns.ProfRecipes', '    local list = keys or KEYS',
                  '    for i = 1, #list do local _ = t[list[i]] end', '    return t', 'end']
    else:
        for key, value in sorted(namespace.items()):
            if not key.isidentifier():
                raise MaintenanceError('unsupported namespace key %s' % key)
            lines.append('ns.%s = %s' % (key, lua_literal(value)))
    return ('\n'.join(lines) + '\n').encode('utf-8')


def render_model(model):
    return {name: render_namespace(name, model[name]) for name in FILES}


def semantic_sha(model):
    return hashlib.sha256(json.dumps(pack(model), ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def _at(model, path):
    current = model
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return MISSING
        current = current[key]
    return pack(current)


def _merge_order(base, maintained, incoming, present):
    """Keep upstream order plus the maintained additions' relative order/anchors."""
    common_base = [key for key in base if key in maintained]
    common_maintained = [key for key in maintained if key in base]
    if common_base != common_maintained:
        raise MaintenanceError('manual reordering of shared records requires explicit review')
    output = [key for key in incoming if key in present]
    for position, key in enumerate(maintained):
        if key not in present or key in output:
            continue
        following = next((anchor for anchor in maintained[position + 1:] if anchor in output), None)
        if following is not None:
            output.insert(output.index(following), key)
        else:
            previous = next((anchor for anchor in reversed(maintained[:position]) if anchor in output), None)
            output.insert(output.index(previous) + 1 if previous is not None else len(output), key)
    # Any new upstream entries were already included. Never silently lose a row
    # introduced by another maintained rule without a sequence anchor.
    if set(output) != set(present) or len(output) != len(set(output)):
        raise MaintenanceError('rebased collection order does not cover every retained record')
    return {index: key for index, key in enumerate(output, 1)}


def prepare_rebase(previous, previous_raw, incoming_raw, approved_removals, provenance,
                   previous_input_sha=None, incoming_input_sha=None, previous_i18n_seed=None):
    """Prepare an auditable new rule revision in memory; never write or publish.

    Metadata, actual collection counts, sequence additions, and explicit UI
    suppressions are reviewed rule intents. Every other field keeps the strict
    old base/value comparison, including sources and profession thresholds.
    """
    old_raw = normalize(copy.deepcopy(previous_raw))
    new_raw = normalize(copy.deepcopy(incoming_raw))
    old_input_sha = previous_input_sha or semantic_sha(old_raw)
    new_input_sha = incoming_input_sha or semantic_sha(new_raw)
    active = select_revision(previous, old_input_sha)
    old_base = copy.deepcopy(old_raw)
    old_base['Data_ProfTrainers.lua'] = unpack(active['trainer_seed'])
    old_target = apply_changes(old_base, active['changes'])
    new_base = copy.deepcopy(new_raw)
    new_base['Data_ProfTrainers.lua'] = unpack(active['trainer_seed'])
    ordinary, intents, conflicts = [], [], []
    for change in active['changes']:
        path = change['path']
        value = _at(new_base, path)
        if value != change['base'] and value != change['value']:
            conflicts.append({'path': path, 'base': change['base'], 'value': change['value'], 'incoming': value})
        metadata = path in (['Data_Professions.lua', 'ProfData', 'build'],
                            ['Data_Professions.lua', 'ProfData', 'updated'])
        counters = (len(path) == 5 and path[:2] == ['Data_ProfRecipes.lua', 'ProfRecipes']
                    and path[3] == 'counts' and path[4] in ('total', 'items'))
        group_count = (len(path) == 7 and path[:2] == ['Data_ProfRecipes.lua', 'ProfRecipes']
                       and path[3:5] == ['groups', '$rows'] and path[-1] == 'count')
        suppression = (change['value'] == MISSING and path[:2] == ['Data_ProfRecipes.lua', 'ProfRecipes']
                       and ((len(path) == 4 and path[-1] == 'favor')
                            or (len(path) == 3 and path[-1] == 'first-aid')))
        if metadata or counters or group_count or path[-1] == '$order' or suppression:
            kind = ('accept_upstream_metadata' if metadata else 'recount_retained_rows' if counters or group_count
                    else 'merge_maintained_sequence' if path[-1] == '$order' else 'preserve_explicit_ui_suppression')
            intents.append({'path': path, 'intent': kind, 'previousBase': change['base'],
                            'previousValue': change['value'], 'incoming': value})
        else:
            ordinary.append(change)
    target = apply_changes(new_base, ordinary)
    for intent in intents:
        if intent['intent'] == 'preserve_explicit_ui_suppression':
            parent = target
            for key in intent['path'][:-1]:
                parent = parent[key]
            parent.pop(intent['path'][-1], None)
    recipes = target['Data_ProfRecipes.lua']['ProfRecipes']
    old_recipes = old_base['Data_ProfRecipes.lua']['ProfRecipes']
    maintained_recipes = old_target['Data_ProfRecipes.lua']['ProfRecipes']
    upstream_recipes = new_base['Data_ProfRecipes.lua']['ProfRecipes']
    counts = []
    for slug, data in recipes.items():
        for collection in SCHEMAS:
            if collection not in data:
                continue
            original = old_recipes.get(slug, {}).get(collection, {}).get('$order', {})
            maintained = maintained_recipes.get(slug, {}).get(collection, {}).get('$order', {})
            incoming = upstream_recipes.get(slug, {}).get(collection, {}).get('$order', {})
            data[collection]['$order'] = _merge_order(_array(original), _array(maintained), _array(incoming),
                                                      data[collection]['$rows'])
        rows = data.get('rows', {}).get('$rows', {})
        if isinstance(data.get('counts'), dict):
            if 'total' in data['counts']:
                data['counts']['total'] = len(rows)
            if 'items' in data['counts']:
                data['counts']['items'] = sum(bool(row.get('formula')) for row in rows.values())
        for group in data.get('groups', {}).get('$rows', {}).values():
            if 'count' in group:
                group['count'] = sum(row.get('cat') == group.get('key') for row in rows.values())
        counts.append({'profession': slug, 'rows': len(rows), 'counts': data.get('counts'),
                       'groups': {key: row.get('count') for key, row in data.get('groups', {}).get('$rows', {}).items()}})
    target_build = target['Data_Professions.lua']['ProfData']['build']
    reviewed = []
    for approval in approved_removals:
        required = {'namespace', 'profession', 'collection', 'spell', 'item', 'target_build', 'reason', 'approval'}
        if set(approval) != required or approval['namespace'] != 'ProfRecipes' or approval['target_build'] != target_build:
            raise MaintenanceError('approved removal must specify an exact recipe identity and target build')
        identity = 'spell:%s/item:%s' % (approval['spell'], approval['item'])
        slug, collection = approval['profession'], approval['collection']
        old_row = maintained_recipes.get(slug, {}).get(collection, {}).get('$rows', {}).get(identity)
        upstream_row = upstream_recipes.get(slug, {}).get(collection, {}).get('$rows', {}).get(identity)
        result_row = recipes.get(slug, {}).get(collection, {}).get('$rows', {}).get(identity)
        if not old_row or upstream_row is not None or result_row is not None:
            raise MaintenanceError('approved removal does not match an old row absent from reviewed upstream')
        if old_row.get('spell') != approval['spell'] or old_row.get('id') != approval['item']:
            raise MaintenanceError('approved removal stable identity mismatch')
        reviewed.append(dict(approval, previous_record=pack(old_row)))
    # Rebase itself must not introduce any other loss relative to the maintained
    # catalogue. Any newly missing stable record needs its own exact approval.
    allowed = {(row['profession'], row['collection'], 'spell:%s/item:%s' % (row['spell'], row['item']))
               for row in approved_removals}
    for slug, data in maintained_recipes.items():
        for collection in SCHEMAS:
            for key in data.get(collection, {}).get('$rows', {}):
                if key not in recipes.get(slug, {}).get(collection, {}).get('$rows', {}) and (slug, collection, key) not in allowed:
                    raise MaintenanceError('unapproved maintained record removal: %s/%s/%s' % (slug, collection, key))
    revision = int(previous.get('revision', 1)) + 1
    archived = copy.deepcopy(active)
    archived.pop('accepted_revisions', None)
    archived['revision'] = int(active.get('revision', 1))
    archived['input_semantic_sha256'] = old_input_sha
    archived['input_fingerprint_phase'] = 'prepared-source-before-i18n'
    if previous_i18n_seed is not None:
        archived['historical_i18n_seed'] = copy.deepcopy(previous_i18n_seed)
    accepted = copy.deepcopy(previous.get('accepted_revisions', []))
    accepted = [entry for entry in accepted if entry['input_semantic_sha256'] != old_input_sha]
    accepted.append({'input_semantic_sha256': old_input_sha, 'revision': archived['revision'], 'manifest': archived})
    updated = copy.deepcopy(active)
    updated.pop('historical_i18n_seed', None)
    rebased_changes = make_changes(new_base, target)
    changed_paths = {tuple(change['path']) for change in rebased_changes}
    carried_guards = []
    for change in ordinary:
        path = change['path']
        desired = _at(target, path)
        if tuple(path) not in changed_paths and desired == change['value']:
            if _at(new_base, path) != desired:
                raise MaintenanceError('manual guard does not match reviewed upstream at %s' % path)
            rebased_changes.append({'path': path, 'base': desired, 'value': desired,
                                    'intent': 'retain_manual_guard_after_upstream_caught_up'})
            carried_guards.append({'path': path, 'previousBase': change['base'],
                                   'previousValue': change['value'], 'reviewedValue': desired})
    updated.update({'revision': revision, 'input_semantic_sha256': new_input_sha,
                    'input_fingerprint_phase': 'prepared-source-before-i18n', 'accepted_revisions': accepted,
                    'approved_removals': copy.deepcopy(approved_removals),
                    'baseline_semantic_sha256': semantic_sha(denormalize(target)),
                    'changes': rebased_changes})
    updated['provenance'] = dict(updated['provenance'], target_build=target_build,
                                  rebase=copy.deepcopy(provenance), revision=revision)
    audit = {'schema': 1, 'revision': revision, 'previous_revision': archived['revision'],
             'previous_input_semantic_sha256': old_input_sha, 'incoming_input_semantic_sha256': new_input_sha,
             'provenance': copy.deepcopy(provenance), 'resolved_conflicts': conflicts, 'rule_intents': intents,
             'carried_forward_manual_guards': carried_guards,
             'approved_removals': reviewed, 'retained_collection_counts': counts,
             'count_policy': {'total': 'retained rows', 'items': 'retained rows carrying a formula',
                              'groups': 'retained rows matching each category',
                              'sourced/unreadable': 'latest upstream coverage counters'},
             'target_semantic_sha256': updated['baseline_semantic_sha256'],
             'previous_maintenance_operations': len(active['changes']),
             'rebased_maintenance_operations': len(updated['changes'])}
    if apply_changes(new_base, updated['changes']) != target:
        raise MaintenanceError('rebased rules fail exact target replay')
    return updated, audit


def migrate(reference_dir, data_dir, output_path=DEFAULT_PATH):
    """Explicit one-time migration; never called by render_data or normal CLI."""
    import fc_gen
    reference = Path(reference_dir).resolve()
    output = Path(output_path).resolve()
    repo = HERE.parent.parent.resolve()
    if repo not in reference.parents or repo not in output.parents:
        raise MaintenanceError('migration reads and writes must stay inside the current repository')
    current_sources = {name: (reference / name).read_bytes() for name in FILES}
    current = load_sources(current_sources)
    area_text = (reference / 'Data_AreaMap.lua').read_text(encoding='utf-8')
    import re
    area_map = {int(a): int(b) for a, b in re.findall(r'\[(\d+)\] = (\d+)', area_text)}
    raw = load_sources(fc_gen.render_unmaintained(data_dir, area_map=area_map))
    raw['Data_ProfTrainers.lua'] = copy.deepcopy(current['Data_ProfTrainers.lua'])
    catalog_evidence = []
    recipe_snapshot = HERE / '_wx_recipes.json'
    if recipe_snapshot.exists():
        candidates = {}
        for recipe in json.loads(recipe_snapshot.read_text(encoding='utf-8')):
            if recipe.get('name') and recipe.get('spell'):
                candidates.setdefault(recipe['name'], set()).add(recipe['spell'])
        for data in current['Data_ProfRecipes.lua']['ProfRecipes'].values():
            for enchant in data.get('enchants', {}).values():
                name = enchant.get(1)
                spells = candidates.get(name, set())
                if not enchant.get(14) and len(spells) == 1:
                    catalog_evidence.append({
                        'collection': 'enchants', 'name': name, 'spell': next(iter(spells)),
                        'source': {'file': recipe_snapshot.name,
                                   'sha256': hashlib.sha256(recipe_snapshot.read_bytes()).hexdigest(),
                                   'relationship': 'exact source recipe name and explicit spell ID'},
                    })
    manifest = {
        'schema': 1,
        'baseline_semantic_sha256': semantic_sha(current),
        'provenance': {'description': 'Current repository semantic baseline; no game installation input',
                       'target_build': current['Data_Professions.lua']['ProfData']['build'],
                       'source_files': {name: hashlib.sha256(data).hexdigest() for name, data in current_sources.items()},
                       'normalized_inputs': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                             for p in sorted(Path(data_dir).glob('*.json'))},
                       'generation_inputs': {name: hashlib.sha256(path.read_bytes()).hexdigest()
                                             for name, path in fc_gen.generation_input_paths(data_dir).items()
                                             if name != 'maintenance/professions.json'},
                       'generator_sources': {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                                             for name in ('fc_gen.py', 'fc_i18n.py', 'fc_maintenance.py')},
                       'supplemental_sources': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                               for p in sorted(HERE.glob('_wx_*.json'))
                                               if p.name in ('_wx_manifest.json', '_wx_recipes.json', '_wx_categories.json')}},
        'area_map': pack(area_map),
        'catalog_id_evidence': sorted(catalog_evidence, key=lambda entry: entry['name']),
        'trainer_seed': pack(current['Data_ProfTrainers.lua']),
        'changes': make_changes(normalize(raw), normalize(current)),
    }
    # Prove that every maintained field, deletion, collection, and order replays.
    if maintained_model(fc_gen.render_unmaintained(data_dir, area_map=area_map), manifest) != current:
        raise MaintenanceError('migration does not replay the complete current baseline')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('maintained %d field changes in %s' % (len(manifest['changes']), output))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--migrate-from', type=Path, required=True)
    parser.add_argument('--data-dir', type=Path, default=HERE / '_fc/data')
    parser.add_argument('--output', type=Path, default=DEFAULT_PATH)
    options = parser.parse_args()
    migrate(options.migrate_from, options.data_dir, options.output)
