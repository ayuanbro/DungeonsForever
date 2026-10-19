# -*- coding: utf-8 -*-
"""抽取 BossSkills 的 id→副本/boss 映射，并生成全量描述探测探针。

产物：
  _probe_all_ids.lua   —— 426 个唯一 id 的客户端名字/描述探测探针（lycheedev live）
  _id_map.json         —— id → [{dungeon, dungZh, bossEn, bossZh}] 映射（join 用）
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
DATA = os.path.join(DF, "Core", "Data")

# ── 1. 副本 key → 中文名（Data_Dungeons.lua） ─────────────────────────────
dung_zh = {}
with open(os.path.join(DATA, "Data_Dungeons.lua"), encoding="utf-8") as f:
    for m in re.finditer(r'id\s*=\s*"([a-z0-9_]+)",\s*name\s*=\s*"([^"]+)"', f.read()):
        dung_zh[m.group(1)] = m.group(2)

# ── 2. DungeonLoot：副本块内的 { "En", "Zh", → en→zh ─────────────────────
boss_zh = {}  # (dungKey, enLower) -> zh
cur = None
pair_re = re.compile(r'\{\s*"((?:[^"\\]|\\.)*)"\s*,\s*"((?:[^"\\]|\\.)*)"')
key_re = re.compile(r'^\s{4}(?:\[")?([a-z0-9_]+)"?\]?\s*=\s*\{')
with open(os.path.join(DATA, "Data_DungeonLoot.lua"), encoding="utf-8") as f:
    for line in f:
        mk = key_re.match(line)
        if mk:
            cur = mk.group(1)
            continue
        if cur:
            for en, zh in pair_re.findall(line):
                k = (cur, en.strip().lower())
                if k not in boss_zh:
                    boss_zh[k] = zh

# ── 3. BossSkills：id → [(副本, boss)]（本文件已无 SpellTips，纯 id 行） ──
id_map = {}
cur = None
boss = None
row_re = re.compile(r'\{\s*"",\s*"",\s*(\d+)')
dkey_re = re.compile(r'^\s{4}([a-z0-9_]+)\s*=\s*\{')
bkey_re = re.compile(r'^\s{8}\["(.+?)"\]\s*=\s*\{')
with open(os.path.join(DATA, "Data_BossSkills.lua"), encoding="utf-8") as f:
    for line in f:
        mk = dkey_re.match(line)
        if mk:
            cur, boss = mk.group(1), None
            continue
        mb = bkey_re.match(line)
        if mb:
            boss = mb.group(1)
            continue
        for sid in row_re.findall(line):
            sid = int(sid)
            ent = id_map.setdefault(sid, [])
            zh = boss_zh.get((cur, boss.strip().lower()) if boss else None)
            ent.append({"dungeon": cur, "dungZh": dung_zh.get(cur, cur),
                        "bossEn": boss or "?", "bossZh": zh or ""})

uniq = sorted(id_map)
print("唯一 id 数 =", len(uniq))
multi = sum(1 for v in id_map.values() if len(v) > 1)
print("跨副本复用 id =", multi)
nozh = sum(1 for v in id_map.values() for e in v if not e["bossZh"])
print("boss 无 zh 名条目 =", nozh)

# ── 4. 生成探针 ──────────────────────────────────────────────────────────
ids_literal = ", ".join(str(i) for i in uniq)
probe = """-- df_spell_desc_all: 全量探测客户端对 BossSkills 全部能力 id 的名字/描述可得性
-- 口径与 MapUI.SpellRowFor 一致：GetSpellInfo → C_Spell.GetSpellInfo；
-- 描述 C_Spell.GetSpellDescription → GetSpellDescription。只读，不动任何游戏状态。

local probe = ...
local ids = { %s }

local function clip(s, n)
    if type(s) ~= "string" then return nil end
    if #s > n then return string.sub(s, 1, n) .. "…" end
    return s
end

local out = {}
for _, id in ipairs(ids) do
    local row = { id = id }
    if GetSpellInfo then
        local ok, a = pcall(GetSpellInfo, id)
        if ok then row.name = clip(a, 48) end
    end
    if not row.name and C_Spell and C_Spell.GetSpellInfo then
        local ok, info = pcall(C_Spell.GetSpellInfo, id)
        if ok and type(info) == "table" then row.name = clip(info.name, 48) end
    end
    if C_Spell and C_Spell.GetSpellDescription then
        local ok, v = pcall(C_Spell.GetSpellDescription, id)
        if ok then row.desc = clip(v, 90) end
    end
    if not row.desc and GetSpellDescription then
        local ok, v = pcall(GetSpellDescription, id)
        if ok then row.desc = clip(v, 90) end
    end
    out[#out + 1] = row
end

probe:Finish({ spells = out })
""" % ids_literal

with open(os.path.join(HERE, "_probe_all_ids.lua"), "w", encoding="utf-8") as f:
    f.write(probe)
with open(os.path.join(HERE, "_id_map.json"), "w", encoding="utf-8") as f:
    json.dump(id_map, f, ensure_ascii=False)
print("探针与映射已写出：_probe_all_ids.lua / _id_map.json")
