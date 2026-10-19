# -*- coding: utf-8 -*-
# 2026-10-10 六轮：快照时间用真扫描时间戳(秒) + NPC 卖店价不再被永久误缓存
# ProfRouteAuto.lua = LF；ProfessionUI.lua = CRLF。
import sys

PRA = 'Core/ProfRouteAuto.lua'
PUI = 'Core/ProfessionUI.lua'

RA_EDITS = []

# R1) NPC 卖店价：去掉「失败也缓存」的钉死 + 加产物预热
RA_EDITS.append(('npc-sell-cache',
'''local sellCache = {}   -- itemID → number | false（false = 取不到）
local function NPCSellPrice(id)
    if sellCache[id] ~= nil then return sellCache[id] or nil end
    local p
    if type(GetItemInfo) == "function" then
        local vals = { pcall(GetItemInfo, id) }
        if vals[1] then
            local sell = vals[12]   -- vals[1]=pcall ok，其后依次是 GetItemInfo 的返回值
            if type(sell) == "number" and sell > 0 then p = sell end
        end
    end
    sellCache[id] = p or false
    return p
end
''',
'''local sellCache = {}   -- itemID → number（只缓存成功值）
local function NPCSellPrice(id)
    if sellCache[id] then return sellCache[id] end
    local p
    if type(GetItemInfo) == "function" then
        local vals = { pcall(GetItemInfo, id) }
        if vals[1] then
            local sell = vals[12]   -- vals[1]=pcall ok，其后依次 GetItemInfo 返回值（第 11 项 = sellPrice）
            if type(sell) == "number" and sell > 0 then p = sell end
        end
    end
    -- ★ 只缓存成功值（2026-10-10）：物品数据是异步到货的，未加载时 GetItemInfo 返回 nil；
    --   若把 nil 钉进缓存，产物「直接卖给NPC收益」会永久停在 0。
    if p then sellCache[id] = p end
    return p
end

-- 产物 itemID 预热：走插件的物品加载通道，到货后 UI 重渲染即可取到卖店价
local function RequestProduct(id)
    local H = ns.ProfHost
    local dg = H and H.DG
    if dg and dg.RequestItem then pcall(dg.RequestItem, id) end
end

-- 真实价格快照时间（秒级）：Auctionator.SavedState 存的是 epoch 时间戳
-- （TimeOfLastGetAllScan / TimeOfLastReplicateScan / TimeOfLastBrowseScan）。
-- 取三者里最新 → time() - ts = 距上次扫描的秒数；取不到返回 nil（调用方回退天级）。
local function SnapshotSec()
    local A = Auctionator
    local st = (type(A) == "table") and A.SavedState
    if type(st) ~= "table" then return nil end
    local best
    for _, k in ipairs({ "TimeOfLastGetAllScan", "TimeOfLastReplicateScan", "TimeOfLastBrowseScan" }) do
        local v = tonumber(st[k])
        if v and v > 0 and (not best or v > best) then best = v end
    end
    if not best then return nil end
    local now = (type(time) == "function") and time() or 0
    local age = now - best
    if age < 0 then return nil end
    return age
end
'''))

# R2) SummarizeCore：产物预热
RA_EDITS.append(('product-request',
'''        local prod = rec and rec[2]
        if type(prod) == "number" then
            local outN = (st[4] or 0) * (rec[3] or 1)
            local ah = AHPrice(prod)
''',
'''        local prod = rec and rec[2]
        if type(prod) == "number" then
            local outN = (st[4] or 0) * (rec[3] or 1)
            RequestProduct(prod)   -- 异步预热产物物品（卖店价要等物品数据到货）
            local ah = AHPrice(prod)
'''))

# R3) Compute result（带注释那处先改，保证锚点唯一）
RA_EDITS.append(('compute-age',
'''        snapshotAge = priceCache.__minAge,   -- 最“新”价格快照的年龄（秒），可能为 nil
''',
'''        snapshotAge = SnapshotSec(),         -- 秒：真实扫描时间戳（TimeOfLast*Scan）
        snapshotDays = priceCache.__minAge,  -- 天：Auctionator 库内最近数据日差（回退用）
'''))

# R4) SummarizeSteps result（剩下的那处）
RA_EDITS.append(('summarize-age',
'''        snapshotAge = priceCache.__minAge,
''',
'''        snapshotAge = SnapshotSec(),
        snapshotDays = priceCache.__minAge,
'''))

UI_EDITS = []

# U1) 信息卡：快照年龄来源（秒优先 + 天回退）
UI_EDITS.append(('card-age-src',
'''    -- Auctionator Age API 返回「天」（>21 天为 nil）；换算分钟后再分级显示
    local ageMin = s.snapshotAge and math.floor(s.snapshotAge * 1440 + 0.5) or nil
''',
'''    -- 快照年龄：snapshotAge = 真实扫描时间戳算出的秒数（优先）；snapshotDays = 库内日差（回退）
    local snapSec, snapDays = s.snapshotAge, s.snapshotDays
'''))

# U2) 信息卡：显示分级（秒）
UI_EDITS.append(('card-age-show',
'''    if s.priced and ageMin then
        if ageMin < 90 then
            atxt = format(L["%d 分钟前 · Auctionator"], math.max(1, ageMin))
        elseif ageMin < 48 * 60 then
            atxt = format(L["%d 小时前 · Auctionator"], math.floor(ageMin / 60 + 0.5))
        else
            atxt = format(L["%d 天前 · Auctionator"], math.floor(ageMin / 1440 + 0.5))
        end
    elseif s.priced then
        atxt = L["快照年龄未知 · Auctionator"]
    end
''',
'''    if s.priced and snapSec then
        if snapSec < 90 * 60 then
            atxt = format(L["%d 分钟前 · Auctionator"], math.max(1, math.floor(snapSec / 60 + 0.5)))
        elseif snapSec < 48 * 3600 then
            atxt = format(L["%d 小时前 · Auctionator"], math.max(1, math.floor(snapSec / 3600 + 0.5)))
        else
            atxt = format(L["%d 天前 · Auctionator"], math.floor(snapSec / 86400 + 0.5))
        end
    elseif s.priced and snapDays then
        atxt = (snapDays <= 0) and L["今天 · Auctionator"]
               or format(L["%d 天前 · Auctionator"], snapDays)
    elseif s.priced then
        atxt = L["快照年龄未知 · Auctionator"]
    end
'''))

# U3) 购物清单：快照年龄来源
UI_EDITS.append(('shop-age-src',
'''    -- Auctionator Age API 返回「天」；换算分钟，nil = 超过 21 天或从未见过
    local ageMin = data.snapshotAge and math.floor(data.snapshotAge * 1440 + 0.5) or nil
''',
'''    -- 快照年龄：秒级真实扫描时间戳优先，天级库差回退
    local snapSec, snapDays = data.snapshotAge, data.snapshotDays
'''))

# U4) 购物清单：显示分级
UI_EDITS.append(('shop-age-show',
'''    if ageMin then
        local atxt
        if ageMin < 90 then
            atxt = format(L["价格快照 %d 分钟前（Auctionator）"], math.max(1, ageMin))
        elseif ageMin < 48 * 60 then
            atxt = format(L["价格快照 %d 小时前（Auctionator）"], math.floor(ageMin / 60 + 0.5))
        else
            atxt = format(L["价格快照 %d 天前（Auctionator）"], math.floor(ageMin / 1440 + 0.5))
        end
        PushText(rows, atxt, 11, C_GREY, 2)
    else
        PushText(rows, L["价格快照年龄未知（Auctionator）"], 11, C_GREY, 2)
    end
''',
'''    local atxt
    if snapSec then
        if snapSec < 90 * 60 then
            atxt = format(L["价格快照 %d 分钟前（Auctionator）"], math.max(1, math.floor(snapSec / 60 + 0.5)))
        elseif snapSec < 48 * 3600 then
            atxt = format(L["价格快照 %d 小时前（Auctionator）"], math.max(1, math.floor(snapSec / 3600 + 0.5)))
        else
            atxt = format(L["价格快照 %d 天前（Auctionator）"], math.floor(snapSec / 86400 + 0.5))
        end
    elseif snapDays then
        atxt = (snapDays <= 0) and L["价格快照：今天（Auctionator）"]
               or format(L["价格快照 %d 天前（Auctionator）"], snapDays)
    else
        atxt = L["价格快照年龄未知（Auctionator）"]
    end
    PushText(rows, atxt, 11, C_GREY, 2)
'''))

# U5) lvSummary 透传 snapshotDays（购物清单分支）
UI_EDITS.append(('summary-shop',
'''            total = data.total, snapshotAge = data.snapshotAge,
''',
'''            total = data.total, snapshotAge = data.snapshotAge,
            snapshotDays = data.snapshotDays,
'''))

# U6) lvSummary 透传 snapshotDays（路线分支）
UI_EDITS.append(('summary-route',
'''        snapshotAge = auto and res.snapshotAge or (fixedSum and fixedSum.snapshotAge),
''',
'''        snapshotAge = auto and res.snapshotAge or (fixedSum and fixedSum.snapshotAge),
        snapshotDays = auto and res.snapshotDays or (fixedSum and fixedSum.snapshotDays),
'''))

# U7) 物品到货后：清自动路线缓存，让 NPC 价/快照重算
UI_EDITS.append(('sweep-invalidate',
'''    PD.notReady = nil
    if got then PD.Render() end
    PD.sweeping = false
''',
'''    PD.notReady = nil
    if got then
        -- 物品数据到货：清自动路线缓存，使产物卖店价 / 价格快照重算（异步数据 2026-10-10）
        if RA then RA.Invalidate() end
        PD.Render()
    end
    PD.sweeping = false
'''))


def check_ra(data):
    ok = True
    for name, old, new in RA_EDITS:
        c = data.count(old)
        if c != 1:
            print('MISS ra %-16s count=%d' % (name, c)); ok = False
        else:
            print('ok   ra', name)
    return ok


def crlf(s):
    # ProfessionUI.lua 是 CRLF；模式串用 \n 书写，替换前归一化（幂等：先归一成 \n 再转 CRLF）
    return s.replace('\r\n', '\n').replace('\n', '\r\n')


def check_ui(data):
    ok = True
    for name, old, new in UI_EDITS:
        c = data.count(crlf(old))
        if c != 1:
            print('MISS ui %-16s count=%d' % (name, c)); ok = False
        else:
            print('ok   ui', name)
    return ok


def check():
    ok = check_ra(open(PRA, encoding='utf-8', newline='').read())
    ok = check_ui(open(PUI, encoding='utf-8', newline='').read()) and ok
    return ok


def apply():
    if not check():
        sys.exit('anchor check failed, abort')
    ra = open(PRA, encoding='utf-8', newline='').read()
    for name, old, new in RA_EDITS:
        ra = ra.replace(old, new, 1)
    open(PRA, 'w', encoding='utf-8', newline='').write(ra)
    ui = open(PUI, encoding='utf-8', newline='').read()
    for name, old, new in UI_EDITS:
        ui = ui.replace(crlf(old), crlf(new), 1)
    open(PUI, 'w', encoding='utf-8', newline='').write(ui)
    print('applied ra=%d ui=%d' % (len(RA_EDITS), len(UI_EDITS)))
    for p in (PRA, PUI):
        d = open(p, 'rb').read()
        print(p, 'CRLF:', d.count(b'\r\n'), 'bare LF:', d.count(b'\n') - d.count(b'\r\n'))


if __name__ == '__main__':
    if '--check' in sys.argv:
        check()
    else:
        apply()
