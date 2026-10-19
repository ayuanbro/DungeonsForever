# -*- coding: utf-8 -*-
# 2026-10-10 用户：自动路线方案化（默认最省钱）+ 升级页「路线方案」卡第二位
# 三文件：ProfRouteAuto.lua(LF) / ProfessionUI.lua(CRLF) / ProfFollow.lua(LF)
import sys


class F:
    def __init__(self, path):
        self.path = path
        self.data = open(path, "rb").read()
        cr = self.data.count(b"\r\n")
        lf = self.data.count(b"\n") - cr
        self.eol = b"\r\n" if cr > lf else b"\n"

    def rep(self, old, new):
        e = self.eol
        o = old.encode("utf-8").replace(b"\n", e)
        n = new.encode("utf-8").replace(b"\n", e)
        c = self.data.count(o)
        assert c == 1, "%s: count=%d for %r" % (self.path, c, old[:70])
        self.data = self.data.replace(o, n)

    def save(self):
        open(self.path, "wb").write(self.data)
        print("patched", self.path)


# ══════════════════ Core/ProfRouteAuto.lua (LF) ══════════════════
ra = F(r"D:/workspace/DungeonsForever/Core/ProfRouteAuto.lua")

# R1 方案常量 + 公开顺序/标签
ra.rep(
    "local G_YELLOW, G_GREEN = 0.5, 0.05",
    """local G_YELLOW, G_GREEN = 0.5, 0.05

-- ── 自动路线方案（2026-10-10 用户：设置内可选，默认最省钱）────────────────────
--   cheapest = 材料+图纸价摊到每点（图纸一次性成本计入选型，修「关掉排除图纸反而
--   更贵」的隐形成本问题）；matcost = 旧口径（只看材料价）；crafts = 期望制作次数
--   最少（同分取便宜）；optim = 乐观计数（参考他站口径：1 次=1 点、变黄前 25 点
--   可学、排除冷却与未公开材料配方、材料按卖店基础价值比价、不依赖价格插件）。
local SCHEME_ORDER = { "cheapest", "matcost", "crafts", "optim" }
local SCHEME_LABEL = {
    cheapest = "最省钱",
    matcost = "材料成本",
    crafts = "次数最少",
    optim = "乐观计数",
}
function RA.SchemeOrder() return SCHEME_ORDER end
function RA.SchemeLabel(s)
    local k = (s and SCHEME_LABEL[s]) and SCHEME_LABEL[s] or "最省钱"
    return L[k]
end""",
)

# R2 ClientKnown（optim 排除未公开材料）
ra.rep(
    "-- 材料清单成本（2026-10-10 配方页「制作成本」列/提示框「成本」行共用）：",
    """-- 客户端是否已公开该物品（optim 方案排除「未公开物品」材料的配方）：
--   GetItemInfo 通道查无名字 = 未公开。物品数据异步到货，首开可能误判 ——
--   数据到货后自动路线缓存会失效重算（ProfessionUI 已有该钩子）。
local function ClientKnown(id)
    local dg = ns.ProfHost and ns.ProfHost.DG
    if dg and type(dg.ItemInfo) == "function" then
        return dg.ItemInfo(id) ~= nil
    end
    if C_Item and C_Item.GetItemInfo then
        return (C_Item.GetItemInfo(id)) ~= nil
    end
    return true
end

-- 材料清单成本（2026-10-10 配方页「制作成本」列/提示框「成本」行共用）：""",
)

# R3 方案相关判定助手
ra.rep(
    """local function Eligible(c, allowUnpriced)
    return allowUnpriced or not c.unpriced
end""",
    """local function Eligible(c, allowUnpriced)
    return allowUnpriced or not c.unpriced
end

-- 方案相关的可用/收益判定（2026-10-10 方案化改造）：
--   optim 用提前学习线 learnO（min(learn, 变黄前 25 点)）、收益恒 1（乐观口径）、
--   排除冷却配方（cat=Transmutes，月布/转化等）与材料未公开的配方；
--   其余方案走原口径（learn 阈值 + 期望概率插值）。
local function CanUse(scheme, c, cur)
    local lo = (scheme == "optim") and (c.learnO or c.learn) or c.learn
    return cur >= lo and cur < c.grey
end
local function Usable(scheme, c, cur, allowUnpriced)
    if (scheme == "optim") and (c.cd or c.unknown) then return false end
    if not Eligible(c, allowUnpriced) then return false end
    return CanUse(scheme, c, cur)
end
local function GainOf(scheme, c, cur)
    if not CanUse(scheme, c, cur) then return nil end
    if scheme == "optim" then return 1 end
    return Gain(cur, c)
end
local function MetricOf(scheme, c, g)
    if scheme == "cheapest" then return (c.cost + (c.fcost or 0)) / g end
    if scheme == "crafts" then return 1 / g end
    if scheme == "optim" then return (c.base or 0) / g end
    return c.cost / g
end""",
)

# R4 Simulate 签名
ra.rep(
    "local function Simulate(cands, start, cap, allowUnpriced)",
    "local function Simulate(cands, start, cap, allowUnpriced, scheme)",
)

# R5 Simulate 选优循环
ra.rep(
    """        local best, bestMetric
        for _, c in ipairs(cands) do
            if not banned[c.spell] and Eligible(c, allowUnpriced)
               and c.learn <= cur and c.grey > cur then
                local g = Gain(cur, c)
                if g then
                    local metric = c.cost / g
                    if not best or metric < bestMetric - 1e-9
                       or (metric < bestMetric + 1e-9 and c.grey > best.grey) then
                        best, bestMetric = c, metric
                    end
                end
            end
        end""",
    """        local best, bestMetric
        for _, c in ipairs(cands) do
            if not banned[c.spell] and Usable(scheme, c, cur, allowUnpriced) then
                local g = GainOf(scheme, c, cur)
                if g then
                    local metric = MetricOf(scheme, c, g)
                    if not best or metric < bestMetric - 1e-9
                       or (metric < bestMetric + 1e-9 and c.grey > best.grey) then
                        best, bestMetric = c, metric
                    end
                end
            end
        end""",
)

# R6 Simulate 缺口跳段
ra.rep(
    """            for _, c in ipairs(cands) do
                if not banned[c.spell] and Eligible(c, allowUnpriced)
                   and c.learn > cur and (not nxt or c.learn < nxt) then
                    nxt = c.learn
                end
            end""",
    """            for _, c in ipairs(cands) do
                if not banned[c.spell] and Usable(scheme, c, cur, allowUnpriced) then
                    local lo = (scheme == "optim") and (c.learnO or c.learn) or c.learn
                    if lo > cur and (not nxt or lo < nxt) then nxt = lo end
                end
            end""",
)

# R7 Simulate 段内切换检查
ra.rep(
    """                for _, c in ipairs(cands) do
                    if c ~= best and not banned[c.spell] and Eligible(c, allowUnpriced)
                       and c.learn <= cur and c.grey > cur then
                        local g2 = Gain(cur, c)
                        if g2 and c.cost / g2 < bestMetric - 1e-9 then
                            stop = true
                            break
                        end
                    end
                end""",
    """                for _, c in ipairs(cands) do
                    if c ~= best and not banned[c.spell] and Usable(scheme, c, cur, allowUnpriced) then
                        local g2 = GainOf(scheme, c, cur)
                        if g2 and MetricOf(scheme, c, g2) < bestMetric - 1e-9 then
                            stop = true
                            break
                        end
                    end
                end""",
)

# R8 SimulateRange 签名
ra.rep(
    "local function SimulateRange(cands, a, b)",
    "local function SimulateRange(cands, a, b, scheme)",
)

# R9 区间选优循环
ra.rep(
    """        local best, bestMetric
        for _, c in ipairs(cands) do
            if not banned[c.spell] and c.learn <= cur and c.grey > cur then
                local g = Gain(cur, c)
                if g then
                    local metric = c.cost / g
                    if not best or metric < bestMetric - 1e-9
                       or (metric < bestMetric + 1e-9 and c.grey > best.grey) then
                        best, bestMetric = c, metric
                    end
                end
            end
        end""",
    """        local best, bestMetric
        for _, c in ipairs(cands) do
            if not banned[c.spell] and CanUse(scheme, c, cur)
               and not ((scheme == "optim") and (c.cd or c.unknown)) then
                local g = GainOf(scheme, c, cur)
                if g then
                    local metric = MetricOf(scheme, c, g)
                    if not best or metric < bestMetric - 1e-9
                       or (metric < bestMetric + 1e-9 and c.grey > best.grey) then
                        best, bestMetric = c, metric
                    end
                end
            end
        end""",
)

# R10 区间缺口跳段
ra.rep(
    """            for _, c in ipairs(cands) do
                if not banned[c.spell] and c.learn > cur and c.learn <= b
                   and (not nxt or c.learn < nxt) then
                    nxt = c.learn
                end
            end""",
    """            for _, c in ipairs(cands) do
                if not banned[c.spell] and not ((scheme == "optim") and (c.cd or c.unknown)) then
                    local lo = (scheme == "optim") and (c.learnO or c.learn) or c.learn
                    if lo > cur and lo <= b and (not nxt or lo < nxt) then nxt = lo end
                end
            end""",
)

# R11 区间段内切换检查
ra.rep(
    """                for _, c in ipairs(cands) do
                    if c ~= best and not banned[c.spell]
                       and c.learn <= cur and c.grey > cur and cur <= b then
                        local g2 = Gain(cur, c)
                        if g2 and c.cost / g2 < bestMetric - 1e-9 then
                            stop = true
                            break
                        end
                    end
                end""",
    """                for _, c in ipairs(cands) do
                    if c ~= best and not banned[c.spell] and CanUse(scheme, c, cur)
                       and cur <= b and not ((scheme == "optim") and (c.cd or c.unknown)) then
                        local g2 = GainOf(scheme, c, cur)
                        if g2 and MetricOf(scheme, c, g2) < bestMetric - 1e-9 then
                            stop = true
                            break
                        end
                    end
                end""",
)

# R12 FillGaps 传 scheme
ra.rep(
    "local function FillGaps(cands, steps, gaps)",
    "local function FillGaps(cands, steps, gaps, scheme)",
)
ra.rep(
    "        local fills, resid = SimulateRange(cands, g[1], g[2])",
    "        local fills, resid = SimulateRange(cands, g[1], g[2], scheme)",
)

# R13 rows 候选补方案字段（fcost/base/cd/unknown/learnO）
ra.rep(
    """                if ok then
                    local itemID = rec[2]
                    cands[#cands + 1] = {
                        spell = spell, item = (type(itemID) == "number") and itemID or nil,
                        learn = learn, yellow = (type(yellow) == "number") and yellow or learn,
                        green = (type(green) == "number") and green or yellow or learn,
                        grey = grey, mats = reagents, cost = cost, unpriced = unpriced,
                    }
                    recOf[spell] = rec
                end""",
    """                if ok then
                    local itemID = rec[2]
                    -- 方案字段（2026-10-10）：fcost=图纸价（已学免费/取不到按 0，仅
                    --   cheapest 计入选型）；base=材料卖店基础价值合计（optim 比价/花费）；
                    --   cd=冷却配方（cat=Transmutes）；unknown=材料客户端未公开；
                    --   learnO=提前学习线（变黄前 25 点）
                    local f = rec[13]
                    local fcost = 0
                    if type(f) == "table" and type(f[1]) == "number" and not LearnKnown(spell) then
                        fcost = MatPrice(f[1], soldSet) or 0
                    end
                    local base, unknown = 0, false
                    for _, m in ipairs(reagents) do
                        if not ClientKnown(m[1]) then unknown = true end
                        local sp = NPCSellPrice(m[1])
                        if sp then base = base + sp * (m[2] or 1) end
                    end
                    local cY = (type(yellow) == "number") and yellow or learn
                    cands[#cands + 1] = {
                        spell = spell, item = (type(itemID) == "number") and itemID or nil,
                        learn = learn, yellow = cY,
                        green = (type(green) == "number") and green or yellow or learn,
                        grey = grey, mats = reagents, cost = cost, unpriced = unpriced,
                        fcost = fcost, base = base, cd = (rec[4] == "Transmutes") or nil,
                        unknown = unknown or nil,
                        learnO = math.max(1, math.min(learn, cY - 25)),
                    }
                    recOf[spell] = rec
                end""",
)

# R14 rinfo 候选补方案字段
ra.rep(
    """                if ok then
                    local y = (type(ri.yellow) == "number") and ri.yellow or ri.learn
                    local g = (type(ri.green) == "number") and ri.green or y
                    cands[#cands + 1] = {
                        spell = spell, item = (type(ri.makes) == "number") and ri.makes or nil,
                        learn = ri.learn, yellow = y, green = g, grey = ri.grey,
                        mats = ri.mats, cost = cost, unpriced = unpriced,
                    }
                    recOf[spell] = ri
                end""",
    """                if ok then
                    local y = (type(ri.yellow) == "number") and ri.yellow or ri.learn
                    local g = (type(ri.green) == "number") and ri.green or y
                    -- 方案字段（2026-10-10）：rinfo 无图纸/分类 → fcost=0、cd=false
                    local base, unknown = 0, false
                    for _, m in ipairs(ri.mats) do
                        if not ClientKnown(m[1]) then unknown = true end
                        local sp = NPCSellPrice(m[1])
                        if sp then base = base + sp * (m[2] or 1) end
                    end
                    cands[#cands + 1] = {
                        spell = spell, item = (type(ri.makes) == "number") and ri.makes or nil,
                        learn = ri.learn, yellow = y, green = g, grey = ri.grey,
                        mats = ri.mats, cost = cost, unpriced = unpriced,
                        fcost = 0, base = base, unknown = unknown or nil,
                        learnO = math.max(1, math.min(ri.learn, y - 25)),
                    }
                    recOf[spell] = ri
                end""",
)

# R15 Compute：方案解析 + 传入 Simulate
ra.rep(
    """    -- 「只用拍卖行可购材料」= 严格模拟（无价配方不参与）；产生的缺口随后放宽回填
    local allowUnpriced = not opts.onlyAH""",
    """    -- 「只用拍卖行可购材料」= 严格模拟（无价配方不参与）；产生的缺口随后放宽回填
    -- 方案（2026-10-10）：未传/非法 = 最省钱（产品默认；调用方不传也拿到新口径）
    local scheme = opts.scheme
    if scheme == nil or not SCHEME_LABEL[scheme] then scheme = "cheapest" end""",
)
ra.rep(
    "    local steps, gaps = Simulate(cands, opts.start, cap, allowUnpriced)",
    "    local steps, gaps = Simulate(cands, opts.start, cap, allowUnpriced, scheme)",
)
ra.rep(
    "        steps, gaps = FillGaps(cands, steps, gaps)",
    "        steps, gaps = FillGaps(cands, steps, gaps, scheme)",
)

# R16 optim 段花费改用基础价值 + 结果带 scheme
ra.rep(
    """        for _, st in ipairs(steps) do
            if st.est then filled = true break end
        end
    end""",
    """        for _, st in ipairs(steps) do
            if st.est then filled = true break end
        end
    end
    -- 乐观计数（2026-10-10）：段花费改用材料卖店基础价值合计 —— 市价口径不适用
    --   （参考口径「只用来挑配方，不写价格」；这里给出量级，页面标注估算）
    if scheme == "optim" then
        local bySpell = {}
        for _, c in ipairs(cands) do bySpell[c.spell] = c end
        for _, st in ipairs(steps) do
            local c = bySpell[st[3]]
            if c then st.cost = (c.base or 0) * (st[4] or 0) end
        end
    end""",
)
ra.rep(
    """        SummarizeCore(steps, recOf, soldSet, opts.learnedOnly)
    return {
        steps = ToReached(steps), gaps = gaps, mats = mats, firstAt = firstAt,""",
    """        SummarizeCore(steps, recOf, soldSet, opts.learnedOnly)
    return {
        scheme = scheme,
        steps = ToReached(steps), gaps = gaps, mats = mats, firstAt = firstAt,""",
)

# R17 缓存键加 scheme
ra.rep(
    """local function Fingerprint(opts)
    return string.format("%s|%s|%s|%s|%s",
        tostring(opts.start), tostring(opts.onlyAH),
        tostring(opts.noFormula), tostring(opts.learnedOnly),
        tostring(opts.target and math.floor(tonumber(opts.target) or CAP)))
end""",
    """local function Fingerprint(opts)
    return string.format("%s|%s|%s|%s|%s|%s",
        tostring(opts.start), tostring(opts.onlyAH),
        tostring(opts.noFormula), tostring(opts.learnedOnly),
        tostring(opts.target and math.floor(tonumber(opts.target) or CAP)),
        tostring(opts.scheme))
end""",
)
ra.save()

# ══════════════════ Core/ProfessionUI.lua (CRLF) ══════════════════
pu = F(r"D:/workspace/DungeonsForever/Core/ProfessionUI.lua")

# U1 默认值
pu.rep(
    'PD.SETTING_DEF.autoLearnedOnly = false  -- 仅使用本角色已学的配方',
    '''PD.SETTING_DEF.autoLearnedOnly = false  -- 仅使用本角色已学的配方
PD.SETTING_DEF.autoScheme = "cheapest"  -- 自动路线方案：最省钱/材料成本/次数最少/乐观计数''',
)

# U2 autoOn 门槛（optim 不依赖价格插件）
pu.rep(
    '    local autoOn = (PD.Setting("autoRoute") and RA and RA.Available()) and true or false',
    '''    -- 乐观计数方案不依赖价格插件（2026-10-10）：其余方案仍要求 RA.Available()
    local scheme = PD.Setting("autoScheme")
    local autoOn = (PD.Setting("autoRoute") and RA
                    and (scheme == "optim" or RA.Available())) and true or false''',
)

# U3 opts 带 scheme
pu.rep(
    """            learnedOnly = PD.Setting("autoLearnedOnly"),
            target = target,   -- 2026-10-09 v2：模拟与缺口回填都 clamp 在目标内
        }""",
    """            learnedOnly = PD.Setting("autoLearnedOnly"),
            target = target,   -- 2026-10-09 v2：模拟与缺口回填都 clamp 在目标内
            scheme = scheme,
        }""",
)

# U4 priced 门槛放宽（optim 除外）
pu.rep(
    "        if res and not res.priced then res = nil end   -- 一条价格都没有 = 未扫描，降级",
    '        if res and not res.priced and scheme ~= "optim" then res = nil end   -- 一条价格都没有 = 未扫描，降级（乐观计数除外）',
)

# U5 方案卡入列（第二位）
pu.rep(
    """    for _, td in ipairs({
        { key = "mode",   w = 200 },
        { key = "cost",   w = 250 },""",
    """    for _, td in ipairs({
        { key = "mode",   w = 200 },
        { key = "scheme", w = 150 },
        { key = "cost",   w = 250 },""",
)

# U6 方案卡点击循环切换
pu.rep(
    """    PD.lvTiles.mode:SetScript("OnClick", function()
        local on = not PD.Setting("autoRoute")
        ProfDB().autoRoute = on
        if not on and RA then RA.Invalidate() end
        PD.Render()
        ns.PlaySound(1)
    end)""",
    """    PD.lvTiles.mode:SetScript("OnClick", function()
        local on = not PD.Setting("autoRoute")
        ProfDB().autoRoute = on
        if not on and RA then RA.Invalidate() end
        PD.Render()
        ns.PlaySound(1)
    end)
    -- 路线方案卡（2026-10-10 用户）：点击循环切换方案，缓存随失效重算
    PD.lvTiles.scheme:SetScript("OnClick", function()
        local order = (RA and RA.SchemeOrder and RA.SchemeOrder()) or {}
        local cur = PD.Setting("autoScheme")
        local n = #order
        local ni = 1
        for i, k in ipairs(order) do
            if k == cur then ni = (i % n) + 1 break end
        end
        ProfDB().autoScheme = order[ni]
        if RA then RA.Invalidate() end
        PD.Render()
        ns.PlaySound(1)
    end)""",
)

# U7 模式卡提示文案改为方案无关
pu.rep(
    """        { auto and L["自动计算：依据 Auctionator 价格算最省钱的制作路线"]
               or L["固定路线：按资料整理的分段练法逐段冲技能"], 1, 0.82, 0 },""",
    """        { auto and L["自动计算：按当前路线方案逐点择优（在「路线方案」卡切换）"]
               or L["固定路线：按资料整理的分段练法逐段冲技能"], 1, 0.82, 0 },""",
)

# U8 方案卡绘制（挂在 mode TipOn 后）
pu.rep(
    "    TipOn(tiles.mode, modeLines)",
    '''    TipOn(tiles.mode, modeLines)
    -- 路线方案卡（2026-10-10 用户）：显示当前方案，tooltip 列全部方案（当前金色）
    local sch = s.scheme or "cheapest"
    tiles.scheme.label:SetText(L["路线方案 · 点击切换"])
    tiles.scheme.val:SetText((RA and RA.SchemeLabel) and RA.SchemeLabel(sch) or L["最省钱"])
    tiles.scheme.val:SetTextColor(Unpack(C_WHITE))
    local schemeDesc = {
        cheapest = L["最省钱：材料价 + 图纸价按升点概率摊到每一点，选期望花费最低的配方"],
        matcost = L["材料成本：只按材料价选配方（不含图纸价）"],
        crafts = L["次数最少：优先升点率高的配方，同分取便宜"],
        optim = L["乐观计数：1 次制作按涨 1 点乐观计（实际更多）；变黄前 25 点可学；排除冷却与未公开材料配方；材料按卖店价比较，不依赖价格插件"],
    }
    local schemeLines = {}
    local sorder = (RA and RA.SchemeOrder and RA.SchemeOrder()) or {}
    for _, sk in ipairs(sorder) do
        local curK = (sk == sch)
        schemeLines[#schemeLines + 1] = { schemeDesc[sk] or sk,
                                          curK and 1 or 0.62, curK and 0.82 or 0.62,
                                          curK and 0 or 0.62 }
    end
    TipOn(tiles.scheme, schemeLines)''',
)

# U9 花费卡 optim 分支
pu.rep(
    """    local costLines
    if s.priced and s.total then""",
    """    local costLines
    if s.scheme == "optim" then
        tiles.cost.val:SetText(RA.MoneyStr(s.total or 0, "copper"))
        tiles.cost.val:SetTextColor(Unpack(C_GREY))
        costLines = { { L["乐观计数：按材料卖店基础价值估算（不含拍卖行市价），仅供参考"], 0.7, 0.7, 0.7 } }
    elseif s.priced and s.total then""",
)

# U10 快照卡 optim 提示
pu.rep(
    "    local atxt\n    if s.priced and snapSec then",
    '''    local atxt
    if s.scheme == "optim" then
        atxt = L["乐观计数 · 不依赖价格插件"]
    elseif s.priced and snapSec then''',
)

# U11 五卡均分 + 绘制顺序
pu.rep(
    """    local usable = PD.RIGHT_W - PD.LIST_PAD - 3 * PD.LV_TILE_GAP
    local tw = math.floor(usable / 4)
    tiles.mode:SetWidth(tw)
    tiles.cost:SetWidth(tw)
    tiles.target:SetWidth(tw)
    tiles.snap:SetWidth(usable - 3 * tw)
    local x = PD.RIGHT_X
    for _, k in ipairs({ "mode", "cost", "target", "snap" }) do""",
    """    -- 五张信息卡均分（2026-10-10 用户：加路线方案卡，第二位）
    local usable = PD.RIGHT_W - PD.LIST_PAD - 4 * PD.LV_TILE_GAP
    local tw = math.floor(usable / 5)
    tiles.mode:SetWidth(tw)
    tiles.scheme:SetWidth(tw)
    tiles.cost:SetWidth(tw)
    tiles.target:SetWidth(tw)
    tiles.snap:SetWidth(usable - 4 * tw)
    local x = PD.RIGHT_X
    for _, k in ipairs({ "mode", "scheme", "cost", "target", "snap" }) do""",
)

# U12 两处 lvSummary 带 scheme（shop 分支 + 路线分支）
pu.rep(
    """        PD.lvSummary = {
            target = target, auto = auto,
            autoSetting = PD.Setting("autoRoute"),""",
    """        PD.lvSummary = {
            target = target, auto = auto,
            scheme = auto and res.scheme or nil,
            autoSetting = PD.Setting("autoRoute"),""",
)
pu.rep(
    """    PD.lvSummary = {
        target = target, auto = auto,
        autoSetting = PD.Setting("autoRoute"),""",
    """    PD.lvSummary = {
        target = target, auto = auto,
        scheme = auto and res.scheme or nil,
        autoSetting = PD.Setting("autoRoute"),""",
)
pu.save()

# ══════════════════ Core/ProfFollow.lua (LF) ══════════════════
pf = F(r"D:/workspace/DungeonsForever/Core/ProfFollow.lua")
pf.rep(
    '    if PD and PD.Setting and PD.Setting("autoRoute") and RA and RA.Available() then',
    '''    local scheme = PD and PD.Setting and PD.Setting("autoScheme") or "cheapest"
    -- 乐观计数方案不依赖价格插件（2026-10-10）；其余方案仍要求 RA.Available()
    if PD and PD.Setting and PD.Setting("autoRoute") and RA
       and (scheme == "optim" or RA.Available()) then''',
)
pf.rep(
    "            target = routeTarget(slug),\n        }",
    "            target = routeTarget(slug),\n            scheme = scheme,\n        }",
)
pf.rep(
    '        if res and res.priced then return "auto", res.steps end',
    '        if res and (res.priced or scheme == "optim") then return "auto", res.steps end',
)
pf.save()
print("ALL OK")
