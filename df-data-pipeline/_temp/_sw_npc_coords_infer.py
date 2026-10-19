# -*- coding: utf-8 -*-
"""稳健版：逐条配对花括号解析 Questie NPC 库，抽出 [1519] 出生点。"""
import re, io, os, json

Q = r"D:/Game/World of Warcraft/_classic_titan_/Interface/AddOns/Questie/Database"

BAGS = {'classic': 'Classic/classicNpcDB.lua', 'tbc': 'TBC/tbcNpcDB.lua',
        'wotlk': 'Wotlk/wotlkNpcDB.lua', 'mop': 'MoP/mopNpcDB.lua'}
FIX = {'wotlk': 'Corrections/wotlkNPCFixes.lua', 'classic': 'Corrections/classicNPCFixes.lua',
       'tbc': 'Corrections/tbcNPCFixes.lua', 'mop': 'Corrections/mopNPCFixes.lua'}


def entries(txt):
    """产出 (npcID, 条目原文)。用花括号配对定位每条 [id] = { ... }。"""
    for m in re.finditer(r'\n\[(\d+)\]\s*=\s*\{', txt):
        nid = int(m.group(1))
        i = m.end() - 1
        depth = 0; instr = False; esc = False
        while i < len(txt):
            ch = txt[i]
            if instr:
                if esc: esc = False
                elif ch == '\\': esc = True
                elif ch == "'" or ch == '"': instr = False
            else:
                if ch == "'" or ch == '"': instr = True
                elif ch == '{': depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        break
            i += 1
        yield nid, txt[m.end() - 1:i + 1]


def top_fields(body):
    """body 形如 {a,b,{c,d},...}；返回顶层字段列表（不含最外层花括号）。"""
    assert body[0] == '{'
    inner = body[1:-1]
    out = []; depth = 0; cur = ''; instr = False; esc = False
    for ch in inner:
        if instr:
            cur += ch
            if esc: esc = False
            elif ch == '\\': esc = True
            elif ch == "'" or ch == '"': instr = False
            continue
        if ch == "'" or ch == '"': instr = True; cur += ch; continue
        if ch == '{': depth += 1; cur += ch; continue
        if ch == '}': depth -= 1; cur += ch; continue
        if ch == ',' and depth == 0:
            out.append(cur.strip()); cur = ''; continue
        cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def load(path):
    res = {}
    if not os.path.exists(path):
        return res
    txt = io.open(path, encoding='utf-8', errors='replace').read()
    for nid, body in entries(txt):
        f = top_fields(body)
        if len(f) < 7:
            res[nid] = (None, None); continue
        nm = f[0].strip().strip("'\"")
        sp = f[6]
        pts = []
        mm = re.search(r'\[1519\]\s*=\s*\{((?:\{[^}]*\}\s*,?\s*)+)\}', sp)
        if mm:
            pts = [(float(a), float(b)) for a, b in re.findall(r'\{([-\d.]+)\s*,\s*([-\d.]+)\}', mm.group(1))]
        res[nid] = (nm, pts if pts else None)
    return res


DB = {k: load(os.path.join(Q, p)) for k, p in BAGS.items()}
for k, v in DB.items():
    n = sum(1 for x in v.values() if x[1])
    print("%-8s 条目 %d，其中有暴风城坐标 %d" % (k, len(v), n))

print()
IDS = [(332, '马迪亚斯·肖尔'), (656, '维尔德·蓟草'), (928, '格雷森·沙东布瑞克公爵'), (1284, '大主教本尼迪塔斯'),
       (1416, '格瑞曼德·艾尔默'), (1646, '巴隆斯·阿历克斯顿'), (1719, '典狱官塞尔沃特'), (1721, '尼科瓦·拉斯克'),
       (1748, '伯瓦尔·弗塔根公爵'), (2198, '公告员古德曼'), (2285, '雷明顿·瑞治维尔伯爵'), (4984, '阿古斯·夜语'),
       (5384, '布罗哈恩·铁桶'), (5413, '弗伦·长须'), (6171, '达索瑞恩·拉尔'), (6579, '沉默的舒尼'),
       (7917, '萨尔努修士'), (12336, '克罗雷修士'), (14450, '孤儿监护员奈丁加尔')]
OLD = {332: (75.8, 59.8), 656: (65.2, 21.2), 928: (37.2, 33.0), 1284: (39.4, 27.4), 1416: (51.6, 12.2),
       1646: (49.0, 30.2), 1719: (41.0, 57.0), 1721: (66.8, 46.4), 1748: (77.4, 18.4), 2198: (33.2, 70.4),
       2285: (74.0, 29.2), 4984: (21.4, 55.4), 5384: (64.2, 20.8), 5413: (57.4, 16.0), 6171: (39.4, 30.4),
       6579: (55.4, 12.4), 7917: (40.4, 30.4), 12336: (42.0, 24.8), 14450: (47.2, 38.4)}
MEASURED = {5413: (64.6, 37.2), 6579: (62.6, 34.1)}
AQ = {656: (70, 41), 1284: (50, 45), 1719: (51, 69), 1721: (75, 63), 5384: (69, 40), 5413: (64, 37), 6579: (62, 34)}

print("=== 标定：用户实测 vs 各资料片 ===")
for nid, (mx, my) in MEASURED.items():
    nm = dict(IDS)[nid]
    s = "  %-6d %-10s 实测 %s,%s →" % (nid, nm, mx, my)
    for k in ('classic', 'tbc', 'wotlk', 'mop'):
        p = DB[k].get(nid)
        if p and p[1]:
            x, y = p[1][0]
            s += "  %s %s,%s Δ%.2f" % (k, round(x, 2), round(y, 2), max(abs(x - mx), abs(y - my)))
        else:
            s += "  %s —" % k
    print(s)
print()

print("=== 全 19 个：巫妖王库（= 标定命中的资料片） ===")
print("%-7s %-12s | %-13s | %-15s | %-10s | %s" % ("ID", "名称", "旧(NPCLoc)", "巫妖王出生点", "AQ口径", "AQ↔WotLK 校验"))
final = {}
for nid, nm in IDS:
    w = DB['wotlk'].get(nid)
    wp = w[1][0] if (w and w[1]) else None
    aq = AQ.get(nid)
    chk = '—'
    if aq and wp:
        d = max(abs(wp[0] - aq[0]), abs(wp[1] - aq[1]))
        chk = '✓ Δ%.2f' % d if d <= 1.5 else '⚠ Δ%.2f（巡逻 NPC）' % d
    elif aq and not wp:
        chk = '（巫妖王库无出生点）'
    ox, oy = OLD[nid]
    print("%-7d %-12s | %5.1f,%-7.1f | %-15s | %-10s | %s" %
          (nid, nm, ox, oy, ("%.2f,%.2f" % wp) if wp else "—", ("%d,%d" % aq) if aq else "—", chk))
    final[nid] = dict(name=nm, old=OLD[nid], wotlk=wp, aq=aq,
                      classic=(DB['classic'][nid][1][0] if DB['classic'].get(nid) and DB['classic'][nid][1] else None),
                      mop=(DB['mop'][nid][1][0] if DB['mop'].get(nid) and DB['mop'][nid][1] else None))

print()
print("=== 巫妖王库无坐标、需要另找依据的 ===")
for nid, nm in IDS:
    if not final[nid]['wotlk']:
        print("  %-7d %-12s  旧=%s  mop=%s" % (nid, nm, OLD[nid], final[nid]['mop']))

json.dump({str(k): v for k, v in final.items()},
          io.open(r"C:/Users/Administrator/AppData/Local/Temp/sw_final.json", 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
