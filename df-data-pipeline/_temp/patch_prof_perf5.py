#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""patch_prof_perf5.py
  给 Core/ProfessionUI.lua 末尾追加「点开耗时打印」探针（/dfprofperf）。

  为什么不再猜：离线桩（lupa）把 GetStringWidth / CreateFrame / GetItemInfo /
  发包全换成了纯 Lua 查表 —— 离线量到的整帧 4.7ms 与实机手感不是一回事。
  真实卡顿只会落在「真实 API」上。这个探针在游戏里把一次点击拆成
  9 段计时 + 5 项调用计数，直接打在聊天框。

  ★ 只追加、不动任何既有行（包函数全在运行期做），对并行会话零冲突。
  ★ 幂等：哨兵命中即 SKIP。--check 只预检不落盘。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.normpath(os.path.join(HERE, '..', 'Core', 'ProfessionUI.lua'))

SENTINEL = '-- ══ 点开耗时打印（/dfprofperf）'

OLD = '''if type(SlashCmdList) == "table" then
    SLASH_DUNGEONSFOREVERPROFGATE1 = "/dfprofgate"
    SlashCmdList["DUNGEONSFOREVERPROFGATE"] = function()
        if PD.DEMO_SAVE then
            PD.EndGateDemo()
            print("|cff46bf72[无限副本手册]|r " .. L["已还原。"])
            return
        end
        if not PD.built or not PD.cur then
            print("|cff46bf72[无限副本手册]|r "
                  .. L["先打开一个专业的配方页，再运行这个命令。"])
            return
        end
        PD.StartGateDemo()
        print("|cff46bf72[无限副本手册]|r "
              .. L["演示：每帧只建 2 行，进度条会走完一遍。"])
    end
end
'''

PROBE = '''
-- ══ 点开耗时打印（/dfprofperf） ═══════════════════════════════════════════
--   ★★ 为什么必须在游戏里量：离线桩（lupa）把 GetStringWidth / CreateFrame /
--      GetItemInfo / 发包全换成了纯 Lua 查表 ⇒ 离线量到的整帧 4.7ms 与实机手感
--      根本不是一回事。真实卡顿只落在「真实 API」上 —— 字体测量走引擎 C 调用、
--      建帧走引擎内存分配、物品名要查客户端缓存、发包要走网络层。
--   ★ 做法：全部在**运行期包函数**，不往 PD.Render 函数体里插一行
--      （并行会话正在改这个文件，动函数体最容易撞车）。
--      一次点击 = 9 段计时 + 6 项调用计数：
--        次数大 ⇒ 该减少调用（省）；单次贵 ⇒ 该换做法（改）。
--   ★ 默认开，但只打「慢过 PD.PERF_MIN」的那一次（正常点不刷屏）。
--      /dfprofperf        开/关
--      /dfprofperf all    连很快的也打
--      /dfprofperf scan   把所有专业挨个走一遍配方页，最后给排序表
--      /dfprofperf off    直接关
PD.PERF     = true
PD.PERF_MIN = 6

local pfUnpack = unpack
if not pfUnpack and type(table) == "table" then pfUnpack = table.unpack end
if not pfUnpack then pfUnpack = function(t) return t[1] end end

local PF_DEPTH, PF_MS, PF_N, PF_WHERE = 0, nil, nil, ""
local PF_TAIL = nil
local PF_SCAN = nil
-- ★★ 只放「Render 顶层」调用的段！ScanRecipe / FitRecipeCols 是在 RowsRecipe
--    内部被调的 ⇒ 它们的时间**已经在「数据」里**，再单列一次就是重复计数
--    （第一版就踩了：实机打出「数据 40.7 + 扫描 10.8 + 列宽 21.7」其实前一项已含后两项）。
local PF_ORDER = { "导航", "数据", "工具行", "信息卡", "布局", "铺行", "开关", "请求" }
-- 「量宽」= ns.hui.TextW（真·引擎字体测量，记忆化**命中不算**）；
-- 「量宽调用」= PD.TextW（含记忆化命中）⇒ 两个一起看能算出缓存命中率。
-- 「完整预热」= DG.RequestItem（掉落页那套：建 tooltip + CreateFromItemID）；
-- 「发包」= C_Item.RequestLoadItemDataByID（只请求载入）。
local PF_KIND  = { "量宽", "量宽调用", "取名", "发包", "完整预热", "建行", "上数据" }

local function pfNow()
    if type(debugprofilestop) == "function" then return debugprofilestop() end
    if type(GetTime) == "function" then return GetTime() * 1000 end
    return 0
end

local function pfOut(s) print("|cff46bf72[DF性能]|r " .. s) end

local function pfBegin(where)
    PF_DEPTH = PF_DEPTH + 1
    if PF_DEPTH == 1 then
        PF_MS, PF_N = {}, {}
        PF_WHERE = where or ""
        local t = PF_TAIL
        if t then
            PF_TAIL = nil
            pfOut(string.format("  └ 顺上一次的分帧段：%d 帧 / %.1fms / %d 行",
                                t.frames, t.ms, t.rows))
        end
    end
end

local function pfTick(tag, t0)
    if PF_MS then PF_MS[tag] = (PF_MS[tag] or 0) + (pfNow() - t0) end
end

local function pfHit(tag, dt)
    if not PF_N then return end
    local e = PF_N[tag]
    if e then e[1] = e[1] + 1; e[2] = e[2] + (dt or 0)
    else PF_N[tag] = { 1, dt or 0 } end
end

local function pfEnd()
    PF_DEPTH = PF_DEPTH - 1
    if PF_DEPTH > 0 then return end
    local ms, n, where = PF_MS, PF_N, PF_WHERE
    PF_MS, PF_N = nil, nil
    if not ms then return end
    local total, other = 0, 0
    local floor = (PD.PERF == "all") and -1 or 0.05
    local parts, seen = {}, {}
    for _, k in ipairs(PF_ORDER) do
        seen[k] = true
        local v = ms[k]
        if v and v >= floor then
            total = total + v
            parts[#parts + 1] = string.format("%s %.1f", k, v)
        end
    end
    for k, v in pairs(ms) do
        if not seen[k] and k ~= "入口" then other = other + v end
    end
    -- ★★ 「入口」= 整次点击的 wall time，它**已经包含**下面各段 ⇒ 绝不能和分解相加。
    --    第一版两者相加，实机打出 757.8ms（真值 363.3ms），数字整整翻了一倍。
    local entry = ms["入口"]
    local grand = entry or (total + other)

    if PD.PERF == "scan" then
        PF_SCAN = PF_SCAN or {}
        PF_SCAN[#PF_SCAN + 1] = { where ~= "" and where or "?", grand, entry }
        return
    end
    if PD.PERF ~= "all" and grand < (PD.PERF_MIN or 6) then return end

    local head = string.format("%.1fms  %s", grand, where ~= "" and where or "?")
    if other >= 0.05 then head = head .. string.format("  （未归类 %.1f）", other) end
    pfOut(head)
    if #parts > 0 then pfOut("  └ " .. table.concat(parts, " · ")) end
    local cnt = {}
    for _, k in ipairs(PF_KIND) do
        local e = n[k]
        if e then cnt[#cnt + 1] = string.format("%s %d次/%.1fms", k, e[1], e[2]) end
    end
    if #cnt > 0 then pfOut("  └ " .. table.concat(cnt, " · ")) end
end

local function pfTime(t, key, tag)
    if type(t) ~= "table" then return end
    local fn = t[key]
    if type(fn) ~= "function" then return end
    t[key] = function(...)
        if not PD.PERF then return fn(...) end
        local t0 = pfNow()
        local r = { fn(...) }
        pfTick(tag or key, t0)
        return pfUnpack(r)
    end
end

local function pfCount(t, key, tag)
    if type(t) ~= "table" then return end
    local fn = t[key]
    if type(fn) ~= "function" then return end
    t[key] = function(...)
        if not PD.PERF then return fn(...) end
        local t0 = pfNow()
        local r = { fn(...) }
        pfHit(tag or key, pfNow() - t0)
        return pfUnpack(r)
    end
end

local function pfWhere()
    local who = PD.cur or "?"
    local bt = PD.navKey and PD.navKey[who]
    if bt and type(bt.GetText) == "function" then
        local s = bt:GetText()
        if type(s) == "string" and s ~= "" then who = s end
    end
    return string.format("「%s·%s」", tostring(who),
                         PD.setOpen and "设置" or tostring(PD.tab or "?"))
end

local function pfEntry(key, label)
    local fn = PD[key]
    if type(fn) ~= "function" then return end
    PD[key] = function(...)
        if not PD.PERF then return fn(...) end
        pfBegin(label)
        local t0 = pfNow()
        local r = { fn(...) }
        -- ★ 只有最外层入口才记 wall time + 取位置：
        --   ① 嵌套时 PF_DEPTH > 1，再 tick 一次会把「入口」double count；
        --   ② 位置要**干完再取** —— 此刻 PD.cur / PD.tab 才是新的
        --      （进函数前取只会拿到上一个页签，等于没告诉你卡在哪个专业）。
        if PF_DEPTH == 1 then
            pfTick("入口", t0)
            PF_WHERE = label .. " " .. pfWhere()
        end
        pfEnd()
        return pfUnpack(r)
    end
end

-- ① 事务边界：整帧 Render（入口层已在里面时只当内部层，不重复打印）
do
    local raw = PD.Render
    PD.Render = function(...)
        if not PD.PERF then return raw(...) end
        pfBegin(PF_DEPTH == 0 and pfWhere() or nil)
        local ok, e = pcall(raw, ...)
        pfEnd()
        if not ok then error(e, 0) end
    end
end

-- ② 分帧段（落在 Render 之后的新帧里，单独攒，下次点击时补报）
do
    local raw = PD.BuildPendRows
    if type(raw) == "function" then
        PD.BuildPendRows = function()
            if not PD.PERF then return raw() end
            local t0 = pfNow()
            local before = #(PD.__pendRows or {})
            local ok, e = pcall(raw)
            local after = #(PD.__pendRows or {})
            local t = PF_TAIL
            if not t then t = { frames = 0, ms = 0, rows = 0 }; PF_TAIL = t end
            t.frames = t.frames + 1
            t.ms = t.ms + (pfNow() - t0)
            if before > after then t.rows = t.rows + (before - after) end
            if not ok then error(e, 0) end
        end
    end
end

-- ③ 分段（只包 Render **顶层**调用的那些；ScanRecipe/FitRecipeCols 在 RowsRecipe 里面）
pfTime(PD, "PickNav",   "导航")
pfTime(PD, "PickTabs",  "导航")
pfTime(PD, "RowsRecipe",   "数据")
pfTime(PD, "RowsOverview", "数据")
pfTime(PD, "RowsGather",   "数据")
pfTime(PD, "RowsFishing",  "数据")
pfTime(PD, "RowsLeveling", "数据")
pfTime(PD, "RowsAutoShop", "数据")
pfTime(PD, "RowsCamp",     "数据")
pfTime(PD, "RowsLegacy",   "数据")
pfTime(PD, "RowsNotes",    "数据")
pfTime(PD, "RowsSettings", "数据")
pfTime(PD, "PaintLvTiles", "信息卡")
pfTime(PD, "PaintTool",    "工具行")
pfTime(PD, "RecipeTool",   "工具行")
pfTime(PD, "LevelTool",    "工具行")
pfTime(PD, "Layout",      "布局")
pfTime(PD, "PaintRows",   "铺行")
pfTime(PD, "PlaceSettingsToggles", "开关")
pfTime(PD, "RequestRows", "请求")

-- ④ 计数：真实引擎调用（这几项离线桩全是假的，正是实机与离线的差）
pfCount(ns.hui, "TextW",   "量宽")       -- 引擎字体测量（记忆化命中不算）
pfCount(PD, "TextW",       "量宽调用")   -- 含记忆化命中 ⇒ 两项相除 = 命中率
pfCount(DG, "ItemName",    "取名")
pfCount(DG, "RequestItem", "完整预热")   -- 掉落页那套（建 tooltip + CreateFromItemID）
if type(C_Item) == "table" then
    pfCount(C_Item, "RequestLoadItemDataByID", "发包")
end
pfCount(PD, "Row",         "建行")
pfCount(PD, "BindRow",     "上数据")

-- ⑤ 入口
pfEntry("Show",       "切专业")
pfEntry("SetTab",     "点页签")
pfEntry("Open",       "打开")
pfEntry("Refresh",    "刷新")
pfEntry("SweepNames", "物品到货重渲")

if type(SlashCmdList) == "table" then
    SLASH_DUNGEONSFOREVERPROFPERF1 = "/dfprofperf"
    SlashCmdList["DUNGEONSFOREVERPROFPERF"] = function(msg)
        msg = string.lower(tostring(msg or ""))
        msg = msg:gsub("^%s+", ""):gsub("%s+$", "")
        PF_DEPTH, PF_MS, PF_N, PF_TAIL = 0, nil, nil, nil
        if msg == "all" then
            PD.PERF = "all"
            pfOut("已开启：全部打印（含很快的）。/dfprofperf off 关闭。")
            return
        end
        if msg == "off" then
            PD.PERF = false
            pfOut("已关闭。")
            return
        end
        if msg == "scan" then
            if not (PD.built and PD.page) then
                pfOut("先打开专业页（/df zy）再 scan。")
                return
            end
            local save = PD.PERF
            PD.PERF = "scan"
            PF_SCAN = {}
            local n = 0
            for _, slug in ipairs(PD.navOrder or {}) do
                local r = R[slug]
                if r and ((r.rows and #r.rows > 0) or (r.enchants and #r.enchants > 0)
                          or (r.crafted and #r.crafted > 0)) then
                    PD.Show(slug)
                    PD.SetTab("recipe")
                    n = n + 1
                end
            end
            PD.PERF = save
            local list = PF_SCAN or {}
            table.sort(list, function(a, b) return a[2] > b[2] end)
            pfOut(string.format("扫描完成：%d 个专业 / %d 次渲染，按耗时排序 ——", n, #list))
            for i = 1, math.min(#list, 30) do
                pfOut(string.format("  %2d. %-26s %.1fms", i, list[i][1], list[i][2]))
            end
            return
        end
        if PD.PERF then
            PD.PERF = false
            pfOut("已关闭。")
        else
            PD.PERF = true
            pfOut(string.format("已开启：只打慢过 %dms 的。点几下配方页即可；"
                                .. "/dfprofperf all 连快的也打，scan 挨个专业跑一遍。",
                                PD.PERF_MIN or 6))
        end
    end
end
'''

NEW = OLD + PROBE


def to_file_style(text, raw):
    """把 text 的行尾改成 raw（字节）自身的风格：CRLF 文件里的裸 \\n 一律补成 \\r\\n。"""
    if b'\r\n' in raw:
        return text.replace('\r\n', '\n').replace('\n', '\r\n')
    return text


def main():
    check = '--check' in sys.argv
    raw = open(TARGET, 'rb').read()
    src = raw.decode('utf-8')

    old = to_file_style(OLD, raw)
    new = to_file_style(NEW, raw)

    if SENTINEL in src:
        print('  [SKIP] 探针已装上（哨兵命中）')
        return 0
    c_old = src.count(old)
    if c_old != 1:
        print('  [BAD ] 锚点 %d 次（应为 1）' % c_old)
        return 1

    out = src.replace(old, new, 1)
    if check:
        print('  [OK  ] 锚点 1 次；预检通过（未落盘）')
        return 0

    with open(TARGET, 'wb') as f:
        f.write(out.encode('utf-8'))
    print('  [OK  ] 已写入 %s（+%d 字节）' % (TARGET, len(out.encode('utf-8')) - len(raw)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
