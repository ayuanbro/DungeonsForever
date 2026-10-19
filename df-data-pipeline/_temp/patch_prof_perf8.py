#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""patch_prof_perf8.py
  给 /dfprofperf 探针加三样「指哪打哪」的东西（全部只动探针区，不碰产品逻辑）：

  ① 细分线  —— ScanRecipe / RecipeList / FitRecipeCols / MatCol / RecipeSpec 各自的
     次数与耗时。它们**已经在「数据」里**，只作分解展示，**不进 PF_ORDER、不相加**
     （上一版把嵌套段相加，数字翻倍，踩过）。
  ② setter 计数 —— 直接数引擎 setter（SetText / SetTextColor）被调了多少次。
     只包这两样：它们身上没有任何 hooksecurefunc，覆盖实例方法不会破坏
     ns.hui.SkinButton 挂在 SetSize 上的 TryBuild 钩子。
  ③ /dfprofperf bench —— 微基准：量出实机里每个 setter 的**单价**（µs/次）。
     离线桩是纯 Lua 空表 ⇒ 单价只能实机量；有了单价，任何一段的「次数 × 单价」
     就能立刻算出它值不值得砍。

  ★ 幂等：哨兵命中即整体 SKIP。--check 只预检不落盘。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.normpath(os.path.join(HERE, '..', 'Core', 'ProfessionUI.lua'))

SENTINEL = '-- ④b 细分：这几项**已经在「数据」里**'

# ── P1 头部：声明 PF_SUB / PF_SET（必须在 pfBegin 之前，否则是全局 nil）──────
P1_OLD = ('local PF_TAIL = nil\n'
          'local PF_SCAN = nil\n')

P1_NEW = ('local PF_TAIL = nil\n'
          'local PF_SCAN = nil\n'
          'local PF_SUB, PF_SET = nil, nil   -- 细分计时 / setter 计数（每次入口重置）\n')

# ── P2 pfBegin：重置 ───────────────────────────────────────────────────────
P2_OLD = ('    if PF_DEPTH == 1 then\n'
          '        PF_MS, PF_N = {}, {}\n'
          '        PF_WHERE = where or ""\n')

P2_NEW = ('    if PF_DEPTH == 1 then\n'
          '        PF_MS, PF_N = {}, {}\n'
          '        PF_SUB, PF_SET = {}, {}\n'
          '        PF_WHERE = where or ""\n')

# ── P3 pfEnd：多打两行（细分 + setter 计数）────────────────────────────────
P3_OLD = ('    if #cnt > 0 then pfOut("  └ " .. table.concat(cnt, " · ")) end\n'
          'end\n')

P3_NEW = ('    if #cnt > 0 then pfOut("  └ " .. table.concat(cnt, " · ")) end\n'
          '    -- ★ 细分：这几项**已经在「数据」里**（RowsRecipe 内部调用），只作分解展示，\n'
          '    --   **不相加**。「setter」是引擎 setter 的真实**调用次数**，单价另用\n'
          '    --   /dfprofperf bench 量（离线桩是空表，只能实机量）。\n'
          '    local sub = {}\n'
          '    for _, k in ipairs({ "扫描", "建spec", "列宽材料", "材料串", "单条spec" }) do\n'
          '        local e = PF_SUB and PF_SUB[k]\n'
          '        if e then sub[#sub + 1] = string.format("%s %d次/%.1f", k, e[1], e[2]) end\n'
          '    end\n'
          '    if #sub > 0 then pfOut("  └ 细分（已含在数据里）：" .. table.concat(sub, " · ")) end\n'
          '    local st = {}\n'
          '    for _, k in ipairs({ "SetText", "SetTextColor" }) do\n'
          '        local e = PF_SET and PF_SET[k]\n'
          '        if e then st[#st + 1] = string.format("%s %d次", k, e[1]) end\n'
          '    end\n'
          '    if #st > 0 then pfOut("  └ setter 调用：" .. table.concat(st, " · ")) end\n'
          'end\n')

# ── P4 PF_KIND：把「取名」拆成「总调用 / 真查」两项 ─────────────────────────
P4_OLD = 'local PF_KIND  = { "量宽", "量宽调用", "取名", "发包", "完整预热", "建行", "上数据" }\n'
P4_NEW = 'local PF_KIND  = { "量宽", "量宽调用", "取名", "取名(引擎)", "发包", "完整预热", "建行", "上数据" }\n'

# ── P5 插在 ① 之前：细分计时 + setter 计数（pfWrapAll 必须早于 Render 包装）──
P5_OLD = ('-- ① 事务边界：整帧 Render（入口层已在里面时只当内部层，不重复打印）\n')

P5_NEW = '''-- ④b 细分：这几项**已经在「数据」里**（RowsRecipe 内部调用），只作分解展示，
--     **不进 PF_ORDER、不相加** —— 上一版把嵌套段一起相加，数字整整翻倍。
--     ★ 只统计「调用发生在本次入口内」的部分；跨帧的分帧段另算。
local function pfSub(t, key, tag)
    if type(t) ~= "table" then return end
    local fn = t[key]
    if type(fn) ~= "function" then return end
    t[key] = function(...)
        if not PD.PERF or not PF_SUB then return fn(...) end
        local t0 = pfNow()
        local r = { fn(...) }
        local e = PF_SUB[tag]
        if e then e[1] = e[1] + 1; e[2] = e[2] + (pfNow() - t0)
        else PF_SUB[tag] = { 1, pfNow() - t0 } end
        return pfUnpack(r)
    end
end
pfSub(PD, "ScanRecipe",    "扫描")
pfSub(PD, "RecipeList",    "建spec")
pfSub(PD, "FitRecipeCols", "列宽材料")
pfSub(PD, "MatCol",        "材料串")
pfSub(PD, "RecipeSpec",    "单条spec")

-- ④c setter 计数：数「引擎 setter」被调了多少次。
--     ★ 只包 SetText / SetTextColor —— 这两样没有任何 hooksecurefunc 挂在上面，
--       覆盖实例方法不会破坏 ns.hui.SkinButton 的 SetSize → TryBuild 钩子。
--     ★ Button:SetText 是 C 函数、直接写 fontstring，**不经过** Lua 方法表 ⇒
--       同时包按钮与它的 fontstring 不会重复计数。
local function pfWrapSetter(obj, meth)
    if type(obj) ~= "table" then return end
    local fn = obj[meth]
    if type(fn) ~= "function" or obj["__dfw" .. meth] then return end
    obj["__dfw" .. meth] = true
    obj[meth] = function(self, ...)
        if PF_SET then
            local e = PF_SET[meth]
            if e then e[1] = e[1] + 1 else PF_SET[meth] = { 1 } end
        end
        return fn(self, ...)
    end
end
local function pfWrapEl(f)
    if type(f) ~= "table" then return end
    pfWrapSetter(f, "SetText")
    if type(f.GetFontString) == "function" then
        local ok, gs = pcall(f.GetFontString, f)
        if ok then
            pfWrapSetter(gs, "SetText")
            pfWrapSetter(gs, "SetTextColor")
        end
    end
end
local function pfWrapAll()
    for _, bt in pairs(PD.toolBtns or {}) do pfWrapEl(bt) end
    for _, bt in pairs(PD.subBtns or {}) do pfWrapEl(bt) end
    for _, bt in pairs(PD.navKey or {}) do pfWrapEl(bt) end
    local rows = PD.rows or {}
    for i = 1, #rows do
        local r = rows[i]
        if type(r) == "table" then
            for _, k in ipairs({ "a", "b", "c", "d", "e", "f", "dv", "tagFs" }) do
                pfWrapSetter(r[k], "SetText")
                pfWrapSetter(r[k], "SetTextColor")
            end
            for _, fs in pairs(r.mn or {}) do pfWrapSetter(fs, "SetText") end
        end
    end
end

-- ① 事务边界：整帧 Render（入口层已在里面时只当内部层，不重复打印）
'''

# ── P6 Render 包装：入口层先补包 setter（新行的 fontstring 会在下一帧被包上）──
P6_OLD = ('    PD.Render = function(...)\n'
          '        if not PD.PERF then return raw(...) end\n'
          '        pfBegin(PF_DEPTH == 0 and pfWhere() or nil)\n')

P6_NEW = ('    PD.Render = function(...)\n'
          '        if not PD.PERF then return raw(...) end\n'
          '        -- 入口层先补包 setter（新池化出来的行、其 fontstring 下一帧才包得上）\n'
          '        if PF_DEPTH == 0 then pfWrapAll() end\n'
          '        pfBegin(PF_DEPTH == 0 and pfWhere() or nil)\n')

# ── P7 计数区：把「取名」拆成总调用 + 真查 ─────────────────────────────────
P7_OLD = 'pfCount(DG, "ItemName",    "取名")\n'
P7_NEW = ('pfCount(PD, "ItemName",    "取名")       -- 总调用（含记忆化命中）\n'
          '-- ★ 必须包 DG.ItemInfo 而不是 DG.ItemName：PD.ItemName 内部调的是**加载期捕获**\n'
          '--   的局部 _origItemName，包 DG.ItemName 收不到数（恒 0 = 白测）。\n'
          '--   ItemInfo 才是真正落到 GetItemInfo(id) 的那一层 ⇒ 两项相除就是命中率。\n'
          'pfCount(DG, "ItemInfo",    "取名(引擎)")\n')

# ── P8 bench 子命令（插在最后的开关分支之前）───────────────────────────────
P8_OLD = ('        if PD.PERF then\n'
          '            PD.PERF = false\n')

P8_NEW = '''        if msg == "bench" then
            -- ★★ 微基准：量出实机里每个 setter 的**单价**（µs/次）。
            --    离线桩（lupa）把 setter 全换成纯 Lua 空表 ⇒ 单价只能实机量。
            --    有了单价，任何一段的「次数 × 单价」立刻能算出值不值得砍。
            if not (PD.built and PD.page) then
                pfOut("先打开专业页（/df zy）再 bench。")
                return
            end
            local save = PD.PERF
            PD.PERF = false                      -- 基准期间关探针，免得互相干扰
            local f = CreateFrame("Button", nil, PD.page)
            f:SetSize(160, 22)
            f:SetPoint("TOPLEFT", PD.page, "TOPLEFT", 0, 0)
            local fsb = f:CreateFontString()
            fsb:SetAllPoints()
            fsb:SetFont(ns.FONT, 12, "OUTLINE")
            f:SetFontString(fsb)
            f:Show()
            local N = 400
            local togg = true
            local function bench(name, fn)
                fn() fn()                        -- 预热
                local t0 = pfNow()
                for _ = 1, N do fn() end
                pfOut(string.format("  ▸ %-16s %7.2f µs/次", name, (pfNow() - t0) / N * 1000))
            end
            pfOut(string.format("setter 单价（各 %d 次；这是实机真实引擎调用）：", N))
            bench("SetText 中文", function() fsb:SetText("全部 511 条配方") end)
            bench("SetText 空串", function() fsb:SetText("") end)
            bench("SetTextColor", function() fsb:SetTextColor(1, 0.82, 0) end)
            bench("SetShown 切换", function() togg = not togg; f:SetShown(togg) end)
            bench("Clear+SetPoint", function()
                f:ClearAllPoints()
                f:SetPoint("TOPLEFT", PD.page, "TOPLEFT", 0, 0)
            end)
            bench("SetSize", function() f:SetSize(160, 22) end)
            bench("Show", function() f:Show() end)
            bench("Hide", function() f:Hide() end)
            f:Hide()
            PD.PERF = save
            pfOut("bench 完成 —— 把上面这组单价发我，配合「细分 / setter 调用」两行即可定位下一刀。")
            return
        end
        if PD.PERF then
            PD.PERF = false
'''

# ── P9 头部说明补 bench ────────────────────────────────────────────────────
P9_OLD = ('--      /dfprofperf scan   把所有专业挨个走一遍配方页，最后给排序表\n'
          '--      /dfprofperf off    直接关\n')

P9_NEW = ('--      /dfprofperf scan   把所有专业挨个走一遍配方页，最后给排序表\n'
          '--      /dfprofperf bench  微基准：量每个 setter 的实机单价（µs/次）\n'
          '--      /dfprofperf off    直接关\n'
          '--   ★ 每条报告会附两行分解：\n'
          '--      └ 细分（已含在数据里）：扫描 / 建spec / 列宽材料 / 材料串 / 单条spec\n'
          '--      └ setter 调用：SetText / SetTextColor 的**次数**（单价由 bench 给）\n')

EDITS = [
    ('P1 声明 PF_SUB/PF_SET', P1_OLD, P1_NEW),
    ('P2 pfBegin 重置', P2_OLD, P2_NEW),
    ('P3 pfEnd 多打两行', P3_OLD, P3_NEW),
    ('P4 PF_KIND 拆取名', P4_OLD, P4_NEW),
    ('P5 细分 + setter 装箱', P5_OLD, P5_NEW),
    ('P6 Render 入口补包', P6_OLD, P6_NEW),
    ('P7 计数拆取名', P7_OLD, P7_NEW),
    ('P8 bench 子命令', P8_OLD, P8_NEW),
    ('P9 头部说明', P9_OLD, P9_NEW),
]


def to_file_style(text, raw):
    if b'\r\n' in raw:
        return text.replace('\r\n', '\n').replace('\n', '\r\n')
    return text


def main():
    check = '--check' in sys.argv
    raw = open(TARGET, 'rb').read()
    src = raw.decode('utf-8')

    if SENTINEL in src:
        print('  [SKIP] 探针扩展已应用（哨兵命中）')
        return 0

    out = src
    bad = 0
    for name, old, new in EDITS:
        o, n = to_file_style(old, raw), to_file_style(new, raw)
        c_o, c_n = out.count(o), out.count(n)
        if c_n >= 1 and c_o == 0:
            print('  [SKIP] %-28s 已应用' % name)
            continue
        if c_o != 1:
            print('  [BAD ] %-28s 锚点 %d 次' % (name, c_o))
            bad += 1
            continue
        if c_n >= 1:
            print('  [BAD ] %-28s 替换串已存在 %d 次' % (name, c_n))
            bad += 1
            continue
        out = out.replace(o, n, 1)
        print('  [OK  ] %-28s 锚点 1 次' % name)

    if bad:
        print('  ✗ 有 %d 处未通过，未落盘' % bad)
        return 1
    if check:
        print('  [OK  ] 预检通过（未落盘）')
        return 0

    with open(TARGET, 'wb') as f:
        f.write(out.encode('utf-8'))
    print('  [OK  ] 已写入 %s（%+d 字节）' % (TARGET, len(out.encode('utf-8')) - len(raw)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
