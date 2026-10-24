# -*- coding: utf-8 -*-
"""生成首领技能数据文件（基表 zhCN + 覆盖层 zhTW/enUS）v4 —— wowhead 法术 id 唯一来源。

输入：
  _temp/_boss_skills_raw.json   foreverchanges 技能（zhCN/zhTW/enUS 三语 [名, 说明]）—— 现仅自制副本用
  _temp/_wh_guide_raw.json      wowhead 攻略页解析（每 boss 的 Abilities spell id 列表）
  _temp/_wh_spell_icons.json    spell id → wowhead 图标 slug（数据侧兜底图标）

口径（2026-09-30 用户定「严格参照窝窝头」；2026-10-01 起领主大厅 / 洛丹伦废墟也并入同口径 ——
它们在 wowhead 同样有 Abilities 段，技能行不再沿用 foreverchanges 文本）：
  · 全部副本：技能行**只**来自 wowhead 能力表的法术 id ——
    { "", "", 法术id[, 图标slug] }。名字/说明/图标运行期全部取自客户端（按 id 查），
    数据侧不再存自编文案（旧 foreverchanges 描述行整体退役 —— 重复行/文案与客户端
    打架即因此而生）。第 4 位 slug 仅作客户端查不到图标时的兜底，不覆盖客户端结果。
  · wowhead 页无 Abilities 段的单位 → 无技能行（诺莫瑞根 Techbot、黑深渊 Lorgus Jett /
    Baron Aquanis、影牙 Arugal's Voidwalker、洛丹伦 Lordaeron Captain —— 页内仅评论区提及）。
  · 不生成任何技能文案（2026-10-01 用户定：名字/说明/图标只来自客户端）——
    v4.1 起 ns.SpellTips wowhead 兜底表整体退役（备份在 _temp/SpellTips_backup/）。
  · zhTW/enUS 覆盖层为**合并**语义（for k,v in pairs(__overlay) do ns.BossSkills[k] = v end）；
    v4 起不再有 BossSkills 翻译内容（id 行三语共用、名字来自客户端本地化）；
    覆盖层为空合并占位。基表在 toc 中先于覆盖层加载，合并安全。

输出：
  Core/Data/Data_BossSkills.lua          （zhCN 基表：ns.BossSkills）
  Core/Data/enUS/Data_BossSkills.lua     （enUS 覆盖层：空合并占位）
  Core/Data/zhTW/Data_BossSkills.lua     （zhTW 覆盖层：空合并占位）

结构：ns.BossSkills[副本 id][首领英文名] = { 行, … }
  行 = { "", "", 法术id[, 图标slug] }
  键 = 首领**英文名**，与 ns.DungeonLoot 的来源名同一个口径（名字是唯一连接键）。
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
LOOT = os.path.join(DF, "Core", "Data", "Data_DungeonLoot.lua")
sys.path.insert(0, HERE)
try:
    from gen_zhtw import to_tw  # noqa: E402  同一条 TW 术语词表 + opencc 管线
except Exception:  # pragma: no cover - 词表缺失时退回简体（离线 harness 仍可跑）
    def to_tw(s):
        return s

DUN7 = ["ragefire_chasm", "wailing_caverns", "the_deadmines", "shadowfang_keep",
        "blackfathom_deeps", "the_stockade", "gnomeregan",
        # 自制副本（wowhead 无覆盖 ⇒ foreverchanges 文本行 + 图标 slug）
        "hall_of_thanes", "ruins_of_lordaeron",
        # 2026-10-03：挖掘场并入 wowhead 口径（abilities 法术 id 行）
        "excavation_wetlands",
        # 经典十九本（2026-10-01）：wowhead 覆盖副本分支（abilities 法术 id 行）
        "razorfen_kraul", "razorfen_downs", "uldaman", "zul_farrak", "maraudon",
        "sm_graveyard", "sm_library", "sm_armory", "sm_cathedral", "scholomance",
        "sunken_temple", "blackrock_depths", "lower_blackrock_spire", "upper_blackrock_spire",
        "dire_maul_east", "dire_maul_north", "dire_maul_west",
        "stratholme_main", "stratholme_service",
        # 2026-10-09：达拉然之城并入 wowhead 口径（abilities 法术 id 行）
        "city_of_dalaran",
        # 2026-10-11：奥妮克希亚的巢穴 —— wowhead 攻略页无标准 Abilities 段，
        # 技能 id 按攻略页内联法术链接手工登记进 _wh_guide_raw.json（_inject_onyxia_skills.py）
        "onyxias_lair"]
CUSTOM_DUN = set()  # v4 起为空：领主大厅 / 洛丹伦废墟已并入 wowhead id 行口径（2026-10-01）

# boss 名对齐（我方掉落表键 → wowhead 页键；lookup：widx[ALIAS.get(norm(en), norm(en))]）
ALIAS = {
    "lady anacondra": "lady andacondra",
    "fel steed / shadow charger": "fel steeds / shadow charger",
    "sneed": "sneed's shredder",
    # 2026-09-30 晚：wowhead 页键带 (Rare) 后缀 / 事件前缀 → 对齐我方掉落表键
    "miner johnson": "miner johnson (rare)",
    "deathsworn captain": "deathsworn captain (rare)",
    "bruegal ironknuckle": "bruegal ironknuckle (rare)",
    "dark iron ambassador": "dark iron ambassador (rare)",
    "mutanus the devourer": "naralax event mutanus the devourer",
    # 2026-10-01：领主大厅并入 wowhead 口径——wowhead 拼写 Dirgen vs 我方 Durgen
    # （旧条目方向写反且从不生效：v3 前该本走 foreverchanges 文本路径、不走 ALIAS）
    "durgen dirgehammer": "dirgen dirgehammer",
}

LOCALES = ("zhCN", "enUS", "zhTW")
PATH = {
    "zhCN": os.path.join(DF, "Core", "Data", "Data_BossSkills.lua"),
    "enUS": os.path.join(DF, "Core", "Data", "enUS", "Data_BossSkills.lua"),
    "zhTW": os.path.join(DF, "Core", "Data", "zhTW", "Data_BossSkills.lua"),
}

HEAD = {
"zhCN": '',
"enUS": '',
"zhTW": '',
}

GUARD = {
    "zhCN": "",
    "enUS": 'if (type(GetLocale) ~= "function") or GetLocale() ~= "enUS" then return end\n\n',
    "zhTW": "local gl = (type(GetLocale) == \"function\") and GetLocale() or \"zhCN\"\n"
            "if gl ~= \"zhTW\" then return end\n\n",
}


def norm(s):
    s = (s or "").replace("\u2019", "'").replace("\u2018", "'")
    return re.sub(r"\s+", " ", s).strip().lower()


def loot_order():
    """→ [ (副本id, [ (en, zh, npc), … ]) ]，按掉落表出现顺序。"""
    src = open(LOOT, encoding="utf-8", errors="replace").read()
    marks = [(m.start(), m.group(1)) for m in re.finditer(r'\["([a-z0-9_]+)"\]\s*=\s*\{', src)]
    out = []
    for i, (pos, did) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(src)
        bosses = [(m.group(1), m.group(2), m.group(4)) for m in
                  re.finditer(r'\{\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]*)",\s*"([^"]*)",\s*\{',
                              src[pos:end])]
        out.append((did, bosses))
    return out


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def main():
    wh = json.load(open(os.path.join(HERE, "_wh_guide_raw.json"), encoding="utf-8"))
    icons = json.load(open(os.path.join(HERE, "_wh_spell_icons.json"), encoding="utf-8"))
    try:
        tips = json.load(open(os.path.join(HERE, "_wh_spell_desc.json"), encoding="utf-8"))
    except Exception:
        tips = {}

    lines = {k: [] for k in LOCALES}
    n_boss = n_id = 0

    for did, bosses in loot_order():
        if did not in DUN7:
            continue
        widx = {norm(k): k for k in (wh.get(did) or {})}
        boss_order = []
        boss_rows = {}
        for en, zh, npc in bosses:
            wh_key = widx.get(ALIAS.get(norm(en), norm(en)))
            if not wh_key:
                continue
            n_boss += 1
            if en not in boss_order:
                boss_order.append(en)
            # 技能行 = 能力表法术 id（wowhead 页序），不存文案；id 行三语共用，只进 zhCN 基表
            ab = (wh.get(did) or {}).get(wh_key, {}).get("spells", []) or []
            acc = []
            for sid in ab:
                slug = icons.get(str(sid)) or ""
                acc.append(("", "", sid, slug) if slug else ("", "", sid))
                n_id += 1
            if acc:
                boss_rows[en] = acc

        if not boss_rows:
            continue
        # id 行三语共用 → 只进 zhCN 基表；zhTW/enUS 覆盖层保持空合并占位
        lines["zhCN"].append("    %s = {" % did)
        for key in boss_order:
            rows = boss_rows.get(key)
            if not rows:
                continue
            lines["zhCN"].append('        ["%s"] = {' % esc(key))
            for r in rows:
                if len(r) == 4:
                    lines["zhCN"].append('            { "%s", "%s", %d, "%s" },'
                                         % (esc(r[0]), esc(r[1] or ""), r[2], esc(r[3])))
                else:
                    lines["zhCN"].append('            { "%s", "%s", %d },'
                                         % (esc(r[0]), esc(r[1] or ""), r[2]))
            lines["zhCN"].append("        },")
        lines["zhCN"].append("    },")

    for loc in LOCALES:
        body = "\n".join(lines[loc])
        if loc == "zhCN":
            # 基表：整体定义 ns.BossSkills（toc 先于覆盖层加载）
            with open(PATH[loc], "w", encoding="utf-8", newline="\n") as f:
                f.write(HEAD[loc] + "\n" + GUARD[loc] + "local _, ns = ...\n\nns.BossSkills = {\n"
                        + (body + "\n" if body else "") + "}\n")
        else:
            # 覆盖层：BossSkills 空合并占位（基表必须已加载）
            with open(PATH[loc], "w", encoding="utf-8", newline="\n") as f:
                f.write(HEAD[loc] + "\n" + GUARD[loc]
                        + "local _, ns = ...\nif type(ns.BossSkills) ~= \"table\" then return end\n\n"
                        + "local __overlay = {\n" + (body + "\n" if body else "") + "}\n"
                        + "for k, v in pairs(__overlay) do ns.BossSkills[k] = v end\n")
        print("%-5s → %s（%d 行）" % (loc, os.path.relpath(PATH[loc], DF),
                                     len(lines[loc])))
    print("— 命中首领 %d 个；wowhead id 行 %d 条（本地不存技能文案）" % (n_boss, n_id))


if __name__ == "__main__":
    main()
