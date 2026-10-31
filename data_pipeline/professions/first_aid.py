"""Generate native First Aid sections from checksum-verified Forever sources.

Never reads historical catalogues/candidate JSON. Existing guide quantities and
other professions are preserved. The audit records every field's source.
"""
from __future__ import annotations
import argparse
import csv
import io
import json
from pathlib import Path
import re

from .model import SourceError, checked_bytes, parse_page, write_json

START = '-- BEGIN GENERATED FIRST AID'
END = '-- END GENERATED FIRST AID'


def native_without_first_aid_update(text):
    """Boundary audits still compare every byte outside the authorized sections."""
    text = text.replace('\r\n', '\n')
    text = re.sub(r'^ *' + re.escape(START) + r'.*?' + re.escape(END) + r'\n\n?', '', text, flags=re.S | re.M)
    return re.sub(r'(\["first-aid"\] = \{.*?recipes = )\d+',
                  lambda match: match[1] + '<FIRST_AID_COUNT>', text, count=1, flags=re.S)


GROUPS = {
    2530: ('Bandages', '绷带', '繃帶', 'inv_misc_bandage_15'),
    2531: ('Potions', '治疗药水', '治療藥水', 'inv_potion_51'),
    2533: ('Remedies', '药膏与解毒剂', '藥膏與解毒劑', 'inv_misc_bandage_01'),
    2535: ('Camping', '营地用品', '營地用品', 'inv_misc_bag_10_blue'),
}


def collect(raw: Path):
    manifest = json.loads((raw / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('product') != 'wowf' or not manifest.get('fetchComplete'):
        raise SourceError('a completed Forever source snapshot is required')
    responses = {r['key']: r for r in manifest['responses']}
    used = {}

    def data(key):
        r = responses.get(key)
        if not r or r.get('status') != 'verified':
            return None
        value = checked_bytes(raw, r)
        used[key] = {k: r[k] for k in ('url', 'path', 'sha256', 'fetchedAt') if k in r}
        return value

    def table(name):
        value = data('db2:' + name)
        if value is None:
            raise SourceError('missing table: ' + name)
        return list(csv.DictReader(io.StringIO(value.decode('utf-8-sig'))))

    abilities = [r for r in table('SkillLineAbility') if r['SkillLine'] == '129'
                 and int(r['TrivialSkillLineRankHigh']) > 0]
    spells = {int(r['Spell']) for r in abilities}
    effects = table('SpellEffect')
    reagents = {int(r['SpellID']): r for r in table('SpellReagents') if int(r['SpellID']) in spells}
    names = {int(r['ID']): r.get('Name_lang', '') for r in table('SpellName') if int(r['ID']) in spells}
    item_effects = {int(r['ID']): r for r in table('ItemEffect')}
    teachers = {}
    for r in effects:
        if int(r['Effect']) == 36 and int(r['EffectTriggerSpell']) in spells:
            teachers.setdefault(int(r['SpellID']), set()).add(int(r['EffectTriggerSpell']))
    for r in table('SpellLearnSpell'):
        if int(r['LearnSpellID']) in spells:
            teachers.setdefault(int(r['SpellID']), set()).add(int(r['LearnSpellID']))
    books = {}
    for r in table('ItemXItemEffect'):
        e = item_effects.get(int(r['ItemEffectID']))
        if not e:
            continue
        sid = int(e['SpellID'])
        targets = set(teachers.get(sid, ()))
        if e['TriggerType'] == '6' and sid in spells:
            targets.add(sid)
        for target in targets:
            books.setdefault(target, set()).add(int(r['ItemID']))
    sparse = {int(r['ID']): r for r in table('ItemSparse') if int(r['ID']) in set().union(*books.values())}
    records, conflicts = [], []
    for a in abilities:
        spell = int(a['Spell'])
        outputs = [r for r in effects if int(r['SpellID']) == spell and r['Effect'] == '24'
                   and int(r.get('DifficultyID', '0')) == 0 and int(r['EffectItemType']) > 0]
        if len(outputs) != 1 or spell not in reagents:
            raise SourceError(f'{spell}: ambiguous/missing crafting inputs or output')
        output, reagent = outputs[0], reagents[spell]
        mats = []
        for key, value in reagent.items():
            match = re.fullmatch(r'Reagent_(\d+)', key)
            if match and int(value) > 0:
                quantity = int(reagent['ReagentCount_' + match[1]])
                if quantity <= 0:
                    raise SourceError(f'{spell}: invalid reagent quantity')
                mats.append([int(value), quantity])
        count = float(output['EffectBasePointsF'])
        if not mats or not count.is_integer() or count <= 0:
            raise SourceError(f'{spell}: incomplete craft')
        yellow, grey = int(a['TrivialSkillLineRankLow']), int(a['TrivialSkillLineRankHigh'])
        green = (yellow + grey) // 2
        page_data = data(f'web:spell:{spell}')
        page = parse_page(page_data, 'spell', spell, responses[f'web:spell:{spell}']['finalUrl']) if page_data else {}
        web = next((r for r in page.get('listviews', {}).get('recipes', []) if r['id'] == spell), {})
        colors = web.get('colors')
        if colors:
            if colors[1:] != [yellow, green, grey]:
                raise SourceError(f'{spell}: source skill curve conflict')
        db_creates = [int(output['EffectItemType']), int(count), int(count)]
        if web.get('creates') and web['creates'] != db_creates:
            conflicts.append({'spell': spell, 'field': 'output', 'db2': db_creates, 'web': web['creates']})
        if web.get('reagents') and sorted(web['reagents']) != sorted(mats):
            raise SourceError(f'{spell}: source reagent conflict')
        formula_ids = sorted(books.get(spell, ()))
        if len(formula_ids) > 1:
            raise SourceError(f'{spell}: multiple books need explicit selection')
        formula = formula_ids[0] if formula_ids else None
        rank = int(sparse.get(formula, {}).get('RequiredSkillRank', '0'))
        if a['AcquireMethod'] == '1':
            learn, basis = int(a['MinSkillLineRank']), 'SkillLineAbility.automaticSkillRank'
        elif rank > 0:
            learn, basis = rank, 'ItemSparse.RequiredSkillRank'
        elif colors and colors[0] > 0:
            learn, basis = colors[0], 'Wowhead.colors.orange'
        else:
            # Zero orange is not skill zero or the recipe's learning threshold.
            # Use the first confirmed usable skill bound; unknown learning routes
            # are independently excluded until learned/observed by the client.
            learn, basis = yellow, 'SkillLineAbility.yellowReference'
        row = dict(spell=spell, item=db_creates[0], count=int(count), mats=mats,
                   learn=learn, yellow=yellow, green=green, grey=grey,
                   category=GROUPS[int(a['TradeSkillCategoryID'])][0],
                   name=web.get('name') or names.get(spell), learnBasis=basis,
                   skillCurveBasis='SkillLineAbility.low/high; green=floor((low+high)/2)',
                   craftingBasis='SpellReagents; SpellEffect.CreateItem',
                   trainer=bool(page.get('listviews', {}).get('taught-by-npc')))
        if formula:
            row['formula'] = formula
        records.append(row)
    records.sort(key=lambda r: (r['learn'], r['spell']))
    return {'build': manifest['build'], 'profession': 'first-aid', 'records': records,
            'sources': used, 'conflicts': conflicts,
            'note': 'Versioned source facts, not in-game verification. Learning coverage is tracked separately.'}


def lua(value):
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return '{ ' + ', '.join(lua(v) for v in value) + ' }'
    if isinstance(value, dict):
        return '{ ' + ', '.join(k + '=' + lua(v) for k, v in value.items()) + ' }'
    raise TypeError(value)


def write_sections(root: Path, audit):
    records = audit['records']
    for locale in ('zhCN', 'zhTW', 'enUS'):
        folder = root / 'Core/Data' / (locale if locale != 'zhCN' else '')
        recipe_path = folder / 'Data_ProfRecipes.lua'
        text = recipe_path.read_text(encoding='utf-8-sig')
        text = re.sub(re.escape(START) + r'.*?' + re.escape(END) + r'\n\n?', '', text, flags=re.S)
        lines = [START, '-- Source build: ' + audit['build'] + '; generated by data_pipeline.professions.first_aid',
                 'KEYS[#KEYS + 1] = "first-aid"', 'PARTS["first-aid"] = function() return {',
                 '    word = "Recipe",', f'    counts = {{ items={sum("formula" in r for r in records)}, total={len(records)} }},',
                 '    groups = {']
        for key, cn, tw, icon in GROUPS.values():
            title = {'zhCN': cn, 'zhTW': tw, 'enUS': key}[locale]
            lines.append('        ' + lua([key, title, icon, sum(r['category'] == key for r in records)]) + ',')
        lines.extend(['    },', '    rows = {'])
        for r in records:
            values = [r['spell'], r['item'], r['count'], r['category'], '', '', r['learn'],
                      r['yellow'], r['green'], r['grey'], False, r['mats']]
            if 'formula' in r:
                values.extend([[r['formula'], 1], {'skill': r['learn'], 'read': 'wowhead'}])
            lines.append('        ' + lua(values) + ',')
        lines.extend(['    },', '} end', END, ''])
        anchor = 'for k, v in pairs(HAND) do'
        if text.count(anchor) != 1:
            raise SourceError('native recipe loader changed')
        recipe_path.write_bytes(text.replace(anchor, '\n'.join(lines) + '\n' + anchor).encode('utf-8'))
        level_path = folder / 'Data_ProfLeveling.lua'
        text = level_path.read_text(encoding='utf-8-sig')
        text = re.sub(r'        ' + re.escape(START) + r'.*?' + re.escape(END) + r'\n', '', text, flags=re.S)
        lines = ['        ' + START, '        rinfo = {']
        for r in records:
            values = {key: r[key] for key in ('item', 'count', 'learn', 'yellow', 'green', 'grey', 'mats')}
            if 'formula' in r:
                values['formula'] = r['formula']
            lines.append(f'            [{r["spell"]}] = ' + lua(values) + ',')
        lines.extend(['        },', '        ' + END, ''])
        anchor = '    ["first-aid"] = {\n'
        if text.count(anchor) != 1:
            raise SourceError('native leveling section changed')
        level_path.write_bytes(text.replace(anchor, anchor + '\n'.join(lines)).encode('utf-8'))
        overview_path = folder / 'Data_Professions.lua'
        text = overview_path.read_text(encoding='utf-8-sig')
        text, replaced = re.subn(r'(\["first-aid"\] = \{.*?recipes = )\d+',
                                 lambda match: match[1] + str(len(records)), text, count=1, flags=re.S)
        if replaced != 1:
            raise SourceError('native overview section changed')
        overview_path.write_bytes(text.encode('utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    args = parser.parse_args()
    audit = collect(args.raw)
    write_sections(args.root, audit)
    write_json(args.audit, audit)
    print(f'Generated {len(audit["records"])} First Aid recipes in three locales from {audit["build"]}')


if __name__ == '__main__':
    main()
