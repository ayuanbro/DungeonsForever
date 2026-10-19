# -*- coding: utf-8 -*-
"""按 fc 2026-10-07 新页同步 Data_DungeonLoot.lua（保守版：只重写发生变化的行）
  · 行字段原文保留（含转义引号）；未改动行字节不动
  · 新增：追加到行尾（掉率/无限版新增标记取 fc）
  · 移除：从行内删除（去向记录日志）
用法：python _fc_loot_apply_1007b.py [--dry]
"""
import re, os, sys, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from _fc_compare import SLUG2DID  # noqa

REF = os.path.join(HERE, '_ref')
LT = os.path.join(ROOT, 'Core', 'Data', 'Data_DungeonLoot.lua')
DRY = '--dry' in sys.argv

def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())

def unesc(s):
    return s.replace('\\"', '"')

ROW_RE = re.compile(
    r'        \{ ("(?:[^"\\]|\\.)*"), ("(?:[^"\\]|\\.)*"), ("(?:[^"\\]|\\.)*"), "(\d*)", \{\n'
    r'(.*?)\n        \} \},', re.S)
IT_RE = re.compile(r'            \{ (\d+), (nil|[\d.]+), (true|false) \},?\n?')

def parse_fc(h):
    out = {}
    for m in re.finditer(r'<section id="([a-z0-9-]+)" class="lb-boss"[^>]*>(.*?)</section>', h, re.S):
        items = {}
        for it in re.finditer(
                r'<a href="/zh-cn/item/(\d+)">.*?<span class="lb-name [^"]*">([^<]*)</span>(.*?)</span></a></li>',
                m.group(2), re.S):
            ch = None
            cm = re.search(r'lb-chance[^>]*>\s*\(\s*([\d.]+)\s*%', it.group(3))
            if cm:
                ch = float(cm.group(1))
            items[int(it.group(1))] = (ch, 'lb-mark-new' in it.group(3))
        out[m.group(1)] = items
    obs = set()
    m = re.search(r'<section id="observed-recipes"[^>]*>(.*?)</section>', h, re.S)
    if m:
        obs = {int(x) for x in re.findall(r'/zh-cn/item/(\d+)', m.group(1))}
    return out, obs

def fmt_ch(ch):
    if ch is None:
        return 'nil'
    return str(int(ch)) if ch == int(ch) else ('%g' % ch)

src = open(LT, encoding='utf-8', newline='').read()
assert '\r' not in src

log = {'add': [], 'remove': [], 'fc_row_unmatched': []}
new_src = src
changed_rows = 0

for slug, did in sorted(SLUG2DID.items()):
    p = os.path.join(REF, 'dg_%s.html' % slug)
    if not os.path.exists(p):
        continue
    fc, obs = parse_fc(open(p, encoding='utf-8').read())
    # 定位本块原文
    bm = re.search(r'\n    \["%s"\] = \{\n(.*?)\n    \},' % did, new_src, re.S)
    if bm is None:
        continue
    blk_raw = bm.group(0)
    blk_body = bm.group(1)
    # fc 全部物品（含所有行）→ 去向判定
    fc_all = {}
    for fitems in fc.values():
        for iid in fitems:
            fc_all.setdefault(iid, []).append(1)
    new_body = blk_body
    rows = list(ROW_RE.finditer(blk_body))
    by_norm = {norm(unesc(r.group(1))): r for r in rows}
    for fslug, fitems in fc.items():
        row = by_norm.get(norm(fslug))
        if row is None:
            log['fc_row_unmatched'].append((did, fslug))
            continue
        item_ids = [int(x.group(1)) for x in IT_RE.finditer(row.group(5))]
        add = [iid for iid in fitems if iid not in item_ids]
        rem = [iid for iid in item_ids if iid not in fitems]
        if not add and not rem:
            continue
        # 重建该行物品段
        seg = row.group(5)
        lines = {int(x.group(1)): x.group(0) for x in IT_RE.finditer(seg)}
        order = item_ids[:]
        for iid in rem:
            order.remove(iid)
            where = fc_all.get(iid)
            tag = 'moved->other-row' if where else (
                'downgraded-to-observed-recipes' if iid in obs else 'dropped-by-fc')
            log['remove'].append((did, unesc(row.group(1)), iid, tag))
        for iid in add:
            ch, is_new = fitems[iid]
            flag = 'true' if (is_new or iid >= 200000) else 'false'
            order.append(iid)
            lines[iid] = '            { %d, %s, %s },' % (iid, fmt_ch(ch), flag)
            log['add'].append((did, unesc(row.group(1)), iid, fmt_ch(ch), flag))
        new_seg = '\n'.join(lines[iid] for iid in order)
        old_row_text = row.group(0)
        new_row_text = old_row_text.replace(row.group(5), new_seg)
        assert new_body.count(old_row_text) == 1, (did, fslug)
        new_body = new_body.replace(old_row_text, new_row_text)
        changed_rows += 1
    if new_body != blk_body:
        new_src = new_src.replace(blk_raw, blk_raw.replace(blk_body, new_body), 1)

print('changed rows:', changed_rows)
if changed_rows and not DRY:
    bak = os.path.join(HERE, '_rl_bak')
    os.makedirs(bak, exist_ok=True)
    shutil.copyfile(LT, os.path.join(bak, 'Data_DungeonLoot.lua.bak'))
    open(LT, 'w', encoding='utf-8', newline='').write(new_src)
    print('WROTE', LT)

for k in ('add', 'remove', 'fc_row_unmatched'):
    print('==', k, len(log[k]))
    for x in log[k]:
        print('  ', x)
