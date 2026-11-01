"""Compare generated facts with the native consumer view, never a build input.

This optional post-build audit reads existing Lua solely for comparison. Neither
fetch nor build imports it, and its output cannot fill missing source facts.
"""
import argparse
import json
from pathlib import Path

from benchmark_delivery import native


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding='utf8'))
    lua = native()
    find = lua.globals().ns['ProfEconomy']['FindRecipe']
    slug_for = lua.globals().ns['ProfEconomy']['ProfessionSlug']
    conflicts = []
    compared = 0
    for slug, records in sorted(report['facts'].items()):
        for spell, fact in sorted(records.items(), key=lambda pair: int(pair[0])):
            recipe = find(slug, int(spell))
            if recipe is None or not isinstance(recipe['learn'], (int, float)):
                continue
            reference = recipe['catalogueLearn'] if isinstance(recipe['catalogueLearn'], (int, float)) else recipe['learn']
            compared += 1
            for route in fact.get('routes', []):
                for condition in route.get('conditions', []):
                    profession = condition.get('profession')
                    if not profession and condition.get('professionID'):
                        profession = slug_for(condition['professionID'])
                    profession = profession or slug
                    if (condition.get('kind') == 'skill' and profession == slug
                            and condition.get('value') != reference):
                        conflicts.append(dict(profession=slug, spell=int(spell), route=route['id'],
                                              sourceValue=condition.get('value'),
                                              retainedDevValue=reference, effectiveRuntimeValue=recipe['learn'],
                                              decision='confirmedAutomaticSkillGrant' if recipe['skillSource']=='automaticSkillGrant' else 'retainDev',
                                              routeStatus=route.get('status')))
    result = dict(generationInput=False, build=report['build'],
                  fingerprint=report['fingerprint'], comparedNativeRecipes=compared,
                  scope='own-profession learning skill thresholds only; no source generation',
                  numericConflicts=conflicts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(comparedNativeRecipes=compared, conflicts=len(conflicts))))


if __name__ == '__main__':
    main()
