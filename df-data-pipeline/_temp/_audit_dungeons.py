# -*- coding: utf-8 -*-
"""一次性审计：全部副本 × (掉落 / 攻略 / 钉点 / 技能) 四层数据完整度。"""
import io, re, os

DF = r"D:/workspace/DungeonsForever"
def read(p): return io.open(os.path.join(DF, p), encoding="utf-8").read()

dun = read("Core/Data/Data_Dungeons.lua")
guide = read("Core/Data/Data_DungeonGuide.lua")
pos = read("Core/Data/Data_BossPos.lua")
sk = read("Core/Data/Data_BossSkills.lua")
loot = read("Core/Data/Data_DungeonLoot.lua")

rows = re.findall(r'\{ id = "([\w]+)",\s*name = "([^"]+)",.*?isNew = (true|false)', dun)

def seg_of(txt, did):
    pat = r'\["' + did + r'"\]\s*=\s*\{'
    pat2 = r'(?m)^\s{4}' + did + r'\s*=\s*\{'
    m = re.search(pat, txt) or re.search(pat2, txt)
    if not m:
        return None
    nxt = txt.find("\n    [", m.end())
    end = nxt if nxt > 0 else min(len(txt), m.start() + 20000)
    return txt[m.start():end]

print("副本总数:", len(rows))
print("%-22s %-14s %-4s %-11s %-6s %-6s" % ("副本id", "中文名", "掉落", "攻略", "钉点", "技能"))
n = dict(loot=0, guide=0, pins=0, sk=0)
miss = {"guide": [], "pins": [], "sk": []}
for did, nm, new in rows:
    lseg, gseg, pseg, kseg = seg_of(loot, did), seg_of(guide, did), seg_of(pos, did), seg_of(sk, did)
    if lseg: n["loot"] += 1
    gb = len(re.findall(r'\{\s*en\s*=', gseg)) if gseg else 0
    tag = ('tagline' in gseg) if gseg else False
    gmark = ("✓tag+%db" % gb) if (gseg and gb) else ("✓仅tag" if tag else "✗")
    if gb: n["guide"] += 1
    else: miss["guide"].append(did)
    pins = len(re.findall(r'\{\s*[\d.]+,\s*[\d.]+', pseg)) if pseg else 0
    if pins: n["pins"] += 1
    else: miss["pins"].append(did)
    rk = len(re.findall(r'(?m)^\s+\{ "', kseg)) if kseg else 0
    if rk: n["sk"] += 1
    else: miss["sk"].append(did)
    print("%-22s %-14s %-4s %-11s %-6s %-6s" % (did, nm[:12], "✓" if lseg else "✗", gmark, pins or "✗", rk or "✗"))

print("\n汇总: 掉落 %d · 攻略(tag+boss) %d · 钉点 %d · 技能 %d / 共 %d" %
      (n["loot"], n["guide"], n["pins"], n["sk"], len(rows)))
for k in ("guide", "pins", "sk"):
    print("缺[%s]: %s" % (k, ", ".join(miss[k]) or "-"))
