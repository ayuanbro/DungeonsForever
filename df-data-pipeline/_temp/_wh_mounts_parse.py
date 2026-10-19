# -*- coding: utf-8 -*-
"""解析 listviewitems（JS 字面量，裸键）→ _wh_mounts_items.json"""
import re, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

html = open('_temp/whb_mounts_items.html', encoding='utf-8').read()
start = html.index('var listviewitems = [') + len('var listviewitems = ')

# 括号计数找数组结束（跳过字符串）
depth = 0; end = None; instr = False; esc = False
for i in range(start, len(html)):
    c = html[i]
    if instr:
        if esc: esc = False
        elif c == '\\': esc = True
        elif c == '"': instr = False
    else:
        if c == '"': instr = True
        elif c == '[': depth += 1
        elif c == ']':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
raw = html[start:end]

# 裸键 → 引号键：只在字符串外生效
out = []
i = 0; instr = False; esc = False
while i < len(raw):
    c = raw[i]
    if instr:
        out.append(c)
        if esc: esc = False
        elif c == '\\': esc = True
        elif c == '"': instr = False
        i += 1
        continue
    if c == '"':
        instr = True; out.append(c); i += 1
        continue
    if c in '{,':
        out.append(c); i += 1
        # 吃掉空白
        while i < len(raw) and raw[i] in ' \t\r\n':
            out.append(raw[i]); i += 1
        m = re.match(r'[A-Za-z_][A-Za-z0-9_]*\s*:', raw[i:])
        if m:
            key = m.group(0)[:-1].rstrip()
            out.append('"%s":' % key)
            i += len(m.group(0))
        continue
    out.append(c); i += 1

fixed = ''.join(out)
data = json.loads(fixed)
print('rows:', len(data))
rows = []
for d in data:
    mv = d.get('modelviewer') or {}
    rows.append({
        'id': d['id'],
        'name': d.get('name') or d.get('displayName'),
        'quality': d.get('quality'),
        'displayid': mv.get('displayid'),
        'icon': d.get('icon'),
        'subclass': d.get('subclass'),
    })
json.dump(rows, open('_temp/_wh_mounts_items.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for r in rows:
    print(r['id'], r['name'], '| disp:', r['displayid'], '| icon:', r['icon'])
