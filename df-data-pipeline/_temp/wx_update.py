import json, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, '_temp')
DATA = os.path.join(ROOT, 'Core', 'Data', 'Data_ProfRecipes.lua')
META = os.path.join(ROOT, 'Core', 'Data', 'Data_Professions.lua')
BASE = 'https://wuxianwow.com/data/'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

PROF_EN = {'炼金术': 'alchemy', '锻造': 'blacksmithing', '附魔': 'enchanting', '工程学': 'engineering',
           '制皮': 'leatherworking', '裁缝': 'tailoring', '烹饪': 'cooking', '急救': 'first-aid'}

GROUP_MAP = {
    '药剂': ('alchemy', 'Elixirs'), '恢复药水': ('alchemy', 'Potions'),
    '板甲胸甲': ('blacksmithing', 'Chest'), '板甲护手': ('blacksmithing', 'Hands'),
    '板甲腰带': ('blacksmithing', 'Waist'), '单手斧': ('blacksmithing', 'One-hand'),
    '护腕': ('tailoring', 'Wrist'), '护肩': ('tailoring', 'Shoulder'), '腰带': ('tailoring', 'Waist'),
    '皮甲靴子': ('leatherworking', 'Feet'),
    '装置': ('engineering', 'Devices'), '配件': ('engineering', 'Devices'), '爆炸物': ('engineering', 'Explosives'),
    '绷带': ('first-aid', 'Bandages'),
    '日常饮食': ('cooking', 'Other buffs'), '杂项烹饪': ('cooking', 'Other buffs'),
}

ENCH_GROUP = {'护腕': '护腕', '胸甲': '胸甲', '手套': '手套', '武器': '武器', '双手武器': '双手武器',
              '盾牌': '盾牌', '披风': '披风', '靴子': '靴子', '副手': '副手', '项链': '项链'}

ENCH_PREFIX = {'附魔双手武器': '双手武器', '附魔武器': '武器', '附魔护腕': '护腕', '附魔胸甲': '胸甲',
               '附魔手套': '手套', '附魔盾牌': '盾牌', '附魔披风': '披风', '附魔靴子': '靴子',
               '附魔副手': '副手', '附魔项链': '项链',
               'Enchant 2H Weapon': '双手武器', 'Enchant Weapon': '武器', 'Enchant Bracer': '护腕',
               'Enchant Chest': '胸甲', 'Enchant Gloves': '手套', 'Enchant Shield': '盾牌',
               'Enchant Cloak': '披风', 'Enchant Boots': '靴子', 'Enchant Off Hand': '副手',
               'Enchant Necklace': '项链'}

SLOT_ZH = {'手腕': '护腕', '肩部': '护肩', '腰部': '腰带', '头部': '头部', '腿部': '腿部', '脚': '靴子', '胸部': '胸甲', '手': '手套'}


def fetch(name):
    fp = os.path.join(TMP, '_wx_' + name + '.json')
    if not os.path.exists(fp):
        req = urllib.request.Request(BASE + name + '.json', headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        with open(fp, 'wb') as f:
            f.write(data)
    return json.load(open(fp, encoding='utf-8'))


def split_top(s):
    parts, depth, cur, i, q = [], 0, [], 0, False
    while i < len(s):
        c = s[i]
        if q:
            if c == '"' and (i == 0 or s[i - 1] != '\\'):
                q = False
            cur.append(c)
        else:
            if c == '"':
                q = True
                cur.append(c)
            elif c == '{':
                depth += 1
                cur.append(c)
            elif c == '}':
                depth -= 1
                cur.append(c)
            elif c == ',' and depth == 0:
                parts.append(''.join(cur).strip())
                cur = []
            else:
                cur.append(c)
        i += 1
    tail = ''.join(cur).strip()
    if tail:
        parts.append(tail)
    return parts


def lua_str(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def load_wx():
    recs = fetch('recipes')
    cats = fetch('categories')
    top = {c['id']: c['name'] for c in cats if c['parent'] == 0}
    parent_of = {c['id']: c['parent'] for c in cats}

    def top_of(cid):
        p = parent_of.get(cid, 0)
        while p and p not in top:
            p = parent_of.get(p, 0)
        return top.get(p, '?')

    by_prof = {}
    for r in recs:
        by_prof.setdefault(top_of(r['cat']), []).append(r)
    return by_prof


def parse(text):
    profs = {}
    cur_prof = None
    cur_tbl = None
    for ln, line in enumerate(text.split('\n')):
        m = re.match(r'^    \["([\w-]+)"\] = \{', line)
        if m:
            cur_prof = m.group(1)
            profs[cur_prof] = {'row_lines': [], 'ench_lines': [], 'rows_open': None, 'rows_close': None,
                               'ench_open': None, 'ench_close': None, 'counts_line': None, 'group_lines': []}
            cur_tbl = None
            continue
        if cur_prof is None:
            continue
        p = profs[cur_prof]
        if re.match(r'^        rows = \{', line):
            cur_tbl = 'rows'
            p['rows_open'] = ln
            continue
        if re.match(r'^        enchants = \{', line):
            cur_tbl = 'enchants'
            p['ench_open'] = ln
            continue
        if re.match(r'^        \},\s*$', line) and cur_tbl:
            if cur_tbl == 'rows':
                p['rows_close'] = ln
            else:
                p['ench_close'] = ln
            cur_tbl = None
            continue
        if cur_tbl == 'rows' and re.match(r'^            \{ \d+, ', line):
            p['row_lines'].append(ln)
            continue
        if cur_tbl == 'enchants' and re.match(r'^            \{ "', line):
            p['ench_lines'].append(ln)
            continue
        if re.match(r'^            \{ "', line) and cur_tbl is None:
            p['group_lines'].append(ln)
            continue
        if 'counts = {' in line:
            p['counts_line'] = ln
    return profs


def row_yellow(line):
    f = split_top(line.strip().lstrip('{ ').rstrip('},').rstrip('}'))
    try:
        return int(f[7])
    except (ValueError, IndexError):
        return 10 ** 9


def wx_green(y, g):
    return (y + g) // 2


def build_recipe_row(r, prof, group):
    prod = (r.get('products') or [[0, 1]])[0]
    pid, pcount = prod[0], prod[1] if len(prod) > 1 else 1
    y, g = r.get('trivial') or [1, 1]
    eff = r.get('desc') or ''
    f = split_top(r.get('reagents') and json.dumps(r['reagents']) or '[]')
    reags = ', '.join('{ %d, %d }' % (i, c) for i, c in (r.get('reagents') or []))
    kind = ''
    return '{ %d, %d, %d, "%s", "%s", %s, %d, %d, %d, %d, %s, { %s }, nil, nil, {}, "", "" }' % (
        r['spell'], pid, pcount, group, kind, lua_str(eff), y, y, wx_green(y, g), g,
        'true' if r.get('new') else 'false', reags)


def build_ench_row(r):
    title = r.get('name') or ''
    y, g = r.get('trivial') or [1, 1]
    slot = ''
    short = title
    for pref, slot_name in ENCH_PREFIX.items():
        if title.startswith(pref + ' - '):
            slot = slot_name
            short = title[len(pref) + 3:]
            break
    reags = ', '.join('{ %d, %d }' % (i, c) for i, c in (r.get('reagents') or []))
    desc = r.get('desc') or ''
    return '{ %s, %s, "%s", %s, %d, %d, %d, %d, { %s }, nil, %s, false, {} }' % (
        lua_str(title), lua_str(short), slot, lua_str(desc), y, y, wx_green(y, g), g, reags,
        'true' if r.get('new') else 'false')


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else '--check'
    if '--refresh' in sys.argv:
        for n in ('_wx_manifest.json', '_wx_recipes.json', '_wx_categories.json'):
            fp = os.path.join(TMP, n)
            if os.path.exists(fp):
                os.remove(fp)
    by_prof = load_wx()
    manifest = fetch('manifest')
    raw = open(DATA, 'rb').read()
    nl = '\r\n' if b'\r\n' in raw[:2000] else '\n'
    text = raw.decode('utf-8')
    lines = text.split('\n')
    profs = parse(text)

    wx_recipe_by_spell = {}
    for zh, lst in by_prof.items():
        for r in lst:
            wx_recipe_by_spell[r['spell']] = (zh, r)

    mismatches = []
    for prof, p in profs.items():
        for ln in p['row_lines']:
            f = split_top(lines[ln].strip().lstrip('{ ').rstrip('},').rstrip('}'))
            try:
                spell = int(f[0])
            except ValueError:
                continue
            hit = wx_recipe_by_spell.get(spell)
            if not hit or hit[0] == '附魔':
                continue
            triv = hit[1].get('trivial')
            if not triv or triv[0] <= 0:
                continue
            y, g = int(f[7]), int(f[9])
            if y != triv[0] or g != triv[1]:
                mismatches.append((prof, spell, hit[1].get('name'), (y, g), tuple(triv)))

    adds = {}
    for zh, lst in by_prof.items():
        prof = PROF_EN.get(zh)
        if not prof or prof not in profs or prof == 'enchanting':
            continue
        have = set()
        for ln in profs[prof]['row_lines']:
            m = re.match(r'^            \{ (\d+), ', lines[ln])
            if m:
                have.add(int(m.group(1)))
        for r in lst:
            if r['spell'] in have:
                continue
            if not r.get('reagents') and not r.get('products'):
                continue
            if not r.get('products'):
                adds.setdefault(prof, []).append(('SKIP_NO_PROD', r['spell'], r.get('name'), ''))
                continue
            triv0 = (r.get('trivial') or [0])[0]
            if triv0 <= 0:
                adds.setdefault(prof, []).append(('SKIP_NO_TRIV', r['spell'], r.get('name'), ''))
                continue
            cat_name = None
            cats = fetch('categories')
            cat_name = next((c['name'] for c in cats if c['id'] == r['cat']), None)
            gm = GROUP_MAP.get(cat_name or '')
            if not gm or gm[0] != prof:
                adds.setdefault(prof, []).append(('SKIP_CAT', r['spell'], r.get('name'), cat_name))
                continue
            adds.setdefault(prof, []).append(('ADD', r['spell'], r.get('name'), gm[1], r))

    wx_ench = {}
    for r in by_prof.get('附魔', []):
        wx_ench[r['spell']] = r

    def ench_slot_of(title):
        for pref, slot in ENCH_PREFIX.items():
            if title.startswith(pref + ' - '):
                return slot
        return ''

    def sig_of(pairs):
        return ','.join('%dx%d' % (i, c) for i, c in sorted(pairs or []))

    our_ench = []
    for ln in profs.get('enchanting', {}).get('ench_lines', []):
        f = split_top(lines[ln].strip().lstrip('{ ').rstrip('},').rstrip('}'))
        if len(f) < 9:
            continue
        pairs = [(int(a), int(b)) for a, b in re.findall(r'\{ (\d+), (\d+) \}', f[8])]
        our_ench.append({'ln': ln, 'slot': f[2].strip('"'), 'sig': sig_of(pairs),
                         'yellow': int(f[5]), 'grey': int(f[7]), 'f': f})
    exact = {(o['slot'], o['sig'], o['yellow'], o['grey']) for o in our_ench}
    loose = {}
    for o in our_ench:
        loose.setdefault((o['slot'], o['sig']), []).append(o)

    ench_adds = []
    ench_thr_fix = []
    for r in by_prof.get('附魔', []):
        if r.get('products'):
            continue
        title = r.get('name') or ''
        if not title or title.startswith('未命名'):
            continue
        triv = r.get('trivial') or [0, 0]
        slot = ench_slot_of(title)
        sig = sig_of(r.get('reagents'))
        if (slot, sig, triv[0], triv[1]) in exact:
            continue
        cands = loose.get((slot, sig), [])
        if len(cands) == 1 and triv[0] > 0:
            o = cands[0]
            if o['yellow'] != triv[0] or o['grey'] != triv[1]:
                ench_thr_fix.append((o, triv, title))
            continue
        ench_adds.append(r)

    print('=== %s | wx build %s ===' % (mode, manifest['build']))
    print('threshold mismatches: %d' % len(mismatches))
    for m in mismatches:
        print('  %s spell=%s %s ours=%s wx=%s' % m)
    n_add = sum(1 for v in adds.values() for x in v if x[0] == 'ADD')
    print('recipe adds: %d' % n_add)
    for prof, v in adds.items():
        for x in v:
            print('  %s %s spell=%s name=%s cat=%s' % (prof, x[0], x[1], x[2], x[3]))
    print('enchant adds: %d' % len(ench_adds))
    for r in ench_adds:
        print('  spell=%s %s trivial=%s' % (r['spell'], r.get('name'), r.get('trivial')))
    print('enchant threshold fixes: %d' % len(ench_thr_fix))
    for o, triv, title in ench_thr_fix:
        print('  %s ours=(%d,%d) wx=%s' % (title, o['yellow'], o['grey'], tuple(triv)))

    if mode != '--apply':
        return

    for prof, spell, name, ours, triv in mismatches:
        for ln in profs[prof]['row_lines']:
            f0 = lines[ln]
            m = re.match(r'^(            \{ )(\d+)(, )', f0)
            if not m or int(m.group(2)) != spell:
                continue
            f = split_top(f0.strip().lstrip('{ ').rstrip('},').rstrip('}'))
            f[7] = str(triv[0])
            f[8] = str(wx_green(triv[0], triv[1]))
            f[9] = str(triv[1])
            end = ''
            st = f0.rstrip()
            if st.endswith('},'):
                end = '},'
            elif st.endswith('}'):
                end = '}'
            lines[ln] = '            { ' + ', '.join(f) + ' ' + end
            break

    for o, triv, title in ench_thr_fix:
        f0 = lines[o['ln']]
        f = o['f']
        f[5] = str(triv[0])
        f[6] = str(wx_green(triv[0], triv[1]))
        f[7] = str(triv[1])
        end = '},' if f0.rstrip().endswith('},') else '}'
        lines[o['ln']] = '            { ' + ', '.join(f) + ' ' + end

    for prof, v in adds.items():
        p = profs[prof]
        for x in v:
            if x[0] != 'ADD':
                print('SKIP', prof, x[1], x[2], x[3])
                continue
            _, spell, name, group, r = x
            newline = '            ' + build_recipe_row(r, prof, group) + ','
            y = (r.get('trivial') or [10 ** 9])[0]
            pos = p['rows_close']
            for ln in p['row_lines']:
                if row_yellow(lines[ln]) > y:
                    pos = ln
                    break
            lines.insert(pos, newline)
            for q in profs.values():
                for key in ('rows_close', 'ench_open', 'ench_close', 'counts_line'):
                    if q[key] is not None and q[key] >= pos:
                        q[key] += 1
                for lst_key in ('row_lines', 'ench_lines', 'group_lines'):
                    q[lst_key] = [ln + 1 if ln >= pos else ln for ln in q[lst_key]]
            p['row_lines'].append(pos)

    p = profs.get('enchanting')
    if p and ench_adds and p['ench_close'] is not None:
        pos = p['ench_close']
        new_lines = ['            ' + build_ench_row(r) + ',' for r in ench_adds]
        lines[pos:pos] = new_lines
        for q in profs.values():
            for key in ('rows_close', 'ench_open', 'ench_close', 'counts_line'):
                if q[key] is not None and q[key] >= pos:
                    q[key] += len(new_lines)
            for lst_key in ('row_lines', 'ench_lines', 'group_lines'):
                q[lst_key] = [ln + len(new_lines) if ln >= pos else ln for ln in q[lst_key]]

    for prof, p in profs.items():
        grp_count = {}
        for ln in p['row_lines']:
            f = split_top(lines[ln].strip().lstrip('{ ').rstrip('},').rstrip('}'))
            if len(f) > 3:
                grp_count[f[3].strip('"')] = grp_count.get(f[3].strip('"'), 0) + 1
        for ln in p['group_lines']:
            f = split_top(lines[ln].strip().lstrip('{ ').rstrip('},').rstrip('}'))
            if len(f) >= 4 and f[0].strip('"') in grp_count:
                f[3] = str(grp_count[f[0].strip('"')])
                end = '},' if lines[ln].rstrip().endswith('},') else '}'
                lines[ln] = '            { ' + ', '.join(f) + ' ' + end
        if p['counts_line'] is not None:
            line = lines[p['counts_line']]
            total = len(p['row_lines'])
            line = re.sub(r'total=\d+', 'total=%d' % total, line)
            lines[p['counts_line']] = line

    out = '\n'.join(lines)
    ver = 'build %s' % manifest['build']
    out = re.sub(r'数据版本 build [\d.]+（标注更新日 [\d-]+）',
                 '数据版本 %s（标注更新日 %s）' % (manifest['build'], manifest['built_at'][:10]), out)
    with open(DATA, 'wb') as f:
        f.write(out.encode('utf-8'))

    mraw = open(META, 'rb').read().decode('utf-8')
    mraw = re.sub(r'build = "[\d.]+"', 'build = "%s"' % manifest['build'], mraw)
    mraw = re.sub(r'updated = "[\d-]+"', 'updated = "%s"' % manifest['built_at'][:10], mraw)
    with open(META, 'wb') as f:
        f.write(mraw.encode('utf-8'))
    print('APPLIED ->', DATA)


if __name__ == '__main__':
    main()
