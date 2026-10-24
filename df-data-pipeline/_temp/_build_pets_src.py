# -*- coding: utf-8 -*-
# 生成 Data_CollectionPets.lua（带真实来源 + NPC 可点击定位标记）
# 来源：_companions_src.json（物品页 sold-by/dropped-by/sourcemore）+ _npc_coords.json（g_mapperData）
import re, json

# ── 物品页提取：displayId + 图标 slug ─────────────────────────────
disp, icon = {}, {}
for iid in json.load(open("_companions_names.json", encoding="utf-8")):
    try:
        raw = open("whb_%s.html" % iid, encoding="utf-8").read()
    except FileNotFoundError:
        continue
    m = re.search(r'data-mv-display-id="(\d+)"', raw)
    if m:
        disp[iid] = int(m.group(1))
    mi = re.search(r'icons/(?:medium|large)/([a-z0-9_-]+)\.(?:jpg|png)', raw)
    if mi:
        icon[iid] = mi.group(1)

# ── 来源表：iid -> (fac, diff, area, x, y, src, steps) ────────────
# steps[i] = { t=整句, m={ {可点击子串, area, x, y}, … } }（探索页同款；x/y 可省=只开区域图）
V = "vendor"; D = "drop"; Q = "quest"; C = "craft"; P = "pick"; U = "unknown"; S = "store"
SRC = {
    # —— 商人出售（NPC 名可点击 → 定位）——
    "8485":  ("A", V, 12, 44.2, 53.2, "商人出售", [{"t": "从冬妮·安萨妮娅（艾尔文森林）处购买", "m": [["冬妮·安萨妮娅", 12, 44.2, 53.2]]}]),
    "8486":  ("A", V, 12, 44.2, 53.2, "商人出售", [{"t": "从冬妮·安萨妮娅（艾尔文森林）处购买", "m": [["冬妮·安萨妮娅", 12, 44.2, 53.2]]}]),
    "8487":  ("A", V, 12, 44.2, 53.2, "商人出售", [{"t": "从冬妮·安萨妮娅（艾尔文森林）处购买", "m": [["冬妮·安萨妮娅", 12, 44.2, 53.2]]}]),
    "8488":  ("A", V, 12, 44.2, 53.2, "商人出售", [{"t": "从冬妮·安萨妮娅（艾尔文森林）处购买", "m": [["冬妮·安萨妮娅", 12, 44.2, 53.2]]}]),
    "8489":  ("A", V, 1519, 50.4, 34.0, "商人出售", [{"t": "从利尔·迪米（暴风城运河）处购买", "m": [["利尔·迪米", 1519, 50.4, 34.0]]}]),
    "8495":  (None, V, 33, 28.2, 74.4, "商人出售", [{"t": "从纳尔克（荆棘谷·藏宝海湾）处购买", "m": [["纳尔克", 33, 28.2, 74.4]]}]),
    "8496":  (None, V, 33, 28.2, 74.4, "商人出售", [{"t": "从纳尔克（荆棘谷·藏宝海湾）处购买", "m": [["纳尔克", 33, 28.2, 74.4]]}]),
    "8497":  ("A", V, 1, 63.2, 50.2, "商人出售", [{"t": "从亚尔林·冻石（丹莫罗）处购买", "m": [["亚尔林·冻石", 1, 63.2, 50.2]]}]),
    "280797": ("A", V, 1, 63.2, 50.2, "商人出售", [{"t": "从亚尔林·冻石（丹莫罗）处购买", "m": [["亚尔林·冻石", 1, 63.2, 50.2]]}]),
    "8501":  ("A", V, 1657, 69.4, 45.4, "商人出售", [{"t": "从夏琳奈尔（达纳苏斯）处购买", "m": [["夏琳奈尔", 1657, 69.4, 45.4]]}]),
    "280803": ("A", V, 1657, 69.4, 45.4, "商人出售", [{"t": "从夏琳奈尔（达纳苏斯）处购买", "m": [["夏琳奈尔", 1657, 69.4, 45.4]]}]),
    "10394": ("H", V, 1638, 62.2, 58.4, "商人出售", [{"t": "从哈尔帕（雷霆崖）处购买", "m": [["哈尔帕", 1638, 62.2, 58.4]]}]),
    "280794": ("H", V, 1638, 62.2, 58.4, "商人出售", [{"t": "从哈尔帕（雷霆崖）处购买", "m": [["哈尔帕", 1638, 62.2, 58.4]]}]),
    "280795": ("H", V, 1638, 62.2, 58.4, "商人出售", [{"t": "从哈尔帕（雷霆崖）处购买", "m": [["哈尔帕", 1638, 62.2, 58.4]]}]),
    "11023": (None, V, 400, 78.2, 75.8, "商人出售", [{"t": "从大法师提尔斯（千针石林·加基森）处购买", "m": [["大法师提尔斯", 400, 78.2, 75.8]]}]),
    "11027": (None, V, 12, 40.4, 69.4, "商人出售", [{"t": "从弗里克（艾尔文森林 / 莫高雷）处购买", "m": [["弗里克", 12, 40.4, 69.4]]}]),
    "276275": (None, V, 33, 27.4, 76.8, "商人出售", [{"t": "从贾恩（荆棘谷·藏宝海湾）处购买", "m": [["贾恩", 33, 27.4, 76.8]]}]),
    "277508": ("H", V, 1637, 36.6, 29.0, "商人出售", [{"t": "从玛霍亚·天蹄（奥格瑞玛）处购买", "m": [["玛霍亚·天蹄", 1637, 36.6, 29.0]]}]),
    "280347": (None, V, 16593, False, False, "商人出售", [{"t": "从 Vayn Moongaze（达拉然）处购买", "m": [["Vayn Moongaze", 16593]]}]),
    "280699": ("H", V, 1497, 67.4, 43.4, "商人出售", [{"t": "从杰雷米亚·派森（幽暗城）处购买", "m": [["杰雷米亚·派森", 1497, 67.4, 43.4]]}]),
    "280703": ("H", V, 1637, 19.0, 59.4, "商人出售", [{"t": "从克萨迪斯（奥格瑞玛）处购买", "m": [["克萨迪斯", 1637, 19.0, 59.4]]}]),
    "284664": (None, V, 17, 49.4, 29.4, "商人出售", [{"t": "从基莎（贫瘠之地）或塔梅琳·奥德里奇（红色山脉）处购买", "m": [["基莎", 17, 49.4, 29.4], ["塔梅琳·奥德里奇", 44]]}]),
    # —— 怪物掉落 ——
    "8490":  (None, D, False, False, False, "怪物掉落", [{"t": "死亡矿井中的鹦鹉「库奇」掉落"}]),
    "8491":  ("H", D, 130, 62.8, 62.2, "怪物掉落", [{"t": "击杀达拉然书记员掉落（银松森林）", "m": [["达拉然书记员", 130, 62.8, 62.2]]}]),
    "8492":  (None, D, False, False, False, "怪物掉落", [{"t": "死亡矿井的迪菲亚海盗掉落"}]),
    "8494":  (None, D, 33, 22.8, 54.0, "怪物掉落", [{"t": "击杀血帆流氓 / 血帆大法师掉落（荆棘谷）", "m": [["血帆流氓", 33, 22.8, 54.0]]}]),
    "8498":  (None, D, 8, 11.4, 62.0, "怪物掉落", [{"t": "击杀睡梦雏龙掉落（悲伤沼泽）", "m": [["睡梦雏龙", 8, 11.4, 62.0]]}]),
    "8499":  (None, D, 11, 57.4, 41.3, "怪物掉落", [{"t": "击杀红色雏龙 / 深红雏龙掉落（湿地）", "m": [["红色雏龙", 11, 57.4, 41.3], ["深红雏龙", 11, 61.0, 34.4]]}]),
    "20769": (None, D, False, False, False, "怪物掉落", [{"t": "从软泥怪掉落的「粘液袋」中开出"}]),
    "284176": ("A", D, 148, 32.8, 88.8, "怪物掉落", [{"t": "击杀雌性森林陆行鸟掉落（黑海岸）", "m": [["雌性森林陆行鸟", 148, 32.8, 88.8]]}]),
    # —— 扒窃 ——
    "282637": (None, P, False, False, False, "扒窃获取", [{"t": "从「康达尔」身上扒窃获得（潜行者专属）"}]),
    # —— 任务 ——
    "11474": (None, Q, False, False, False, "任务奖励", [{"t": "完成任务「Becoming a Parent」获得"}]),
    # —— 工程学制造 ——
    "4401":  (None, C, False, False, False, "工程学制造", [{"t": "工程学制造（结构图：机械松鼠）"}]),
    "11825": (None, C, False, False, False, "工程学制造", [{"t": "工程学制造（结构图：宠物炸弹）"}]),
    "11826": (None, C, False, False, False, "工程学制造", [{"t": "工程学制造（结构图：发条娃娃）"}]),
    "15996": (None, C, False, False, False, "工程学制造", [{"t": "工程学制造（结构图：仿真机械蛙）"}]),
    "21277": (None, C, False, False, False, "工程学制造", [{"t": "工程学制造（结构图：安静的机械雪人）"}]),
    # —— 商城（保持原状）——
    "13582": (None, S, False, False, False, "商城获取", [{"t": "购买「天蓝史诗礼包」或「魔兽世界：无限」合集获得"}]),
    "13583": (None, S, False, False, False, "商城获取", [{"t": "购买「天蓝史诗礼包」或「魔兽世界：无限」合集获得"}]),
    "13584": (None, S, False, False, False, "商城获取", [{"t": "购买「天蓝史诗礼包」或「魔兽世界：无限」合集获得"}]),
    "280614": (None, S, False, False, False, "商城获取", [{"t": "购买「天蓝史诗礼包」或「魔兽世界：无限」合集获得"}]),
    # —— 待补充（wowhead 页无来源标注）——
    "275069": (None, U, False, False, False, "获取方式待补充", None),
    "277483": (None, U, False, False, False, "获取方式待补充", None),
    "277493": (None, U, False, False, False, "获取方式待补充", None),
    "277651": (None, U, False, False, False, "获取方式待补充", None),
    "277714": (None, U, False, False, False, "获取方式待补充", None),
    "280615": (None, U, False, False, False, "获取方式待补充", None),
}

names = json.load(open("_companions_names.json", encoding="utf-8"))
KNOWN = {"13582", "13583", "13584", "268109", "275682", "280456", "280614", "282047"}
names = {k: v for k, v in names.items() if k not in KNOWN or k in SRC}
assert set(SRC) == set(names), "来源表与清单不一致：%s" % (set(names) ^ set(SRC))

def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')

rows = []
for iid in sorted(names, key=int):
    fac, diff, area, x, y, src, steps = SRC[iid]
    disp_id = disp.get(iid)
    slug = icon.get(iid, "")
    parts = []
    parts.append("    [%d] = {" % (len(rows) + 1))
    parts.append('        %s, "%s", %s, "%s",' % (iid, slug, "nil" if fac is None else '"%s"' % fac, diff))
    parts.append("        %s, %s, %s, \"%s\","
                 % ("false" if area is False else area,
                    "false" if x is False else x,
                    "false" if y is False else y,
                    esc(src)))
    if disp_id:
        parts.append("        __display = %d," % disp_id)
    if steps:
        parts.append("        {")
        for st in steps:
            marks = st.get("m")
            if marks:
                mstr = ", ".join(
                    '{ "%s", %s, %s, %s }' % (esc(mk[0]),
                        mk[1], "nil" if len(mk) < 3 or mk[2] is False else mk[2],
                        "nil" if len(mk) < 4 or mk[3] is False else mk[3])
                    for mk in marks)
                parts.append('            { t = "%s", m = { %s } },' % (esc(st["t"]), mstr))
            else:
                parts.append('            { t = "%s" },' % esc(st["t"]))
        parts.append("        },")
    parts.append("    },")
    rows.append("\n".join(parts))

body = ",\n".join(r.rstrip(",\n") if False else r.rstrip().rstrip(",") for r in rows)
head = '''local _, ns = ...
ns.CollectionPets = {'''
out = head + body + "\n}\n"
open("../Core/Data/Data_CollectionPets.lua", "w", encoding="utf-8", newline="\n").write(out)
print("written lines =", out.count("\n") + 1)
nmark = sum(1 for iid in SRC if SRC[iid][6] and any(st.get("m") for st in SRC[iid][6]))
print("rows: %d, 带可点击标记的条目: %d" % (len(rows), nmark))
print("无 __display:", [i for i in sorted(SRC, key=int) if i not in disp])