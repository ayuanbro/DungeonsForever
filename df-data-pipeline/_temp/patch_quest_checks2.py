# -*- coding: utf-8 -*-
"""同步 df_dungeon_check.py：删旧「行状态色条」断言，新增任务页小卡片/开关/地图名断言。"""
import io
import sys

PATH = r"D:\workspace\DungeonsForever\_temp\df_dungeon_check.py"


def sub(text, old, new, tag):
    n = text.count(old)
    if n != 1:
        print("!! %s 命中 %d 次" % (tag, n))
        sys.exit(1)
    return text.replace(old, new)


def main():
    text = io.open(PATH, encoding="utf-8").read()

    # 1) 动态区：行状态色条断言 → 行内小卡片断言
    text = sub(
        text,
        '    ck("★ 行有左状态色条（实心贴图，不用字体符号）",\n'
        '       qpool0.row[1].bar ~= nil and qpool0.row[1].bar.__ct ~= nil)\n',
        '    ck("★ 行不再有左状态色条（2026-10-13 强调条全删，行内改小卡片）",\n'
        '       rawget(qpool0.row[1], "bar") == nil)\n'
        '    ck("★ 行内小卡片：前置 / 可共享（挂行帧上，紧贴任务名右侧）",\n'
        '       rawget(qpool0.row[1], "preB") ~= nil and rawget(qpool0.row[1], "shareB") ~= nil)\n'
        '    ck("★★ 任务页「未完成 / 已完成」筛选钮退役，改 iOS 开关「显示已完成」（默认开）",\n'
        '       U.dungeonQDoneTg ~= nil and not U.dungeonFilterBtns[4].__shown\n'
        '       and not U.dungeonFilterBtns[5].__shown and (U.dungeonQFilter or "all") ~= "todo")\n',
        "dyn-row")

    # 2) 静态区：任务页重排断言后追加新四条
    anchor = (
        '    ck(\'★ 任务页重排（2026-10-13）：两卡顶上移贴 hero + 筛选按钮入左卡顶部 + 进度行不再显示\',\n'
        '       \'plateL:SetPoint("TOPLEFT", detail, "TOPLEFT", 0, -DG.FILTER_Y)\' in src\n'
        '       and \'DG.Q_HEAD_H = DG.Q_PAD + 24 + DG.Q_PAD\' in src\n'
        '       and \'local nH, nR, y = 0, 0, -DG.Q_HEAD_H\' in src\n'
        '       and \'U.dungeonQuestSum:Hide()\' in src\n'
        '       and \'bt:SetPoint("TOPLEFT", plateL, "TOPLEFT", DG.Q_PAD + (i - 1) * 100, -DG.Q_PAD)\' in src)\n'
    )
    extra = anchor + (
        '    ck(\'★★ 任务行小卡片（2026-10-13 用户定：前置改小卡片 + 新增可共享，紧贴任务名右侧）\',\n'
        '       \'function DG.MakeBadge(parent)\' in src and \'function DG.PlaceBadge(b, x, text)\' in src\n'
        '       and \'r.preB = DG.MakeBadge(r)\' in src and \'r.shareB = DG.MakeBadge(r)\' in src\n'
        '       and \'DG.PlaceBadge(r.preB, bx, L["前置"])\' in src\n'
        '       and \'DG.PlaceBadge(r.shareB, bx, L["可共享"])\' in src)\n'
        '    ck(\'★★ 可共享判定走数据表（ns.DungeonQuestShare = QuestieDB questFlags & 0x08）\',\n'
        '       \'function DG.QuestShare(id)\' in src\n'
        '       and \'ns.DungeonQuestShare and ns.DungeonQuestShare[id]\' in src\n'
        '       and \'ns.DungeonQuestShare = {\' in qdat)\n'
        '    ck(\'★ 第二列只显示大地图名（去坐标 + 去子区域）\',\n'
        '       \'function DG.QuestMapName(s)\' in src\n'
        '       and \'r.sub:SetText(DG.QuestMapName(loc))\' in src)\n'
        '    ck(\'★★ 任务页「显示已完成」iOS 开关（ReskinToggle + 默认开 + 4/5 号钮退役）\',\n'
        '       \'U.dungeonQDoneTg\' in src and \'ns.hui.ReskinToggle(tg)\' in src\n'
        '       and \'function U:SetQuestShowDone(on)\' in src\n'
        '       and \'if bt and i > 3 then\' in src)\n'
    )
    text = sub(text, anchor, extra, "static-row")

    io.open(PATH, "w", encoding="utf-8", newline="\n").write(text)
    print("OK")


if __name__ == "__main__":
    main()
