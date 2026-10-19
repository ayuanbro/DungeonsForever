# -*- coding: utf-8 -*-
"""两处收尾修正（2026-09-30）：

① df_mut_check.py 里两条打 Core/MapUI.lua 的变异锚点，bytes 字面量只写了两层反斜杠
   ⇒ bytes 值 = 一个反斜杠，而 Lua 源码里是**两个**（路径分隔符）⇒ 锚点 0 命中。
   写成四层（源码文本）才对：bytes 值 = 两个反斜杠。

② df_dungeon_check.py 的「行点击分派」断言只认无限服口径：泰坦 / 正式服没有专业页与
   探索页，那两行会落回 OpenPage ⇒ 输出少两段。按端给两种合法口径（不是分派坏了）。

    python fix_map_anchors.py --check
    python fix_map_anchors.py
"""
import sys

M = r"D:/workspace/DungeonsForever/_temp/df_mut_check.py"
D = r"D:/workspace/DungeonsForever/_temp/df_dungeon_check.py"

MUT_PATCHES = [
    (
        "锚点反斜杠补到 4 层（bytes 值才等于 Lua 源码里的两个反斜杠）",
        r"""    b'    city_of_dalaran       = "Interface\\WorldMap\\Dalaran\\Dalaran1_",\n',""",
        r"""    b'    city_of_dalaran       = "Interface\\\\WorldMap\\\\Dalaran\\\\Dalaran1_",\n',""",
    ),
    (
        "区域图变异的 new 同样补到 4 层",
        r"""    b'    hall_of_thanes        = "Interface\\WorldMap\\OldIronforge\\OldIronforge",\n'))""",
        r"""    b'    hall_of_thanes        = "Interface\\\\WorldMap\\\\OldIronforge\\\\OldIronforge",\n'))""",
    ),
]

DYN_OLD = """local got = table.concat(calls, '|')
ck("★ ㊱ 行点击分派（副本→详情 / 专业→Show / 探索→ShowSub / 页级→OpenPage；nil 与 dead 行不动作）",
   got == 'detail:the_stockade|Professions|show:alchemy|Explore|sub:bm|Raids', got)
"""

DYN_NEW = """local got = table.concat(calls, '|')
-- ★ 泰坦 / 正式服没有专业页与探索页（无限服专属）⇒ 这两行落回 OpenPage，输出少两段。
--   不是分派坏了，是那两页在本端不存在；按端给两种合法口径。
local _ok1 = (got == 'detail:the_stockade|Professions|show:alchemy|Explore|sub:bm|Raids')
local _ok2 = (not PD) and (not EG)
   and (got == 'detail:the_stockade|Professions|Explore|Raids')
ck("★ ㊱ 行点击分派（副本→详情 / 专业→Show / 探索→ShowSub / 页级→OpenPage；nil 与 dead 行不动作）",
   _ok1 or _ok2, got)
"""

DYN_PATCHES = [("行点击分派断言按端给两种口径", DYN_OLD, DYN_NEW)]


def apply(path, patches, check):
    raw = open(path, "rb").read()
    crlf = raw.count(b"\r\n") > 0
    txt = raw.decode("utf-8").replace("\r\n", "\n")
    bad = 0
    for name, old, new in patches:
        n = txt.count(old)
        print("  %s[%d] %s" % ("OK " if n == 1 else "!! ", n, name))
        if n != 1:
            bad += 1
        elif not check:
            txt = txt.replace(old, new, 1)
    if not check and not bad:
        out = txt.replace("\r\n", "\n")
        if crlf:
            out = out.replace("\n", "\r\n")
        open(path, "wb").write(out.encode("utf-8"))
    return bad


def main():
    check = "--check" in sys.argv
    bad = 0
    print("① %s" % M)
    bad += apply(M, MUT_PATCHES, check)
    print("② %s" % D)
    bad += apply(D, DYN_PATCHES, check)
    if bad:
        print("\n锚点异常 %d 条，未写入。" % bad)
        return 2
    print("\n%s" % ("锚点各命中 1 次（未写入）。" if check else "已写入。"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
