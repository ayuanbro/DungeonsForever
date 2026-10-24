# -*- coding: utf-8 -*-
"""解析 fc 页 fights → 每 boss 技能行清单"""
import re, json, sys

def unescape(s):
    return s.replace('\\\\', '\x00').replace('\\"', '"').replace('\x00', '\\')

def extract_block(h, key):
    """取 \"fights\":{...} 平衡扫描"""
    out = []
    for m in re.finditer(r'\\"%s\\":\{' % key, h):
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
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
            j += 1
        out.append(h[i:j - 1])
    return out

PAT_FIGHT = re.compile(r'"([a-z0-9-]+)":\{"trigger":')
PAT_ABIL = re.compile(
    r'\{"spell":(\d+),"name":"([^"]*)","names":\{[^}]*\},"icon":"([^"]*)","flags":\[([^\]]*)\],"text":"([^"]*)"')

slug = sys.argv[1]
h = open('_fc_dg_%s.html' % slug, encoding='utf-8').read()
result = {}
for blk in extract_block(h, 'fights'):
    fj = unescape(blk)
    # 逐 fight 切
    starts = list(PAT_FIGHT.finditer(fj))
    for i, m in enumerate(starts):
        boss = m.group(1)
        end = starts[i + 1].start() if i + 1 < len(starts) else len(fj)
        seg = fj[m.end():end]
        abils = []
        for a in PAT_ABIL.finditer(seg):
            abils.append(dict(spell=int(a.group(1)), name=a.group(2),
                              icon=a.group(3), flags=a.group(4), text=a.group(5)))
        result[boss] = abils

json.dump(result, open('_fc_fights_%s.json' % slug, 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('##', slug)
for boss, abils in result.items():
    print('  BOSS', boss, len(abils))
    for a in abils:
        print('    %-6d %-12s %-28s flags=%-14s %s' % (a['spell'], a['name'], a['icon'], a['flags'], a['text'][:40]))
