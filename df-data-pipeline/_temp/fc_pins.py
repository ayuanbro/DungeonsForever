# -*- coding: utf-8 -*-
"""生成 Core/Data/Data_MapPins.lua（副本内地图「入口 / 任务 / 物品 / 稀有」钉点）。

数据源 = _ref/dg_<slug>.html 缓存页（先跑 _fc_pins_rsc.py 同款抓取即可，本脚本只读缓存）：
  · 入口 / 任务钉：静态 HTML 里的 dgx-pin + data-kind="entrance"/"quest"；
  · 物品 / 稀有钉：RSC flight 数据里的 {"x":..,"faceKind":"object"/"rare"}；
    - 物品钉 itemID 取 <section id="<boss-slug>"> 段内第一个 /zh-cn/item/NNN；
    - 稀有怪 npcID/中文名按下表（face 字段与本站 id 不同源，勿用；已逐个 wowhead 复核）：
        dark-iron-ambassador → 6228 黑铁大使
        miner-johnson        → 3586 矿工约翰森
        deathsworn-captain   → 3872 死亡之誓
        bruegal-ironknuckle  → 无官方页（Forever 自定义 NPC），npcID=0、名字保留原文

用法：python _temp/fc_pins.py
"""
import os
import re
import json

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "_ref")
DF = os.path.dirname(HERE)
DST = os.path.join(DF, "Core", "Data", "Data_MapPins.lua")

SLUG = {
    "ragefire-chasm": "ragefire_chasm",
    "wailing-caverns": "wailing_caverns",
    "the-deadmines": "the_deadmines",
    "shadowfang-keep": "shadowfang_keep",
    "blackfathom-deeps": "blackfathom_deeps",
    "the-stockade": "the_stockade",
    "gnomeregan": "gnomeregan",
    "razorfen-kraul": "razorfen_kraul",
    "razorfen-downs": "razorfen_downs",
    "scarlet-monastery-graveyard": "sm_graveyard",
    "scarlet-monastery-library": "sm_library",
    "scarlet-monastery-armory": "sm_armory",
    "scarlet-monastery-cathedral": "sm_cathedral",
    "uldaman": "uldaman",
    "zulfarrak": "zul_farrak",
    "maraudon": "maraudon",
    "sunken-temple": "sunken_temple",
    "blackrock-depths": "blackrock_depths",
    "dire-maul-east": "dire_maul_east",
    "dire-maul-north": "dire_maul_north",
    "dire-maul-west": "dire_maul_west",
    "lower-blackrock-spire": "lower_blackrock_spire",
    "upper-blackrock-spire": "upper_blackrock_spire",
    "scholomance": "scholomance",
    "stratholme-main-gate": "stratholme_main",
    "stratholme-service-gate": "stratholme_service",
    "city-of-dalaran": "city_of_dalaran",
    "alcaz-prison": "alcaz_prison",
    "blackmaw-hold": "blackmaw_hold",
    "excavation-site": "excavation_wetlands",
    "hall-of-thanes": "hall_of_thanes",
    "kroldok-stronghold": "kroldok_stronghold",
    "ruins-of-lordaeron": "ruins_of_lordaeron",
    "shapers-terrace": "shapers_terrace",
    "the-drowned-city": "the_drowned_city",
}

# 稀有怪：fc 的 4 个稀有钉（黑铁大使 / 矿工约翰森 / 死亡之誓 / Bruegal Ironknuckle）
# 全部已由 ns.BossPos 以首领钉覆盖（坐标相同且楼层正确），2026-10-04 起不再在此重复
# 登记 —— 解析端仍识别 rare，但不再产出（渲染端 rare 分支保留给将来 BossPos 没有的怪）。
# 对象钉：按 RSC 钉点 x 坐标 → (itemID, 层号) 登记。层号省略 = 第 1 层。
# ★★ 2026-10-04 两级实锤：
#   ① 原「section 起 3000 字符窗口内第一个 /zh-cn/item/ 链接」的关联法会把相邻 section
#     的物品抓串（窗口只有 ~700 字符就撞到下一个 section）——废弃；
#   ② fc RSC 的 slug 与坐标在影牙页也是**交叉**的（slug=jordan 挂在乌尔之书的点上）。
#     wowhead classic 页标题已核：6895 = Jordan's Smithing Hammer、6283 = The Book of Ur。
#     实机（用户实机查验定案，2026-10-04 第三轮对调）：
#       (37.3,53.8) = 乔丹铁锤 6895（第 1 层庭院铁匠铺；曾误摆 BossPos 当 boss，已删）
#       (47.2,79.3) = 乌尔之书 6283（第 6 层阿鲁高档）
#   ⇒ 干脆按坐标登记，不再信 slug。
OBJ_BY_COORD = {
    37.3: (6895, None),
    47.2: (6283, 6),
}

# 手工入口钉（2026-10-04 用户实机截图标位，fc 站没给的副本由用户在地图页标 1 落钉）。
# 坐标 = 地图画布百分比。检测口径：截图红圈 = 白色数字心 + 红环（首版红质心被熔岩/红色
# 纹理污染，y 系统性偏 7~8%——怒焰/死矿实锤），再用图上已渲染 boss 钉（BossPos 已知百
# 分比）做线性标定 px=a*n+b 消掉截图边框的系统偏差。
#   · ragefire-chasm   怒焰裂谷：入口漩涡 (61.0, 8.6)
#   · wailing-caverns  哀嚎洞穴：入口漩涡 (47.1, 60.3)
#   · the-deadmines    死亡矿井：第 1 层左上入口漩涡 (30.8, 15.7)
#   · 2026-10-09 达拉然城：fc floors JSON 的 entrance 钉（本脚本只认静态 dgx-pin，
#     读不到 RSC 里的 kind=entrance）⇒ 抄 fc 页坐标；第 3 位 = **客户端层号**
#     （入口钉在第 2 层「下水道」图上，MapPins entrance 第 4 位 = 层号）
ENTR_MANUAL = {
    "ragefire-chasm": (61.0, 8.6),
    "wailing-caverns": (47.1, 60.3),
    "the-deadmines": (30.8, 15.7),
    "city-of-dalaran": (14.4, 79.2, 2),
}

# RSC flight 里转义形态的钉点记录
PIN_RE = re.compile(
    r'\{\\"x\\":([\d.]+),\\"y\\":([\d.]+),\\"boss\\":\\"([\w-]+)\\",\\"face\\":(\d+),\\"faceKind\\":\\"(\w+)\\",\\"label\\":\\"((?:[^"\\\\]|\\\\.)*)\\"')
# 静态 HTML 里的入口 / 任务钉
HTML_PIN_RE = re.compile(r'<(a|span|button)([^>]*class="dgx-pin"[^>]*)>(.*?)</\1>', re.S)


def unesc(s):
    try:
        return s.encode().decode('unicode_escape')
    except Exception:
        return s


def parse(slug):
    p = os.path.join(REF, "dg_%s.html" % slug)
    if not os.path.exists(p):
        return None
    d = open(p, encoding="utf-8", errors="replace").read()
    ent, qst, obj, rare = [], [], [], []
    # ⓪ 手工入口（2026-10-04 用户实机截图标位）：fc 站只有 halls/ruins 给了 entrance 钉，
    #   其余副本由用户在地图页上标 1 的位置落钉。坐标 = 地图画布百分比（截图质心换算，
    #   用图上既有 boss 钉反验过口径，偏差 ~1%）。
    e = ENTR_MANUAL.get(slug)
    if e:
        # 第 3 位 = 客户端层号时，按 MapUI 口径落第 4 格（entrance 层号位），第 3 格留 nil
        ent.append([e[0], e[1], None, e[2]] if len(e) > 2 else list(e))
    # ① 静态 HTML：entrance / quest
    for m in HTML_PIN_RE.finditer(d):
        attrs, body = m.group(2), m.group(3)
        k = re.search(r'data-kind="(\w+)"', attrs)
        k = k.group(1) if k else ""
        if k not in ("entrance", "quest"):
            continue
        if k == "entrance" and e:
            continue  # 已有手工入口（含层号）⇒ 静态钉不再重复落（达拉然城两处同坐标）
        st = re.search(r'left:\s*([\d.]+)%;\s*top:\s*([\d.]+)%', attrs)
        if not st:
            continue
        qid = re.search(r'href="#quest-(\d+)"', attrs)
        rec = [float(st.group(1)), float(st.group(2))]
        if k == "quest" and qid:
            rec.append(int(qid.group(1)))
        (ent if k == "entrance" else qst).append(rec)
    # ② RSC：object / rare（对象钉按坐标精确登记、稀有钉不产出 —— 见头部 OBJ_BY_COORD/RARE 注）
    for m in PIN_RE.finditer(d):
        x, y, slug2, _face, kind, _label = m.groups()
        if kind == "object":
            info = OBJ_BY_COORD.get(float(x))
            if info:
                row = [float(x), float(y), info[0]]
                if info[1]:
                    row.append(info[1])
                obj.append(row)
    return ent, qst, obj, rare


def fmt(v):
    s = ("%.1f" % v)
    return s.rstrip("0").rstrip(".") if "." in s else s


def main():
    slugs = open(os.path.join(HERE, "_fc_slugs.txt")).read().split()
    blocks = []
    for slug in slugs:
        myid = SLUG.get(slug)
        if not myid:
            print("跳过（无映射）:", slug)
            continue
        parsed = parse(slug)
        if not parsed:
            print("跳过（无缓存）:", slug)
            continue
        ent, qst, obj, rare = parsed
        if not (ent or qst or obj or rare):
            continue
        lines = ['    ["%s"] = {' % myid]
        for key, arr in (("entrance", ent), ("quest", qst), ("object", obj), ("rare", rare)):
            if not arr:
                continue
            rows = []
            for p in arr:
                cells = [fmt(p[0]), fmt(p[1])]
                for v in p[2:]:
                    if v is None:
                        cells.append("nil")     # 占位（entrance 层号在第 4 位时）
                    else:
                        cells.append('"%s"' % v if isinstance(v, str) else str(v))
                rows.append("{ " + ", ".join(cells) + " }")
            lines.append("        %s = { %s }," % (key, ", ".join(rows)))
        lines.append("    },")
        blocks.append("\n".join(lines))
        print("%-24s 入口%d 任务%d 物品%d 稀有%d" % (slug, len(ent), len(qst), len(obj), len(rare)))

    head = '''local _, ns = ...
ns.MapPins = {'''

    out = head + "\n".join(blocks) + "\n}\n"
    open(DST, "w", encoding="utf-8", newline="\n").write(out)
    print("已写", DST, len(out), "bytes,", len(blocks), "个副本")


if __name__ == "__main__":
    main()
