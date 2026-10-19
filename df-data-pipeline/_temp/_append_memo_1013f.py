import io, os

D = r"D:\workspace\DungeonsForever\.workbuddy\memory\2026-10-13.md"
lines = (
    "- 任务页五次（用户四条）：① 详情卡标题「前导任务」→「**前置任务**」（三语链：改 DungeonUI L 键 → 重跑 gen_locales/gen_zhtw/gen_enus；\n"
    "  gen_enus 显式表 `'前导任务': 'Intro quest'` → `'前置任务': 'Pre-quests'`；zhCN 走键名回退无需登记）\n"
    "  ② 详情节点行（**前置/后续同一个行池 `takeNode`**）左强调条 `r.bar` 整套删净 —— 创建块 + 三处 SetColorTexture（前置 done/active/unknown 两分支 + 后续），\n"
    "  内衬 10→8（name/sub），与右内衬 -8 对称。★ 用户只说前置，但同一池同一款 ⇒ 后续一并删，已回报。\n"
    "  ③ 行内「可共享」徽章判定改走**客户端共享数据** `DG.QLCall(\"IsPushableQuest\", id)`（＝详情卡「共享：可分享/不可共享」同源）；\n"
    "  `ns.DungeonQuestShare`（QuestieDB questFlags & 0x08）降级为**离线/接口缺失回退**。原口径只吃数据表 ⇒ 与客户端实际不符，徽章该出的不出。\n"
    "  ④ 徽章配色：`DG.MakeBadge(parent, bg)`，前置 = `DG.Q_BADGE_PRE_BG {0.78,0.60,0.10,1}` 黄底、可共享 = `DG.Q_BADGE_SHARE_BG {0.16,0.52,0.26,1}` 绿底，\n"
    "  一律 **白字**（C_WHITE）。★ 上色手法：直接 `ns.hui.BuildRoundedBG(b, 6, bg, \"both\", true, 1)`（不走 HuiCardFX 的 L3），\n"
    "  自定色进 `tex.__huiGlass.c` ⇒ 主题重绘（AddRepaint→GlassPaint）自动保住色；`BuildRoundedBG` 只在色值命中 L0/L1/L2/L3 灰档时才改档，发光色不会被吃。\n"
    "- 探针实测（`_dbg_qbadge.py` 扩印）：preB bg=0.78/0.60/0.10、shareB bg=0.16/0.52/0.26 且 shown/txt=可共享；详情节点行 name_x=8。\n"
    "- ★ 探针坑：桩对**未知字段一律返回函数**（`n1.bar` 返回 function 而非 nil）⇒ 「是否删净」只能用**源码静态断言**（`'r.bar' not in src`），别拿探针字段判空。\n"
    "- ★ 探针坑：给详情卡喂带前置链的任务会走 `DG.HarvestTipName` → 桩的 `tip:NumLines()` 返回 table ⇒ `table > 0` 报错。桩限制，非真 bug；\n"
    "  详情渲染的运行时断言留给 harness，探针保持默认选本。\n"
    "- harness 同步：徽章断言（MakeBadge 双参 + 两色常量 + C_WHITE）、QuestShare 断言（IsPushableQuest + 回退）、\n"
    "  新增「前置任务」改名 pin 与「详情节点行 r.bar 删净 + 内衬 8」pin。变异体检：注入 304 / 死锚 0 / 被抓住。\n"
)
os.makedirs(os.path.dirname(D), exist_ok=True)
if not os.path.exists(D):
    io.open(D, "w", encoding="utf-8", newline="\n").write("# 2026-10-13 工作日志\n\n")
with io.open(D, "ab") as f:
    f.write(lines.encode("utf-8"))
print("appended")
