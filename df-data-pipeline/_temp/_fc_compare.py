# -*- coding: utf-8 -*-
"""fc 对比 v2：pins 全量 vs BossPos；fights(8本) vs BossSkills；boss 名单只对 fc 有 bosses 数据的本"""
import re, json, os

ROOT = r'D:\workspace\DungeonsForever'
PAT_FIGHT = re.compile(r'"([a-z0-9-]+)":\{"trigger":')
PAT_ABIL = re.compile(
    r'\{"spell":(\d+),"name":"([^"]*)","names":\{[^}]*\},"icon":"([^"]*)","flags":\[([^\]]*)\],"text":"([^"]*)')
PAT_PIN = re.compile(
    r'\{"x":([\d.]+),"y":([\d.]+),"boss":"([^"]*)","face":(\d+),"faceKind":"([^"]*)","label":(?:"([^"]*)"|\$undefined)')

SLUG2DID = {
    'ragefire-chasm': 'ragefire_chasm', 'wailing-caverns': 'wailing_caverns',
    'the-deadmines': 'the_deadmines', 'shadowfang-keep': 'shadowfang_keep',
    'blackfathom-deeps': 'blackfathom_deeps', 'the-stockade': 'the_stockade',
    'gnomeregan': 'gnomeregan', 'razorfen-kraul': 'razorfen_kraul',
    'razorfen-downs': 'razorfen_downs', 'scarlet-monastery-graveyard': 'sm_graveyard',
    'scarlet-monastery-library': 'sm_library', 'scarlet-monastery-armory': 'sm_armory',
    'scarlet-monastery-cathedral': 'sm_cathedral', 'zulfarrak': 'zul_farrak',
    'maraudon': 'maraudon', 'sunken-temple': 'sunken_temple', 'uldaman': 'uldaman',
    'blackrock-depths': 'blackrock_depths', 'lower-blackrock-spire': 'lower_blackrock_spire',
    'upper-blackrock-spire': 'upper_blackrock_spire', 'scholomance': 'scholomance',
    'stratholme-main-gate': 'stratholme_main', 'stratholme-service-gate': 'stratholme_service',
    'dire-maul-east': 'dire_maul_east', 'dire-maul-west': 'dire_maul_west',
    'dire-maul-north': 'dire_maul_north', 'excavation-site': 'excavation_wetlands',
    'city-of-dalaran': 'city_of_dalaran', 'hall-of-thanes': 'hall_of_thanes',
    'ruins-of-lordaeron': 'ruins_of_lordaeron', 'blackmaw-hold': 'blackmaw_hold',
    'alcaz-prison': 'alcaz_prison', 'kroldok-stronghold': 'kroldok_stronghold',
    'shapers-terrace': 'shapers_terrace', 'the-drowned-city': 'the_drowned_city',
}
NON_BOSS = {'trashmobs', 'tribute', 'cache', 'plans', 'chest', 'chestoftheseven',
            'knotthimblejackscache', 'darkcoffer', 'guzzler'}

def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())

def ours_block(src, did):
    for pre in ('    ["%s"] = {' % did, '    %s = {' % did):
        i = src.find(pre)
        if i >= 0:
            break
    else:
        return None
    j = src.find('{', i)
    depth = 0
    k = j
    while k < len(src):
        if src[k] == '{':
            depth += 1
        elif src[k] == '}':
            depth -= 1
            if depth == 0:
                break
        k += 1
    return src[j:k + 1]

def unesc(s):
    return s.replace('\\\\', '\x00').replace('\\"', '"').replace('\x00', '\\')

def balanced(h, start_pat, close_c):
    out = []
    for m in re.finditer(start_pat, h):
        i = m.end()
        depth = 1
        j = i
        instr = False
        esc = False
        while j < len(h) and depth > 0:
            c = h[j]
            if esc:
                esc = False
            elif c == '\\\\':
                esc = True
            elif c == '"':
                instr = not instr
            elif not instr:
                if c in '{[':
                    depth += 1
                elif c in '}]':
                    depth -= 1
            j += 1
        out.append(h[i:j - 1])
    return out

bs = open(os.path.join(ROOT, 'Core/Data/Data_BossSkills.lua'), encoding='utf-8').read()
bp = open(os.path.join(ROOT, 'Core/Data/Data_BossPos.lua'), encoding='utf-8').read()
lt = open(os.path.join(ROOT, 'Core/Data/Data_DungeonLoot.lua'), encoding='utf-8').read()

def ours_skills(did):
    blk = ours_block(bs, did)
    if not blk:
        return None
    out = {}
    for m in re.finditer(r'\["([^"]+)"\] = \{(.*?)\n        \},', blk, re.S):
        out[m.group(1)] = [(int(a), b) for a, b in
                           re.findall(r'\{ "", "", (\d+), "([^"]*)"', m.group(2))]
    return out

def ours_pos(did):
    blk = ours_block(bp, did)
    if not blk:
        return None
    out = {}
    for m in re.finditer(r'\["([^"]+)"\] = \{ \{ ([\d., ]+) \} \}', blk):
        coords = []
        for c in m.group(2).split('}, {'):
            coords.append(tuple(float(x) for x in re.findall(r'[\d.]+', c)))
        out[m.group(1)] = coords
    return out

def ours_loot_bosses(did):
    blk = ours_block(lt, did)
    if not blk:
        return None
    return [n for n in re.findall(r'\{ "([^"]+)", "[^"]*", "', blk) if norm(n) not in NON_BOSS]

def fc_page(slug):
    h = open('_fc_dg_%s.html' % slug, encoding='utf-8').read()
    pins = []
    for f in balanced(h, r'\\"floors\\":\[', ']'):
        fj = unesc(f)
        for m in PAT_PIN.finditer(fj):
            x, y, b, face, kind, label = m.groups()
            pins.append(dict(x=float(x), y=float(y), boss=b, face=int(face), kind=kind, label=label or ''))
    fights = {}
    for blk in balanced(h, r'\\"fights\\":\{', '}'):
        fj = unesc(blk)
        starts = list(PAT_FIGHT.finditer(fj))
        for idx, fm in enumerate(starts):
            boss = fm.group(1)
            end = starts[idx + 1].start() if idx + 1 < len(starts) else len(fj)
            fights[boss] = [(int(a.group(1)), a.group(3)) for a in PAT_ABIL.finditer(fj[fm.end():end])]
    bosses = re.findall(r'\\"english\\":\\"([^\\]+)\\"', h)
    return pins, fights, list(dict.fromkeys(bosses))

def show(t, items):
    if items:
        print('== %s (%d) ==' % (t, len(items)))
        for s, typ, a, b in items:
            print('  %-28s %-26s %s' % (s, a, b))

if __name__ != '__main__':
    import sys as _s
    _s.modules[__name__].__dict__  # no-op guard
    report = []
    _SKIP_MAIN = True
else:
    _SKIP_MAIN = False
    report = []
for slug in ([] if _SKIP_MAIN else SLUG2DID):
    did = SLUG2DID[slug]
    path = '_fc_dg_%s.html' % slug
    if not os.path.exists(path):
        report.append((slug, 'NO-PAGE', '', ''))
        continue
    pins, fights, fc_bosses = fc_page(slug)
    my_loot = ours_loot_bosses(did)
    my_skills = ours_skills(did)
    my_pos = ours_pos(did)

    # 1) 名单（仅当 fc 有 bosses 数据时才有意义）
    if fc_bosses:
        fc_set = {norm(b) for b in fc_bosses if norm(b) not in NON_BOSS}
        if my_loot is not None:
            for fb in sorted(fc_set):
                if fb not in {norm(n) for n in my_loot}:
                    report.append((slug, 'FC-BOSS-NOT-IN-OUR-LOOT', fb, ''))
            for mn in my_loot:
                if norm(mn) not in fc_set:
                    report.append((slug, 'OUR-LOOT-BOSS-NOT-ON-FC', mn, ''))
    # 2) 技能行
    if fights and my_skills:
        sk_norm = {norm(k): k for k in my_skills}
        for fb, abils in fights.items():
            key = sk_norm.get(norm(fb))
            if key is None:
                continue
            fc_ids = {a[0] for a in abils}
            fc_icons = {a[1] for a in abils}
            my_ids = {a[0] for a in my_skills[key]}
            my_icons = {a[1] for a in my_skills[key]}
            for sid, icon in abils:
                if sid not in my_ids and icon not in my_icons:
                    report.append((slug, 'FC-SKILL-WE-LACK', key, '%d (%s)' % (sid, icon)))
            for sid, icon in my_skills[key]:
                if sid not in fc_ids and icon not in fc_icons:
                    report.append((slug, 'OUR-SKILL-NOT-ON-FC', key, '%d (%s)' % (sid, icon)))
    # 3) 钉点
    if my_pos:
        pos_norm = {norm(k): k for k in my_pos}
        for p in pins:
            key = pos_norm.get(norm(p['boss']))
            if key is None:
                continue
            mine = my_pos[key]
            if not any(abs(c[0] - p['x']) < 0.35 and abs(c[1] - p['y']) < 0.35 for c in mine):
                report.append((slug, 'PIN-DIFF', key,
                               'fc=%.1f,%.1f ours=%s' % (p['x'], p['y'], mine)))

json.dump(report, open('_fc_compare_report.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
show('PIN-DIFF', [r for r in report if r[1] == 'PIN-DIFF'])
show('FC-SKILL-WE-LACK', [r for r in report if r[1] == 'FC-SKILL-WE-LACK'])
show('OUR-SKILL-NOT-ON-FC', [r for r in report if r[1] == 'OUR-SKILL-NOT-ON-FC'])
show('FC-BOSS-NOT-IN-OUR-LOOT', [r for r in report if r[1] == 'FC-BOSS-NOT-IN-OUR-LOOT'])
show('OUR-LOOT-BOSS-NOT-ON-FC', [r for r in report if r[1] == 'OUR-LOOT-BOSS-NOT-ON-FC'])
print('total diff', len(report))
