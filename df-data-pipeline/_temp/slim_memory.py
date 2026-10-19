"""MEMORY.md 瘦身：把 BIS 段落到专题件 BIS.md、性能段落并入 PERF.md，原位留指针。
文本逐字节搬运，不做改写。"""
import os
import re
import shutil

MEM = r"D:\workspace\DungeonsForever\.workbuddy\memory\MEMORY.md"
PERF = r"D:\workspace\DungeonsForever\.workbuddy\memory\PERF.md"
BIS = r"D:\workspace\DungeonsForever\.workbuddy\memory\BIS.md"
BAK = r"D:\workspace\DungeonsForever\_temp\_bak_MEMORY_md.txt"

shutil.copyfile(MEM, BAK)
src = open(MEM, encoding="utf-8").read()

# 按 "## " 切段（保留分隔符）
chunks = re.split(r"(?m)^(?=## )", src)
preamble = chunks[0]
secs = {}
order = []
for c in chunks[1:]:
    title = c.split("\n", 1)[0][3:].strip()
    secs[title] = c
    order.append(title)


def take(pred):
    return [t for t in order if pred(t)]


bis_titles = take(lambda t: t.startswith("BIS "))
perf_titles = take(lambda t: t.startswith("性能 / 分帧 / 预热"))

assert len(bis_titles) == 4, bis_titles
assert len(perf_titles) == 1, perf_titles

# 1) BIS.md
bis_body = "".join(secs[t] for t in bis_titles)
bis_header = (
    "# DungeonsForever · BIS 配装页（专题件）\n\n"
    "> 由 MEMORY.md 迁出（判据留 MEMORY.md，细节详情见本件）。\n\n"
)
open(BIS, "w", encoding="utf-8", newline="\n").write(bis_header + bis_body)

# 2) 性能段落并入 PERF.md
perf_sec = secs[perf_titles[0]]
with open(PERF, "a", encoding="utf-8", newline="\n") as f:
    f.write("\n\n<!-- 由 MEMORY.md 迁入（10-16） -->\n" + perf_sec)

# 3) 重写 MEMORY.md：置换成指针
bis_ptr = (
    "## BIS 配装页（判据速览，全文见 `BIS.md`）\n"
    "- ★★★ 「目标等级」= `BG.filterLv`，**空 ⇒ 按 60 级**（不回落 `PlayerLevel()`）；三处消费点同口径 `EnchCap`/`PaintBrowser`/`GeneratePlan`。「当前」按钮 = 把玩家当前等级填入输入框（clamp 1..60）。\n"
    "- ★★★ **备选池只跟过滤器等级，与预设卷解耦**：`CatRowsFor` 上限 = `(BG.onlyUsable and tonumber(BG.filterLv)) or 60`。\n"
    "- ★★★ 进页优先**玩家职业** + 会话内记忆 + 重登/reload 复位（`PlayerClassSlug`/`__clsPicked`）；`pcall(UnitClass)` 取**第三个**返回值才是英文职业名。\n"
    "- ★★★ 预设方案：一个类型只有一页 = 三系共用 ⇒ 标题只写类型名且对所有天赋可见。★ 禁写 `cond and nil or v`（恒真式）。\n"
    "- ★★★ 两套自动方案置顶两行：①已知内容（排除 other）②包含位置来源（全收）；等级取玩家实际等级；每次进页默认回到①。来源过滤器含 **vendor 商人**（从 other 拆出，迁移须用版本号只补该键）。\n"
    "- ★★★ `CatRowsFor` 是**单条缓存**，逐槽遍历 = 每槽一次全表扫描 ⇒ 多槽批量选装要自己扫一次 catalog 按 `r.s` 分桶。\n"
)
perf_ptr = (
    "## 性能 / 分帧 / 预热（判据速览，全文见 `PERF.md` §9 及文末迁入段）\n"
    "- ★★★ 页面渲染统一走 `ns.PaintJob`（4ms/帧）；入口一律 `X.RequestRender()`，禁直接 `Render()`；判页面真可见用 `ns.PageVisible(page)`。\n"
    "- ★★★ 后台轮询禁「永不放弃」：放弃判据放唯一排程函数、只在页面打开处复位；收尾判据用**进展判据**（`named>0` 才续排）而非「还剩什么没做」+ 死信短路。\n"
    "- ★★★ 分页构建 GC 停帧：进构建 `collectgarbage(\"stop\")`、Finish `restart`。接 PaintJob 前 grep `coroutine.yield`/`PY()`。\n"
    "- ★★★ 登录预热唯一入口 `Core/Core.lua` gcGuard（302-430）；SIL tooltip 同步递归冲突与本客户端 `GetTime()` 是桩等细节全在 PERF.md。\n"
    "- ★★ 性能取证正途 = `C_AddOnProfiler.GetAddOnMetric`；`GetAddOnCPUUsage` 是桩。\n"
)

out = preamble
for t in order:
    if t in bis_titles:
        if t == bis_titles[0]:
            out += bis_ptr
        continue
    if t in perf_titles:
        out += perf_ptr
        continue
    out += secs[t]

open(MEM, "w", encoding="utf-8", newline="\n").write(out)

print("MEMORY.md:", len(src.encode()), "->", len(out.encode()))
print("BIS.md:", len(bis_body.encode()))
print("迁出 BIS 段:", bis_titles)
print("迁出性能段:", perf_titles)
