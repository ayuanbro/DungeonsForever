# -*- coding: utf-8 -*-
"""追加当日记忆：五人本任务页三次改造。"""
import io

PATH = r"D:\workspace\DungeonsForever\.workbuddy\memory\2026-10-13.md"

TEXT = """
## 五人本任务页三次改造（iOS 开关 / 删强调条 / 行内小卡片 / 地图名）
- 需求：①「未完成/已完成」两钮删 → iOS 开关「显示已完成」（默认开）② 左列行强调条删 ③「前置」改行内小卡片、放任务名右侧紧贴 ④ 新增「可共享」小卡片同位置 ⑤ 第二列只显示地图名（去坐标）。
- 「可共享」数据口径（用户拍板「用任务库自带标志」）：QuestieDB-Forever.toc 的 Quest 标量行 **字段 23 = questFlags**，`& 0x08` = QUEST_FLAGS_SHARABLE；字段缺失按 0（不可共享）。新生成器 `_temp/gen_quest_share.py` → 追加 `ns.DungeonQuestShare = { [id]=true }` 到 `Core/Data/Data_DungeonQuests.lua` 尾部（纯 ID、无文案 ⇒ 三语覆盖层只整表替换 ns.DungeonQuests/Alias/PreExtra/PreNote，不冲它）。本表 344 任务 / 190 可共享（55%）。
- 代码（Core/DungeonUI.lua）：
  - 新增 `DG.QuestShare(id)` / `DG.QuestMapName(s)`（去尾部坐标 + 去「 - 子区域」）/ `DG.MakeBadge(parent)`（帧 + `HuiCardFX(b,nil,3)` L3 底 + 白边，高 20）/ `DG.PlaceBadge(b,x,text)`（宽 = `lab:GetStringWidth()+2×5`，返下一枚 x）。
  - 行池：删 `r.bar`（创建 + 上色）；`r.pre` 灰字 → `r.preB` / `r.shareB` 两枚 badge；badge 起点 = `Q_X_NAME(+14 职业字) + min(名称实宽, 列宽) + 4`。
  - 列位重排：`Q_X_LOC 200→288`、`Q_X_LV 348→386`、`Q_W_NAME 164→150`、`Q_W_LOC 144→90`；`Q_X_PRE` / `Q_BAR_W` 退役。badge 最大右缘 ≈280 < 地图列 288。
  - 开关：`U.dungeonQDoneTg`（`CheckButton` + `ns.hui.ReskinToggle`，36×20）。★ **label 必须挂 tg 本体** —— 挂 detail 会被 plateL 实底卡盖住（§5.2 父帧 FontString 在子帧之下），且挂 tg 后显隐自动跟随；文字「显示已完成」，hit 区右扩。`U:SetQuestShowDone(on)` 直接写 `U.dungeonQFilter`（"all"/"todo"），沿用 `SetQuestFilter` 与存档 `dungeonQuestFilter`（harness 的 done 档断言仍活）。4/5 号钮在任务页 `bt and i > 3` 分支 Hide。
  - 开关显隐/位置统一在 `ApplyDetailChrome`（独立块，非任务页 Hide）；存档初始化把旧值 "done" 归一 "all"。
  - 踩坑：tf_dryrun 桩里 `ns.hui.ReskinToggle` 会因 `bt.Text`（万能壳返回 function）在 Hui.lua:2214 抛错 —— 探针须先 `TF_NS.hui.ReskinToggle = function() end`；真机 CheckButton 无 `.Text` 字段，`if bt.Text then` 直接跳过，安全。
- 文案：`L["显示已完成"]` / `L["可共享"]` → gen_enus.py 补键（Show completed / Sharable）、gen_zhtw.py 自动（「可共享」简繁同形走键名回退）。
- 断言同步（_temp/df_dungeon_check.py）：删 3 处 `r.bar` 断言（改用 `rawget(...,"bar")==nil` / 只查状态字），新增 5 条（行内小卡片 / 可共享数据表 / 地图名 / iOS 开关 / 4-5 号钮退役）。
- 验证：lua51 OK；DungeonUI 工作区 CRLF 6211/0；deploy 210/210；串行全检 10/11（唯一红 = qa_lf G3 基线 stale=13）。探针 `_temp/_dbg_qbadge.py`：开关 {TOPLEFT,308,-10} w36、badge 起 x=130/满宽 244 < 288。
- 遗留：名称超列宽（>150px）时文字溢出会跑到 badge 下面（与旧行为同级）；未 git 提交。
"""


def main():
    with io.open(PATH, "a", encoding="utf-8", newline="\n") as f:
        f.write(TEXT)
    print("OK")


if __name__ == "__main__":
    main()
