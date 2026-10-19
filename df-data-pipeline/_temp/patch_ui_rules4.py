import sys

P = r"D:\workspace\DungeonsForever\.workbuddy\UI_RULES.md"
d = open(P, "rb").read()
assert d.count(b"\r\n") == 0

old1 = "例外：「新」文字徽标、金选中描边/金框、时间轴 bar 描边可保留。"
new1 = ("例外：「新」文字徽标、金选中描边/金框、时间轴 bar 描边可保留。"
        "★ 2026-10-13 收紧：**行/卡级别的选中指示不再用强调条**——五人本任务行原本保留的右缘 3px 金标条 "
        "`r.selMark` 已删（睡袋 BagRowTint 金条同步先例 2026-10-10），选中态一律只靠 **L4 胶囊常显**"
        "（`HuiCardState(r, \"hover\")`）。金描边仅限**按钮**的选中态（`SetOutline`），不属于行指示。")

old2 = "⑤ 「显示已完成」开关改**靠左卡最右**（`TOPRIGHT` 右内衬 8，标签移到开关左侧）|"
new2 = ("⑤ 「显示已完成」开关改**靠左卡最右**（`TOPRIGHT` 右内衬 8，标签移到开关左侧）；"
        "**六次**：任务行右缘金标条 `r.selMark` 删除（选中态只留 L4 胶囊，§6 定案）；"
        "**七次（bug 修）**：「全部」按钮选中态恒不亮——侧栏值域 all/A/H 而按钮键是 `qall`，"
        "归一为 `side == (i == 1 and \"all\" or key)` |")

for name, o, n in (("s6", old1, new1), ("s149", old2, new2)):
    c = d.count(o.encode("utf-8"))
    print(name, "命中", c)
    if c != 1:
        sys.exit(1)
    d = d.replace(o.encode("utf-8"), n.encode("utf-8"))

open(P, "wb").write(d)
print("UI_RULES 写回 OK")
