import io, os

D = r"D:\workspace\DungeonsForever\.workbuddy\memory\2026-10-13.md"
lines = (
    "- 任务行二次（用户：选中时右边还有强调条没删）：`r.selMark`（右缘 3px 金条）整套删除 —— "
    "创建块 6 行 + `r.selMark:SetShown(isSel)` 使用行；选中态只留 L4 胶囊常显（HuiCardState \"hover\"）。"
    "DungeonUI 6211→6204 行，CRLF 保住。UI_RULES §6 收紧：「行/卡级选中指示不再用强调条」，"
    "金描边仅限按钮选中态（SetOutline）。\n"
    "- ★ 行内元素用 `r.xxx` 起名时，静态断言 `'r.xxx' not in src` 可当「已删」判据；"
    "但遗留注释若含同名（本条注释写的是「金 selMark 条」，无 `r.` 前缀）不会误伤；"
    "代码注释按纪律**不改写**，失配只报告。\n"
    "- ★ 顺手清掉一条**死锚**变异：`MUT_ROW_GIVER`（锚 `local loc = q[6]` 拼接体）在本日 `QuestMapName` 重构后已 0 次命中，"
    "静默没人守。定式：**只改 `_temp/df_mut_check.py`，跑 `check_mut_anchors.py` 复检，禁重跑 `mk_df_mut.py`**；"
    "重锚到 `DG.QuestMapName` 里剥坐标那行（`s = s:gsub(\"%s*[%d%.]+%s*,%s*[%d%.]+%s*$\", \"\")`），"
    "并给 harness 静态断言补 pin 该 gsub 行（原断言只 pin 调用形状，改函数体抓不住）。"
    "重锚后：注入 304 / 死锚 0 / 冲突 3。\n"
    "- ★ 风险：`_temp/df_mut_check.py` 与 `df_dungeon_check.py` 均为 **LF**（写补丁别按 CRLF 处理）；"
    "变异锚点按 LF 书写、由 `to_file_style` 换算成产物行尾。\n"
    "- ★ 探针选中态判据坑（`_dbg_qbadge.py`）：hui 路径下 `MakeOutline` 的显隐落在 `bt.__outlineFrame`，"
    "而 `bt.__bars` 是 `BuildRoundBorder` 的静态 pieces（恒 true）。判据必须**先看 `type(bt.__outlineFrame)=='table'`**，"
    "否则三颗筛选钮全报 ON（假结论）。\n"
)
os.makedirs(os.path.dirname(D), exist_ok=True)
if not os.path.exists(D):
    io.open(D, "w", encoding="utf-8", newline="\n").write("# 2026-10-13 工作日志\n\n")
with io.open(D, "ab") as f:
    f.write(lines.encode("utf-8"))
print("appended")
