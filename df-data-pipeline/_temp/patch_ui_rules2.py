# -*- coding: utf-8 -*-
"""更新 UI_RULES.md：§7 补 iOS 开关/行内小卡片口径；§11 五人本行追加三次改动。"""
import io
import sys

PATH = r"D:\workspace\DungeonsForever\.workbuddy\UI_RULES.md"


def main():
    text = io.open(PATH, encoding="utf-8").read()

    old7 = ("按钮宽度按**最长本地化文案反算**（enUS 常最长，须留左右内衬）"
            "——例：楼层按钮须容 enUS「Floor 7」⇒ 宽 66；开关须容 enUS「Hide pins」⇒ 宽 80。\n")
    new7 = old7 + (
        "\n"
        "**iOS 开关（2026-10-13 五人本任务页实测口径）**：`ns.hui.ReskinToggle(tg[, w, h])`，默认 **36×20**（圆钮 14）。"
        "标签必须挂**父帧**（`PurgeNative` 会隐藏 tg 上一切非自建子件），锚 `LEFT tg RIGHT 6`、字号 14。"
        "状态读写只走 `tg:SetChecked(on)` / `tg:GetChecked()` —— ReskinToggle 覆写了 SetChecked，"
        "既存内部态又立即重绘（少了这句只会静默失败：数据照存、外观不刷）。\n"
        "\n"
        "**行内小卡片 / 徽章（2026-10-13 五人本任务行）**：`DG.MakeBadge(parent)` = 帧 + `HuiCardFX(b, nil, 3)`"
        "（L3 底 + 白 10% 细边 —— 行底是 L2，按 §2 提亮一档）+ 居中 FontString（14 号）。"
        "宽度 = `lab:GetStringWidth() + 2×5`；高 **20**、枚间距 **4**、贴着前一元素右缘排（`DG.PlaceBadge` 返下一枚 x）。"
        "★ 徽章是**子帧**，按 §5.2 永远画在行的 FontString 之上；落点按「名称实际文字宽（上限 = 名称列宽）」算，"
        "保证名称不超列宽时不重叠。\n"
    )
    n = text.count(old7)
    if n != 1:
        print("§7 锚点命中 %d 次" % n)
        sys.exit(1)
    text = text.replace(old7, new7)

    old11 = ("筛选行仍 8 待拍板）；**任务页重排**（同日二次：两卡顶上移贴 hero、"
             "筛选按钮移入左卡顶部、进度行隐藏、联盟/部落按钮改 PvP 图标样式） |")
    new11 = ("筛选行仍 8 待拍板）；**任务页重排**（同日二次：两卡顶上移贴 hero、"
             "筛选按钮移入左卡顶部、进度行隐藏、联盟/部落按钮改 PvP 图标样式）；"
             "**任务页三次**（同日：① 「未完成/已完成」筛选钮退役 → iOS 开关「显示已完成」"
             "（`U.dungeonQDoneTg` / `U:SetQuestShowDone`；默认开 = status「all」，关 = 「todo」；存档 `dungeonQuestFilter` 沿用）"
             "② 行内左状态色条 `r.bar` 删除（§6 定案）③ 「前置」改行内小卡片 + 新增「可共享」小卡片"
             "（紧贴任务名右侧；可共享判定 = `ns.DungeonQuestShare`，QuestieDB questFlags & 0x08，本表 190/344）"
             "④ 第二列只显示大地图名（`DG.QuestMapName` 去坐标 + 去子区域）；"
             "列位重排 `Q_X_LOC` 200→288 / `Q_X_LV` 348→386 / `Q_W_NAME` 164→150 / `Q_W_LOC` 144→90，`Q_X_PRE`/`Q_BAR_W` 退役） |")
    n = text.count(old11)
    if n != 1:
        print("§11 锚点命中 %d 次" % n)
        sys.exit(1)
    text = text.replace(old11, new11)

    io.open(PATH, "w", encoding="utf-8", newline="\n").write(text)
    print("OK")


if __name__ == "__main__":
    main()
