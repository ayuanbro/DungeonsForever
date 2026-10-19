# -*- coding: utf-8 -*-
"""
暴风城 NPC 坐标 · 三源交叉核对（定稿用）
=========================================================
源 A：Data_NPCLoc.lua（现行值 = wowhead forever 分支口径，经典边界）
源 B：Questie/Database/Wotlk/wotlkNpcDB.lua（新生代边界，用户两点实测命中）
源 C：_wh_wotlk_npccache/npc=<id>.txt 的 g_mapperData coords 全列表（wowhead wotlk 页）
判据：B 值若能在 C 的点集里找到 ±0.8 的近邻 → 「双源确认」；
      只有 B 无 C → 「单源」；无 B → 回退旧值经边界变换。
边界变换（上轮由 263 组静止 NPC 拟合）：x' = 0.760476x + 21.0335, y' = 0.781010y + 23.7064
"""
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ADDONS = os.path.dirname(ROOT)
QDB = os.path.join(ADDONS, "Questie", "Database", "Wotlk", "wotlkNpcDB.lua")
CACHE = os.path.join(HERE, "_wh_wotlk_npccache")

AX, BX = 0.760476, 21.0335
AY, BY = 0.781010, 23.7064

IDS = [332, 656, 928, 1284, 1416, 1646, 1719, 1721, 1748, 2198, 2285,
       4984, 5384, 5413, 6171, 6579, 7917, 12336, 14450]
NAMES = {
    332: "马迪亚斯·肖尔", 656: "维尔德·蓟草", 928: "格雷森·沙东布瑞克公爵",
    1284: "大主教本尼迪塔斯", 1416: "格瑞曼德·艾尔默", 1646: "巴隆斯·阿历克斯顿",
    1719: "典狱官塞尔沃特", 1721: "尼科瓦·拉斯克", 1748: "伯瓦尔·弗塔根公爵",
    2198: "公告员古德曼", 2285: "雷明顿·瑞治维尔伯爵", 4984: "阿古斯·夜语",
    5384: "布罗哈恩·铁桶", 5413: "弗伦·长须", 6171: "达索瑞恩·拉尔",
    6579: "沉默的舒尼", 7917: "萨尔努修士", 12336: "克罗雷修士",
    14450: "孤儿监护员奈丁加尔",
}

# ── 源 A：现行数据 ──────────────────────────────────────────────
cur = {}
txt = io.open(os.path.join(ROOT, "Core", "Data", "Data_NPCLoc.lua"), encoding="utf-8").read()
for m in re.finditer(r'\[(\d+)\] = \{ (\d+), ([\d.]+), ([\d.]+), "([^"]*)" \}', txt):
    cur[int(m.group(1))] = (int(m.group(2)), float(m.group(3)), float(m.group(4)), m.group(5))

# ── 源 B：Questie 巫妖王库 spawns ───────────────────────────────
qraw = io.open(QDB, encoding="utf-8", errors="replace").read()
q = {}
for nid in IDS:
    m = re.search(r'\n\[%d\] = \{' % nid, qraw)
    if not m:
        q[nid] = None
        continue
    # 取该条目到下一个顶层键（\n[数字] = {）之间的片段
    m2 = re.compile(r'\n\[\d+\] = \{').search(qraw, m.end())
    seg = qraw[m.end(): m2.start() if m2 else m.end() + 20000]
    pts = []
    for mm in re.finditer(r'\[1519\]\s*=\s*\{', seg):          # 1519 = 东部王国
        # 花括号配平取出 spawns[1519] 数组
        i = mm.end() - 1
        d = 0
        for k in range(i, min(i + 40000, len(seg))):
            if seg[k] == '{':
                d += 1
            elif seg[k] == '}':
                d -= 1
                if d == 0:
                    blk = seg[i:k + 1]
                    break
        else:
            continue
        for pm in re.finditer(r'\{\s*([\d.]+)\s*,\s*([\d.]+)', blk):
            pts.append((float(pm.group(1)), float(pm.group(2))))
    q[nid] = pts

# ── 源 C：wowhead wotlk 页 coords 全列表 ────────────────────────
wh = {}
for nid in IDS:
    p = os.path.join(CACHE, "npc=%d.txt" % nid)
    pts = []
    if os.path.exists(p):
        h = io.open(p, encoding="utf-8", errors="replace").read()
        i = h.find("g_mapperData")
        j = h.find("{", i) if i >= 0 else -1
        if j >= 0:
            d, end = 0, None
            for k in range(j, min(j + 200000, len(h))):
                if h[k] == "{":
                    d += 1
                elif h[k] == "}":
                    d -= 1
                    if d == 0:
                        end = k + 1
                        break
            if end:
                try:
                    data = json.loads(h[j:end])
                    for zv in data.values():
                        if isinstance(zv, list):
                            for e in zv:
                                if e.get("uiMapId") == 1453:
                                    for c in (e.get("coords") or []):
                                        pts.append((float(c[0]), float(c[1])))
                except Exception:
                    pass
    wh[nid] = pts


def near(pts, x, y, tol=0.8):
    """点集里找 ±tol 内的近邻 → (dist, x, y) 或 None"""
    best = None
    for (px, py) in pts:
        d = max(abs(px - x), abs(py - y))
        if d <= tol and (best is None or d < best[0]):
            best = (d, px, py)
    return best


print("%-7s %-21s %-13s %-13s %-13s %s" % ("NPC", "名称", "现行(经典)", "Questie-Wotlk", "wowhead-wotlk", "判定"))
print("-" * 118)
lines = []
for nid in IDS:
    c = cur.get(nid)
    old = "%6.1f,%6.1f" % (c[1], c[2]) if c else "   --   "
    pred = (AX * c[1] + BX, AY * c[2] + BY) if c else None
    qp = q.get(nid) or []
    wl = wh.get(nid) or []
    # 选定 B 值：优先「与 C 点集近邻」的那个 spawn；否则第一个
    pick = None
    if qp:
        if wl:
            for (x, y) in qp:
                if near(wl, x, y):
                    pick = (x, y)
                    break
        if pick is None:
            pick = qp[0]
    verdict = ""
    if pick:
        nz = near(wl, pick[0], pick[1]) if wl else None
        if nz:
            verdict = "双源确认(±%.1f)" % nz[0]
        elif wl:
            # B 不在 C 里 → 看 C 有没有「离旧值变换后最近」的点
            if pred:
                nb = near(wl, pred[0], pred[1], 1.5)
                verdict = "单源；C 近变换点 %s" % ("%6.1f,%6.1f Δ%.1f" % (nb[1], nb[2], nb[0]) if nb else "无")
            else:
                verdict = "单源"
        else:
            verdict = "单源(无C)"
        val = "%6.1f,%6.1f" % pick
        nspawn = len(qp)
    else:
        val = "   --   "
        nspawn = 0
        if pred:
            nb = near(wl, pred[0], pred[1], 2.0) if wl else None
            verdict = "无B → 变换 %.1f,%.1f" % (pred[0], pred[1])
            if nb:
                verdict += " C近邻 %.1f,%.1f" % (nb[1], nb[2])
        else:
            verdict = "无B无变换"
    wshow = "  ".join("%.1f,%.1f" % p for p in wl[:6]) + (" …(%d)" % len(wl) if len(wl) > 6 else "")
    print("%-7d %-21s %-13s %-13s %-13s %s" % (nid, NAMES[nid], old, val, wshow[:34], verdict))
    lines.append((nid, val, nspawn, verdict, wl, qp, pred))

print()
print("=== 逐条细节：Questie 全部 spawn 点 / wowhead 全部点 ===")
for nid, val, nspawn, verdict, wl, qp, pred in lines:
    print("%d %s  questie(%d)=%s" % (nid, NAMES[nid], len(qp), " ".join("%.1f,%.1f" % p for p in qp[:8])))
    print("      wh(%d)=%s" % (len(wl), " ".join("%.1f,%.1f" % p for p in wl[:10])))
    if pred:
        print("      变换=%0.1f,%0.1f" % pred)
