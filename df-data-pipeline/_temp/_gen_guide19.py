# -*- coding: utf-8 -*-
"""把 _temp/_batch19/ 的 19 本攻略 JSON 并入数据层（2026-10-01 经典十九本补齐）。

输入：_temp/_batch19/<did>_guide.json ×19（并行采集产出；bosses[].en 已对齐掉落表源名）
产出：
  1. Core/Data/Data_DungeonGuide.lua —— 19 本完整条目（标记块之间，可重跑覆盖）
  2. _temp/enus_data_guide19.py —— enUS 对照层（zh 全文 → en 全文）；
     需在 gen_enus_data.py 注册（import + EXACT.update），之后由它产出 enUS 覆盖层
  3. _temp/_wh_guide_raw.json —— 追加 19 本 boss 攻略（«S»/«N» 占位符原文 + abilities），
     供 _df_wh_names2 / _df_wh_spell_icons 收集 id、gen_boss_skills 读 abilities
  4. _temp/_wh_translate_zh.json —— 追加 19 本 boss 攻略成品中文（占位符已按中文名解析）
zhTW 覆盖层由 gen_zhtw_data.py 对 zhCN 自动 opencc，不经本脚本。

占位符解析失败（名字 json 里没有该 id）→ 占位符替换为空串，与 7 本管道同口径。
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
BATCH = os.path.join(HERE, "_batch19")
GUIDE = os.path.join(DF, "Core", "Data", "Data_DungeonGuide.lua")

MK_B = "-- ↓↓ 经典十九本攻略（_gen_guide19.py 生成；改文案请改 _batch19/<did>_guide.json 后重跑）↓↓"
MK_E = "-- ↑↑ 经典十九本攻略 ↑↑"

# 与 Data_Dungeons.lua 的出现顺序一致（新区块按此排）
# 2026-10-01 扩：+7 自制本（meta-e/meta-f 采集，fc 页素材 + 常识补全）
DUN19 = ["razorfen_kraul", "razorfen_downs", "uldaman", "zul_farrak", "maraudon",
         "sm_graveyard", "sm_library", "sm_armory", "sm_cathedral", "scholomance",
         "sunken_temple", "blackrock_depths", "lower_blackrock_spire", "upper_blackrock_spire",
         "dire_maul_east", "dire_maul_north", "dire_maul_west",
         "stratholme_main", "stratholme_service",
         "excavation_wetlands", "city_of_dalaran", "the_drowned_city", "kroldok_stronghold",
         "alcaz_prison", "blackmaw_hold", "shapers_terrace"]


def esc(s):
    return (s or "").replace("\\", "\\\\").replace('"', '\\"')


def ph(t, names, npcs, key):
    """解析 «S123»/«N456» 占位符；查不到 → 空串（与 7 本管道一致）。
    采集件偶有 schema 偏差（str 字段给了 list）—— 列表按序拼接兜底。
    名字 json 的 en 值带站点后缀（"Warder Stilgiss - NPC - Forever"）—— 回填前剥掉，
    否则后缀会漏进正文（2026-10-01 实锤：enUS 对照层 108 处污染）。"""
    def rep(m, tbl, key):
        v = (tbl.get(m.group(1)) or {}).get(key) or ""
        return re.sub(r"\s*-\s*(NPC|Spell|Item)\s*-\s*Forever\s*$", "", v)
    if isinstance(t, list):
        t = "".join(str(x) for x in t)
    elif not isinstance(t, str):
        t = "" if t is None else str(t)
    t = re.sub(r"«S(\d+)»", lambda m: rep(m, names, key), t)
    t = re.sub(r"«N(\d+)»", lambda m: rep(m, npcs, key), t)
    return re.sub(r"\s+", " ", t).strip()


def loot_bosses():
    """从 Data_DungeonLoot.lua 提取全部副本的 boss 名单（_batch19_bosslists.json 的兜底源）。"""
    src = open(os.path.join(DF, "Core", "Data", "Data_DungeonLoot.lua"),
               encoding="utf-8", errors="replace").read()
    marks = [(m.start(), m.group(1)) for m in re.finditer(r'\["([a-z0-9_]+)"\]\s*=\s*\{', src)]
    out = {}
    for i, (pos, did) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(src)
        out[did] = [{"en": m.group(1), "zh": m.group(2)} for m in
                    re.finditer(r'\{\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]*)",\s*"([^"]*)",\s*\{',
                                src[pos:end])]
    return out


def load_batch(did):
    p = os.path.join(BATCH, "%s_guide.json" % did)
    return json.load(open(p, encoding="utf-8"))


def norm_entrance(ent):
    """entrance 形态归一化：H 可能是 str/list，A 可能是 [str]；统一成
    H={"zh","en"} / A={"zh":[...],"en":[...]}。"""
    if not isinstance(ent, dict):
        return None, None
    def _pair(v):
        if isinstance(v, dict):
            return v
        return {"zh": v if isinstance(v, (str, list)) else "", "en": ""}
    eh = _pair(ent.get("H")) if ent.get("H") is not None else None
    ea = ent.get("A")
    if ea is not None:
        if isinstance(ea, dict):
            ea = {"zh": ea.get("zh") if isinstance(ea.get("zh"), list) else ([ea["zh"]] if ea.get("zh") else []),
                  "en": ea.get("en") if isinstance(ea.get("en"), list) else ([ea["en"]] if ea.get("en") else [])}
        elif isinstance(ea, list):
            ea = {"zh": [x if isinstance(x, str) else x.get("zh", "") for x in ea],
                  "en": [x.get("en", "") if isinstance(x, dict) else "" for x in ea]}
        else:
            ea = None
    return eh, ea


def main():
    names = json.load(open(os.path.join(HERE, "_wh_spell_names.json"), encoding="utf-8"))
    npcs = json.load(open(os.path.join(HERE, "_wh_npc_names.json"), encoding="utf-8"))
    bosslists = json.load(open(os.path.join(HERE, "_batch19_bosslists.json"), encoding="utf-8"))
    _loot = loot_bosses()
    for did in DUN19:
        bosslists.setdefault(did, _loot.get(did) or [])

    raw = json.load(open(os.path.join(HERE, "_wh_guide_raw.json"), encoding="utf-8"))
    zh_tr = json.load(open(os.path.join(HERE, "_wh_translate_zh.json"), encoding="utf-8"))
    pairs = {}          # zh 全文 → en 全文（enUS 对照层）
    blocks = []
    n_boss = n_ab = 0
    warns = []

    for did in DUN19:
        j = load_batch(did)
        listed = {b["en"] for b in (bosslists.get(did) or [])}
        zh_of = {b["en"]: b.get("zh", "") for b in (bosslists.get(did) or [])}

        # ── bosses 段（逐字对齐名单，未listed丢弃并告警）──
        lua_bosses, raw_bosses = [], {}
        for b in j.get("bosses") or []:
            en = b.get("en") or ""
            if en not in listed:
                warns.append("%s: boss「%s」不在掉落表名单，丢弃" % (did, en))
                continue
            zt = ph(b["text"].get("zh", ""), names, npcs, "zh")
            et = ph(b["text"].get("en", ""), names, npcs, "en")
            if not zt and not et:
                warns.append("%s: boss「%s」中英文均空，丢弃" % (did, en))
                continue
            lua_bosses.append('            { en = "%s",\n              text = "%s" },'
                              % (esc(en), esc(zt)))
            if zt:
                pairs[zt] = et
            raw_bosses[en] = {"text": (b["text"].get("en", "") or ""),
                              "spells": [int(x) for x in (b.get("abilities") or [])]}
            zh_tr.setdefault(did, {})[en] = zt
            n_boss += 1
            n_ab += len(raw_bosses[en]["spells"])

        # ── meta 三语 ──
        meta = j.get("meta") or {}
        out = ["    %s = {" % did]
        tg = meta.get("tagline") or {}
        if tg.get("zh"):
            out.append('        tagline = "%s",' % esc(ph(tg["zh"], names, npcs, "zh")))
            pairs[ph(tg["zh"], names, npcs, "zh")] = ph(tg.get("en", ""), names, npcs, "en")
        tips = meta.get("tips") or []
        if tips:
            out.append("        tips = {")
            for t in tips:
                zt = ph(t.get("zh", ""), names, npcs, "zh")
                out.append('            "%s",' % esc(zt))
                pairs[zt] = ph(t.get("en", ""), names, npcs, "en")
            out.append("        },")
        ent = meta.get("entrance") or {}
        eh, ea = norm_entrance(ent)
        if eh or ea:
            out.append("        entrance = {")
            if eh and eh.get("zh"):
                zt = ph(eh["zh"], names, npcs, "zh")
                out.append('            H = "%s",' % esc(zt))
                pairs[zt] = ph(eh.get("en", ""), names, npcs, "en")
            if ea and (ea.get("zh") or ea.get("en")):
                out.append("            A = {")
                for step in (ea.get("zh") or []):
                    zt = ph(step, names, npcs, "zh")
                    out.append('                "%s",' % esc(zt))
                out.append("            },")
                # en 步骤（对齐层用；zh 数量可能与 en 不一，逐条按序配对，缺的空串）
                for i, step in enumerate(ea.get("zh") or []):
                    zt = ph(step, names, npcs, "zh")
                    en_steps = ea.get("en") or []
                    et = ph(en_steps[i], names, npcs, "en") if i < len(en_steps) else ""
                    pairs[zt] = et
            out.append("        },")
        trash = meta.get("trash") or []
        if trash:
            out.append("        trash = {")
            for t in trash:
                t = t if isinstance(t, dict) else {}
                def _b(v):
                    return v if isinstance(v, dict) else {"zh": v if isinstance(v, str) else "", "en": ""}
                ttd, txd = _b(t.get("title")), _b(t.get("text"))
                zt = ph(ttd.get("zh", ""), names, npcs, "zh")
                zx = ph(txd.get("zh", ""), names, npcs, "zh")
                out.append('            { title = "%s",\n              text = "%s" },'
                           % (esc(zt), esc(zx)))
                pairs[zt] = ph(ttd.get("en", ""), names, npcs, "en")
                pairs[zx] = ph(txd.get("en", ""), names, npcs, "en")
            out.append("        },")
        if lua_bosses:
            out.append("        bosses = {")
            out.extend(lua_bosses)
            out.append("        },")
        out.append("    },")
        blocks.append("\n".join(out))

        # ── raw / translate 追加 ──
        raw.setdefault(did, {}).update(raw_bosses)

    # ── 1. Data_DungeonGuide.lua 标记块 ──
    new_block = MK_B + "\n" + "\n".join(blocks) + "\n" + MK_E
    src = open(GUIDE, encoding="utf-8").read()
    if MK_B in src:
        src = re.sub(re.escape(MK_B) + r".*?" + re.escape(MK_E), new_block, src, flags=re.S)
    else:
        m = re.search(r"\n?\}\s*$", src)
        if not m:
            raise SystemExit("Data_DungeonGuide.lua 尾部找不到收口 }，拒绝插入")
        src = src[:m.start()] + "\n" + new_block + "\n}\n"
    open(GUIDE, "w", encoding="utf-8", newline="\n").write(src)
    print("zhCN：写入 %d 副本 / %d 条 boss 攻略 / abilities 合计 %d" % (len(blocks), n_boss, n_ab))

    # ── 2. enus_data_guide19.py ──
    mod = '''# -*- coding: utf-8 -*-
"""经典十九本攻略（enUS 对照层，_gen_guide19.py 生成）。

键 = Data_DungeonGuide.lua 经典十九本标记块里的 zhCN 全文，值 = 采集英文原文（占位符已回填）。
zhTW 由 gen_zhtw_data.py 对 zhCN 自动 opencc，不经本表。
"""

FREE = {
'''
    for k in sorted(pairs):
        mod += '    "%s": "%s",\n' % (esc(k), esc(pairs[k]))
    mod += "}\n"
    open(os.path.join(HERE, "enus_data_guide19.py"), "w", encoding="utf-8", newline="\n").write(mod)
    print("enUS：%d 条对照 → enus_data_guide19.py" % len(pairs))

    # ── 3/4. raw / translate 落盘 ──
    json.dump(raw, open(os.path.join(HERE, "_wh_guide_raw.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(zh_tr, open(os.path.join(HERE, "_wh_translate_zh.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("raw/translate 已追加 19 本")

    if warns:
        print("\n".join("⚠ " + w for w in warns))


if __name__ == "__main__":
    main()
