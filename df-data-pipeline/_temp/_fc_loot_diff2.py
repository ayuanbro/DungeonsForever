# -*- coding: utf-8 -*-
"""掉落全量对查 v2（2026-10-05）：fc 改版新页（_ref/dg_<slug>.html，含 bosses[].items
富字段 i/n/q/t/z/ne）vs Core/Data/Data_DungeonLoot.lua。

对齐：fc boss.display(npcid) ↔ 我方来源行第 4 位 npcid；无号回退 english↔英文名
（norm 去符号）；kind=trash ↔ 我方「Trash mobs」行。

报告维度：
  FC-BOSS-NOT-IN-OUR-LOOT   fc 有该来源、我们没有
  FC-ITEM-WE-LACK           fc 有该物品、该来源下我们没有（附 t/z）
  OUR-ITEM-NOT-ON-FC        我们有、fc 没有（不自动删，仅报）
  FLAG-DIFF                 无限版新增旗标不一致（fc t=new vs 我们 true）
  CHANCE-DIFF               掉率不一致（fc z 四舍五入 vs 我们）

用法：python _fc_loot_diff2.py
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fc_compare import SLUG2DID, norm, unesc, ours_block, ROOT  # noqa

LT = os.path.join(ROOT, "Core", "Data", "Data_DungeonLoot.lua")
REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_ref")


def extract_bosses(h):
    """→ [ {name, kind, level, display, english, items:[{i,t,z,ne,n}]}, … ]"""
    i = h.find('bosses\\":[')
    if i < 0:
        return []
    j = i + len('bosses\\":')
    depth, k = 0, j
    while k < len(h):
        c = h[k]
        if c == "\\":
            k += 2
            continue
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                break
        k += 1
    return json.loads(unesc(h[j:k + 1]))


def ours_rows(did):
    """→ [ {en, zh, note, npc, items:{iid:(chance,flag)}} ]"""
    src = open(LT, encoding="utf-8").read()
    blk = ours_block(src, did)
    if not blk:
        return None
    out = []
    ROW = re.compile(
        r'\{ "((?:[^"\\]|\\.)*)", "((?:[^"\\]|\\.)*)", "((?:[^"\\]|\\.)*)", "((?:[^"\\]|\\.)*)", \{(.*?)\n        \} \}',
        re.S)
    IT = re.compile(r'\{ (\d+), (nil|[\d.]+), (true|false|nil) \}')
    for m in ROW.finditer(blk):
        items = {}
        for it in IT.finditer(m.group(5)):
            items[int(it.group(1))] = (None if it.group(2) == "nil" else float(it.group(2)),
                                       it.group(3) == "true")
        out.append({"en": m.group(1), "zh": m.group(2), "note": m.group(3),
                    "npc": m.group(4), "items": items})
    return out


def main():
    report = []
    for slug, did in sorted(SLUG2DID.items()):
        p = os.path.join(REF, "dg_%s.html" % slug)
        if not os.path.exists(p):
            report.append((did, "NO-PAGE", slug, ""))
            continue
        fc = extract_bosses(open(p, encoding="utf-8", errors="replace").read())
        if not fc:
            report.append((did, "NO-BOSSES", slug, ""))
            continue
        ours = ours_rows(did)
        if ours is None:
            report.append((did, "NO-OUR-LOOT", slug, ""))
            continue
        # 对齐：只认英文名（fc display 是服务器号且三卫兵共用 11561，不可信）；
        # kind=trash ↔ 我方「Trash mobs」行。同名 fc 对象先合并（union）再比。
        by_en = {}
        for r in ours:
            by_en.setdefault(norm(r["en"]), r)
        fc_merged = {}   # our_row_id(en) -> {iid: item dict}
        fc_unmatched = []
        for b in fc:
            en = b.get("english") or b.get("name") or ""
            kind = b.get("kind") or ""
            row = by_en.get(norm(en))
            if row is None and kind == "trash":
                row = by_en.get("trashmobs")
            if row is None:
                fc_unmatched.append(b)
                continue
            dst = fc_merged.setdefault(row["en"], {})
            for it in b.get("items") or []:
                iid = int(it["i"])
                if iid not in dst:
                    dst[iid] = it
        for b in fc_unmatched:
            en = b.get("english") or b.get("name") or ""
            report.append((did, "FC-BOSS-NOT-IN-OUR-LOOT", en,
                           "kind=%s display=%s items=%d" % (b.get("kind"), b.get("display"), len(b.get("items") or []))))
        for en, items in fc_merged.items():
            row = by_en[norm(en)] if norm(en) in by_en else by_en["trashmobs"]
            my = row["items"]
            for iid, it in items.items():
                t = it.get("t")
                z = it.get("z")
                if iid not in my:
                    report.append((did, "FC-ITEM-WE-LACK", "%s/%s" % (row["en"], iid),
                                   "t=%s z=%s ne=%s" % (t, z, it.get("ne", ""))))
                    continue
                ch, fl = my[iid]
                fc_new = (t == "new")
                if fc_new != fl:
                    report.append((did, "FLAG-DIFF", "%s/%s" % (row["en"], iid),
                                   "fc t=%s vs ours flag=%s" % (t, fl)))
                fz = None if z is None else round(float(z), 2)
                if fz and ((ch is None) or abs((ch or 0) - fz) >= 0.05):
                    report.append((did, "CHANCE-DIFF", "%s/%s" % (row["en"], iid),
                                   "fc z=%s vs ours=%s" % (z, ch)))
            for iid in my:
                if iid not in items:
                    report.append((did, "OUR-ITEM-NOT-ON-FC", "%s/%s" % (row["en"], iid), ""))
    json.dump(report, open("_fc_loot_report2.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for typ in ("NO-PAGE", "NO-BOSSES", "NO-OUR-LOOT", "FC-BOSS-NOT-IN-OUR-LOOT",
                "FC-ITEM-WE-LACK", "FLAG-DIFF", "CHANCE-DIFF", "OUR-ITEM-NOT-ON-FC"):
        rows = [r for r in report if r[1] == typ]
        print("== %s (%d) ==" % (typ, len(rows)))
        for r in rows[:60]:
            print("   %-20s %s" % (r[0], r[2] + ("  " + r[3] if r[3] else "")))
    print("total", len(report))


if __name__ == "__main__":
    main()
