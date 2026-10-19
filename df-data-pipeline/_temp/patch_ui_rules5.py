import sys

P = r"D:\workspace\DungeonsForever\.workbuddy\UI_RULES.md"
d = open(P, "rb").read()
assert d.count(b"\r\n") == 0

old1 = "宽度 = `lab:GetStringWidth() + 2×5`；高 **20**、枚间距 **4**、贴着前一元素右缘排（`DG.PlaceBadge` 返下一枚 x）。"
new1 = ("宽度 = `lab:GetStringWidth() + 2×5`；高 **20**、枚间距 **4**、贴着前一元素右缘排（`DG.PlaceBadge` 返下一枚 x）。"
        "**配色（2026-10-13 用户定）**：小卡片一律 **白字**，底色随语义——「前置」= 黄底 `DG.Q_BADGE_PRE_BG`、"
        "「可共享」= 绿底 `DG.Q_BADGE_SHARE_BG`（`DG.MakeBadge(parent, bg)` 直接用 `ns.hui.BuildRoundedBG(f, 6, bg, …)` "
        "上色，颜色进 `tex.__huiGlass.c` ⇒ 主题重绘不丢色；非 hui 回退仍走 SetBackdrop）。")

old2 = "④ 第二列只显示大地图名（`DG.QuestMapName` 去坐标 + 去子区域）"
new2 = ("④ 第二列只显示大地图名（`DG.QuestMapName` 去坐标 + 去子区域）\n"
        "    - ★ 可共享判定改走**客户端共享数据** `C_QuestLog.IsPushableQuest`（`DG.QLCall`），与详情卡「共享：可分享/不可共享」"
        "同口径；`ns.DungeonQuestShare` 数据表降级为**离线/接口缺失回退**（原来只吃数据表 ⇒ 与客户端实际不一致导致徽章不出）")

old3 = "| 五人本（DungeonUI，含四子页） | ✅ 已规整"
new3 = "| 五人本（DungeonUI，含四子页） | ✅ 已规整"

# 追加到状态表的「八次」条目：插在 ⑤ 之后的分号串里
old4 = "归一为 `side == (i == 1 and \"all\" or key)` |"
new4 = ("归一为 `side == (i == 1 and \"all\" or key)`；"
        "**八次**：① 详情卡「前导任务」→「**前置任务**」② 详情节点行（前置/后续同一行池）左强调条 `r.bar` 删净、"
        "内衬 10→8 ③ 行内「可共享」徽章改客户端 `IsPushableQuest`（原数据表口径与客户端不符 ⇒ 不出）"
        "④ 徽章配色：前置黄底白字 / 可共享绿底白字 |")


def rep(o, n, tag):
    global d
    c = d.count(o.encode("utf-8"))
    print(tag, "命中", c)
    if c != 1:
        sys.exit(1)
    d = d.replace(o.encode("utf-8"), n.encode("utf-8"))


rep(old1, new1, "s7")
rep(old2, new2, "s149-a")
rep(old4, new4, "s149-b")
open(P, "wb").write(d)
print("UI_RULES 写回 OK")
