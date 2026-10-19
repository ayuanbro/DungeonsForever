# -*- coding: utf-8 -*-
"""全表审计：NPCLoc 的坐标到底跟「经典口径」还是「巫妖王口径」对得上？按地图汇总。"""
import re, io, os, json, collections

TITAN = r"D:/workspace/DungeonsForever"
Q = r"D:/Game/World of Warcraft/_classic_titan_/Interface/AddOns/Questie/Database"


def entries(txt):
    for m in re.finditer(r'\n\[(\d+)\]\s*=\s*\{', txt):
        nid = int(m.group(1)); i = m.end() - 1
        depth = 0; instr = False; esc = False
        while i < len(txt):
            ch = txt[i]
            if instr:
                if esc: esc = False
                elif ch == '\\': esc = True
                elif ch in "'\"": instr = False
            else:
                if ch in "'\"": instr = True
                elif ch == '{': depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0: break
            i += 1
        yield nid, txt[m.end() - 1:i + 1]


def top_fields(body):
    inner = body[1:-1]
    out = []; depth = 0; cur = ''; instr = False; esc = False
    for ch in inner:
        if instr:
            cur += ch
            if esc: esc = False
            elif ch == '\\': esc = True
            elif ch in "'\"": instr = False
            continue
        if ch in "'\"": instr = True; cur += ch; continue
        if ch == '{': depth += 1; cur += ch; continue
        if ch == '}': depth -= 1; cur += ch; continue
        if ch == ',' and depth == 0:
            out.append(cur.strip()); cur = ''; continue
        cur += ch
    if cur.strip(): out.append(cur.strip())
    return out


def load_pts(path):
    """{npcID: [(x,y), ...]} —— 所有地图的所有点位"""
    res = {}
    for nid, body in entries(io.open(path, encoding='utf-8', errors='replace').read()):
        f = top_fields(body)
        if len(f) < 7: continue
        pts = [(float(a), float(b)) for a, b in re.findall(r'\{([-\d.]+)\s*,\s*([-\d.]+)\}', f[6])]
        if pts: res[nid] = pts
    return res


C = load_pts(os.path.join(Q, 'Classic/classicNpcDB.lua'))
W = load_pts(os.path.join(Q, 'Wotlk/wotlkNpcDB.lua'))
MoP = load_pts(os.path.join(Q, 'MoP/mopNpcDB.lua'))
print("经典 %d / 巫妖王 %d / 潘达利亚 %d 条有坐标的 NPC" % (len(C), len(W), len(MoP)))

loc = io.open(TITAN + "/Core/Data/Data_NPCLoc.lua", encoding='utf-8').read()
nploc = {}
for m in re.finditer(r'\[\s*(\d+)\s*\]\s*=\s*\{\s*(\d+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*"([^"]*)"\s*\}', loc):
    nploc[int(m.group(1))] = (int(m.group(2)), float(m.group(3)), float(m.group(4)), m.group(5))


def mind(pool, nid, x, y):
    if nid not in pool: return None
    return min(max(abs(px - x), abs(py - y)) for px, py in pool[nid])


stat = collections.defaultdict(lambda: collections.Counter())
detail = []
for nid, (mp, x, y, zone) in nploc.items():
    dc = mind(C, nid, x, y); dw = mind(W, nid, x, y); dm = mind(MoP, nid, x, y)
    cand = {'经典': dc, '巫妖王': dw, '潘达利亚': dm}
    cand = {k: v for k, v in cand.items() if v is not None}
    if not cand: continue
    best = min(cand, key=lambda k: cand[k])
    stat[zone][best] += 1
    stat[zone]['总'] += 1
    detail.append((nid, zone, x, y, best, dc, dw, dm))

print()
print("=== 每张地图：NPCLoc 坐标最接近哪个资料片口径 ===")
print("%-20s %6s %8s %8s %10s" % ("地图", "条目", "经典", "巫妖王", "潘达利亚"))
for zone in sorted(stat, key=lambda z: -stat[z]['总']):
    s = stat[zone]
    print("%-20s %6d %8d %8d %10d" % (zone, s['总'], s['经典'], s['巫妖王'], s['潘达利亚']))

print()
print("=== 暴风城逐条明细 ===")
for nid, zone, x, y, best, dc, dw, dm in sorted(detail):
    if zone != '暴风城': continue
    print("  %-7d 旧 %5.1f,%5.1f  最接近=%-6s  经典Δ=%s 巫妖王Δ=%s"
          % (nid, x, y, best, ("%.2f" % dc) if dc is not None else "—",
             ("%.2f" % dw) if dw is not None else "—"))

print()
print("=== 除暴风城外，「巫妖王吻合并与经典差 >2」的条目（可能是同一坑）===")
n = 0
for nid, zone, x, y, best, dc, dw, dm in sorted(detail):
    if zone == '暴风城': continue
    if dw is not None and dw < 1.2 and dc is not None and dc > 2:
        print("  %-7d %-14s 旧 %5.1f,%5.1f  经典Δ=%.1f 巫妖王Δ=%.2f" % (nid, zone, x, y, dc, dw))
        n += 1
if not n:
    print("  无 —— 说明这个坑只影响暴风城")
