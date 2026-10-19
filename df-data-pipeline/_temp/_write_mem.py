# -*- coding: utf-8 -*-
"""本轮（详情页地图页签）记忆落盘：今日日志 append + MAP_ART 专题 + MEMORY 基线 + PAGES 一行。"""
import os

MEM = r"D:/Game/World of Warcraft/_classic_beta_/Interface/AddOns/DungeonsForever/.workbuddy/memory"

LOG = """
### 详情页「地图」页签（用户 5 条拍板全部落地 · 本轮主交付）
- **新件 `Core/MapUI.lua`**（手写 / LF，不进生成链），toc 排在 `Core\\DungeonUI.lua` **之后**
  —— 它取 `ns.ProfHost` 的 `MakeFS` / `C_GREY`，而 ProfHost 在 DungeonUI **末尾**才赋值。
- **挂点 10 处全在 DungeonUI.lua（CRLF）**：`tabs` 加第 4 项 `{ key = "map", text = L["地图"] }`
  （**放最后 = 视觉最左**，因按钮右起排布）／Build 里 `U.dungeonMapFrame = ns.MapModule.Build(detail, hero)`／
  `SetDungeonTab` 四态／`RenderDungeonTab` 认 `isMap` + 掉落滚动区让位（`and not isMap`）+ 容器显隐 +
  筛选按钮 `if isGuide or isMap then` 全隐 + 分派 `elseif isMap then ns.MapModule.Paint(U.dungeonDetailCur)`／
  Build 复位 `U.dungeonMapFrame = nil`／存档还原四态。补丁脚本 `_temp/patch_map_tab.py`。
- **取图口径**：客户端世界地图瓦片，12 块 = 4 列 × 3 行、每块 256×256、**行优先**；画布 1024×768，
  有效画面 = 左上 **1002×668**（右 22 / 底 100 是装饰边）⇒ 上屏按交集裁掉；**只取第 1 层**；
  路径 `Interface\\WorldMap\\<目录>\\<前缀><n>`，**直接用路径 SetTexture（不用 fid）**。
- **表口径（27/8）**：27 个副本 id 有图（21 条独立路径 —— 血色 4 分区 / 厄运 3 区 / 斯坦索姆 2 区
  各登记同一前缀）；8 个走空态（只有区域图的 3 个：领主大厅 / 挖掘场湿地 / 洛丹伦废墟
  + 完全没图的 5 个：沉没之城 / 克罗多克 / 奥卡兹 / 黑喉 / 塑造者平台）。
  ★★ **区域图目录（OldIronforge / Wetlands / Tirisfal / RuinsofLordaeron）一个都不许进表** —— 静态 + 动态双闸。
- **几何抽成纯函数**（离线可直调）：`M.FitBox(aw, ah)` 等比适应居中、`M.Layout(cw, ch)` 出 12 块落点 + UV。
  实测详情页 936×502 → **753×502、左右各 91**（`1002×502/668 = 753.0` 正好整除 ⇒ 取整后左右差 1px）
  ⇒ 断言必须写 `math.abs(w + 2x - 936) <= 1`；写成 `== 936` **当场假红**（本轮踩到）。
- **验证**：`check_mut_anchors` **246/0** → 16001 **1038/0** · 38002 **823/0** →
  9 条新变异逐条隔离 **9/9 抓住、漏网 0**（`df_check_new_muts.py 地图`）→ `run_all_checks.py` **五项全绿**；
  两侧零漂移（`sync_beta.py` 报「仅源有/仅副本有/内容不同」全无）。
- **顺手修的三处既有缺陷**（都与地图无关，但挡路）：
  ① `df_mut_check.py` 两条攻略变异锚点被四态改动打烂（页签表长了第 4 项 / 让位条件长了 `and not isMap`）⇒ 重锚
     （攻略页签那条改成「只摘 `, { key = "guide", … }`」，**别把表收尾 `} }` 留在替换区间外** —— 那是语法错 = 脏抓）；
  ② **「行点击分派」断言只认无限服口径**：泰坦/正式服没有专业页与探索页，那两行落回 `OpenPage` ⇒
     按端给两种合法口径。★ 这是 38002 端**预存的红**，它让 `df_mut_check` 的 `nFail > 0` 判据**恒真**（等于白测）；
  ③ `gen_zhtw.py` 的 `SCAN_FILES` 漏了 LootFilter / LootFilterUI / TierUI / QuickBar（重跑会**误删**它们的键，
     已捕 50 条繁体缺口）+ `gen_enus.py` 的 EN 表落后 16 键（生成器一直 exit 1）⇒ 一并补齐，
     现在两个生成器都能干净重跑（各自 re-run 幂等：zhTW 只增 2 条地图文案 + 删 3 条真死键；enUS 只增 18 条）。
- ⚠️ **变异锚点的反斜杠层数**：Lua 源码里路径是**两个**反斜杠 ⇒ `df_mut_check.py` 的 bytes 字面量要写 **4 个**
  （即源码文本 `b'…Interface\\\\WorldMap\\\\…'`，bytes 值才是两个）。写成 2 个 ⇒ bytes 值 = 1 个 ⇒ **锚点 0 命中**
  （回显「锚点 0 次」，很容易误判成「抄错路径」）。★ 若这段定义是用补丁脚本的**非 raw 三引号**字符串生成的，
  还得再翻倍写 8 个 —— 正解是**插入块一律用 `r'''…'''`**，或改用 `.encode()` 拼接。
- 预览件 `_temp/MAP_TAB_PREVIEW.png`（`_map_tab_preview.py`）：拿实机导出的 12 块怒焰瓦片按代码常量
  渲染最终上屏版式 + 页签排布（画面 753×502 / 左右各 91）。
- **待用户实机确认**：进游戏开详情页点「地图」看真实瓦片（客户端版本差异可能让某个副本贴图缺块；
  缺块时 v1 不判定，后续可加「任一块 fid == 0 即空态」）。
"""

MAPART = """
## 落地：详情页「地图」页签（2026-09-30）

- 新件 `Core/MapUI.lua`（手写/LF，toc 在 `Core\\DungeonUI.lua` 之后）+ DungeonUI 10 处挂点；
  页签排最左（右起排布 ⇒ `tabs` 第 4 项）。空态文案「这个副本没有客户端自带的地图。」
- 27 个副本 id 有图 / 8 个空态；**区域图不进表**（见上「副本内图 vs 区域图」）。
- 上屏几何：有效画面 1002×668 按交集裁装饰边 → 等比适应（纯函数 `M.FitBox` / `M.Layout`）→
  详情页可用 936×502 时得 **753×502、左右各 91**。瓦片**行优先**、只取第 1 层、**直接路径 SetTexture**。
- 验证 1038/0 · 823/0 · mut 9/9 · 五项全绿；预览 `_temp/MAP_TAB_PREVIEW.png`。
"""


def append(path, text):
    d = open(path, "rb").read()
    assert b"\r\n" not in d, path + " 意外是 CRLF"
    if not d.endswith(b"\n"):
        d += b"\n"
    open(path, "wb").write(d + text.lstrip("\n").encode("utf-8"))
    print("append", path)


def patch(path, pairs):
    d = open(path, "rb").read().decode("utf-8")
    for old, new in pairs:
        n = d.count(old)
        assert n == 1, (path, n, old[:60])
        d = d.replace(old, new, 1)
    open(path, "wb").write(d.encode("utf-8"))
    print("patch", path)


append(os.path.join(MEM, "2026-09-30.md"), LOG)
append(os.path.join(MEM, "MAP_ART.md"), MAPART)

patch(os.path.join(MEM, "MEMORY.md"), [
    (
        "## 基线（2026-09-30 · 快捷栏 v4 后）\n"
        "`run_all_checks.py` **五项全绿**：244/0 · **1005/0** · 75/0 · 12/12 · mut exit 0。真 Lua 5.1 全过、两侧零漂移。\n"
        "- ⚠️ `df_mut_check` 的 `MUT_QUAL_FALLBACK` 让 `static_guard()` 早崩 ⇒ 变异批次里动态断言**从不执行**（预存缺陷）⇒ "
        "「某断言真抓住某变异」一律用 `_qb_probe_nonvacuous.py`（20 条，隔离注入+还原）证。\n",
        "## 基线（2026-09-30 · 详情页地图页签后）\n"
        "`run_all_checks.py` **五项全绿**：244/0 · **1038/0**（16001）· 823/0（38002）· 75/0 · 12/12 · mut exit 0；"
        "`check_mut_anchors` **246/0**。真 Lua 5.1 全过、两侧零漂移。\n"
        "- ⚠️ `df_mut_check` 的 `MUT_QUAL_FALLBACK` 历史上会让 `static_guard()` 早崩 ⇒ 变异批次里动态断言**从不执行**（预存缺陷）。"
        "★ 2026-09-30 实测：地图页 9 条变异逐条隔离**全部命中**，说明该批**没有**早崩 —— 但别把「mut exit 0」当全量证明，"
        "「某断言真抓住某变异」仍一律用 `df_check_new_muts.py <关键字>` 逐条隔离证。\n"
        "- ★★ `df_mut_check` 的判据是「**nFail > 0**」⇒ 只要 harness 里有任何既有 FAIL 就**恒真**。"
        "2026-09-30 就抓到一条：38002 端的「行点击分派」断言没按端分流（泰坦/正式服无专业页与探索页）⇒ 长期挂着 1 条红，"
        "把整个变异闸变成白测。**改了通用页/挂点后一定要两端都跑 `df_dungeon_check.py` 确认 0 失败**。\n",
    ),
    (
        "- ★★ 「某标识符不许出现」型断言，注释里也不能写；Bash heredoc 写 Python 锚点，反斜杠会被 JSON 再吃一层。探针选 beta 要**连续两次一致**才采信。\n",
        "- ★★ 「某标识符不许出现」型断言，注释里也不能写；Bash heredoc 写 Python 锚点，反斜杠会被 JSON 再吃一层。探针选 beta 要**连续两次一致**才采信。\n"
        "- ★★ **变异锚点的反斜杠层数**：Lua 源码里的路径是**两个**反斜杠 ⇒ `df_mut_check.py` 的 bytes 字面量要写 **4 个**（源码文本），"
        "bytes 值才是两个；写 2 个 ⇒ 锚点 **0 命中**。★ 用补丁脚本插入这种块时，若插入串是**非 raw 三引号**还得再翻倍（8 个）"
        "⇒ **一律用 `r'''…'''` 或 `.encode()` 拼接**（2026-09-30 地图页踩到，回显「锚点 0 次」）。\n",
    ),
])

patch(os.path.join(MEM, "PAGES.md"), [
    (
        "- **副本攻略子页签**：详情页左侧第三页签「攻略」（`U.dungeonTab` 三态）；",
        "- **详情页地图页签**：`Core/MapUI.lua`（手写/LF，toc 在 DungeonUI 后）+ DungeonUI 10 处挂点；"
        "`U.dungeonTab` **四态**（掉落/任务/攻略/地图，地图最左）；取图 = 客户端世界地图瓦片 12 块（4×3 行优先、"
        "有效画面 1002×668、只取第 1 层、直接路径贴图）；27 副本有图 / 8 空态，**区域图不进表**；"
        "几何纯函数 `FitBox`/`Layout`（936×502 → 753×502 左右各 91，断言容忍 ±1）。详见 `MAP_ART.md`。\n"
        "- **副本攻略子页签**：详情页左侧第三页签「攻略」（`U.dungeonTab` 四态中的一员）；",
    ),
])
print("done")
