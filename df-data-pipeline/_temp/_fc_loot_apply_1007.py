# -*- coding: utf-8 -*-
"""按 fc 2026-10-07 新页同步 Data_DungeonLoot.lua：
  · 逐行（lb-boss 节）对齐物品集：新增（含掉率/无限版新增标记）、移除（含去向判定）
  · observed-recipes 节 = fc 降级项，从 boss 行移除并记录
  · 保留行身份（en/zh/note/npc）与既有物品的掉率/标记；npc 回填不受影响
用法：python _fc_loot_apply_1007.py [--dry]
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

ROW_RE = re.compile(r'\{ "([^"]+)", "([^"]*)", "([^"]*)", "(\d*)", \{\n(.*?)\n        \} \},', re.S)
IT_RE = re.compile(r'\{ (\d+), (nil|[\d.]+), (true|false) \}')

def parse_fc(h):
    """slug -> {'zh','npc','items':{iid:(chance,is_new)}}；全部 lb-boss 节"""
    out = {}
    for m in re.finditer(r'<section id="([a-z0-9-]+)" class="lb-boss"[^>]*>(.*?)</section>', h, re.S):
        slug, body = m.group(1), m.group(2)
        zh = ''
        hm = re.search(r'<h2[^>]*>([^<]*)</h2>', body)
        if hm:
            zh = hm.group(1).strip()
        items = {}
        for it in re.finditer(
                r'<a href="/zh-cn/item/(\d+)">.*?<span class="lb-name [^"]*">([^<]*)</span>(.*?)</span></a></li>',
                body, re.S):
            iid = int(it.group(1))
            ch = None
            cm = re.search(r'lb-chance[^>]*>\s*\(\s*([\d.]+)\s*%', it.group(3))
            if cm:
                ch = float(cm.group(1))
            items[iid] = (ch, 'lb-mark-new' in it.group(3))
        out[slug] = {'zh': zh, 'items': items}
    # observed-recipes（fc 降级项）
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
assert '\r' not in src, 'unexpected CRLF'

# 解析本地整表
head_end = src.find('ns.DungeonLoot = {') + len('ns.DungeonLoot = {')
head, body = src[:head_end], src[head_end:]
blocks = []  # (did, rows[(en,zh,note,npc,items,order)], raw)
pos = 0
for bm in re.finditer(r'\n    (\["[a-z_]+"\]) = \{\n(.*?)\n    \},', body, re.S):
    did = bm.group(1)[2:-2]
    blocks.append([did, [], bm.group(0)])
    for rm in ROW_RE.finditer(bm.group(2)):
        items = {}
        order = []
        for im in IT_RE.finditer(rm.group(5)):
            iid = int(im.group(1))
            ch = None if im.group(2) == 'nil' else float(im.group(2))
            items[iid] = [ch, im.group(3) == 'true']
            order.append(iid)
        blocks[-1][1].append([rm.group(1), rm.group(2), rm.group(3), rm.group(4), items, order])

log = {'add': [], 'remove': [], 'obs_downgrade': [], 'fc_row_unmatched': [], 'dup': []}
changed = False

for slug, did in sorted(SLUG2DID.items()):
    p = os.path.join(REF, 'dg_%s.html' % slug)
    if not os.path.exists(p):
        continue
    h = open(p, encoding='utf-8').read()
    fc, obs = parse_fc(h)
    blk = next((b for b in blocks if b[0] == did), None)
    if blk is None:
        continue
    rows = blk[1]
    by_norm = {}
    for r in rows:
        by_norm.setdefault(norm(r[0]), r)
    fc_all_items = {}
    for fslug, fd in fc.items():
        for iid in fd['items']:
            fc_all_items.setdefault(iid, []).append(fslug)
    for fslug, fd in fc.items():
        row = by_norm.get(norm(fslug))
        if row is None:
            # 中文名兜底
            for r in rows:
                if r[1] and r[1] == fd['zh']:
                    row = r
                    break
        if row is None:
            log['fc_row_unmatched'].append((did, fslug, fd['zh']))
            continue
        ours = row[4]
        # 新增
        for iid, (ch, is_new) in fd['items'].items():
            if iid not in ours:
                flag = is_new or iid >= 200000
                ours[iid] = [ch, flag]
                row[5].append(iid)
                log['add'].append((did, row[0], iid, fmt_ch(ch), flag,
                                   obs and iid in obs))
                changed = True
            else:
                # fc 降级观察项但仍在行里：保持
                pass
        # 移除
        for iid in list(ours.keys()):
            if iid not in fd['items']:
                dest = fc_all_items.get(iid)
                if dest:
                    log['remove'].append((did, row[0], iid, 'moved->%s' % ','.join(dest)))
                elif iid in obs:
                    log['remove'].append((did, row[0], iid, 'downgraded-to-observed-recipes'))
                else:
                    log['remove'].append((did, row[0], iid, 'dropped-by-fc'))
                del ours[iid]
                row[5].remove(iid)
                changed = True
    # 本地重复物品警告
    seen = {}
    for r in rows:
        for iid in r[4]:
            seen.setdefault(iid, []).append(r[0])
    for iid, rs in seen.items():
        if len(rs) > 1:
            log['dup'].append((did, iid, rs))

# 重序列化
def ser_row(r):
    en, zh, note, npc, items, order = r
    lines = ['        { "%s", "%s", "%s", "%s", {' % (en, zh, note, npc)]
    for iid in order:
        ch, flag = items[iid]
        lines.append('            { %d, %s, %s },' % (iid, fmt_ch(ch), 'true' if flag else 'false'))
    lines.append('        } },')
    return '\n'.join(lines)

if changed and not DRY:
    parts = [head]
    for did, rows, _raw in blocks:
        parts.append('\n    ["%s"] = {\n%s\n    },' % (did, '\n'.join(ser_row(r) for r in rows)))
    out = ''.join(parts) + '\n}\n'
    bak = os.path.join(HERE, '_rl_bak')
    os.makedirs(bak, exist_ok=True)
    shutil.copyfile(LT, os.path.join(bak, 'Data_DungeonLoot.lua.bak'))
    open(LT, 'w', encoding='utf-8', newline='').write(out)
    print('WROTE', LT)

for k in ('add', 'remove', 'obs_downgrade', 'fc_row_unmatched', 'dup'):
    v = log[k]
    print('==', k, len(v))
    for x in v[:60]:
        print('  ', x)
