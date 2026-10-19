import io, os

D = r"D:\workspace\DungeonsForever\.workbuddy\memory\2026-10-13.md"
line = ("- 任务页 bug 修（用户报「选全部时全部按钮没选中效果」）：`RenderDungeonQuests` 里 "
        "`local sel = (i <= 3 and side == key)` —— side 值域是 all/A/H（`SetQuestSide` 归一），"
        "而 1 号按钮 key 是 \"qall\"（OnClick 分支靠它区分阵营 vs 状态），`side == \"qall\"` 恒 false ⇒ 全部钮永不亮。"
        "修法：`side == (i == 1 and \"all\" or key)`（保留 key=\"qall\" 不动，否则会误落到 SetQuestFilter 分支）。"
        "另：探针 `_dbg_qbadge.py` 的选中判据要优先读 `type(bt.__outlineFrame)=='table'`（hui 路径 SetShown 在框帧上，"
        "`bt.__bars` 只是 BuildRoundBorder 的静态 pieces，永为 true 会假报全 ON）。实测：side=H→仅部落 ON，"
        "side=all→仅全部 ON。harness 补静态 pin `side == (i == 1 and \"all\" or key)`。\n")
os.makedirs(os.path.dirname(D), exist_ok=True)
if not os.path.exists(D):
    io.open(D, "w", encoding="utf-8", newline="\n").write("# 2026-10-13 工作日志\n\n")
with io.open(D, "ab") as f:
    f.write(line.encode("utf-8"))
print("appended")
