# -*- coding: utf-8 -*-
"""把参考站钉点的 npcID 与本插件 Data_DungeonLoot 的来源对齐，产出可用子集。"""
import re, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "..", "Core", "Data", "Data_DungeonLoot.lua"), encoding="utf-8").read()

BLOCK = re.compile(r'^\s*\["([a-z_0-9]+)"\]\s*=\s*\{')
SRC = re.compile(r'^\s*\{ "((?:[^"\\]|\\.)*)", "((?:[^"\\]|\\.)*)", "((?:[^"\\]|\\.)*)", "((?:[^"\\]|\\.)*)",')

blocks, cur = {}, None
for line in src.splitlines():
    m = BLOCK.match(line)
    if m:
        cur = m.group(1)
        blocks[cur] = []
        continue
    if cur:
        m2 = SRC.match(line)
        if m2:
            blocks[cur].append({"en": m2.group(1), "zh": m2.group(2), "note": m2.group(3), "npc": m2.group(4)})

raw = json.load(open(os.path.join(HERE, "_boss_pins_raw.json"), encoding="utf-8"))
out = {}
for did, info in raw.items():
    if not info["pins"]:
        continue
    ours = blocks.get(did, [])
    our_npcs = {s["npc"] for s in ours if s["npc"]}
    print("###", did, " 我方来源=%d 有npc=%d" % (len(ours), len(our_npcs)))
    keep = {}
    for p in info["pins"]:
        n = str(p["npcid"]) if p["npcid"] else None
        hit = "✓" if (n and n in our_npcs) else ("(无npc)" if not n else "✗不匹配")
        nm = next((s["zh"] for s in ours if s["npc"] == n), "")
        print("    %-7s %-6s %-6s %-8s %s  %s" % (p["npcid"], p["left"], p["top"], hit, p["name"], nm))
        if n and n in our_npcs:
            keep.setdefault(n, []).append([p["left"], p["top"]])
    print("    我方 npc 名单:", sorted(our_npcs))
    out[did] = keep
print()
print("=== 可挂载钉点汇总 ===")
for did, keep in out.items():
    print("  %-24s %d 个首领有坐标" % (did, len(keep)))
json.dump(out, open(os.path.join(HERE, "_boss_pins_matched.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
