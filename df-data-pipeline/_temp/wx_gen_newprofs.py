import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = os.path.join(ROOT, 'Core', 'Data', 'Data_ProfRecipes.lua')
META = os.path.join(ROOT, 'Core', 'Data', 'Data_Professions.lua')
TMP = os.path.join(ROOT, '_temp')

recs = json.load(open(os.path.join(TMP, '_wx_recipes.json'), encoding='utf-8'))
cats = json.load(open(os.path.join(TMP, '_wx_categories.json'), encoding='utf-8'))
byid = {c['id']: c for c in cats}


def lua_str(s):
    return '"' + (s or '').replace('\\', '\\\\').replace('"', '\\"') + '"'


def build_row(r, group):
    prod = (r.get('products') or [[0, 1]])[0]
    pid, pcount = prod[0], prod[1] if len(prod) > 1 else 1
    triv = r.get('trivial') or [0, 0]
    y, gr = triv[0], triv[1]
    g = (y + gr) // 2 if y > 0 else 0
    reags = ', '.join('{ %d, %d }' % (i, c) for i, c in (r.get('reagents') or []))
    return '{ %d, %d, %d, "%s", "", %s, %d, %d, %d, %d, %s, { %s }, nil, nil, {}, "", "" }' % (
        r['spell'], pid, pcount, group, lua_str(r.get('desc') or ''), y, y, g, gr,
        'true' if r.get('new') else 'false', reags)


def collect(cat_ids):
    out = []
    for r in recs:
        if r['cat'] in cat_ids:
            out.append(r)
    out.sort(key=lambda r: (r.get('trivial') or [9999])[0])
    return out


def emit_section(slug, zh, groups):
    lines = ['    ["%s"] = {' % slug]
    lines.append('        word = "Recipe",')
    total = sum(n for _, _, _, n, _ in groups)
    lines.append('        counts = { total=%d, sourced=0, unreadable=0, items=0 },' % total)
    lines.append('        groups = {')
    for key, gzh, icon, n, cids in groups:
        lines.append('            { "%s", "%s", "%s", %d },' % (key, gzh, icon, n))
    lines.append('        },')
    lines.append('')
    lines.append('        rows = {')
    for key, gzh, icon, n, cids in groups:
        for r in collect(cids):
            lines.append('            ' + build_row(r, key) + ',')
    lines.append('        },')
    lines.append('    },')
    return lines


poison_sec = emit_section('poisons', '毒药', [
    ('Poisons', '药膏', 'inv_potion_54', 26, {2734}),
])
comprehension_sec = emit_section('comprehension', '理解', [
    ('Comprehension', '理解', 'inv_scroll_15', 1, {2757}),
    ('Other', '其他技能', 'inv_scroll_11', 6, {93012}),
])

text = open(REC, 'rb').read().decode('utf-8')
assert '"poisons"' not in text
nl = '\r\n' if '\r\n' in text[:2000] else '\n'
idx = text.rstrip().rfind('\n}')
head = text[:idx].rstrip()
out = head + '\n' + '\n'.join(poison_sec + [''] + comprehension_sec) + '\n}\n'
if nl == '\r\n':
    pass
with open(REC, 'wb') as f:
    f.write(out.encode('utf-8'))

meta = open(META, 'rb').read().decode('utf-8')
assert '"poisons"' not in meta
old_order = '"first-aid", "camping"'
assert old_order in meta
meta = meta.replace(old_order, '"first-aid", "poisons", "comprehension", "camping"')

pro_entries = '''        ["poisons"] = {
            name = "毒药",
            icon = 136242,
            kind = "secondary",
            section = "crafting",
            summary = "盗贼的辅助专业：技能越高能调制的毒药越强。材料向毒药商人与黑市贩子购买，调成腐蚀、削弱与消磨敌人的药剂，涂在武器上生效。1.60 新增萎缩、迟钝、解离与玄秘毒药。",
            status = "待实地核对",
            recipes = 26,
            sub = 1,
            kinds = { Recipe = 26 },
        },

        ["comprehension"] = {
            name = "理解",
            icon = 135933,
            kind = "secondary",
            summary = "解读散落世界各处的魔法卷轴：理解技能越高，能解译的卷轴越强。卷轴读取后消耗，提供各类增益效果；在图书馆中研究可以提升理解技能。",
            status = "待实地核对",
            recipes = 7,
            sub = 2,
            kinds = { Recipe = 7 },
        },
'''
m = re.search(r'\n    \},\n\}\s*$', meta)
assert m, 'pro table close not found'
meta = meta[:m.start()] + '\n' + pro_entries + '    },\n}\n'
with open(META, 'wb') as f:
    f.write(meta.encode('utf-8'))

print('poisons rows:', sum(1 for _ in collect({2734})), '| comprehension rows:', sum(1 for _ in collect({2757, 93012})))
print('OK')
