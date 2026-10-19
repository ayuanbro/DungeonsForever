# -*- coding: utf-8 -*-
"""按名字（en 优先，其次 zh）对齐钉点，输出 ns.BossPos 数据表草稿。"""
import re, json, os, html

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "..", "Core", "Data", "Data_DungeonLoot.lua"), encoding="utf-8").read()
BLOCK = re.compile(r'^\s*\["([a-z_0-9]+)"\]\s*=\s*\{')
SRC = re.compile(r'^\s*\{ "((?:[^"\\]|\\.)*)", "((?:[^"\\]|\\.)*)", "((?:[^"\\]|\\.)*)", "((?:[^"\\]|\\.)*)",')

blocks, cur = {}, None
for line in src.splitlines():
    m = BLOCK.match(line)
    if m:
        cur = m.group(1); blocks[cur] = []; continue
    if cur:
        m2 = SRC.match(line)
        if m2:
            blocks[cur].append({"en": m2.group(1).replace("\\'", "'"), "zh": m2.group(2), "npc": m2.group(4)})

raw = json.load(open(os.path.join(HERE, "_boss_pins_raw.json"), encoding="utf-8"))
# 站点译名与我方不同、人工确认是同一首领的补录（站点名 → 我方英文名）
MANUAL = {("the_stockade", "巴吉尔·特雷德"): "Bazil Thredd"}
out, unmatched = {}, {}
for did, info in raw.items():
    if not info["pins"]:
        continue
    ours = blocks.get(did, [])
    by_en = {s["en"]: s for s in ours}
    by_zh = {s["zh"]: s for s in ours}
    res = {}
    for p in info["pins"]:
        nm = html.unescape(p["name"] or "").strip()
        forced = MANUAL.get((did, nm))
        s = by_en.get(forced) if forced else (by_en.get(nm) or by_zh.get(nm))
        if not s:
            unmatched.setdefault(did, []).append(nm)
            continue
        res.setdefault(s["en"], []).append([p["left"], p["top"]])
    out[did] = res

print("=== 对齐结果 ===")
for did, res in out.items():
    ours = blocks.get(did, [])
    print("###", did, " 覆盖 %d/%d" % (len(res), len([s for s in ours if s['en'] != 'Trash mobs'])))
    for en, pts in res.items():
        print("    %-34s %s" % (en, pts))
    miss = [s["en"] for s in ours if s["en"] not in res and s["en"] != "Trash mobs"]
    print("    未覆盖:", ", ".join(miss) or "-")
print()
print("=== 站点有、我方认不出的名字 ===")
for did, names in unmatched.items():
    print("  ", did, names)
json.dump(out, open(os.path.join(HERE, "_bosspos_draft.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
