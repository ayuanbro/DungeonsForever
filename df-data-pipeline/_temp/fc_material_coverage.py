"""Report static recipe reagents without claiming that all should be NPC goods."""
import json

from fc_pipeline_common import PipelineError, require_repo_path, sha

TARGET_PROFESSIONS = frozenset(('engineering', 'alchemy', 'leatherworking', 'tailoring', 'blacksmithing'))


def reagent_coverage(catalog_dir, offers):
    """Return coverage and fingerprints for the exact catalog bytes consumed.

    ``offers`` is the collector's qualified numeric item/merchant map. Missing
    NPC evidence is a coverage outcome, never a request to grant eligibility.
    """
    directory = require_repo_path(catalog_dir)
    files = sorted(directory.glob('prof_*.json'))
    if not files:
        raise PipelineError('material reagent coverage requires a profession catalog')
    groups = {}
    observations = []
    for path in files:
        path = require_repo_path(path)
        content = path.read_bytes()
        try:
            data = json.loads(content)
        except (ValueError, UnicodeDecodeError) as error:
            raise PipelineError('invalid material coverage catalog: %s' % path) from error
        slug = path.stem[len('prof_'):]
        if not isinstance(data, dict):
            raise PipelineError('invalid material coverage profession: %s' % slug)
        all_ids, below225 = set(), set()
        for collection in ('rows', 'enchants', 'crafted'):
            rows = data.get(collection) or []
            if not isinstance(rows, list):
                raise PipelineError('invalid material coverage recipe collection')
            for recipe in rows:
                if not isinstance(recipe, dict) or not isinstance(recipe.get('reagents', []), list):
                    raise PipelineError('invalid material coverage recipe')
                learning = recipe.get('learn')
                low = type(learning) in (int, float) and 0 <= learning < 225
                for reagent in recipe.get('reagents', []):
                    if not isinstance(reagent, list) or len(reagent) != 2 \
                            or type(reagent[0]) is not int or reagent[0] <= 0 \
                            or type(reagent[1]) not in (int, float) or reagent[1] <= 0:
                        raise PipelineError('invalid material coverage reagent')
                    all_ids.add(reagent[0])
                    if low:
                        below225.add(reagent[0])
        groups[slug] = (all_ids, below225)
        observations.append({'role': 'material_reagent_catalog', 'path': str(path), 'sha256': sha(content)})

    qualified = {'a': set(), 'h': set()}
    for item, entry in offers.items():
        for offer in entry.get('offers', {}).values():
            if offer.get('side') in ('a', 'n'):
                qualified['a'].add(int(item))
            if offer.get('side') in ('h', 'n'):
                qualified['h'].add(int(item))

    def describe(ids):
        any_side = qualified['a'] | qualified['h']
        return {'materialCount': len(ids), 'qualifiedForAnyFaction': len(ids & any_side),
                'withoutConfirmedNpcSupply': sorted(ids - any_side),
                'allianceWithoutConfirmedNpcSupply': sorted(ids - qualified['a']),
                'hordeWithoutConfirmedNpcSupply': sorted(ids - qualified['h'])}

    all_ids = set().union(*(values[0] for values in groups.values()))
    five225 = set().union(*(values[1] for slug, values in groups.items() if slug in TARGET_PROFESSIONS))
    report = {'scope': 'static_recipe_reagents_not_dynamic_routes',
              'meaning': 'Missing NPC evidence continues through AH or crafting; it is not a route failure.',
              'allProfessions': describe(all_ids), 'fiveProfessionsBelow225': describe(five225),
              'professions': {slug: {'all': describe(values[0]), 'below225': describe(values[1])}
                              for slug, values in sorted(groups.items())}}
    return report, observations
