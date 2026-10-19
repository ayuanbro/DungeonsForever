# -*- coding: utf-8 -*-
"""第九刀（rev15）：把「工具P 25.0ms」钉到 `bt:Show()` 上，并按数据修掉真凶。

14:11 / 14:20 / 14:21 三次实机（三组数据完全一致）：
  · 点页签 recipe：工具P **25.3/25.4/25.0ms**，闸门拆解恒为
        16 开 = 尺寸 0.1 + 锚点 0.2 + 文本 0.1 + **显示 24.5**
    ⇒ 25ms 全在 `bt:Show()` **一句**上（闸门里那两个 _MK 之间没有别的调用）。
  · 反面样本（同一份日志）：切到 leveling 时 `3 开 / 0.1ms = 显示 0.0`，
    而那 3 颗按钮**本来就没被 Hide 过** ⇒ Show() 空操作、OnShow 不触发 ⇒ 0ms。
    ⇒ 「1.5ms/颗」只在 **Hide→Show 跃迁**时出现 —— 这正是 OnShow 链的特征。
  · `皮按钮帧：建 0 次 · TryBuild 调用 0 次` ⇒ 与建帧无关（第七刀那条已证伪）。

机制（Hui.lua 自己的注释就是证据，见 596-600 行：「OnShow 会落在暴雪 tooltip
管线里（TooltipDataHandler:300 → Show 链 / NineSlice:Show）」）：
  引擎 Show() 沿「Show 链」把 OnShow 打给子帧。工具的圆角边框帧是 bt 的子帧，
  它挂的正是 **ReapplyStripPixels** —— 而它是 `for tex in pairs(pixelStrips)`
  **全表扫描**，pixelStrips 是**全插件一张弱表**（每个直角边框帧注册 4 条：
  2 横 + 2 竖，见 DrawRoundBorder 的 thick==1 分支）。
  20 颗工具按钮 × 2 副边框帧 × 4 条 = 160 条，再加上全插件所有换皮元素 ⇒
  16 次 × 全表 ≈ 24.5ms。**每次悬停（hoverFrame:Show()）也在付同一笔账。**

本补丁：
  A1/A2/A3  Core/Hui.lua —— ① `RegisterPixelStrip` 维护**帧内索引** `p.__huiStrips`；
             ② `ReapplyStripPixelsBody(frame)` 有 frame 时只扫本帧（O(4) 而非 O(全插件)），
                语义不变（仍复核 tex:GetParent() == frame，尺寸仍按本帧算一次）；
             ③ 计数器 `ns.hui.__stripStat()`（次数 / 耗时 / 扫描条数 / 注册条数）。
  B1..B6     Core/ProfessionUI.lua —— 闸门多记一项「已显」（判定 Hide→Show 跃迁），
             并**无条件**打印 `皮条纹复算：N 次 / x.xms / 共扫 M 条（rev15）`。
  C1/C2      双 harness 各加 1 条断言（帧内索引 + 计数器 + 打印行）。
  D1/D2/D3   变异 `MUT_HUI_STRIP_SCAN_ALL` + 登记 + DEFAULT_WANT。
  E1         探针离线冒烟：新行必须恒打（带 rev15）。

★ 插入型改动（新串含旧串）⇒ 幂等靠**哨兵串**判，不靠 count(old)。
★ 变异锚点必须**纯 ASCII**（Python 3 的 b'...' 不许含非 ASCII 字面量）。
★ 刻意**不动** `（rev14` 那两处（patch14 的哨兵），新证据靠新行的 rev15 承担。
"""

import sys

HUI = 'Core/Hui.lua'
PROF = 'Core/ProfessionUI.lua'
CHECK = '_temp/df_dungeon_check.py'
MK = '_temp/mk_df_check.py'
MUT = '_temp/df_mut_check.py'
WANT = '_temp/df_check_new_muts.py'
SMOKE = '_temp/_prof_perf_print_check.py'

# ────────────────────────────── Core/Hui.lua ──────────────────────────────

# A1：计数器 + 时钟（放在 pixelStrips / pixelShowHooks 之后）
OLD_CNT = ("    local pixelStrips = setmetatable({}, { __mode = \"k\" })\n"
           "    local pixelShowHooks = setmetatable({}, { __mode = \"k\" })\n")

NEW_CNT = ("    local pixelStrips = setmetatable({}, { __mode = \"k\" })\n"
           "    local pixelShowHooks = setmetatable({}, { __mode = \"k\" })\n"
           "    -- ★★ 第九刀（rev15）：像素条复算的计数与耗时。\n"
           "    --   实机「点页签 recipe」时工具行 16 颗按钮 Hide→Show，`工具P 25.0ms`\n"
           "    --   里 `显示 24.5ms` 全在 `bt:Show()` **一句**上 —— 引擎 Show 沿「Show 链」\n"
           "    --   把 OnShow 打到子帧，而子帧（按钮的圆角边框帧）挂的正是\n"
           "    --   ReapplyStripPixels，它是**全表扫描**。这组数字用来把这条链钉死\n"
           "    --   （没有这组数就只剩「读代码猜」，项目铁律不允许）。\n"
           "    local stripRepN, stripRepMs, stripScanN, stripRegN = 0, 0, 0, 0\n"
           "    ns.hui.__stripStat = function() return stripRepN, stripRepMs, stripScanN, stripRegN end\n"
           "    local function huiNow()\n"
           "        if type(debugprofilestop) == \"function\" then return debugprofilestop() end\n"
           "        if type(GetTime) == \"function\" then return GetTime() * 1000 end\n"
           "        return 0\n"
           "    end\n")

# A2：帧内索引快速通道 + 计数
OLD_BODY = ("    local stripsApplying = false\n"
            "    local function ReapplyStripPixelsBody(frame)\n"
            "        for tex in pairs(pixelStrips) do\n"
            "            local p = tex:GetParent()\n"
            "            if p and (not frame or p == frame) then\n"
            "                local s = PixelStripSize(p)\n"
            "                if tex.__huiStripAxis == \"h\" then tex:SetHeight(s) else tex:SetWidth(s) end\n"
            "            end\n"
            "        end\n"
            "    end\n"
            "    local function ReapplyStripPixels(frame)\n"
            "        if stripsApplying then return end\n"
            "        stripsApplying = true\n"
            "        pcall(ReapplyStripPixelsBody, frame)\n"
            "        stripsApplying = false\n"
            "    end\n")

NEW_BODY = ("    local stripsApplying = false\n"
            "    local function ReapplyStripPixelsBody(frame)\n"
            "        -- ★★ 第九刀（rev15）：给了 frame 就只扫**本帧**挂的条（帧内索引）。\n"
            "        --   原实现无论 frame 给不给都是 `for tex in pairs(pixelStrips)`\n"
            "        --   **全表扫**，而 pixelStrips 是**全插件一张弱表**（每个直角边框帧\n"
            "        --   注册 4 条：2 横 + 2 竖，见 DrawRoundBorder 的 thick==1 分支）。\n"
            "        --   实机代价：工具行 16 颗按钮 Hide→Show 时子边框帧 OnShow 各触发\n"
            "        --   一次全表扫 ⇒ 16 × 全表 ≈ 24.5ms，正好等于「工具P」的全部。\n"
            "        --   ★ 语义不变：仍复核 tex:GetParent() == frame（换父后的旧索引项会被\n"
            "        --     这条挡掉），尺寸仍按本帧算一次；变的只有「扫多少条」：\n"
            "        --     从 O(全插件) 降到 O(本帧 4 条)。\n"
            "        if frame then\n"
            "            local list = frame.__huiStrips\n"
            "            if list then\n"
            "                local s, n = PixelStripSize(frame), #list\n"
            "                stripScanN = stripScanN + n\n"
            "                for i = 1, n do\n"
            "                    local tex = list[i]\n"
            "                    if tex:GetParent() == frame then\n"
            "                        if tex.__huiStripAxis == \"h\" then tex:SetHeight(s) else tex:SetWidth(s) end\n"
            "                    end\n"
            "                end\n"
            "                return\n"
            "            end\n"
            "        end\n"
            "        local cnt = 0\n"
            "        for tex in pairs(pixelStrips) do\n"
            "            cnt = cnt + 1\n"
            "            local p = tex:GetParent()\n"
            "            if p and (not frame or p == frame) then\n"
            "                local s = PixelStripSize(p)\n"
            "                if tex.__huiStripAxis == \"h\" then tex:SetHeight(s) else tex:SetWidth(s) end\n"
            "            end\n"
            "        end\n"
            "        stripScanN = stripScanN + cnt\n"
            "    end\n"
            "    local function ReapplyStripPixels(frame)\n"
            "        if stripsApplying then return end\n"
            "        stripsApplying = true\n"
            "        local t0 = huiNow()\n"
            "        pcall(ReapplyStripPixelsBody, frame)\n"
            "        stripRepMs = stripRepMs + (huiNow() - t0)\n"
            "        stripRepN = stripRepN + 1\n"
            "        stripsApplying = false\n"
            "    end\n")

# A3：注册时维护帧内索引
OLD_REG = ("    local function RegisterPixelStrip(tex, axis)\n"
           "        tex.__huiStripAxis = axis\n"
           "        pixelStrips[tex] = true\n"
           "        local p = tex:GetParent()\n"
           "        if p then\n"
           "            local s = PixelStripSize(p)\n")

NEW_REG = ("    local function RegisterPixelStrip(tex, axis)\n"
           "        tex.__huiStripAxis = axis\n"
           "        pixelStrips[tex] = true\n"
           "        stripRegN = stripRegN + 1\n"
           "        local p = tex:GetParent()\n"
           "        if p then\n"
           "            -- ★★ 第九刀（rev15）：帧内索引 —— 供 OnShow 的 O(本帧) 复算用\n"
           "            --   （原来那条 OnShow 路径是 O(全插件) 全表扫）。\n"
           "            local list = p.__huiStrips\n"
           "            if not list then list = {}; p.__huiStrips = list end\n"
           "            list[#list + 1] = tex\n"
           "            local s = PixelStripSize(p)\n")

# ────────────────────────── Core/ProfessionUI.lua ──────────────────────────

# B1：闸门里再取一个「只记次数」的记号器（**另起一行**，不许改 patch14 的哨兵行）
OLD_T0L = "    local _T0, _MK = PD.__pfT0, PD.__pfMark\n"
NEW_T0L = (OLD_T0L +
           "    local _AD = PD.__pfAdd\n")

# B2：闸门里先记「此刻是否已显示」
OLD_G0 = ("                local _m0 = _T0 and _T0()\n"
          "                local _g0 = _m0\n"
          "                bt:SetSize(w, PD.TOOL_H)\n")

NEW_G0 = ("                local _m0 = _T0 and _T0()\n"
          "                local _g0 = _m0\n"
          "                -- ★★ 第九刀（rev15）：先记「这颗粒此刻是不是已经显示着」。\n"
          "                --   引擎 Show() 在帧已可见时是**空操作** ⇒ 不触发 OnShow 链；\n"
          "                --   只有 Hide→Show 跃迁才吃那 ~1.5ms/颗。实机反面样本：切到\n"
          "                --   leveling 时 3 颗本来就没被 Hide ⇒ 显示 0.0ms。\n"
          "                if _AD then _AD(\"闸-已显\", bt:IsShown() and 1 or 0) end\n"
          "                bt:SetSize(w, PD.TOOL_H)\n")

# B3：探针口径声明
OLD_DECL = "local PF_TB0 = nil                -- ★ 第八刀：TryBuild 调用次数的入口快照\n"
NEW_DECL = (OLD_DECL +
            "local PF_STR0 = nil               -- ★ 第九刀：像素条复算的入口快照（次数/耗时/扫描条数）\n"
            "local PF_STRM0 = nil\n"
            "local PF_STRS0 = nil\n")

# B4：入场快照
OLD_BEGIN = "        PF_TB0 = (ns.hui and ns.hui.__tryBuilds) or 0\n"
NEW_BEGIN = (OLD_BEGIN +
             "        local _st = ns.hui and ns.hui.__stripStat\n"
             "        if _st then\n"
             "            local a, b, c = _st()\n"
             "            PF_STR0, PF_STRM0, PF_STRS0 = a or 0, b or 0, c or 0\n"
             "        else\n"
             "            PF_STR0, PF_STRM0, PF_STRS0 = 0, 0, 0\n"
             "        end\n")

# B5：PD.__pfAdd 定义（挂在 __pfMark 之后）
OLD_MARK = ("function PD.__pfMark(tag, t0)\n"
            "    if not PF_SUB or not t0 then return end\n"
            "    local dt = pfNow() - t0\n"
            "    local e = PF_SUB[tag]\n"
            "    if e then e[1] = e[1] + 1; e[2] = e[2] + dt\n"
            "    else PF_SUB[tag] = { 1, dt } end\n"
            "end\n")

NEW_MARK = (OLD_MARK +
            "\n"
            "-- ★★ 第九刀（rev15）：只记次数、不计时的记号器（闸门里判「已显 / 未显」用）。\n"
            "--   与 __pfMark 同源 ⇒ 同样必须**运行期动态取**。\n"
            "function PD.__pfAdd(tag, n)\n"
            "    if not PF_SUB or not n then return end\n"
            "    local e = PF_SUB[tag]\n"
            "    if e then e[1] = e[1] + n else PF_SUB[tag] = { n, 0 } end\n"
            "end\n")

# B6：打印（闸门行加「已显」+ 新增像素条复算行）
OLD_END = ("        pfOut(string.format(\"  └ 工具闸门（已含在「工具P」里）：%d 开 / %.1fms = %s\",\n"
           "                            hit, zg[2], table.concat(seg, \" + \")))\n"
           "    end\n")

NEW_END = ("        pfOut(string.format(\"  └ 工具闸门（已含在「工具P」里）：%d 开 / %.1fms = %s（其中已显 %d）\",\n"
           "                            hit, zg[2], table.concat(seg, \" + \"),\n"
           "                            (PF_SUB[\"闸-已显\"] and PF_SUB[\"闸-已显\"][1]) or 0))\n"
           "    end\n"
           "    -- ★★ 第九刀（rev15）：**无条件**打印像素条复算（Hui 侧计数器）。\n"
           "    --   实机「点页签 recipe」时工具行 16 颗按钮 Hide→Show，每一步都触发子帧\n"
           "    --   OnShow 的 ReapplyStripPixels —— 这条数字直接说明它是不是那 24.5ms：\n"
           "    --   改对了应当是「16 次 / ~0.0ms / 共扫 ~64 条」（16 × 4）。\n"
           "    local stn, stms, stscan = 0, 0, 0\n"
           "    if ns.hui and ns.hui.__stripStat then stn, stms, stscan = ns.hui.__stripStat() end\n"
           "    pfOut(string.format(\"  └ 皮条纹复算：%d 次 / %.1fms / 共扫 %d 条（rev15）\",\n"
           "                        stn - (PF_STR0 or 0), stms - (PF_STRM0 or 0), stscan - (PF_STRS0 or 0)))\n")

# ────────────────────────────── 双 harness 断言 ──────────────────────────────

ANCHOR_CK = ("       and 'if sk > 0 then' not in profui\n"
             "       and '（rev14' in profui)\n")

NEW_CK = (ANCHOR_CK +
          "    # ★★ 2026-10-09 第九刀（rev15）：实机把「工具P 25.0ms」逼到一句 `bt:Show()`\n"
          "    #   上（闸门 16 开 = 尺寸 0.1 + 锚点 0.2 + 文本 0.1 + **显示 24.5**）。引擎\n"
          "    #   Show 沿「Show 链」把 OnShow 打到子帧，而按钮的圆角边框帧挂的正是\n"
          "    #   ReapplyStripPixels —— 它原来是 `for tex in pairs(pixelStrips)` **全表扫**\n"
          "    #   （全插件一张弱表）⇒ 16 次 ≈ 24.5ms。必须改成帧内索引（O(本帧 4 条)），\n"
          "    #   并留计数器把这条链钉死（否则下一轮又只能读代码猜）。\n"
          "    ck('★★ 像素条复算走帧内索引（不许全表扫）+ 有计数器（rev15）',\n"
          "       'ns.hui.__stripStat' in hui\n"
          "       and 'local list = frame.__huiStrips' in hui\n"
          "       and 'p.__huiStrips = list' in hui\n"
          "       and 'PD.__pfAdd' in profui\n"
          "       and '皮条纹复算：%d 次' in profui\n"
          "       and '（rev15' in profui)\n")

# ────────────────────── 探针离线冒烟断言 ──────────────────────

OLD_SMOKE = ("       next((l for l in lines if '工具闸门（已含在' in l), '(无)'))\n"
             "    # ★★ /dfprofperf rep：连渲同一页 3 次（冷 / 热对照）\n")

NEW_SMOKE = ("       next((l for l in lines if '工具闸门（已含在' in l), '(无)'))\n"
             "    # ★★ 第九刀（rev15）：像素条复算那行必须**恒打**（带 rev15 版本号）。\n"
             "    #   第七刀的教训：写成「有值才打」⇒ 实机看不到它时**无法区分**\n"
             "    #   「本版没加载」与「一次复算都没发生」。\n"
             "    ck('★★ 「皮条纹复算」行恒打（带 rev15）',\n"
             "       any('皮条纹复算：' in l and 'rev15' in l for l in lines),\n"
             "       next((l for l in lines if '皮条纹复算' in l), '(无)'))\n"
             "    # ★★ /dfprofperf rep：连渲同一页 3 次（冷 / 热对照）\n")

# ────────────────────────────── 变异 ──────────────────────────────

MUT_DEF_ANCHOR = ("    b'    local _T0, _MK = nil, nil  -- MUT: tool gate left uninstrumented\\n'))\n")

MUT_DEF = (
    "\n"
    "# ★★ 像素条复算（2026-10-09 第九刀 rev15）：把帧内索引摘掉 ⇒ 退回\n"
    "#   `for tex in pairs(pixelStrips)` 全表扫 ⇒ 工具行 16 颗按钮 Hide→Show\n"
    "#   每颗又 ~1.5ms（= 工具P 的 24.5ms 全回来）。\n"
    "#   ★ 锚点必须**纯 ASCII**：Python 3 的 b'...' 不许含非 ASCII 字面量。\n"
    "MUT_HUI_STRIP_SCAN_ALL = ('Core/Hui.lua', (\n"
    "    b'            local list = frame.__huiStrips\\n',\n"
    "    b'            local list = nil  -- MUT: strip reapply falls back to full-table scan\\n'))\n")

MUT_REG_ANCHOR = ("    ('专业页：工具行闸门插桩被摘（21ms 又拆不开，只能读代码猜）',"
                  " MUT_PROF_TOOL_GATE_UNMARKED),\n")
MUT_REG_NEW = (MUT_REG_ANCHOR +
               "    ('Hui：像素条复算退回全表扫描（工具行 Show 每颗又 ~1.5ms）',"
               " MUT_HUI_STRIP_SCAN_ALL),\n")

WANT_ANCHOR = "    '专业页：工具行闸门插桩被摘（21ms 又拆不开，只能读代码猜）',\n"
WANT_NEW = (WANT_ANCHOR +
            "    'Hui：像素条复算退回全表扫描（工具行 Show 每颗又 ~1.5ms）',\n")

# (文件, 名字, 旧, 新, 哨兵) —— 哨兵只在「已应用」后出现。
JOBS = [
    (HUI, 'A1 Hui 条纹计数器', OLD_CNT, NEW_CNT, 'ns.hui.__stripStat = function()'),
    (HUI, 'A2 Hui 帧内索引快路径', OLD_BODY, NEW_BODY, 'local list = frame.__huiStrips'),
    (HUI, 'A3 Hui 注册维护索引', OLD_REG, NEW_REG, 'list[#list + 1] = tex'),
    (PROF, 'B1 取 __pfAdd', OLD_T0L, NEW_T0L, 'local _AD = PD.__pfAdd'),
    (PROF, 'B2 闸门记「已显」', OLD_G0, NEW_G0, '_AD("闸-已显"'),
    (PROF, 'B3 条纹快照声明', OLD_DECL, NEW_DECL, 'local PF_STR0 = nil'),
    (PROF, 'B4 pfBegin 快照', OLD_BEGIN, NEW_BEGIN, 'PF_STR0, PF_STRM0, PF_STRS0 = a or 0'),
    (PROF, 'B5 __pfAdd 定义', OLD_MARK, NEW_MARK, 'function PD.__pfAdd(tag, n)'),
    (PROF, 'B6 打印条纹复算行', OLD_END, NEW_END, '皮条纹复算：%d 次 / %.1fms / 共扫 %d 条（rev15）'),
    (CHECK, 'C1 harness 加断言', ANCHOR_CK, NEW_CK, '像素条复算走帧内索引'),
    (MK, 'C2 生成器加断言', ANCHOR_CK, NEW_CK, '像素条复算走帧内索引'),
    (MUT, 'D1 变异定义', MUT_DEF_ANCHOR, MUT_DEF_ANCHOR + MUT_DEF, 'MUT_HUI_STRIP_SCAN_ALL = '),
    (MUT, 'D2 变异登记', MUT_REG_ANCHOR, MUT_REG_NEW, 'MUT_HUI_STRIP_SCAN_ALL),'),
    (WANT, 'D3 DEFAULT_WANT', WANT_ANCHOR, WANT_NEW, '像素条复算退回全表扫描'),
    (SMOKE, 'E1 冒烟断言', OLD_SMOKE, NEW_SMOKE, '「皮条纹复算」行恒打（带 rev15）'),
]


def main():
    check = '--check' in sys.argv
    bad, plans, raws = 0, {}, {}
    for path, name, old, new, key in JOBS:
        if path not in raws:
            raws[path] = open(path, 'rb').read()
        raw = raws[path]
        src = plans.get(path) or raw.decode('utf-8')
        nl = '\r\n' if b'\r\n' in raw else '\n'

        def fx(s):
            return s if nl == '\n' else s.replace('\n', nl)

        if key and fx(key) in src:
            print('  [SKIP] %-26s 已应用' % name)
            continue

        o, n = fx(old), fx(new)
        if src.count(o) != 1:
            print('  [BAD ] %-26s 锚点 %d 次' % (name, src.count(o)))
            bad += 1
            continue
        plans[path] = src.replace(o, n, 1)
        print('  [OK  ] %-26s 锚点 1 次' % name)

    if bad:
        print('  \u2717 %d 处未通过，未落盘' % bad)
        return 1
    if check:
        print('  [OK  ] 预检通过（未落盘）')
        return 0
    for path, src in plans.items():
        if src != raws[path].decode('utf-8'):
            with open(path, 'wb') as f:
                f.write(src.encode('utf-8'))
            print('  [OK  ] 已写入 %s' % path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
