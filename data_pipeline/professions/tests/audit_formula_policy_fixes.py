"""Reproduce source coverage and immutable-data checks for the policy fixes.

Uses the recorded same-build snapshot and exact verified response hashes.
Writes no addon data and makes no claim about live stock or quest completion.
"""
import csv
import hashlib
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'validation'), str(ROOT / '.pipeline-runtime/lib')]
from data_pipeline.professions.model import checked_bytes, parse_page
from test_prof_production_learning import production_runtime


def audit():
    run = ROOT / '.pipeline-runtime/formula-policy-fixes-20261030'
    raw = ROOT / '.pipeline-runtime/formula-purchase-fix-20261030/df-learning-replay-546danv8'
    manifest = json.loads((raw / 'manifest.json').read_text(encoding='utf-8'))
    responses = {r['key']: r for r in manifest['responses']}
    provider_audit = json.loads((ROOT / '.pipeline-runtime/formula-purchase-fix-20261030/audit.json').read_text(encoding='utf-8'))
    baseline = json.loads((run / 'data-before.json').read_text(encoding='utf-8'))
    current = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in (ROOT / 'Core/Data').rglob('*') if p.is_file()}
    assert baseline == current, 'Core/Data changed during this task'
    fixtures = json.loads((Path(__file__).parent / 'fixtures/formula_bindings_20261030.json').read_text(encoding='utf-8'))
    evidence = []
    for row in fixtures:
        r = responses['web:item:' + str(row['item'])]
        assert r['status'] == 'verified' and r['sha256'] == row['sha256']
        page = parse_page(checked_bytes(raw, r), 'item', row['item'], r['finalUrl'])
        assert page['bindingType'] == 1
        evidence.append({k: row[k] for k in ('item', 'url', 'sha256', 'sourcePath')})
    lua = production_runtime();ns = lua.globals().ns
    native = {(r['profession'], int(r['spell'])) for r in csv.DictReader(
        (ROOT / '.pipeline-runtime/formula-policy-data-audit-20261030/native-catalogue.csv').open(encoding='utf-8-sig'))}
    before_ids, after_ids, specs = set(), set(), []
    before_routes = after_routes = native_before = native_after = 0
    recovered_faction = unknown_faction = neutral_faction = 0
    for slug, records in provider_audit['facts'].items():
        for spell, record in records.items():
            spell = int(spell)
            view = ns.ProfEconomy.GetLearningInfo(slug, spell)
            for route in record['routes']:
                if route['kind'] != 'item':
                    continue
                item = route['teachingItemID'];a = route['acquisition']
                actual = next(r for r in view['routes'].values() if r['teachingItemID'] == item)
                if 'nonAuctionable' not in a:
                    before_routes += 1;before_ids.add(item)
                    native_before += (slug, spell) in native
                if actual['acquisition']['nonAuctionable'] is None:
                    after_routes += 1;after_ids.add(item)
                    native_after += (slug, spell) in native
                for vendor in a.get('vendors', []):
                    if not (vendor.get('hasExtendedCost') or vendor.get('currencies') or vendor.get('costItems')):
                        continue
                    facts = ns.ProfSupply.FormulaFacts(item)[vendor['id']]
                    side = vendor.get('faction') or (facts['faction'] if facts else None)
                    recovered_faction += side in ('A', 'H')
                    neutral_faction += side == 'N';unknown_faction += side is None
            if ns.ProfGates.RequiredAbility(spell) == 0:
                probe = lua.table_from({'profession': slug, 'spell': spell})
                ns.ProfEconomy.AttachLearningInfo(probe, True)
                groups = probe['learningSpecializations']
                if groups:
                    specs.append({'profession': slug, 'spell': spell, 'native': (slug, spell) in native,
                                  'alternatives': [list(g.values()) for g in groups.values()]})
    result = {
        'build': manifest['build'], 'offline': True, 'coreDataUnchanged': len(current),
        'providerFingerprint': ns.ProfLearningSources.meta.fingerprint,
        'binding': {'beforeUniqueMissing': len(before_ids), 'afterUniqueMissing': len(after_ids),
                    'beforeMissingRoutes': before_routes, 'afterMissingRoutes': after_routes,
                    'nativeBeforeMissingRoutes': native_before, 'nativeAfterMissingRoutes': native_after,
                    'remainingUnknownItems': sorted(after_ids), 'verifiedAdditions': evidence},
        'currencyVendorFaction': {'singleFaction': recovered_faction, 'neutral': neutral_faction,
                                 'unknownPreserved': unknown_faction},
        'supplementalSpecializations': specs,
        'auctionAdmission': 'Positive finite price and recent complete owner-excluded quantity >= 2; binding and source metadata never veto a teaching-item market quote. Specialization requirements remain enforced.',
        'rawStructure': {'rules': 7, 'added': ['bindingType', 'bindingSource', 'bindOnPickup', 'SpecializationGroups'],
                        'legacyCompatibility': 'No tuple replacement, TOC change or original-data rewrite'},
    }
    for name in ('benchmark-capture', 'benchmark-source-policy'):
        result[name] = json.loads((run / (name + '.json')).read_text(encoding='utf-8'))
    result['validation'] = {}
    for name in ('runtime', 'pipeline'):
        text = (run / (name + '-tests.log')).read_text(encoding='utf-8', errors='replace')
        count = re.search(r'Ran (\d+) tests', text)
        assert count and re.search(r'^OK\s*$', text, re.M), 'validation did not pass: ' + name
        result['validation'][name] = {'tests': int(count[1]), 'passed': True}
    path = ROOT / 'data_pipeline/professions/reports/formula-policy-fixes-2026-10-30.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('binding', 'benchmark-capture', 'benchmark-source-policy')}, ensure_ascii=False, indent=2))
    print('binding:', before_routes, '->', after_routes, 'routes;', len(before_ids), '->', len(after_ids), 'items; native', native_before, '->', native_after)


if __name__ == '__main__':
    audit()
