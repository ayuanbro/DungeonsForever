# -*- coding: utf-8 -*-
"""把 wowhead 攻略正文（汉化稿）写进数据层。

产出：
  1. Core/Data/Data_DungeonGuide.lua —— 追加 7 个副本的 bosses 条目（标记块之间，可重跑覆盖）；
  2. _temp/enus_data_whguide.py —— enUS 对照层（zh 全文 → en 全文），注册进 gen_enus_data.py
     后由 gen_enus_data.py 产出 enUS 覆盖层；zhTW 覆盖层由 gen_zhtw_data.py 自动 opencc。

汉化稿：_temp/_wh_translate_zh.json（人工翻译，键 = 副本 id / 首领英文名）。
英文原文：_temp/_wh_guide_raw.json（«S»/«N» 占位符回填 wowhead 英文名）+ 手工补丁。
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
LOOT = os.path.join(DF, "Core", "Data", "Data_DungeonLoot.lua")
GUIDE = os.path.join(DF, "Core", "Data", "Data_DungeonGuide.lua")

MK_B = "-- ↓↓ wowhead 攻略正文（_df_wh_guide_gen.py 生成；改文案请改 _wh_translate_zh.json 后重跑）↓↓"
MK_E = "-- ↑↑ wowhead 攻略正文 ↑↑"

DUN7 = ["ragefire_chasm", "wailing_caverns", "the_deadmines", "shadowfang_keep",
        "blackfathom_deeps", "the_stockade", "gnomeregan"]

# boss 名对齐（同 gen_boss_skills.py）
ALIAS = {
    "dirgen dirgehammer": "durgen dirgehammer",  # wowhead 拼写 Dirgen vs 我方 Durgen（2026-09-30）
    "lady anacondra": "lady andacondra",
    "fel steed / shadow charger": "fel steeds / shadow charger",
    "sneed": "sneed's shredder",
}


def norm(s):
    s = (s or "").replace("\u2019", "'").replace("\u2018", "'")
    return re.sub(r"\s+", " ", s).strip().lower()


def strip_title(s):
    s = re.sub(r"\s*\(Rare\)\s*$", "", s or "").strip()
    s = re.sub(r"^Naralax Event\s+", "", s, flags=re.I)
    return s.strip()


def loot_bosses():
    src = open(LOOT, encoding="utf-8", errors="replace").read()
    marks = [(m.start(), m.group(1)) for m in re.finditer(r'\["([a-z0-9_]+)"\]\s*=\s*\{', src)]
    out = {}
    for i, (pos, did) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(src)
        out[did] = [m.group(1) for m in
                    re.finditer(r'\{\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]*)",\s*"([^"]*)",\s*\{',
                                src[pos:end])]
    return out


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


# 英文原文补丁（wowhead 原句里被剥掉的 item 引用）
EN_PATCH = [
    (" will drop the first time you kill VanCleef.",
     " The Defias Leather Cloak will drop the first time you kill VanCleef."),
    (" This boss drops .", ""),
]


def en_texts():
    """→ { (did, bossEn): enText }（wowhead 英文原文，回填英文名 + 补丁）"""
    wh = json.load(open(os.path.join(HERE, "_wh_guide_raw.json"), encoding="utf-8"))
    names = json.load(open(os.path.join(HERE, "_wh_spell_names.json"), encoding="utf-8"))
    npcs = json.load(open(os.path.join(HERE, "_wh_npc_names.json"), encoding="utf-8"))
    loot = loot_bosses()
    out = {}
    for did in DUN7:
        widx = {norm(strip_title(k)): k for k in (wh.get(did) or {})}
        for en in loot.get(did, []):
            k = norm(en)
            wkey = widx.get(ALIAS.get(k, k))
            if not wkey:
                continue
            t = (wh[did][wkey] or {}).get("text", "")
            if not t:
                continue
            t = re.sub(r"«S(\d+)»", lambda m: (names.get(m.group(1)) or {}).get("en") or "", t)
            t = re.sub(r"«N(\d+)»", lambda m: (npcs.get(m.group(1)) or {}).get("en") or "", t)
            t = re.sub(r"\s+", " ", t).strip()
            for a, b in EN_PATCH:
                t = t.replace(a, b)
            out[(did, en)] = t
    return out


def main():
    zh = json.load(open(os.path.join(HERE, "_wh_translate_zh.json"), encoding="utf-8"))
    loot = loot_bosses()
    en_map = en_texts()

    # ── meta 四块（2026-10-01 补齐：_batch_meta7/<did>_guide.json，meta-7 成员产出）──
    # 有则 7 本条目从 bosses-only 升级为完整条目（tagline/tips/entrance/trash + bosses），
    # enUS 对照层同步携带 meta 文本。占位符 «S»/«N» 解析口径与 _gen_guide19.py 一致。
    META_DIR = os.path.join(HERE, "_batch_meta7")
    names = json.load(open(os.path.join(HERE, "_wh_spell_names.json"), encoding="utf-8"))
    npcs = json.load(open(os.path.join(HERE, "_wh_npc_names.json"), encoding="utf-8"))

    def ph(t, key):
        if isinstance(t, list):
            t = "".join(str(x) for x in t)
        elif not isinstance(t, str):
            t = "" if t is None else str(t)
        t = re.sub(r"«S(\d+)»", lambda m: (names.get(m.group(1)) or {}).get(key) or "", t)
        t = re.sub(r"«N(\d+)»", lambda m: (npcs.get(m.group(1)) or {}).get(key) or "", t)
        return re.sub(r"\s+", " ", t).strip()

    def meta_of(did):
        """→ (lua_lines, zh→en pairs)；无 meta7 文件 → ([], {})"""
        p = os.path.join(META_DIR, "%s_guide.json" % did)
        if not os.path.exists(p):
            return [], {}
        meta = (json.load(open(p, encoding="utf-8")).get("meta") or {})

        def _b(v):
            return v if isinstance(v, dict) else {"zh": v if isinstance(v, str) else "", "en": ""}

        out, mp = [], {}
        tg = _b(meta.get("tagline"))
        if tg.get("zh"):
            zt = ph(tg["zh"], "zh")
            out.append('        tagline = "%s",' % esc(zt))
            mp[zt] = ph(tg.get("en", ""), "en")
        tips = meta.get("tips") or []
        if tips:
            out.append("        tips = {")
            for t in tips:
                t = _b(t)
                zt = ph(t.get("zh", ""), "zh")
                out.append('            "%s",' % esc(zt))
                mp[zt] = ph(t.get("en", ""), "en")
            out.append("        },")
        ent = meta.get("entrance") or {}
        eh = _b(ent["H"]) if ent.get("H") is not None else None
        ea = ent.get("A")
        if ea is not None and not isinstance(ea, dict):
            ea = {"zh": ea if isinstance(ea, list) else [], "en": []}
        if eh or ea:
            out.append("        entrance = {")
            if eh and eh.get("zh"):
                zt = ph(eh["zh"], "zh")
                out.append('            H = "%s",' % esc(zt))
                mp[zt] = ph(eh.get("en", ""), "en")
            if ea and (ea.get("zh") or ea.get("en")):
                out.append("            A = {")
                zs = [ph(s, "zh") for s in (ea.get("zh") or [])]
                ens = [ph(s, "en") for s in (ea.get("en") or [])]
                for s in zs:
                    out.append('                "%s",' % esc(s))
                out.append("            },")
                for i, s in enumerate(zs):
                    mp[s] = ens[i] if i < len(ens) else ""
            out.append("        },")
        trash = meta.get("trash") or []
        if trash:
            out.append("        trash = {")
            for t in trash:
                t = t if isinstance(t, dict) else {}
                ttd, txd = _b(t.get("title")), _b(t.get("text"))
                zt = ph(ttd.get("zh", ""), "zh")
                zx = ph(txd.get("zh", ""), "zh")
                out.append('            { title = "%s",\n              text = "%s" },'
                           % (esc(zt), esc(zx)))
                mp[zt] = ph(ttd.get("en", ""), "en")
                mp[zx] = ph(txd.get("en", ""), "en")
            out.append("        },")
        return out, mp

    # ── 1. zhCN：Data_DungeonGuide.lua 标记块 ──
    blocks = []
    n_en = 0
    meta_pairs = {}
    n_meta7 = 0
    for did in DUN7:
        rows = []
        for en in loot.get(did, []):
            t = (zh.get(did) or {}).get(en)
            if not t:
                continue
            rows.append('            { en = "%s",\n              text = "%s" },' % (esc(en), esc(t)))
        mlines, mp = meta_of(did)
        if mp:
            meta_pairs.update(mp)
            n_meta7 += 1
        if not rows and not mlines:
            continue
        body = "    %s = {\n%s\n        bosses = {\n%s\n        },\n    }," % (
            did, "\n".join(mlines), "\n".join(rows))
        blocks.append(body)
    new_block = MK_B + "\n" + "\n".join(blocks) + "\n" + MK_E

    src = open(GUIDE, encoding="utf-8").read()
    if MK_B in src:
        src = re.sub(re.escape(MK_B) + r".*?" + re.escape(MK_E), new_block, src, flags=re.S)
    else:
        # 追加：剥掉尾部收口的 }（含前面空行），插标记块后重新收口
        m = re.search(r"\n?\}\s*$", src)
        if not m:
            raise SystemExit("Data_DungeonGuide.lua 尾部找不到收口 }，拒绝插入")
        src = src[:m.start()] + "\n" + new_block + "\n}\n"
    open(GUIDE, "w", encoding="utf-8", newline="\n").write(src)
    n_zh = sum(len(v) for v in zh.values())
    print("zhCN：写入 %d 副本 / %d 条 boss 攻略（meta 四块：%d 本）"
          % (len(blocks), n_zh, n_meta7))

    # ── 2. enUS：对照层模块 ──
    pairs = {}
    miss = []
    for did, m in zh.items():
        for en, zt in m.items():
            et = en_map.get((did, en))
            if not et:
                miss.append("%s/%s" % (did, en))
                continue
            pairs[zt] = et
            n_en += 1
    pairs.update(meta_pairs)
    mod = '''# -*- coding: utf-8 -*-
"""wowhead 首领攻略（enUS 对照层，_df_wh_guide_gen.py 生成）。

键 = Data_DungeonGuide.lua 里的 zhCN 攻略全文，值 = wowhead 英文原文（回填英文名 + 手工补丁）。
zhTW 由 gen_zhtw_data.py 对 zhCN 自动 opencc，不经本表。
"""

FREE = {
'''
    for k in sorted(pairs):
        mod += '    "%s": "%s",\n' % (esc(k), esc(pairs[k]))
    mod += "}\n"
    open(os.path.join(HERE, "enus_data_whguide.py"), "w", encoding="utf-8", newline="\n").write(mod)
    print("enUS：%d 条对照（缺英文原文：%s）" % (n_en, miss or "无"))


if __name__ == "__main__":
    main()
