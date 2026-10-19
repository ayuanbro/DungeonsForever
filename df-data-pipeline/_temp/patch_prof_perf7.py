#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""patch_prof_perf7.py
  配方页「点开那一瞬间」第五刀 —— 只做「口径一字不变、调用变少」。

  实机证据（/dfprofperf，2026-10-09）：
    点开「制皮·recipe」  363.3ms → 上一刀（按需轻量请求）后 79.8ms
    剩余分解：数据 37.3 · 工具行 25.5 · 铺行 7.6 · 导航 4.1 · 请求 3.1
    计数：取名(DG.ItemName) 2228次/16.3ms · 量宽 1189次 · 量宽调用 3090次

  ★★ 关键认知：离线（lupa 桩把 GetStringWidth / CreateFrame / GetItemInfo / 发包
     全换成纯 Lua 空表）**永远看不到这笔钱** —— 它全在「引擎调用」上。
     所以本刀只砍两样东西：① 引擎调用的**次数** ② 纯 Lua 的重复计算。

  E1  PD.ItemName 事务内记忆化（DG.ItemName → GetItemInfo 零缓存）
  E2  本文件 26 处 DG.ItemName( → PD.ItemName(（不动 DungeonUI，不动 DG.ItemName 本身）
  E3  PD.Fit 先走记忆化量宽早退（ns.hui.Fit 内部那次量宽是**未记忆化**的原始 TextW）
  E4  setter 去重闸：PickNav / PickTabs / PaintTool —— 值没变就一个 setter 都不写
  E5  文件头纪律说明补一条

  ★ 幂等：哨兵命中即整体 SKIP。--check 只预检不落盘（但会做替换计数校验）。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.normpath(os.path.join(HERE, '..', 'Core', 'ProfessionUI.lua'))

SENTINEL = '★★ 物品名事务内记忆化（2026-10-09 第五轮'

# ── E1：PD.Fit 早退 + 物品名记忆化（插在 PD.Fit 定义处）───────────────────────
E1_OLD = 'PD.Fit = function(text, fs, width) return ns.hui.Fit(text, fs, width) end\n'
E1_NEW = '''PD.Fit = function(text, fs, width)
    -- ★ 先走**记忆化**量宽做早退（2026-10-09 第五轮）：ns.hui.Fit 内部那次量宽是
    --   **未记忆化**的原始 ns.hui.TextW；配方页一帧要对 300 条逐条 Fit，绝大多数
    --   文本根本不用裁 ⇒ 早退掉即可（结果与原来逐字等价）。
    if PD.TextW(text, fs) <= width then return text end
    return ns.hui.Fit(text, fs, width)
end

-- ★★ 物品名事务内记忆化（2026-10-09 第五轮；实机 /dfprofperf：取名 2228 次/16.3ms）
--   DG.ItemName → DG.ItemInfo → GetItemInfo(id) 是**零缓存**的真实引擎调用
--   （Core/DungeonUI.lua:1873）。一页配方 2228 次里绝大多数是**同一种材料反复查**。
--   一次 Render 是同步执行、中间没有任何异步插入 ⇒ 同一个 id 的名字不可能变，
--   按 id 记忆化绝对安全。Render 开头清空（PD.ResetItemNameMemo）；物品到货后的
--   重扫（PD.SweepNames → PD.Render）自然拿到新名字。
--   ★ 只替换**配方页热路径**的 7 处调用点（一页 2000+ 次）。其它页面（升级 / 采集 /
--     营地 / 图纸行…）调用量小，绕记忆表没有收益；而且 harness 把它们的调用**写法**
--     钉死了（改了就是误伤断言，不是回归）。
local _nmMemo, _nmN = {}, 0
function PD.ResetItemNameMemo()
    _nmMemo, _nmN = {}, 0
end
function PD.ItemName(id)
    if id == nil then return L["暂时没有客户端数据"], false end
    local c = _nmMemo[id]
    if c then return c[1], c[2] end
    -- ★ 动态取 DG.ItemName（**不要**在加载期抓成局部）：探针会在运行期替换
    --   DG.ItemName 来造态，抓成局部就把桩绕过了（离线审计探针会因此变哑）。
    --   ⚠️ 这一行是本文件唯一一处**故意**保留的 `DG.ItemName(` —— 别用全局替换。
    local nm, got = DG.ItemName(id)
    if _nmN >= 8192 then _nmMemo, _nmN = {}, 0 end
    _nmMemo[id] = { nm, got }
    _nmN = _nmN + 1
    return nm, got
end
'''

# ── E3：PD.Render 开头清空记忆表 ────────────────────────────────────────────
E3_OLD = ('function PD.Render()\n'
          '    if not (PD.built and PD.page) or not PD.cur then return end\n'
          '    PD.PickNav()\n')

E3_NEW = ('function PD.Render()\n'
          '    if not (PD.built and PD.page) or not PD.cur then return end\n'
          '    -- ★ 每次渲染清空物品名记忆表（同一次渲染内名字不会变；到货后的重扫会再清）\n'
          '    PD.ResetItemNameMemo()\n'
          '    PD.PickNav()\n')

# ── E4a：PickNav 签名闸 ─────────────────────────────────────────────────────
E4A_OLD = ('    local function paint(bt, sel, lv)\n'
           '        SetOutline(bt, sel, 1, 0.82, 0)\n')

E4A_NEW = ('    local function paint(bt, sel, lv)\n'
           '        -- ★ 签名不变就整颗按钮都不重画（见文件头 setter 去重说明）：换专业时\n'
           '        --   只有「旧选中 + 新选中」两颗真的变了，其余十几颗原样却重写了一遍 setter。\n'
           '        local key = (sel and "1" or "0") .. "|" .. (lv and (lv.cur .. "/" .. lv.max) or "")\n'
           '        if bt.__pnKey == key then return end\n'
           '        bt.__pnKey = key\n'
           '        SetOutline(bt, sel, 1, 0.82, 0)\n')

# ── E4b：PickTabs 签名闸 ────────────────────────────────────────────────────
E4B_OLD = '''    local shown = 0
    for _, def in ipairs(DG.PROF_SUBTABS) do
        local bt = PD.subBtns[def.key]
        local on = PD.avail[def.key] and true or false
        bt:SetShown(on)
        if on then
            bt:ClearAllPoints()
            bt:SetPoint("TOPLEFT", PD.page, "TOPLEFT",
                        PD.RIGHT_X + shown * PD.SUB_STEP, -PD.SUB_Y)
            shown = shown + 1
            if def.key == "camp" and PD.cur == "camping" then
                bt:SetText(L["职业加成"])
            else
                bt:SetText(def.text)
            end
            local sel = (not PD.setOpen) and (def.key == PD.tab)
            SetOutline(bt, sel, 1, 0.82, 0)
            bt:GetFontString():SetTextColor(Unpack(sel and C_GOLD or C_GREY))
        end
    end
'''

E4B_NEW = '''    local shown = 0
    for _, def in ipairs(DG.PROF_SUBTABS) do
        local bt = PD.subBtns[def.key]
        local on = PD.avail[def.key] and true or false
        local txt = (def.key == "camp" and PD.cur == "camping")
                    and L["职业加成"] or def.text
        local sel = (not PD.setOpen) and (def.key == PD.tab)
        -- ★ 签名 = 显隐 + 落位序 + 选中 + 文案；四项都没变就一个 setter 都不写。
        local key = (on and "1" or "0") .. "|" .. shown .. "|"
                    .. (sel and "1" or "0") .. "|" .. txt
        if bt.__ptKey ~= key then
            bt.__ptKey = key
            bt:SetShown(on)
            if on then
                bt:ClearAllPoints()
                bt:SetPoint("TOPLEFT", PD.page, "TOPLEFT",
                            PD.RIGHT_X + shown * PD.SUB_STEP, -PD.SUB_Y)
                if def.key == "camp" and PD.cur == "camping" then
                    bt:SetText(L["职业加成"])
                else
                    bt:SetText(def.text)
                end
                SetOutline(bt, sel, 1, 0.82, 0)
                bt:GetFontString():SetTextColor(Unpack(sel and C_GOLD or C_GREY))
            end
        end
        if on then shown = shown + 1 end
    end
'''

# ── E4c：PaintTool 签名闸 ───────────────────────────────────────────────────
E4C_OLD = '''        if def then
            local w, text = PD.ToolSize(def.text)
            local lim = PD.RIGHT_W - ((row == 0) and PD.SearchReserve() or 0)
            if x > 0 and x + w > lim then row = row + 1; x = 0 end
            bt:SetSize(w, PD.TOOL_H)
            bt:ClearAllPoints()
            bt:SetPoint("TOPLEFT", PD.page, "TOPLEFT", PD.RIGHT_X + x,
                        -(PD.BODY_TOP + yoff + row * (PD.TOOL_H + PD.TOOL_GAP)))
            bt:SetText(text)
            bt.__key = def.key
            SetOutline(bt, def.on and true or false, 1, 0.82, 0)
            bt:GetFontString():SetTextColor(Unpack(def.on and C_GOLD or C_GREY))
            bt:Show()
            x = x + w + (def.gap or PD.TOOL_GAP)
        else
            bt:Hide()
            bt.__key = nil
        end
'''

E4C_NEW = '''        if def then
            local w, text = PD.ToolSize(def.text)
            local lim = PD.RIGHT_W - ((row == 0) and PD.SearchReserve() or 0)
            if x > 0 and x + w > lim then row = row + 1; x = 0 end
            -- ★ 签名进「尺寸 + 落点 x + 行号 + 文案 + 选中」。落点 x 也必须进：
            --   前面任意一颗按钮变宽都会把后面所有按钮整体推挤一位。
            local key = "1|" .. w .. "|" .. x .. "|" .. row .. "|"
                        .. tostring(def.on) .. "|" .. text
            if bt.__ptk ~= key then
                bt.__ptk = key
                bt:SetSize(w, PD.TOOL_H)
                bt:ClearAllPoints()
                bt:SetPoint("TOPLEFT", PD.page, "TOPLEFT", PD.RIGHT_X + x,
                            -(PD.BODY_TOP + yoff + row * (PD.TOOL_H + PD.TOOL_GAP)))
                bt:SetText(text)
                SetOutline(bt, def.on and true or false, 1, 0.82, 0)
                bt:GetFontString():SetTextColor(Unpack(def.on and C_GOLD or C_GREY))
                bt:Show()
            end
            bt.__key = def.key
            x = x + w + (def.gap or PD.TOOL_GAP)
        else
            if bt.__ptk ~= "0" then bt.__ptk = "0"; bt:Hide() end
            bt.__key = nil
        end
'''

# ── E5：文件头纪律说明 ──────────────────────────────────────────────────────
E5_OLD = ('--   · 一切「显示/隐藏」都走 SetShown，绝不 SetParent(nil)、绝不重建 scroll child\n'
          '--     （ScrollFrame 内部持有旧 child 指针，卸载会 ACCESS_VIOLATION，副本页踩过）。\n')

E5_NEW = ('--   · 一切「显示/隐藏」都走 SetShown，绝不 SetParent(nil)、绝不重建 scroll child\n'
          '--     （ScrollFrame 内部持有旧 child 指针，卸载会 ACCESS_VIOLATION，副本页踩过）。\n'
          '--   · ★★ setter 去重（2026-10-09 第五轮）：实机 /dfprofperf 证明「离线 5.8ms、\n'
          '--     实机 79.8ms」的差距全在**引擎调用**上 —— SetText（带 CJK 文本）/ SetPoint /\n'
          '--     SetShown / SetTextColor 每次都是真调用，而离线桩全是纯 Lua 空表。\n'
          '--     页签 / 工具行 / 导航每帧整排重画，绝大多数按钮**什么都没变** ⇒ 一律先比\n'
          '--     签名（`bt.__pnKey` / `bt.__ptKey` / `bt.__ptk`），没变就一个 setter 都不写。\n'
          '--     另：PD.ItemName = DG.ItemName 的**事务内记忆化**（Render 开头清空）。\n')

EDITS = [
    ('E1 PD.Fit 早退 + PD.ItemName', E1_OLD, E1_NEW),
    ('E3 Render 开头清记忆表', E3_OLD, E3_NEW),
    ('E4a PickNav 签名闸', E4A_OLD, E4A_NEW),
    ('E4b PickTabs 签名闸', E4B_OLD, E4B_NEW),
    ('E4c PaintTool 签名闸', E4C_OLD, E4C_NEW),
    ('E5 文件头说明', E5_OLD, E5_NEW),
]

# E2：只改**配方页热路径**那 7 处（用带上下文的锚点保证唯一 + 逐条计数校验）
E2_SITES = [
    ('MatCol  材料列取名',
     '        local name = DG.ItemName(m[1])\n'
     '        local cw = PD.TextW(cnt, fs) + px + PD.TextW(name, fs)\n',
     '        local name = PD.ItemName(m[1])\n'
     '        local cw = PD.TextW(cnt, fs) + px + PD.TextW(name, fs)\n'),
    ('SearchHit 材料命中',
     '        local nm = tostring(DG.ItemName(m[1]) or "")\n',
     '        local nm = tostring(PD.ItemName(m[1]) or "")\n'),
    ('RecipeSpec 成品名',
     '        text = DG.ItemName(r[2]),\n'
     '        sub = tostring(r[5] or ""),\n',
     '        text = PD.ItemName(r[2]),\n'
     '        sub = tostring(r[5] or ""),\n'),
    ('RawHit 成品名',
     '    local nm = DG.ItemName(r[2])\n'
     '    if nm and nm ~= "" and string.find(string.lower(tostring(nm)), q, 1, true) then\n',
     '    local nm = PD.ItemName(r[2])\n'
     '    if nm and nm ~= "" and string.find(string.lower(tostring(nm)), q, 1, true) then\n'),
    ('RawHit 材料名',
     '        local mn = DG.ItemName(m[1])\n',
     '        local mn = PD.ItemName(m[1])\n'),
    ('ScanRecipe 全量名宽',
     '                local nm = DG.ItemName(r[2])\n'
     '                local w = (nm and nm ~= "" and PD.TextW(nm, 13)) or 0\n',
     '                local nm = PD.ItemName(r[2])\n'
     '                local w = (nm and nm ~= "" and PD.TextW(nm, 13)) or 0\n'),
    ('RequestRows 到货判据',
     '        local hasName = select(2, DG.ItemName(id))\n',
     '        local hasName = select(2, PD.ItemName(id))\n'),
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
        print('  [SKIP] 第五刀已应用（哨兵命中）')
        return 0

    out = src
    bad = 0
    for name, old, new in EDITS:
        o, n = to_file_style(old, raw), to_file_style(new, raw)
        c_o, c_n = out.count(o), out.count(n)
        if c_n == 1 and c_o == 0:
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

    # E2：配方页热路径 7 处调用点（计数校验，防止并行会话漂移后静默少改/多改）
    for name, old, new in E2_SITES:
        o, n = to_file_style(old, raw), to_file_style(new, raw)
        c_o, c_n = out.count(o), out.count(n)
        if c_n == 1 and c_o == 0:
            print('  [SKIP] %-28s 已应用' % ('E2 ' + name))
            continue
        if c_o != 1:
            print('  [BAD ] %-28s 锚点 %d 次' % ('E2 ' + name, c_o))
            bad += 1
            continue
        out = out.replace(o, n, 1)
        print('  [OK  ] %-28s 锚点 1 次' % ('E2 ' + name))

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
