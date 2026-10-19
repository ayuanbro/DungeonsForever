# -*- coding: utf-8 -*-
"""按名字对齐：参考站钉点（中文名/英文名）→ 我方 Data_DungeonLoot 来源。"""
import re, json, os

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
            blocks[cur].append({"en": m2.group(1), "zh": m2.group(2), "note": m2.group(3), "npc": m2.group(4)})

raw = json.load(open(os.path.join(HERE, "_boss_pins_raw.json"), encoding="utf-8"))
import html
for did, info in raw.items():
    if not info["pins"]:
        continue
    ours = blocks.get(did, [])
    print("###", did)
    print("   我方:", " | ".join("%s/%s(%s)" % (s["zh"], s["en"], s["npc"]) for s in ours))
    print("   站点:", " | ".join("%s[%s]" % (html.unescape(p["name"]), p["npcid"]) for p in info["pins"]))
    print()
