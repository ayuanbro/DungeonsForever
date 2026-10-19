# -*- coding: utf-8 -*-
"""把本次「注释精简」写入项目记忆（append，绝不动并行会话已写的内容）。"""
import io
import os

MEM = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever\.workbuddy\memory'

DAILY = '''

## 注释精简（用户定口径：每个 Lua 只留「开头那点注释」）

- **实情**：本插件**从未清过**注释 —— 清理前 44 个 lua = 4,079 行纯注释 + 433 处行尾注释（42,097 行里占 10.7%）。
- **口径**：只留每个 lua **开头**的注释块（`-- ====` 边框 + 文件用途 + 数据来源那几行）；
  中间的整行注释、`---------------- 分段横幅 ----------------`、行尾注释**全删**；
  数据文件的逐字段说明也删（如 `-- 升级分段 {起始技能, 目标技能, 配方法术ID, 做几个}`）。
  **Libs/ 第三方版权头与作者署名不碰**；`_temp/` 与 `.toc` 不在范围。
- **结果**：42,097 → 36,666 行（−5,431）；纯注释 4,079 → **457**（= 各文件头块之和）；行尾注释 433 → **0**。
- **工具**：`_temp/strip_comments.py`（真词法扫描短串/长串/长注释，`--dry-run` / `--apply`，保 CRLF）；
  清理前 44 个文件全量备份在 `_temp/_pre_comment_strip/**/*.lua.bak`（`.bak` 后缀，不被 luacheck 扫）；
  正确性铁证脚本 `_temp/verify_strip.py`（判据：`strip(备份) == 当前文件`）。

### ★★★ 连带必修：本项目的注释被当成「结构锚」

注释一删，离线回归立刻崩，四处都要跟着改：

1. **harness 切片锚 7 处**（`df_dungeon_check.py`）：`src.index('---- 构建 ----')` 之类 → 改**代码锚**
   （`构建` → `U.dungeonDetailScroll:SetVerticalScroll(0)`、`品质取值：` → `function DG.QualOf(id)`、
   `物品名：` → `function DG.ItemName(id)`、`副本任务取数口` → `function DG.QLFn(name)`、
   `左导航 / 子页签` → `local NAV_SKILL_SLUG = {`、`全部专业总览` → `local function ixCardSub(slug, p)`）；
   `mk_df_check.py` 同步 2 处。
2. **5 条断言**靠「代码 + 行尾注释」消歧（注释一删就落空，harness 直接红）→ 改「代码 + **紧邻下一句**」复合锚，
   强度不变（例：`r.f:SetText("")` 靠下一句 `r.a:ClearAllPoints()` 跟配方页那支区分）。其中
   `'三档合一卡' in profui` 是纯注释文本条件（本就白测），已移除。
3. **`df_mut_check.py` 加 `_strip_cmt` 归一化层**：变异锚点自动跟随注释精简（整行注释删、行尾注释剥），
   对不含注释的片段是恒等变换；另加 `_b(*lines)` 帮助函数。**4 条锚点补后变短、命中 2~3 次** →
   用**清理前备份定位落点**再逐行向后补足到唯一（脚本 `_temp/fix_short_anchors.py`，AST 取变量定义区间后整块改写）。
4. **4 个数据生成器**（`gen_zhtw_data` / `gen_enus_data` / `gen_locales` / `fc_gen`）加
   `_strip_comments_after_gen()` 收尾 —— 不加就会在下次重跑时把中间注释原样带回来。

### 验证

lua51 真解释器 44/44；luacheck 0 errors；残检旧身份串 0 处；**变异锚点 177 条全部恰好命中 1 次**；
变异抽验 4 条（到货不打 __named / 任务行退回 Frame / 卡墙底色复位 / RequestItem 不保证监听器）**全部被抓住**；
harness **38002 = 595 通过 / 0 失败**。

### ★★ 并行会话提醒（同工作区）

同时段另一条会话在做「设置页 iOS 开关 / DungeonUI 悬停预热」，双方**都在改**
`_temp/df_dungeon_check.py`、`_temp/mk_df_check.py` 与 `Core/ProfessionUI.lua`。
grep 复核双方特征串**目前都在**（无互相覆盖），但 **Edit 工具是「读-改-写」，交叉写入必丢改动** ——
以后并行时改这两个文件一律走 python 脚本字节替换。

`16001` 现存 1 条失败（`㉒ iOS 开关摆位且绑定 greyPassed（行右缘、可见）`，787/1；此前的 795/0 已证明非注释清理所致），
归属 iOS 开关那条线：新版 `PD.PlaceSettingsToggles` 若 `ti == 0`，收尾
`for j = 1, #PD.setToggles do Hide()` 会把开关池全部隐藏 → `__shown == false`。
**排查线索**：`PD.RowsSettings` 里两行开关的 spec 是否真带上了 `togKey`（`PlaceSettingsToggles` 只认 `spec.togKey`）。
'''

LM = '''

## 注释口径（用户定，2026-09-29）

**每个 Lua 只保留文件开头的注释块**，其余注释（中间整行注释、分段横幅、行尾注释、数据字段说明）一律不留 ——
理由：那些踩坑/决策内容都在项目记忆与 `_temp` 生成脚本里，放代码里没有意义。

- 生成物重跑会带回注释 → 4 个数据生成器已加 `_strip_comments_after_gen()` 收尾；
  手改别的文件后如需复核，跑 `_temp/strip_comments.py --dry-run Core Locales` 看是否有新注释。
- **注释在本项目是结构锚**（harness 切片锚 / 变异锚 / 断言消歧都在用）→ 以后**新写 harness 断言禁止拿注释当锚**，
  必须钉在**代码**上（多行复合锚用「相邻下一句」消歧，不要用行尾注释）。
- 基线（2026-09-29 注释精简后）：行数 36,666；变异锚 **177 条**；harness **795(16001) / 595(38002)**；
  luacheck 0 errors / 44 files。
'''

for fn, text in (('2026-09-29.md', DAILY), ('MEMORY.md', LM)):
    p = os.path.join(MEM, fn)
    with io.open(p, 'a', encoding='utf-8', newline='') as f:
        f.write(text)
    print('%s 已追加 %d 字符' % (fn, len(text)))
