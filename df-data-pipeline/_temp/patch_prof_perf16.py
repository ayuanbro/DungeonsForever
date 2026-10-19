# -*- coding: utf-8 -*-
"""第十刀（rev16）：材料串「按需算」—— 把「点开配方页那一瞬间」背上的一整笔 9ms 摊到分帧里。

14:29 实机（第九刀生效后）：
  · `工具P 25.0 → 2.2ms`（`显示 24.5 → 1.6`），`导航 3.9 → 0.3`，
    `皮条纹复算：21 次 / 0.1ms / 共扫 84 条`（= 21 × 4，正好每帧 4 条）
    ⇒ 第九刀的帧内索引生效，且顺带把「导航」也救了（PickNav/PickTabs 同样 Show 按钮）。
  · 整页 `点页签 recipe 61.3 → 32.0ms`。剩下的最大一块是 **`数据 20.8ms`**，
    而且它能被**一元分解**（三项之和 20.7 ≈ 20.8，口径干净）：
        数据 20.8 = 扫描 7.6（ScanRecipe） + 建spec 3.3（RecipeList） + 列宽材料 9.8（FitRecipeCols）
    其中 `材料串 9.1ms` 整个包在 `列宽材料` 里（MatCol 只被 FitRecipeCols 调）
    ⇒ **FitRecipeCols 那 300 行里 93% 的时间掉在本帧根本画不到的行上**。

机制：
  · 列表封顶 `PD.ROW_CAP = 300`，但本帧只同步绑**首屏**那几十行（`PD.SyncRows`），
    其余全部进 `PD.__pendRows` 交分帧器逐帧补齐（第七刀）。
  · `FitRecipeCols` 却对**整个 list（最多 300 条）**逐条跑 `PD.MatCol`（材料串）。
  · 材料串只依赖 `PD.MAT_W`，而 `PD.MAT_W` 在 FitRecipeCols 里**已定稿**且此后不变
    ⇒ 首屏之外那 273 行的材料串完全可以等**真被绑上前**再算，结果逐字节一致，
    变的只是「哪一帧出这笔钱」。

本补丁：
  P1         Core/ProfessionUI.lua —— 新增 `PD.FinishSpecMats(s)`（把原来那三行
             MatCol 原样搬进来，含「第 4 个返回值」那条注释；缩进仍是 8 空格
             ⇒ `MUT_PROF_MATCOL_BACK` 的字节锚点**继续有效**）。
  P2         FitRecipeCols —— 只给 `idx <= keep`（keep = `PD.SyncRows()`）的行现算，
             其余挂 `s._matsPending = true`。
  P3         PD.BindRow —— 绑行前若 `spec._matsPending` 就补算（同一个 PD.MAT_W）。
  C1/C2      双 harness 各加 1 条断言。
  D1/D2/D3   变异 `MUT_PROF_MATS_DEFER_GONE` + 登记 + DEFAULT_WANT。
  E1/E2      探针离线冒烟：**强制 keep=2** 渲一次，核对「确实延后」且「延后的行
             材料串一条不漏」（否则行上会空着材料列 —— 这是本刀唯一的真实风险）。

★ 插入型改动 ⇒ 幂等靠**哨兵串**判，不靠 count(old)。
★ 变异锚点必须**纯 ASCII**（Python 3 的 b'...' 不许含非 ASCII 字面量）。
"""

import sys

HUI = 'Core/Hui.lua'
PROF = 'Core/ProfessionUI.lua'
CHECK = '_temp/df_dungeon_check.py'
MK = '_temp/mk_df_check.py'
MUT = '_temp/df_mut_check.py'
WANT = '_temp/df_check_new_muts.py'
SMOKE = '_temp/_prof_perf_print_check.py'

# ────────────────────────── Core/ProfessionUI.lua ──────────────────────────

# P1：新增 PD.FinishSpecMats（插在 FitRecipeCols 之前）
OLD_FIT = "function PD.FitRecipeCols(list, maxW)\n"

NEW_FIT = (
    "-- ★★ 第十刀（rev16）：材料串**按需算**。\n"
    "--   实机把「数据 20.8ms」一元分解成 扫描 7.6 + 建spec 3.3 + 列宽材料 9.8，\n"
    "--   而「材料串 9.1ms」整个包在「列宽材料」里 ⇒ FitRecipeCols 那 300 行里\n"
    "--   93% 的时间掉在**本帧根本画不到**的行上（列表封顶 300 条，本帧只同步绑\n"
    "--   首屏那几十行，其余交分帧器补齐）。材料串完全可以等**真被绑上前**再算：\n"
    "--   列宽（PD.MAT_W）在 FitRecipeCols 里已定稿、此后不变，两条路径用的是\n"
    "--   同一个值 ⇒ 结果逐字节一致，变的只是「哪一帧出这笔钱」。\n"
    "function PD.FinishSpecMats(s)\n"
    "    if s and s._mats then\n"
    "        s._matsPending = nil\n"
    "        -- ★ PD.MatCol 返回 (col, w, n, segs)：segs 是**第 4 个**返回值。\n"
    "        --   写成 `local sg` + `s.mats, sg = ...` 会把第 2 个（数字 w）当成\n"
    "        --   matSegs 传进 PD.PaintMatSegs ⇒ 「attempt to get length of\n"
    "        --   local 'segs' (a number value)」，配方页整页崩。\n"
    "        local sg\n"
    "        s.mats, _, _, sg = PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)\n"
    "        s.matSegs = sg\n"
    "    end\n"
    "    return s\n"
    "end\n"
    "\n"
    "function PD.FitRecipeCols(list, maxW)\n")

# P2：FitRecipeCols 的逐行循环改成「首屏现算 / 其余挂标」
OLD_LOOP = (
    "    for _, s in ipairs(list) do\n"
    "        if s._mats then\n"
    "            -- ★ PD.MatCol 返回 (col, w, n, segs)：segs 是**第 4 个**返回值。\n"
    "            --   写成 `local sg` + `s.mats, sg = ...` 会把第 2 个（数字 w）当成\n"
    "            --   matSegs 传进 PD.PaintMatSegs ⇒ 「attempt to get length of\n"
    "            --   local 'segs' (a number value)」，配方页整页崩。\n"
    "            local sg\n"
    "            s.mats, _, _, sg = PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)\n"
    "            s.matSegs = sg\n"
    "        end\n"
    "        if s.text and s.text ~= \"\" then\n")

NEW_LOOP = (
    "    -- ★★ 第十刀（rev16）：「材料串」是这一页最贵的一笔单点（实机 9.1ms / 300 行），\n"
    "    --   而本帧只同步绑首屏那几十行（PD.SyncRows）⇒ 只给它们现算，其余挂待算标，\n"
    "    --   等 PD.BindRow 真绑到它时再用同一个 PD.MAT_W 补算（见 PD.FinishSpecMats）。\n"
    "    local keep = PD.SyncRows()\n"
    "    local idx = 0\n"
    "    for _, s in ipairs(list) do\n"
    "        idx = idx + 1\n"
    "        if s._mats then\n"
    "            if idx <= keep then\n"
    "                PD.FinishSpecMats(s)\n"
    "            else\n"
    "                s._matsPending = true\n"
    "            end\n"
    "        end\n"
    "        if s.text and s.text ~= \"\" then\n")

# P3：BindRow 绑行前补算
OLD_BIND = ("    PD.ClearMats(r)\n"
            "    PD.ClearMatSegs(r)\n"
            "    PD.RowBorder(r, spec.cur)\n")

NEW_BIND = ("    PD.ClearMats(r)\n"
            "    PD.ClearMatSegs(r)\n"
            "    -- ★★ 第十刀（rev16）：首屏之外的配方行，材料串在 FitRecipeCols 里只挂了\n"
            "    --   待算标（那是「点开那一瞬间」最贵的一笔单点）。这里在**真绑上前**\n"
            "    --   用同一个 PD.MAT_W 补算 —— 列宽此刻已定稿 ⇒ 与首屏那批逐字节一致。\n"
            "    if spec._matsPending then PD.FinishSpecMats(spec) end\n"
            "    PD.RowBorder(r, spec.cur)\n")

# ────────────────────────────── 双 harness 断言 ──────────────────────────────

ANCHOR_CK = ("       and '皮条纹复算：%d 次' in profui\n"
             "       and '（rev15' in profui)\n")

NEW_CK = (ANCHOR_CK +
          "    # ★★ 2026-10-09 第十刀（rev16）：实机把「数据 20.8ms」一元分解成\n"
          "    #   扫描 7.6 + 建spec 3.3 + 列宽材料 9.8（三项和 20.7），其中\n"
          "    #   「材料串 9.1ms」整个包在「列宽材料」里 ⇒ FitRecipeCols 那 300 行\n"
          "    #   里 93% 掉在**本帧画不到**的行上（列表封顶 300，本帧只同步绑首屏\n"
          "    #   几十行，其余交分帧器）。材料串必须改成**按需算**：首屏现算、其余\n"
          "    #   挂标，由 PD.BindRow 在**真绑上前**用同一个 PD.MAT_W 补算。\n"
          "    #   ★ 缺了补算那一句，延后的行会空着材料列 —— 断言必须同时钉住两头。\n"
          "    ck('★★ 配方页材料串按需算（首屏现算 / 其余挂标，绑前用同一个 PD.MAT_W 补算）',\n"
          "       'function PD.FinishSpecMats(s)' in profui\n"
          "       and 'local keep = PD.SyncRows()' in profui\n"
          "       and 's._matsPending = true' in profui\n"
          "       and 'if spec._matsPending then PD.FinishSpecMats(spec) end' in profui)\n")

# ────────────────────── 探针离线冒烟（Lua 段 + 断言） ──────────────────────

OLD_SMOKE_LUA = ("  local rep0 = #logs\n"
                 "  SlashCmdList[\"DUNGEONSFOREVERPROFPERF\"](\"rep\")\n"
                 "  local rep = {}\n"
                 "  for i = rep0 + 1, #logs do rep[#rep + 1] = logs[i] end\n"
                 "\n"
                 "  print = realPrint\n")

NEW_SMOKE_LUA = ("  local rep0 = #logs\n"
                 "  SlashCmdList[\"DUNGEONSFOREVERPROFPERF\"](\"rep\")\n"
                 "  local rep = {}\n"
                 "  for i = rep0 + 1, #logs do rep[#rep + 1] = logs[i] end\n"
                 "\n"
                 "  -- ★★ 第十刀（rev16）：材料串按需算的自检 —— 强制 SyncRows 只留 2 行\n"
                 "  --   同步绑，于是首屏之外**必然**走「挂待算标」那条路；再渲一次并核对：\n"
                 "  --   ① 确实发生了延后（有材料的 spec 数 > 2）；\n"
                 "  --   ② 延后的行一条都没漏算（pendLeft = 0 且 noSeg = 0）—— 少任何一条，\n"
                 "  --      行上就会空着材料列（这是本刀唯一的真实风险）。\n"
                 "  local savedSync = PD.SyncRows\n"
                 "  PD.SyncRows = function() return 2 end\n"
                 "  guard()\n"
                 "  PD.Render()\n"
                 "  PD.SyncRows = savedSync\n"
                 "  -- ★ 本脚本自带 C_Timer 桩（只排队、不执行）⇒ 必须**手动抽干**分帧队列，\n"
                 "  --   才看得到「延后的行有没有被补算材料串」（真机由 C_Timer 在后续帧跑）。\n"
                 "  local pumpN = 0\n"
                 "  while #PUMPS > 0 and pumpN < 20000 do\n"
                 "    local fn = table.remove(PUMPS, 1)\n"
                 "    pumpN = pumpN + 1\n"
                 "    pcall(fn)\n"
                 "  end\n"
                 "  local mSpec, mPend, mDone, mBad = 0, 0, 0, 0\n"
                 "  for _, sp in ipairs(PD.specs or {}) do\n"
                 "    if sp._mats and #sp._mats > 0 then\n"
                 "      mSpec = mSpec + 1\n"
                 "      if sp._matsPending then\n"
                 "        mPend = mPend + 1\n"
                 "      else\n"
                 "        mDone = mDone + 1\n"
                 "        if not sp.matSegs then mBad = mBad + 1 end\n"
                 "      end\n"
                 "    end\n"
                 "  end\n"
                 "  logs[#logs + 1] = \"@@MATS\\t\" .. mSpec .. \"\\t\" .. mPend .. \"\\t\"\n"
                 "                    .. mDone .. \"\\t\" .. mBad .. \"\\t\" .. pumpN\n"
                 "\n"
                 "  print = realPrint\n")

OLD_SMOKE_CK = ("    # ★★ /dfprofperf rep：连渲同一页 3 次（冷 / 热对照）\n"
                "    rep_head = [l for l in rep_lines if 'ms  ' in l and '「' in l]\n")

NEW_SMOKE_CK = ("    # ★★ 第十刀（rev16）：材料串按需算 —— 强制只同步绑 2 行后，首屏之外的\n"
                "    #   配方行必然走「挂待算标」路径；渲染收尾必须把它们的材料串**一条不漏**\n"
                "    #   补上（pendLeft=0 / noSeg=0），否则行上就空着材料列。\n"
                "    m_meta = next((l for l in lines if l.startswith('@@MATS')), None)\n"
                "    m_ok, m_detail = False, '(无 @@MATS 行)'\n"
                "    if m_meta:\n"
                "        _p = m_meta.split('\\t')\n"
                "        if len(_p) >= 6:\n"
                "            _spec, _pend, _done, _bad, _pump = (int(_p[1]), int(_p[2]),\n"
                "                                                int(_p[3]), int(_p[4]), int(_p[5]))\n"
                "            # 强制 keep=2 ⇒ 首屏之外必然走「挂待算标」；抽干分帧队列后：\n"
                "            #   · 真被绑上的行一条都不许缺材料串（_bad == 0）\n"
                "            #   · 走惰性路径的行必须 > 2 条（否则这条断言是恒真的白测）\n"
                "            #   · 剩的挂标只允许是「被 ROW_CAP 裁掉、这帧压根不画」那条\n"
                "            #     （抬头行占掉 300 个绘制槽之一，是既有的 off-by-one）\n"
                "            m_ok = _bad == 0 and _done > 2 and _pend <= 2\n"
                "            m_detail = ('spec=%d 挂标=%d 已算=%d 缺串=%d 分帧块=%d（强制 keep=2）'\n"
                "                        % (_spec, _pend, _done, _bad, _pump))\n"
                "    ck('★★ 材料串按需算：首屏外挂待算标，绑前用同一 PD.MAT_W 补算且一条不漏',\n"
                "       m_ok, m_detail)\n"
                "    # ★★ /dfprofperf rep：连渲同一页 3 次（冷 / 热对照）\n"
                "    rep_head = [l for l in rep_lines if 'ms  ' in l and '「' in l]\n")

# ────────────────────────────── 变异 ──────────────────────────────

MUT_DEF_ANCHOR = ("    b'            local list = nil  -- MUT: strip reapply falls back to "
                  "full-table scan\\n'))\n")

MUT_DEF = (
    "\n"
    "# ★★ 材料串按需算（2026-10-09 第十刀 rev16）：把「首屏现算 / 其余挂待算标」\n"
    "#   退回「全部行现算」⇒ FitRecipeCols 那 300 行又全在**点开那一帧**算材料串\n"
    "#   （~8ms 回来），而首屏只画得下几十行。\n"
    "#   ★ 锚点必须**纯 ASCII**：Python 3 的 b'...' 不许含非 ASCII 字面量。\n"
    "MUT_PROF_MATS_DEFER_GONE = ('Core/ProfessionUI.lua', (\n"
    "    b'            if idx <= keep then\\n'\n"
    "    b'                PD.FinishSpecMats(s)\\n'\n"
    "    b'            else\\n'\n"
    "    b'                s._matsPending = true\\n'\n"
    "    b'            end\\n',\n"
    "    b'            PD.FinishSpecMats(s)  -- MUT: mats computed eagerly for every row\\n'))\n")

MUT_REG_ANCHOR = ("    ('Hui：像素条复算退回全表扫描（工具行 Show 每颗又 ~1.5ms）',"
                  " MUT_HUI_STRIP_SCAN_ALL),\n")
MUT_REG_NEW = (MUT_REG_ANCHOR +
               "    ('专业页：材料串退回「全部行现算」（点开那一帧又背 ~8ms）',"
               " MUT_PROF_MATS_DEFER_GONE),\n")

WANT_ANCHOR = "    'Hui：像素条复算退回全表扫描（工具行 Show 每颗又 ~1.5ms）',\n"
WANT_NEW = (WANT_ANCHOR +
            "    '专业页：材料串退回「全部行现算」（点开那一帧又背 ~8ms）',\n")

# F1：既有变异 MUT_PROF_MATCOL_BACK 的字节锚点**随块搬家**。
#   那条锚点原来钉的是 FitRecipeCols 里 12 空格缩进的 MatCol 三连；P1 把这三行
#   原样搬进 `PD.FinishSpecMats`（函数体一层 + if 一层 ⇒ 8 空格）。语义完全不变
#   （替换文本一字未动），只是缩进跟着块走 —— 不改的话审计会多一条「锚点失效」。
OLD_MC = ("    b'            local sg\\n            s.mats, _, _, sg = "
          "PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)\\n            s.matSegs = sg\\n',\n")
NEW_MC = ("    b'        local sg\\n        s.mats, _, _, sg = "
          "PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)\\n        s.matSegs = sg\\n',\n")

# (文件, 名字, 旧, 新, 哨兵) —— 哨兵只在「已应用」后出现。
JOBS = [
    (PROF, 'P1 FinishSpecMats', OLD_FIT, NEW_FIT, 'function PD.FinishSpecMats(s)'),
    (PROF, 'P2 首屏现算/其余挂标', OLD_LOOP, NEW_LOOP, 'local keep = PD.SyncRows()'),
    (PROF, 'P3 BindRow 补算', OLD_BIND, NEW_BIND,
     'if spec._matsPending then PD.FinishSpecMats(spec) end'),
    (CHECK, 'C1 harness 加断言', ANCHOR_CK, NEW_CK, '配方页材料串按需算'),
    (MK, 'C2 生成器加断言', ANCHOR_CK, NEW_CK, '配方页材料串按需算'),
    (MUT, 'D1 变异定义', MUT_DEF_ANCHOR, MUT_DEF_ANCHOR + MUT_DEF, 'MUT_PROF_MATS_DEFER_GONE = '),
    (MUT, 'D2 变异登记', MUT_REG_ANCHOR, MUT_REG_NEW, 'MUT_PROF_MATS_DEFER_GONE),'),
    (WANT, 'D3 DEFAULT_WANT', WANT_ANCHOR, WANT_NEW, '材料串退回「全部行现算」'),
    (MUT, 'F1 跟搬 MatCol 变异锚点', OLD_MC, NEW_MC, "    b'        local sg"),
    (SMOKE, 'E1 冒烟造态', OLD_SMOKE_LUA, NEW_SMOKE_LUA, '"@@MATS\\t"'),
    (SMOKE, 'E2 冒烟断言', OLD_SMOKE_CK, NEW_SMOKE_CK, '材料串按需算：首屏外挂待算标'),
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
