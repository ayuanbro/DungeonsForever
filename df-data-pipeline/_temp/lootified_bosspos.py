# -*- coding: utf-8 -*-
"""从 Lootified 插件提取 boss 图钉，补齐我方 ns.BossPos 缺口。

口径（2026-10-10 用户）：
  · 参考 Lootified（客户端 AddOns/Lootified，Data/DungeonMaps.lua + Data/Instances.lua）；
  · **不动已添加的 boss 图钉**（已收录副本只补「还没有钉点的首领名」，已有坐标/刷点一律不碰）；
  · 只添加我们没有的。

原理：
  Lootified 的 DungeonMaps[KEY].s = { [boss 序号] = { 层号, x, y[, 层号, x, y …] } }，
  序号对应 Instances[KEY].bosses[序号].name（已在 RFC/DM/WC/BFD/GNOMER/RFK 上用我方
  现有钉点逐点验证，精确吻合）。坐标 0-1、左上原点，×100 即我方百分比口径；
  层号同为客户端层号（SFK 6/7、GNOMER 4/10 等与我方 ART 前缀尾数一致）。
  ZF（Zul'Farrak）客户端无楼层（floor=0）⇒ 落成第 1 层（无层号后缀，同 gen_boss_pos 口径）。

跳过（本脚本明确不收）：
  · upper_blackrock_spire：Lootified 的 UBRS 钉挂 BlackrockSpire 4/6/7 层，我方 ART 是
    UpperBlackrockSpire1-3（两套层空间，离线无法对齐）⇒ 不猜；
  · ONY（奥妮克西亚）：我方副本列表没有该副本；
  · 已收录副本里「已有首领的额外刷点」：避免与用户既有取舍（REVERT 等）打架；
  · shadowfang_keep 的 s[7]（floor 4, 57.4, 43.3）：Lootified 字面= Arugal's Voidwalker，
    但其自身尾段序号有 +1 错位证据（s[8..10] 恰为我方 Wolf Master/Archmage/Deathsworn），
    归属存疑 ⇒ 不收。

输出：_bosspos_lootified.json（gen_boss_pos.py 的第三份数据源，schema 同 _bosspos_floors_all）。
用法：python _temp/lootified_bosspos.py        # 只生成 + 报告，不改 Lua
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
LOOT = r"D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\Lootified"

OUT = os.path.join(HERE, "_bosspos_lootified.json")
# 同批第二产物：boss 3D 模型显示 id（npc → CreatureDisplayInfoID），
# 给 gen_boss_model.py 渲染 Core/Data/Data_BossModel.lua。
# 背景：我方 MapUI 走 SetCreature(npcid)，本客户端对部分 npcid 解析出错误默认形态
# ⇒ 模型与 boss 不匹配；参考数据每个 boss 带精配 display，SetDisplayInfo 精准。
MODEL_OUT = os.path.join(HERE, "_bossmodel_lootified.json")

# Lootified key -> 我方副本 id
KEY2ID = {
    "RFC": "ragefire_chasm", "DM": "the_deadmines", "WC": "wailing_caverns",
    "SFK": "shadowfang_keep", "BFD": "blackfathom_deeps", "STOCKS": "the_stockade",
    "GNOMER": "gnomeregan", "RFK": "razorfen_kraul",
    "SMGY": "sm_graveyard", "SMLIB": "sm_library", "SMARM": "sm_armory",
    "SMCATH": "sm_cathedral", "RFD": "razorfen_downs", "ULDA": "uldaman",
    "ZF": "zul_farrak", "MARA": "maraudon", "ST": "sunken_temple",
    "BRD": "blackrock_depths", "DME": "dire_maul_east", "DMW": "dire_maul_west",
    "DMN": "dire_maul_north", "LBRS": "lower_blackrock_spire",
    "UBRS": "upper_blackrock_spire", "SCHOLO": "scholomance",
    "STRATLIVE": "stratholme_main", "STRATUD": "stratholme_service",
    # 我方已有钉点的自制副本（对账用，不应产出新增）
    "HOT": "hall_of_thanes", "ROL": "ruins_of_lordaeron", "DAL": "city_of_dalaran",
    "EXC": "excavation_wetlands",
}

# 明确不收的（key -> 原因）
SKIP = {
    "UBRS": "层空间不齐（BlackrockSpire4/6/7 vs 我方 UpperBlackrockSpire1-3），离线无法对齐",
    "ONY": "我方副本列表没有奥妮克西亚",
    "SFK": "s[7] 归属存疑（Lootified 尾段序号 +1 错位），且影牙只差这一颗 —— 不收",
}


def read(p):
    with io.open(p, encoding="utf-8") as f:
        return f.read()


def parse_instances():
    """key -> [boss 名有序列表]；另有 key -> [ {name, npc, display} 有序表 ]（模型提取用）"""
    src = read(os.path.join(LOOT, "Data", "Instances.lua"))
    out = {}
    rows = {}
    # 按块切：key = "XXX" ... 下一个 key 或文件尾
    parts = re.split(r'key = "([A-Z]+)"', src)
    # parts = [前导, key1, 块1, key2, 块2, ...]
    for i in range(1, len(parts), 2):
        key, block = parts[i], parts[i + 1]
        m = re.search(r"bosses = \{(.*?)\n        \},", block, re.S)
        if not m:
            continue
        names = []
        entries = []
        # 每个 boss 条目独占一行（生成器格式稳定），逐行抽 name / npc / display
        for line in m.group(1).splitlines():
            nm = re.search(r'name\s*=\s*"((?:[^"\\]|\\.)*)"', line)
            if not nm:
                continue
            name = nm.group(1).replace('\\"', '"')
            npc = re.search(r"\bnpc\s*=\s*(\d+)", line)
            disp = re.search(r"\bdisplay\s*=\s*(\d+)", line)
            names.append(name)
            entries.append({
                "name": name,
                "npc": int(npc.group(1)) if npc else None,
                "display": int(disp.group(1)) if disp else None,
            })
        out[key] = names
        rows[key] = entries
    return out, rows


def parse_maps():
    """key -> {boss 序号: [(floor, x, y), …]}（floor/x/y 原值，0-1 坐标）"""
    src = read(os.path.join(LOOT, "Data", "DungeonMaps.lua"))
    out = {}
    parts = re.split(r"\n    ([A-Z]+) = \{", src)
    for i in range(1, len(parts), 2):
        key, block = parts[i], parts[i + 1]
        m = re.search(r"\n        s = \{(.*?)\n        \},", block, re.S)
        if not m:
            continue
        pins = {}
        for em in re.finditer(r"\[(\d+)\] = \{([^}]*)\}", m.group(1)):
            idx = int(em.group(1))
            nums = [float(v) for v in re.findall(r"-?\d+\.?\d*", em.group(2))]
            pts = []
            for j in range(0, len(nums), 3):
                pts.append((int(nums[j]), nums[j + 1], nums[j + 2]))
            pins[idx] = pts
        out[key] = pins
    return out


def parse_our_loot_names():
    """我方副本 id -> {来源英文名: npcid(str，可能空串)}（Data_DungeonLoot.lua，生成物只读）"""
    src = read(os.path.join(DF, "Core", "Data", "Data_DungeonLoot.lua"))
    out = {}
    parts = re.split(r'\n    \["([a-z_]+)"\] = \{', src)
    for i in range(1, len(parts), 2):
        did, block = parts[i], parts[i + 1]
        # 来源行 = { "英文名", "中文名", "说明", "npcid", …（物品行是数字开头，不会命中；
        #   英文名可能带转义引号，如 Eric \"The Swift\"）
        for m in re.finditer(r'\{\s*"((?:[^"\\]|\\.)*)",\s*"(?:[^"\\]|\\.)*",\s*'
                             r'(?:"(?:[^"\\]|\\.)*"|nil)\s*,\s*"([^"]*)"', block):
            out.setdefault(did, {})[m.group(1).replace('\\"', '"')] = m.group(2)
    return out


def parse_our_bosspos():
    """现有 ns.BossPos：did -> set(首领英文名)"""
    src = read(os.path.join(DF, "Core", "Data", "Data_BossPos.lua"))
    out = {}
    parts = re.split(r'\n    \["([a-z_]+)"\] = \{', src)
    for i in range(1, len(parts), 2):
        did, block = parts[i], parts[i + 1]
        out[did] = set(re.findall(r'\n        \["((?:[^"\\]|\\.)*)"\] =', block))
    return out


def main():
    inst, inst_rows = parse_instances()
    maps = parse_maps()
    loot_names = parse_our_loot_names()
    have = parse_our_bosspos()

    report = []
    data = {}   # did -> { floor(str): [ {en,x,y}, … ] }
    stats = {"new_dungeon": set(), "new_boss_in_existing": {}, "skipped_name": [],
             "skipped_existing": 0, "pins": 0}

    # ── 第二产物：boss 模型显示 id（[副本][首领英文名] → display）────────────
    # 按名字对齐（不涉楼层，UBRS 也照收）。★ 键用「副本+名」不用 npcid：
    #   我方掉落表 npcid 列混有显示 id 且存在撞车（如黑石深渊 Bael'Gar/Magmus 同值），
    #   名字才是全项目验证过的连接键。
    model = {}           # did -> { en: display }
    npc_mismatch = []    # (did, en, 我方npc, 参考npc)
    for key, entries in sorted(inst_rows.items()):
        did = KEY2ID.get(key)
        if did is None:
            continue
        loot = loot_names.get(did) or {}
        for e in entries:
            if not e["display"] or e["name"] not in loot:
                continue
            our_npc = loot[e["name"]]
            if e["npc"] and our_npc and e["npc"] != int(our_npc):
                npc_mismatch.append((did, e["name"], our_npc, e["npc"]))
            model.setdefault(did, {})[e["name"]] = e["display"]

    for key in sorted(maps):
        did = KEY2ID.get(key)
        if did is None:
            report.append("  [跳过] %-10s 我方无此副本（%s）" % (key, key))
            continue
        if key in SKIP:
            report.append("  [跳过] %-10s %s" % (key, SKIP[key]))
            continue
        bosses = inst.get(key) or []
        loot = loot_names.get(did) or set()
        existing = have.get(did) or set()
        is_new = did not in have
        added_here = []
        for idx in sorted(maps[key]):
            pts = maps[key][idx]
            if idx < 1 or idx > len(bosses):
                stats["skipped_name"].append((did, "#%d(越界)" % idx))
                continue
            en = bosses[idx - 1]
            if en in existing:
                stats["skipped_existing"] += len(pts)
                continue
            if en not in loot:
                stats["skipped_name"].append((did, en))
                continue
            for fl, x, y in pts:
                floor = "1" if fl <= 1 else str(int(fl))   # ZF floor 0 → 第 1 层
                data.setdefault(did, {}).setdefault(floor, []).append(
                    {"en": en, "x": round(x * 100, 1), "y": round(y * 100, 1)})
                stats["pins"] += 1
            added_here.append(en)
            if not is_new:
                stats["new_boss_in_existing"].setdefault(did, []).append(en)
        if is_new and did in data:
            stats["new_dungeon"].add(did)

    # ── 报告 ──────────────────────────────────────────────────────────────
    print("== Lootified → 我方 BossPos 提取报告 ==")
    print("新增副本 %d 个；新增钉点 %d 颗；已收录副本跳过已有首领刷点 %d 颗"
          % (len(stats["new_dungeon"]), stats["pins"], stats["skipped_existing"]))
    for did in sorted(data):
        fls = data[did]
        tag = "新副本" if did in stats["new_dungeon"] else "补缺"
        n = sum(len(v) for v in fls.values())
        nb = len({r["en"] for v in fls.values() for r in v})
        print("  [%s] %-24s 首领 %2d  钉点 %2d  层 %s"
              % (tag, did, nb, n, ",".join(sorted(fls, key=int))))
    if stats["new_boss_in_existing"]:
        for did, names in sorted(stats["new_boss_in_existing"].items()):
            print("  [已收录副本补缺] %s: %s" % (did, ", ".join(names)))
    if stats["skipped_name"]:
        print("  [名字对不上/越序号，未收] %s"
              % "; ".join("%s:%s" % (d, n) for d, n in stats["skipped_name"]))
    for line in report:
        print(line)
    print("模型显示 id：登记 %d 个副本 / %d 个首领"
          % (len(model), sum(len(v) for v in model.values())))
    if npc_mismatch:
        print("  [npcid 不一致 = 模型/头像必错，已按参考修正] %s" %
              "; ".join("%s %s: 我方%s → 参考%s" % r for r in npc_mismatch))

    # 已收录副本不应有任何产出的自检：HOT/ROL/DAL/EXC/RFC/DM/BFD/STOCKS/GNOMER/RFK
    unexpected = set(data) - (stats["new_dungeon"] | set(stats["new_boss_in_existing"]))
    if unexpected:
        print("!! 意外产出（不在新增副本/补缺名单里）：%s" % ", ".join(sorted(unexpected)))
        sys.exit(1)

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
    print("写出", OUT)

    with io.open(MODEL_OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(model, f, ensure_ascii=False, indent=1, sort_keys=True)
    print("写出", MODEL_OUT)


if __name__ == "__main__":
    main()
