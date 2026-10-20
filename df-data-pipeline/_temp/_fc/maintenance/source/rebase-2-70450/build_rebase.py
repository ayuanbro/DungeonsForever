"""Explicit reviewed 2026-10-21 rebase; outputs stay in maintenance/source.

The completed latest web cache and the old translation snapshot are migration
inputs only. Daily rendering consumes the self-contained professions manifest.
"""
from pathlib import Path
import copy
import hashlib
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[6]
SCRIPTS = ROOT / 'df-data-pipeline/_temp'
SOURCE = Path(__file__).resolve().parent
CACHE = ROOT / '.pipeline-runtime/csv-review-20261021/cache'
OLD_ZH = ROOT / '.pipeline-runtime/online-check-20261021/diagnostics/normalized/zh.json'
sys.path.insert(0, str(SCRIPTS))
import fc_gen
import fc_parse
import fc_zones
import fc_maintenance as maintenance


def sha(content):
    return hashlib.sha256(content).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def record(name, content):
    path = (SOURCE / name).resolve()
    if SOURCE not in path.parents:
        raise ValueError('rebase evidence must stay within its versioned source directory')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def retain_runtime_fallback(updated, audit, old_model, new_model):
    """Keep one valid legacy recipe callable after its fixed guide step changes."""
    updated, audit = copy.deepcopy(updated), copy.deepcopy(audit)
    path = ['Data_ProfLeveling.lua', 'ProfLeveling', 'enchanting', 'rinfo', 13746]
    previous = maintenance.select_revision(updated, audit['previous_input_semantic_sha256'])
    old_base = maintenance.normalize(copy.deepcopy(old_model))
    old_base['Data_ProfTrainers.lua'] = maintenance.unpack(previous['trainer_seed'])
    old_target = maintenance.apply_changes(old_base, previous['changes'])
    value = maintenance._at(old_target, path)
    expected = maintenance.pack({'learn': 205, 'yellow': 225, 'green': 245, 'grey': 265,
                                 'mats': {1: {1: 11137, 2: 1}}, 'trainer': True})
    if value != expected:
        raise ValueError('reviewed legacy 13746 fallback changed; inspect before retaining')
    incoming = maintenance.normalize(copy.deepcopy(new_model))
    incoming['Data_ProfTrainers.lua'] = maintenance.unpack(updated['trainer_seed'])
    if maintenance._at(incoming, path) != maintenance.MISSING:
        raise ValueError('latest source now carries 13746; review the fallback rule base')
    change = {'path': path, 'base': maintenance.MISSING, 'value': value,
              'intent': 'retain_legacy_runtime_recipe_fallback'}
    existing = next((entry for entry in updated['changes'] if entry['path'] == path), None)
    if existing is not None and existing != change:
        raise ValueError('13746 already has a different maintained rule')
    if existing is None:
        updated['changes'].append(change)
    evidence = {
        'path': path, 'base': maintenance.MISSING, 'value': value,
        'previous_target_semantic_sha256': previous['baseline_semantic_sha256'],
        'old_frozen_input': 'source/rebase-2-70450/previous-input-model.json',
        'latest_frozen_input': 'source/rebase-2-70450/incoming-input-model.json',
        'reason': ('The latest fixed guide replaces spell 13746 with 13815 for 218-225. '
                   'The surviving enchant catalogue row intentionally has no spell field 14. '
                   'ProfEconomy.FindRecipe and the automatic planner therefore still require '
                   'this numeric fallback. Retain its existing recipe capability without '
                   'changing the latest guide steps or restoring the suppressed main-row ID.'),
        'runtime_consumers': ['Core/ProfEconomy.lua:FindRecipe', 'Core/ProfEconomy.lua:Capture',
                              'Core/ProfRouteAuto.lua:rinfo candidate fallback'],
        'authorization': 'Preserve existing data and functionality; no additional recipe deletion.',
    }
    updated['provenance']['rebase']['runtime_fallback_preservations'] = [evidence]
    audit['provenance']['runtime_fallback_preservations'] = [evidence]
    audit['runtime_fallback_preservations'] = [evidence]
    target = maintenance.denormalize(maintenance.apply_changes(incoming, updated['changes']))
    updated['baseline_semantic_sha256'] = maintenance.semantic_sha(target)
    audit['target_semantic_sha256'] = updated['baseline_semantic_sha256']
    audit['rebased_maintenance_operations'] = len(updated['changes'])
    return updated, audit, target


def preserve_catalog_source_provenance(updated, audit, previous_bytes):
    """Attribute manual-only partitions to their frozen original baseline."""
    updated, audit = copy.deepcopy(updated), copy.deepcopy(audit)
    previous = json.loads(previous_bytes)
    if previous['provenance']['target_build'] != '1.60.1.70338':
        raise ValueError('reviewed manual catalogue source baseline changed')
    sources = {slug: {
        'kind': 'preserved_manual_partition',
        'source_build': '1.60.1.70338',
        'source_file': 'source/rebase-2-70450/revision-1-manifest.json',
        'source_sha256': sha(previous_bytes),
        'record_path': ['Data_ProfRecipes.lua', 'ProfRecipes', slug],
        'baseline_lua': {'file': 'Core/Data/Data_ProfRecipes.lua',
                         'sha256': previous['provenance']['source_files']['Data_ProfRecipes.lua']},
        'status': 'preserved baseline; not reverified against the latest upstream webpage',
    } for slug in ('poisons', 'comprehension')}
    updated['supplemental_catalog_sources'] = sources
    for accepted in updated.get('accepted_revisions', []):
        accepted['manifest']['supplemental_catalog_sources'] = copy.deepcopy(sources)
    audit['supplemental_catalog_sources'] = copy.deepcopy(sources)
    return updated, audit


def main():
    if '--retain-reviewed-catalog-provenance' in sys.argv:
        updated = maintenance.read_manifest()
        if updated.get('revision') != 2:
            raise ValueError('catalogue provenance amendment requires reviewed revision 2')
        audit = json.loads((SOURCE / 'audit.json').read_text(encoding='utf-8'))
        previous_bytes = (SOURCE / 'revision-1-manifest.json').read_bytes()
        updated, audit = preserve_catalog_source_provenance(updated, audit, previous_bytes)
        record('audit.json', encoded(audit))
        record('revision-2-manifest.json', encoded(updated))
        maintenance.DEFAULT_PATH.write_bytes(encoded(updated))
        print('retained 70338 source provenance for manual poison/comprehension catalogues')
        return
    if '--retain-reviewed-runtime-fallback' in sys.argv:
        updated = maintenance.read_manifest()
        if updated.get('revision') != 2:
            raise ValueError('runtime fallback amendment requires reviewed revision 2')
        audit = json.loads((SOURCE / 'audit.json').read_text(encoding='utf-8'))
        old_model = maintenance.unpack(json.loads((SOURCE / 'previous-input-model.json').read_text(encoding='utf-8')))
        new_model = maintenance.unpack(json.loads((SOURCE / 'incoming-input-model.json').read_text(encoding='utf-8')))
        updated, audit, target = retain_runtime_fallback(updated, audit, old_model, new_model)
        record('audit.json', encoded(audit))
        record('revision-2-manifest.json', encoded(updated))
        record('target-model.json', encoded(maintenance.pack(target)))
        maintenance.DEFAULT_PATH.write_bytes(encoded(updated))
        print('retained reviewed runtime fallback enchanting:13746 in revision 2')
        return
    if '--apply-reviewed-rebase' not in sys.argv:
        raise SystemExit('explicit --apply-reviewed-rebase required; this is a historical migration tool')
    original_bytes = maintenance.DEFAULT_PATH.read_bytes()
    previous = json.loads(original_bytes)
    if previous.get('revision', 1) != 1:
        raise ValueError('this one-time migration requires the original revision 1 manifest')
    old_seed = json.loads(OLD_ZH.read_text(encoding='utf-8'))
    latest_seed = json.loads(Path(fc_gen.ZH_PATH).read_text(encoding='utf-8'))
    fc_parse.CACHE = str(CACHE)
    index, details = fc_parse.build()
    if index['build'] != '1.60.1.70450' or index['updated'] != '2026-10-16':
        raise ValueError('latest checked upstream changed; review the new source before rebasing')
    normalized = {'index.json': index, 'item_ids.json': fc_parse.collect_item_ids(index, details)}
    normalized.update({'prof_%s.json' % slug: value for slug, value in details.items() if value is not None})
    inputs = SOURCE / 'normalized'
    inputs.mkdir(parents=True, exist_ok=True)
    for name, path in fc_gen.generation_input_paths().items():
        if name.startswith('prof_') or name in ('index.json', 'item_ids.json') or name.startswith('maintenance/'):
            continue
        if name.startswith('questie/'):
            # Its exact hash and the complete prepared model are recorded below;
            # daily input remains the unchanged canonical Questie snapshot.
            continue
        target = inputs / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    for name, value in normalized.items():
        record('normalized/' + name, encoded(value))
    fc_zones.DATA = str(inputs)
    zone_table = fc_zones.load_name_index(str(CACHE / fc_zones.CSV_NAME))
    wanted = fc_zones.wanted_zones()
    if wanted - zone_table.keys():
        raise ValueError('latest AreaTable lacks a requested profession zone')
    record('normalized/zone_ids.json', encoded({zone: zone_table[zone] for zone in sorted(wanted)}))
    area = maintenance.unpack(previous['area_map'])
    old_data = SCRIPTS / '_fc/data'
    old_sources = fc_gen.render_unmaintained(old_data, area_map=area, i18n_seed=old_seed)
    new_sources = fc_gen.render_unmaintained(inputs, area_map=area, i18n_seed=latest_seed)
    old_model, new_model = maintenance.load_sources(old_sources), maintenance.load_sources(new_sources)
    old_prepared = fc_gen.render_unmaintained(old_data, area_map=area, no_i18n=True)
    new_prepared = fc_gen.render_unmaintained(inputs, area_map=area, no_i18n=True)
    old_input_sha = maintenance.prepared_input_sha(old_prepared)
    new_input_sha = maintenance.prepared_input_sha(new_prepared)
    approval = {'namespace': 'ProfRecipes', 'profession': 'alchemy', 'collection': 'rows',
                'spell': 1251750, 'item': 250952, 'target_build': '1.60.1.70450',
                'reason': 'User chose to follow the reviewed latest upstream catalogue removal.',
                'approval': '跟随最新网页，从生成数据中移除1251750（item250952）'}
    pages = [CACHE / 'professions.html', *sorted(CACHE.glob('professions_*.html'))]
    provenance = {
        'date': '2026-10-21', 'reviewed_source_build': index['build'], 'reviewed_source_updated': index['updated'],
        'previous_manifest_sha256': sha(original_bytes),
        'page_sources': {path.name: sha(path.read_bytes()) for path in pages},
        'old_normalized_sources': {path.name: sha(path.read_bytes()) for path in sorted(old_data.glob('*.json'))},
        'new_normalized_sources': {path.name: sha(path.read_bytes()) for path in sorted(inputs.glob('*.json'))},
        'support_inputs': {name: sha(path.read_bytes()) for name, path in fc_gen.generation_input_paths().items()
                           if not name.startswith('maintenance/')},
        'old_i18n_sha256': sha(encoded(old_seed)), 'new_i18n_sha256': sha(encoded(latest_seed)),
        'approved_removal_sources': {
            'old_formal_recipes_sha256': sha((ROOT / 'Core/Data/Data_ProfRecipes.lua').read_bytes()),
            'old_prof_alchemy_sha256': sha((old_data / 'prof_alchemy.json').read_bytes()),
            'new_prof_alchemy_sha256': sha((inputs / 'prof_alchemy.json').read_bytes()),
            'new_webpage_sha256': sha((CACHE / 'professions_alchemy.html').read_bytes()),
            'stable_identity': 'spell:1251750/item:250952', 'approval': approval['approval']},
        'audit_file': 'source/rebase-2-70450/audit.json',
    }
    updated, audit = maintenance.prepare_rebase(previous, old_model, new_model, [approval], provenance,
                                                old_input_sha, new_input_sha, old_seed)
    updated, audit, _ = retain_runtime_fallback(updated, audit, old_model, new_model)
    updated, audit = preserve_catalog_source_provenance(updated, audit, original_bytes)
    record('revision-1-manifest.json', original_bytes)
    record('previous-input-model.json', encoded(maintenance.pack(old_model)))
    record('incoming-input-model.json', encoded(maintenance.pack(new_model)))
    record('old-i18n-seed.json', encoded(old_seed))
    record('audit.json', encoded(audit))
    record('revision-2-manifest.json', encoded(updated))
    # Prove both exact revisions before installing the default rule manifest.
    old_active = maintenance.select_revision(updated, old_input_sha)
    replay_old = maintenance.maintained_model(old_sources, old_active)
    if maintenance.semantic_sha(replay_old) != previous['baseline_semantic_sha256']:
        raise ValueError('historical 70245 inputs no longer replay the exact 70338 baseline')
    replay_new = maintenance.maintained_model(new_sources, updated)
    if maintenance.semantic_sha(replay_new) != updated['baseline_semantic_sha256']:
        raise ValueError('reviewed 70450 target replay mismatch')
    record('target-model.json', encoded(maintenance.pack(replay_new)))
    maintenance.DEFAULT_PATH.write_bytes(encoded(updated))
    print('installed revision 2: %d guarded changes, %d historical guards, %d reviewed conflicts' % (
        len(updated['changes']), len(audit['carried_forward_manual_guards']), len(audit['resolved_conflicts'])))


if __name__ == '__main__':
    main()
