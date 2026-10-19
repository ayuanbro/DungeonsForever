# -*- coding: utf-8 -*-
# 2026-10-08 设置弹窗「卡片背景」：给 harness 落守卫（静态断言 + 动态断言 + 反向变异 + 登记）。
# 改三份（均 LF）：_temp/df_dungeon_check.py、_temp/df_mut_check.py、_temp/df_check_new_muts.py。
# 每条锚点断言恰好命中 1 次；幂等（含标记 SKIP）。
import sys, io

ROOT = r"D:/workspace/DungeonsForever/_temp/"
MARK = "QB_SET_CARD_BG"

def load(p):
    with io.open(p, "r", encoding="utf-8", newline="") as f:
        return f.read()

def save(p, s):
    assert "\r" not in s, p + " must stay LF"
    with io.open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)

# ---------- ① df_dungeon_check.py：静态 + 动态 ----------
p1 = ROOT + "df_dungeon_check.py"
s = load(p1)
if MARK in s:
    print("SKIP①: df_dungeon_check already patched")
else:
    A_OLD = "   'SetAllPoints' not in _qb_src)\n"
    A_NEW = (
        "   'SetAllPoints' not in _qb_src)\n"
        "ck('★★ ㊱ 设置弹窗卡片背景（" + MARK + "，2026-10-08 用户：内容区垫 L2 圆角大卡；"
        "先建垫底 + 排完回填高度）',\n"
        "   'QB_SET_CARD_BG' in _qb_src\n"
        "   and 'self.cardBg:ClearAllPoints()' in _qb_src\n"
        "   and 'self.cardBg:SetPoint(\"TOPLEFT\", pop, \"TOPLEFT\", 6, -6)' in _qb_src\n"
        "   and 'self.cardBg:SetPoint(\"TOPRIGHT\", pop, \"TOPRIGHT\", -6, -6)' in _qb_src\n"
        "   and 'self.cardBg:SetHeight(6 - y)' in _qb_src\n"
        "   and _qb_src.find('self.cardBg = card') < _qb_src.find('local function Header(text)'))\n"
    )
    B_OLD = (
        "   QB.slotX == 8, 'slot=' .. tostring(QB.slotX))\n"
        "\n"
        "return table.concat(R, '\\n')\n"
        "\"\"\"\n"
    )
    B_NEW = (
        "   QB.slotX == 8, 'slot=' .. tostring(QB.slotX))\n"
        "\n"
        "-- 设置弹窗「卡片背景」（2026-10-08 用户）：垫底卡已建 + 锚定弹窗内容区\n"
        "-- （桩只记最后一次 SetPoint 的实参；SetHeight 不落 __h ⇒ 高度走上面的静态闸）\n"
        "QB:EnsureSettings()\n"
        "local cardBg = rawget(QB, 'cardBg')\n"
        "ck(\"★ ㊱ 设置弹窗卡片背景已建（EnsureSettings 后存在）\", cardBg ~= nil)\n"
        "ck(\"★ ㊱ 卡片背景锚定弹窗内容区（末次 SetPoint = TOPRIGHT 槽 -6）\",\n"
        "   cardBg ~= nil and cardBg.__pts ~= nil and cardBg.__pts[1] == 'TOPRIGHT'\n"
        "   and cardBg.__pts[4] == -6 and cardBg.__pts[5] == -6,\n"
        "   'p1=' .. tostring(cardBg and cardBg.__pts and cardBg.__pts[1])\n"
        "   .. ' x=' .. tostring(cardBg and cardBg.__pts and cardBg.__pts[4]))\n"
        "\n"
        "return table.concat(R, '\\n')\n"
        "\"\"\"\n"
    )
    ca, cb = s.count(A_OLD), s.count(B_OLD)
    if ca != 1 or cb != 1:
        print("ABORT①: anchors A=%d B=%d (expect 1/1)" % (ca, cb))
        sys.exit(1)
    s = s.replace(A_OLD, A_NEW, 1).replace(B_OLD, B_NEW, 1)
    save(p1, s)
    print("OK①: df_dungeon_check patched")

# ---------- ② df_mut_check.py：反向变异 ----------
p2 = ROOT + "df_mut_check.py"
s = load(p2)
if MARK in s:
    print("SKIP②: df_mut_check already patched")
else:
    C_OLD = "\n]\n"
    if s.count(C_OLD) != 1:
        print("ABORT②: tail anchor hits %d" % s.count(C_OLD))
        sys.exit(1)
    C_NEW = (
        "\n"
        "    ('快捷栏：设置弹窗卡片背景高度不回填（底板缩成 0 高 = 没有卡片背景）', "
        "('Core/QuickBar.lua', (b'    if self.cardBg then self.cardBg:SetHeight(6 - y) end\\n', "
        "b'    -- MUT: card bg height never set\\n'))),\n"
        "]\n"
    )
    s = s.replace(C_OLD, C_NEW, 1)
    save(p2, s)
    print("OK②: df_mut_check patched")

# ---------- ③ df_check_new_muts.py：登记 ----------
p3 = ROOT + "df_check_new_muts.py"
s = load(p3)
if MARK in s:
    print("SKIP③: df_check_new_muts already patched")
else:
    D_OLD = "]\n\n# ----"
    if s.count(D_OLD) != 1:
        print("ABORT③: DEFAULT_WANT tail anchor hits %d" % s.count(D_OLD))
        sys.exit(1)
    D_NEW = (
        "    # ㊱ 设置弹窗卡片背景（2026-10-08 用户）\n"
        "    '快捷栏：设置弹窗卡片背景高度不回填（底板缩成 0 高 = 没有卡片背景）',\n"
        "]\n\n# ----"
    )
    s = s.replace(D_OLD, D_NEW, 1)
    save(p3, s)
    print("OK③: df_check_new_muts patched")
