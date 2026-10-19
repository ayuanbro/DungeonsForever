# -*- coding: utf-8 -*-
# 2026-10-10 三轮：信息卡跨签残留 + 快照单位修复(天→时分) + 购物清单价格到铜 + 币种图标
# ProfessionUI.lua = CRLF；ProfRouteAuto.lua = LF。全部二进制读写。
import re
import sys

PUI = 'Core/ProfessionUI.lua'
PRA = 'Core/ProfRouteAuto.lua'

UI_EDITS = []

# ---- U1) Render else 分支也调 PaintLvTiles（内部按 tab 隐藏，否则其它签残留）
UI_EDITS.append(('render-hide-tiles', '''    local toolH\r
    if PD.tab == "leveling" and not PD.setOpen then\r
        toolH = PD.PaintLvTiles() + PD.PaintTool(tool, handler, PD.LV_TILE_H + 6)\r
    else\r
        toolH = PD.PaintTool(tool, handler)\r
    end''',
'''    local toolH\r
    if PD.tab == "leveling" and not PD.setOpen then\r
        toolH = PD.PaintLvTiles() + PD.PaintTool(tool, handler, PD.LV_TILE_H + 6)\r
    else\r
        -- 其它签也要走一次 PaintLvTiles：内部会按 tab 隐藏信息卡（否则残留在其它签）\r
        toolH = PD.PaintLvTiles() + PD.PaintTool(tool, handler)\r
    end'''))

# ---- U2) 信息卡快照年龄：Auctionator Age API 返回「天」，旧代码当秒除 60 → 永远 0
UI_EDITS.append(('tile-age-calc', '''    local ageMin = s.snapshotAge\r
    ageMin = (ageMin and math.floor(ageMin / 60 + 0.5)) or 0\r''',
'''    -- Auctionator Age API 返回「天」（>21 天为 nil）；换算分钟后再分级显示\r
    local ageMin = s.snapshotAge and math.floor(s.snapshotAge * 1440 + 0.5) or nil\r'''))

# ---- U3) 快照卡显示：分钟/小时/天 分级 + 未知态
UI_EDITS.append(('tile-age-show', '''    tiles.snap.label:SetText(L["价格快照"])\r
    if s.priced then\r
        tiles.snap.val:SetText(format(L["%d 分钟前 · Auctionator"], ageMin))\r
        tiles.snap.val:SetTextColor(0.55, 0.85, 0.6, 1)\r
        TipOn(tiles.snap, { { format(L["价格快照 %d 分钟前（Auctionator）"], ageMin), 0.7, 0.7, 0.7 } })\r
    else\r
        tiles.snap.val:SetText(L["未接入 Auctionator"])\r
        tiles.snap.val:SetTextColor(0.95, 0.75, 0.4, 1)\r
        TipOn(tiles.snap, { { L["安装 Auctionator 并完成一次拍卖行扫描后，这里显示价格快照年龄。"],\r
                              0.7, 0.7, 0.7 } })\r
    end''',
'''    tiles.snap.label:SetText(L["价格快照"])\r
    local atxt\r
    if s.priced and ageMin then\r
        if ageMin < 90 then\r
            atxt = format(L["%d 分钟前 · Auctionator"], math.max(1, ageMin))\r
        elseif ageMin < 48 * 60 then\r
            atxt = format(L["%d 小时前 · Auctionator"], math.floor(ageMin / 60 + 0.5))\r
        else\r
            atxt = format(L["%d 天前 · Auctionator"], math.floor(ageMin / 1440 + 0.5))\r
        end\r
    elseif s.priced then\r
        atxt = L["快照年龄未知 · Auctionator"]\r
    end\r
    if atxt then\r
        tiles.snap.val:SetText(atxt)\r
        tiles.snap.val:SetTextColor(0.55, 0.85, 0.6, 1)\r
        TipOn(tiles.snap, { { atxt, 0.7, 0.7, 0.7 } })\r
    else\r
        tiles.snap.val:SetText(L["未接入 Auctionator"])\r
        tiles.snap.val:SetTextColor(0.95, 0.75, 0.4, 1)\r
        TipOn(tiles.snap, { { L["安装 Auctionator 并完成一次拍卖行扫描后，这里显示价格快照年龄。"],\r
                              0.7, 0.7, 0.7 } })\r
    end'''))

# ---- U4) 信息卡总花费 → 币种图标 + 到铜（与购物清单一致）
UI_EDITS.append(('cost-card-copper',
    '        tiles.cost.val:SetText(RA.MoneyStr(s.total))\r',
    '        tiles.cost.val:SetText(RA.MoneyStr(s.total, "copper"))\r'))

# ---- U5) 购物清单头部的快照年龄换算
UI_EDITS.append(('shop-age-calc', '''    local ageMin = data.snapshotAge\r
    ageMin = (ageMin and math.floor(ageMin / 60 + 0.5)) or 0\r''',
'''    -- Auctionator Age API 返回「天」；换算分钟，nil = 超过 21 天或从未见过\r
    local ageMin = data.snapshotAge and math.floor(data.snapshotAge * 1440 + 0.5) or nil\r'''))

# ---- U6) 购物清单快照行：分级 + 未知态
UI_EDITS.append(('shop-age-show',
    '''    PushText(rows, format(L["价格快照 %d 分钟前（Auctionator）"], ageMin), 11, C_GREY, 2)\r''',
    '''    if ageMin then\r
        local atxt\r
        if ageMin < 90 then\r
            atxt = format(L["价格快照 %d 分钟前（Auctionator）"], math.max(1, ageMin))\r
        elseif ageMin < 48 * 60 then\r
            atxt = format(L["价格快照 %d 小时前（Auctionator）"], math.floor(ageMin / 60 + 0.5))\r
        else\r
            atxt = format(L["价格快照 %d 天前（Auctionator）"], math.floor(ageMin / 1440 + 0.5))\r
        end\r
        PushText(rows, atxt, 11, C_GREY, 2)\r
    else\r
        PushText(rows, L["价格快照年龄未知（Auctionator）"], 11, C_GREY, 2)\r
    end\r'''))

RA_EDITS = []

# ---- R1) MAX_STALE 单位修正（原 48*3600 秒对着「天」比，陈旧过滤失效）
RA_EDITS.append(('max-stale-days',
    "local MAX_STALE = 48 * 3600      -- 价格快照年龄上限（秒），超过视为无价\n",
    "local MAX_STALE = 2              -- 价格快照年龄上限（天；Auctionator Age API 返回的就是「天」），超过视为无价\n"))

# ---- R2) MoneyStr：币种图标 + opt="copper" 到铜
RA_EDITS.append(('moneystr-icons', '''function RA.MoneyStr(copper)
    copper = tonumber(copper)
    if not copper or copper <= 0 then return format(L["%d银"], 0) end
    local totalSilver = math.floor(copper / 100 + 0.5)   -- 四舍五入到银
    local g = math.floor(totalSilver / 100)
    local s = totalSilver % 100
    if g > 0 then return format(L["%d金%02d银"], g, s) end
    return format(L["%d银"], s)
end
''',
'''-- 币种图标（|T|t 尺寸 0 = 跟随所在文本字号；2026-10-10 金/银/铜不用文字用图标）
local ICON_G = "|TInterface\\\\MoneyFrame\\\\UI-GoldIcon:0|t"
local ICON_S = "|TInterface\\\\MoneyFrame\\\\UI-SilverIcon:0|t"
local ICON_C = "|TInterface\\\\MoneyFrame\\\\UI-CopperIcon:0|t"

-- opt = "copper"：最小单位到铜（购物清单 / 花费卡）；默认抹到银（路线段落等保持紧凑）
function RA.MoneyStr(copper, opt)
    copper = tonumber(copper)
    if not copper or copper <= 0 then
        return (opt == "copper") and ("0" .. ICON_C) or ("0" .. ICON_S)
    end
    if opt == "copper" then
        local g = math.floor(copper / 10000)
        local s = math.floor(copper / 100) % 100
        local c = copper % 100
        if g > 0 then
            return format("%d%s%02d%s%02d%s", g, ICON_G, s, ICON_S, c, ICON_C)
        end
        return format("%d%s%02d%s", s, ICON_S, c, ICON_C)
    end
    local totalSilver = math.floor(copper / 100 + 0.5)   -- 四舍五入到银
    local g = math.floor(totalSilver / 100)
    local s = totalSilver % 100
    if g > 0 then return format("%d%s%02d%s", g, ICON_G, s, ICON_S) end
    return format("%d%s", s, ICON_S)
end
'''))

# ---- R3) MoneyStr 里的 L 键没了，若 L 再无他用则删掉 local L 防止 unused
def L_uses(src):
    return len(re.findall(r'\bL\["', src))

SHOP_LO, SHOP_HI = 2920, 3062   # 购物清单构建器行号区间（1-based，改前状态）


def ui_check(data):
    ok = True
    for name, old, new in UI_EDITS:
        c = data.count(old)
        if c != 1:
            print('MISS ui anchor %-16s count=%d' % (name, c))
            ok = False
        else:
            print('ok   ui anchor', name)
    return ok


def ra_check(data):
    ok = True
    for name, old, new in RA_EDITS:
        c = data.count(old)
        if c != 1:
            print('MISS ra anchor %-16s count=%d' % (name, c))
            ok = False
        else:
            print('ok   ra anchor', name)
    return ok


def check():
    ok = ui_check(open(PUI, encoding='utf-8', newline='').read())
    ok = ra_check(open(PRA, encoding='utf-8', newline='').read()) and ok
    # 购物清单区间 MoneyStr 计数应为 13
    lines = open(PUI, encoding='utf-8', newline='').read().split('\n')
    rng = ''.join(lines[SHOP_LO - 1:SHOP_HI])
    n = len(re.findall(r'RA\.MoneyStr\(([^()]*)\)', rng))
    print('shop-range MoneyStr count =', n, '(expect 13)')
    ok = ok and n == 13
    return ok


def apply():
    if not check():
        sys.exit('anchor check failed, abort')

    # 1) ProfessionUI：先按行号区间给购物清单的 MoneyStr 全部追加 "copper"
    src = open(PUI, encoding='utf-8', newline='').read()
    lines = src.split('\n')
    cnt = 0
    for i in range(SHOP_LO - 1, min(SHOP_HI, len(lines))):
        new, k = re.subn(r'RA\.MoneyStr\(([^()]*)\)', r'RA.MoneyStr(\1, "copper")', lines[i])
        if k:
            lines[i] = new
            cnt += k
    assert cnt == 13, cnt
    src = '\n'.join(lines)
    # 2) ProfessionUI：结构锚点替换
    for name, old, new in UI_EDITS:
        assert src.count(old) == 1, name
        src = src.replace(old, new, 1)
    open(PUI, 'w', encoding='utf-8', newline='').write(src)
    print('ProfessionUI: %d copper + %d edits' % (cnt, len(UI_EDITS)))

    # 3) ProfRouteAuto：锚点替换（LF）
    ra = open(PRA, encoding='utf-8', newline='').read()
    for name, old, new in RA_EDITS:
        assert ra.count(old) == 1, name
        ra = ra.replace(old, new, 1)
    print('L remaining uses =', L_uses(ra))
    if L_uses(ra) == 0:
        assert ra.count('local L = ns.L\n') == 1
        ra = ra.replace('local L = ns.L\n', '', 1)
        print('removed unused local L')
    open(PRA, 'w', encoding='utf-8', newline='').write(ra)
    print('ProfRouteAuto:', len(RA_EDITS), 'edits')


if __name__ == '__main__':
    if '--check' in sys.argv:
        check()
    else:
        apply()
