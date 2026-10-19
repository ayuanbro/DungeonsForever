# -*- coding: utf-8 -*-
"""详情页「地图」页签补丁（2026-09-30）。

在 Core/DungeonUI.lua 上一次性完成 10 处挂点改动（每条锚点必须恰好命中 1 次）。
DungeonUI.lua 是 CRLF，读写按文件自身换行风格处理，落盘后复核「裸 LF == 0」。

    python patch_map_tab.py --check     # 只看锚点命中数
    python patch_map_tab.py             # 正式写入
"""
import sys

P = r"D:/workspace/DungeonsForever/Core/DungeonUI.lua"

PATCHES = [
    (
        "1 页签表加「地图」（放最后 = 视觉最左，因按钮右起排布）",
        '    local tabs = { { key = "loot", text = L["掉落"] }, { key = "quest", text = L["任务"] }, { key = "guide", text = L["攻略"] } }\n',
        '    local tabs = { { key = "loot", text = L["掉落"] }, { key = "quest", text = L["任务"] }, { key = "guide", text = L["攻略"] }, { key = "map", text = L["地图"] } }\n',
    ),
    (
        "2 建帧：地图容器（照攻略区的落点，帧只在 Build 里建一次）",
        '    U.dungeonGuideScroll = gscroll\n'
        '    U.dungeonGuideChild = gchild\n'
        '    U.dungeonGuidePool = { card = {} }\n',
        '    U.dungeonGuideScroll = gscroll\n'
        '    U.dungeonGuideChild = gchild\n'
        '    U.dungeonGuidePool = { card = {} }\n'
        '\n'
        '    if ns.MapModule then\n'
        '        U.dungeonMapFrame = ns.MapModule.Build(detail, hero)\n'
        '    end\n',
    ),
    (
        "3 SetDungeonTab 四态",
        '    if tab == "quest" then t = "quest" elseif tab == "guide" then t = "guide" end\n',
        '    if tab == "quest" then t = "quest" elseif tab == "guide" then t = "guide" elseif tab == "map" then t = "map" end\n',
    ),
    (
        "4 RenderDungeonTab 认地图态",
        '    local isQuest = (cur == "quest")\n'
        '    local isGuide = (cur == "guide")\n',
        '    local isQuest = (cur == "quest")\n'
        '    local isGuide = (cur == "guide")\n'
        '    local isMap = (cur == "map")\n',
    ),
    (
        "5 掉落滚动区在地图态也要让位",
        '    if U.dungeonDetailScroll then U.dungeonDetailScroll:SetShown(not isQuest and not isGuide) end\n',
        '    if U.dungeonDetailScroll then U.dungeonDetailScroll:SetShown(not isQuest and not isGuide and not isMap) end\n',
    ),
    (
        "6 地图容器随页签显隐",
        '    if U.dungeonGuideScroll then U.dungeonGuideScroll:SetShown(isGuide) end\n',
        '    if U.dungeonGuideScroll then U.dungeonGuideScroll:SetShown(isGuide) end\n'
        '    if U.dungeonMapFrame then U.dungeonMapFrame:SetShown(isMap) end\n',
    ),
    (
        "7 地图态下筛选按钮全隐（地图不分档）",
        '    if isGuide then\n'
        '        for i = 1, #(U.dungeonFilterBtns or {}) do\n'
        '            U.dungeonFilterBtns[i]:Hide()\n'
        '        end\n'
        '    end\n',
        '    if isGuide or isMap then\n'
        '        for i = 1, #(U.dungeonFilterBtns or {}) do\n'
        '            U.dungeonFilterBtns[i]:Hide()\n'
        '        end\n'
        '    end\n',
    ),
    (
        "8 分派加地图分支",
        '    if isQuest then\n'
        '        U:RenderDungeonQuests()\n'
        '    elseif isGuide then\n'
        '        U:RenderDungeonGuide()\n'
        '    else\n'
        '        U:RenderDungeonLoot()\n'
        '    end\n',
        '    if isQuest then\n'
        '        U:RenderDungeonQuests()\n'
        '    elseif isGuide then\n'
        '        U:RenderDungeonGuide()\n'
        '    elseif isMap then\n'
        '        if ns.MapModule then ns.MapModule.Paint(U.dungeonDetailCur) end\n'
        '    else\n'
        '        U:RenderDungeonLoot()\n'
        '    end\n',
    ),
    (
        "9 Build 复位清单收进地图容器",
        '    U.dungeonGuidePool = nil\n'
        '    U.dungeonTabBtns = nil\n',
        '    U.dungeonGuidePool = nil\n'
        '    U.dungeonMapFrame = nil\n'
        '    U.dungeonTabBtns = nil\n',
    ),
    (
        "10 存档页签四态都能还原（漏 map ⇒ 重开界面跳回掉落）",
        '        U.dungeonTab = (dt == "quest" or dt == "guide") and dt or "loot"\n',
        '        U.dungeonTab = (dt == "quest" or dt == "guide" or dt == "map") and dt or "loot"\n',
    ),
]


def main():
    check = "--check" in sys.argv
    raw = open(P, "rb").read()
    crlf = raw.count(b"\r\n") > 0
    txt = raw.decode("utf-8").replace("\r\n", "\n")
    bad = 0
    for name, old, new in PATCHES:
        n = txt.count(old)
        tag = "OK " if n == 1 else "!! "
        if n != 1:
            bad += 1
        print("%s[%d] %s" % (tag, n, name))
        if n == 1 and not check:
            txt = txt.replace(old, new, 1)
    if bad:
        print("\n锚点异常 %d 条，未写入。" % bad)
        return 2
    if check:
        print("\n全部锚点各命中 1 次（--check，未写入）。")
        return 0
    out = txt.replace("\r\n", "\n")
    if crlf:
        out = out.replace("\n", "\r\n")
    data = out.encode("utf-8")
    if crlf:
        bare = data.count(b"\n") - data.count(b"\r\n")
        assert bare == 0, "裸 LF 残留 %d 个" % bare
    open(P, "wb").write(data)
    print("\n已写入 %s（CRLF=%s，%d 字节）" % (P, crlf, len(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
