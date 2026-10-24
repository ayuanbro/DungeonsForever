-- =============================================================================
-- DungeonsForever · 专业升级自动路线（按拍卖行价格）
-- 输入专业与过滤设置，输出与固定路线同构的分段路线与成本汇总；不持有任何 UI。
-- =============================================================================

local _, ns = ...

if not ns.LoadForeverPages then return end

local RA = {}
ns.ProfRouteAuto = RA

local CALLER = "DungeonsForever"
local CAP = 300                  -- 无限服 1.60.1 专业上限
local MAX_STALE = 2              -- 价格快照年龄上限（天；价格插件 Age API 返回的就是「天」），超过视为无价
local CACHE_TTL = 600            -- 结果缓存 10 分钟
local VENDOR_QUOTE_REVISION = 5
-- 期望收益插值端点（调参集中在这里）
-- ★★ 语义 = 「单次制作的升点概率 P（点/次）」，不是收益系数 —— Simulate 里按 1/P 累计次数。
--   端点须与 ProfFollow.expPerPoint（经典 1/P 口径）一致：
--     黄段 P 1.0 → 0.5、绿段 P 0.5 → 0.05（段末深绿只有 5% 涨点率，要做 20 次）。
--   2026-10-09 修：原为 0.7 / 0.25，把绿色段升点率最高高估 5 倍 ⇒ 次数系统性偏小
--   （91 个攻略段标定：现值 3.2% 误差 / 旧值 11.0%；总次数 2548 → 3822）。
local G_YELLOW, G_GREEN = 0.5, 0.05

-- ── 自动路线方案（2026-10-10 用户：设置内可选，默认最省钱）────────────────────
--   cheapest = 完整依赖链的材料采购支出；matcost = 旧版逐点材料成本；
--   crafts = 期望制作次数最少（同分取便宜）；optim = 乐观计数参考。
--   所有方案计入一次性图纸采购，仍不计已有库存、训练学费或制作工具。
local SCHEME_ORDER = { "cheapest", "matcost", "crafts", "optim" }
-- ★ 本文件加载序在 Locales 之前 ⇒ 不能在加载期取 L；标签存键名、运行时查。
--   方案标签键（供三语扫描器登记，正则只认 L["…"] 字面量）：
--   L["最省钱"] L["材料成本"] L["次数最少"] L["乐观计数"]
local SCHEME_LABEL = {
    cheapest = "最省钱",
    matcost = "材料成本",
    crafts = "次数最少",
    optim = "乐观计数",
    fishing = "纯钓鱼",
}
function RA.SchemeOrder() return SCHEME_ORDER end
function RA.SchemeLabel(s)
    local k = (s and SCHEME_LABEL[s]) and SCHEME_LABEL[s] or "最省钱"
    return type(L) == "table" and L[k] or k
end

-- ── 拍卖行价格插件可用性与价格层 ──────────────────────────────────────────────

function RA.Available()
    local bridge=ns.AuctionBridge
    if bridge and bridge.PriceReady then return bridge.PriceReady() end
    return type(Auctionator) == "table"
        and type(Auctionator.API) == "table"
        and type(Auctionator.API.v1) == "table"
        and type(Auctionator.API.v1.GetAuctionPriceByItemID) == "function"
end

local function CallAPI(fn, ...)
    local ok, v = pcall(fn, CALLER, ...)
    if ok then return v end
    return nil
end

local priceCache = {}   -- itemID → number | false（false = 已查无价）
local NEG_TTL = 60

local function AHPrice(id)
    -- API functions can exist before Auctionator opens its price database.
    -- Do not cache that transient state as a missing item quote.
    if not RA.Available() then return nil end
    local c = priceCache[id]
    if c ~= nil then
        if c ~= false then return c end
        local now = (type(time) == "function") and time() or 0
        local t0 = priceCache.__t and priceCache.__t[id] or nil
        if t0 and (now - t0) < NEG_TTL then return nil end
    end
    local p
    if RA.Available() then
        p = CallAPI(Auctionator.API.v1.GetAuctionPriceByItemID, id)
        if type(p) ~= "number" or p <= 0 then p = nil end
        if p and type(Auctionator.API.v1.GetAuctionAgeByItemID) == "function" then
            local age = CallAPI(Auctionator.API.v1.GetAuctionAgeByItemID, id)
            if type(age) == "number" then
                if age > MAX_STALE then p = nil end
                if age < (priceCache.__minAge or math.huge) then
                    priceCache.__minAge = age
                end
            end
        end
    end
    priceCache[id] = p or false
    if not p then
        priceCache.__t = priceCache.__t or {}
        priceCache.__t[id] = (type(time) == "function") and time() or 0
    end
    if p then priceCache.__any = true end
    return p
end

local function VendorPrice(id)
    -- 材料先验证不限量供货资格，再使用独立生成的组价。
    if ns.ProfItemPrices then
        local ok, p = pcall(ns.ProfItemPrices.GetPrice, id)
        if ok and type(p) == "number" and p >= 0 then return p end
    end
    return nil
end

-- Compare actual AH purchasing with the configured NPC gold quotation.
local function MatPrice(id)
    local v = VendorPrice(id)
    local economy=ns.ProfEconomy
    local a = not (economy and economy.NonAuctionableItem and economy.NonAuctionableItem(id)) and AHPrice(id) or nil
    if a and v and v < a then return v end
    return a or v
end
function RA.VendorMaterialOf(id)
    local db=ns.ProfItemPrices
    return db and db.GetOffers and #db.GetOffers(id)>0 or false
end

local function vendorQuoteData()
    local meta=ns.ProfItemsMeta
    local csv=meta and meta.sources and meta.sources.csv
    local material=ns.ProfMaterialSupplyMeta
    return "material-supply-v1:"..tostring(material and material.fingerprint or "missing")
        .."|formula:"..tostring(csv and csv.sha256 or "missing")
end
function RA.StampFormulaPolicy(result,opts)
    if result and ns.ProfEconomy and type(ns.ProfEconomy.AllowLimitedFormulas)=="function" then
        result.formulaPolicy={revision=1,allowLimited=ns.ProfEconomy.AllowLimitedFormulas(opts)}
    end
    return result
end
function RA.FormulaPolicyChanged(result,opts)
    if not result or result.status=="selection_required" or result.status=="recalculate_required" then return false end
    local economy=ns.ProfEconomy
    -- The public quotation validator is also used without the route/economy
    -- modules. Material fingerprints can still be checked in that context.
    if not (economy and type(economy.AllowLimitedFormulas)=="function"
        and type(economy.LimitedFormulaOffer)=="function") then return false end
    local policy=result.formulaPolicy
    if not policy then
        -- Before this setting existed, every limited seller was eligible. A
        -- retained plan only needs blocking if it actually relies on one.
        if economy.AllowLimitedFormulas(opts) then return false end
        for _,entry in ipairs(result.formulas or {}) do
            if entry.source=="vendor" and not entry.known and
                (entry.offer and economy.LimitedFormulaOffer(entry.offer)
                    or not entry.offer and entry.limited) then return true end
        end
        return false
    end
    return policy.revision~=1 or policy.allowLimited~=economy.AllowLimitedFormulas(opts)
end
function RA.ValidateFormulaPolicy(result,opts)
    if not RA.FormulaPolicyChanged(result,opts) then return result end
    return {planVersion=2,mode=result.mode,scheme=result.scheme,status="recalculate_required",
        start=result.start,target=result.target,steps={},executionSteps={},actions={},mats={},formulas={},gaps={},
        total=0,matTotal=0,ahTotal=0,vendorTotal=0,formulasTotal=0,crafts=0,
        feasible=false,priced=false,costComplete=false,completeCost=false,targetReached=false,
        cached=true,stale=true,staleReason="formula-policy",revision=result.revision,
        diagnostics={{code="formulaPolicyChanged"}}}
end
function RA.StampVendorQuotes(result,opts)
    if result then
        result.vendorQuoteRevision=VENDOR_QUOTE_REVISION
        result.vendorQuoteData=vendorQuoteData()
    end
    return RA.StampFormulaPolicy(result,opts)
end
function RA.VendorQuotesChanged(result)
    -- Selection/profession/specialization gates already expose no purchasing
    -- view. Preserve their actionable diagnostic when UI validates it again.
    if result and (result.status=="selection_required" or result.status=="recalculate_required")
        and (result.total or 0)==0 and #(result.steps or {})==0 and #(result.actions or {})==0
        and #(result.mats or {})==0 and #(result.formulas or {})==0 then return false end
    return result and not result.inFlight and result.status~="searching" and
        (result.vendorQuoteRevision~=VENDOR_QUOTE_REVISION or result.vendorQuoteData~=vendorQuoteData()) or false
end
function RA.ValidateVendorQuotes(result,opts)
    result=RA.ValidateFormulaPolicy(result,opts)
    if not RA.VendorQuotesChanged(result) then return result end
    -- Keep stored execution facts intact; the current purchasing view is empty
    -- until a manual calculation uses this version's item/NPC quotations.
    return RA.StampVendorQuotes({planVersion=2,mode=result.mode,scheme=result.scheme,
        status="recalculate_required",start=result.start,target=result.target,
        steps={},executionSteps={},actions={},mats={},formulas={},gaps={},
        total=0,matTotal=0,ahTotal=0,vendorTotal=0,formulasTotal=0,crafts=0,
        feasible=false,priced=false,costComplete=false,completeCost=false,targetReached=false,
        cached=true,stale=true,staleReason="vendor-quotes",revision=result.revision,
        diagnostics={{code="vendorQuoteChanged"}}})
end

-- Keep planned specialization learning separate from the character's current
-- abilities. Acquiring a planned ability advances an existing frozen plan;
-- changing its selection/data or losing an original ability invalidates it.
local function specializationContext(slug,opts)
    local economy=ns.ProfEconomy
    if not (economy and economy.GetEngineeringSpecializationContext) then return end
    local options={}; for key,value in pairs(opts or {}) do options[key]=value end
    options.profession=slug or options.profession or "engineering"
    if options.target==nil then
        local saved=DungeonsForeverDB and DungeonsForeverDB.prof
        options.target=tonumber(saved and saved.lvTarget and saved.lvTarget[options.profession]) or 300
    end
    return economy.GetEngineeringSpecializationContext(options)
end
function RA.StampSpecializations(result,slug,opts,snapshot)
    if not result then return end
    RA.StampToolPolicy(result,slug,opts,snapshot)
    local economy=ns.ProfEconomy
    local context=snapshot and snapshot.specializationContext or specializationContext(slug,opts)
    if not context then return result end
    local abilities={}
    for id,known in pairs(snapshot and snapshot.specializationAbilities or context.abilities or {}) do
        if known==true then abilities[id]=true end
    end
    result.specializationPolicy={revision=1,choice=context.choice or "none",
        fingerprint=economy.SpecializationFingerprint(context),actualAbilities=abilities,
        selectionConflict=context.selectionConflict==true,
        profession=slug or (snapshot and snapshot.targetProfession)}
    return result
end
function RA.StampToolPolicy(result,slug,opts,snapshot)
    if not result then return end
    local economy=ns.ProfEconomy
    slug=slug or result.toolProfession or opts and opts.profession
    if not slug or not economy or not economy.ToolFingerprint then return result end
    result.toolProfession=slug
    result.toolPolicy={revision=1,fingerprint=snapshot and snapshot.toolFingerprint or economy.ToolFingerprint(slug,opts)}
    return result
end
function RA.ToolPolicyChanged(result,slug,opts)
    if not result then return false end
    local economy=ns.ProfEconomy
    slug=slug or result.toolProfession or (result.specializationPolicy or {}).profession or opts and opts.profession
    if not economy or not economy.ToolFingerprint or not slug then return false end
    local expected=economy.ToolFingerprint(slug,opts)
    if expected=="" then return false end
    local policy=result.toolPolicy
    return not policy or policy.revision~=1 or policy.fingerprint~=expected
end
function RA.ValidateToolPolicy(result,slug,opts)
    if not RA.ToolPolicyChanged(result,slug,opts) then return result end
    return {planVersion=2,mode=result.mode,scheme=result.scheme,status="recalculate_required",
        start=result.start,target=result.target,steps={},executionSteps={},actions={},mats={},formulas={},gaps={},
        total=0,matTotal=0,ahTotal=0,vendorTotal=0,formulasTotal=0,crafts=0,
        feasible=false,priced=false,costComplete=false,completeCost=false,targetReached=false,
        cached=true,stale=true,staleReason="tool-policy",revision=result.revision,
        diagnostics={{code="toolPolicyChanged"}}}
end
function RA.SpecializationPlanChanged(result,slug,opts)
    if not result then return false end
    local context=specializationContext(slug or (result.specializationPolicy or {}).profession,opts)
    if not context then return false end
    local policy=result.specializationPolicy
    if not policy then
        return (ns.ProfSpecializations and next(ns.ProfSpecializations)~=nil)
            or (context.choice and context.choice~="none") or false
    end
    if policy.revision~=1 or policy.fingerprint~=ns.ProfEconomy.SpecializationFingerprint(context) then return true end
    for id in pairs(policy.actualAbilities or {}) do
        if (context.abilities or {})[id]~=true then return true end
    end
    return context.profession=="engineering" and context.selectionConflict==true and not policy.selectionConflict
end
function RA.ValidateSpecializationPlan(result,slug,opts)
    result=RA.ValidateToolPolicy(result,slug,opts)
    if not result or result.status=="recalculate_required" or not RA.SpecializationPlanChanged(result,slug,opts) then return result end
    return {planVersion=2,mode=result.mode,scheme=result.scheme,status="recalculate_required",
        start=result.start,target=result.target,steps={},executionSteps={},actions={},mats={},formulas={},gaps={},
        total=0,matTotal=0,ahTotal=0,vendorTotal=0,formulasTotal=0,crafts=0,
        feasible=false,priced=false,costComplete=false,completeCost=false,targetReached=false,
        cached=true,stale=true,staleReason="specialization",revision=result.revision,
        diagnostics={{code="specializationChanged"}}}
end
RA.ValidateSpecializations=RA.ValidateSpecializationPlan

function RA.FilterFixedSpecializations(slug,steps,opts)
    local economy=ns.ProfEconomy
    if not (economy and economy.LearningEligibility) then return steps or {},{},false end
    local context=specializationContext(slug,opts)
    local snapshot={specializationContext=context,specializationAbilities=context and context.abilities or {},known={}}
    local filtered,blocked={},{}
    for _,step in ipairs(steps or {}) do
        local spell=step[3] or step.spell
        local recipe=step.recipe or (spell and economy.FindRecipe and economy.FindRecipe(step.profession or slug,spell))
        if recipe and economy.Known(recipe.spell) then snapshot.known[recipe.key or recipe.spell]=true end
        local allowed,reason=true
        if recipe then allowed,reason=economy.LearningEligibility(recipe,snapshot) end
        if allowed then filtered[#filtered+1]=step
        else blocked[#blocked+1]={spell=spell,from=step[1],to=step[2],reason=reason or "specializationRequired"} end
    end
    return filtered,blocked,context and #(context.goals or {})>0 or false
end

-- 物品卖店价（直接卖给 NPC 的收益）：三通道依次尝试。
-- 本客户端全局 GetItemInfo 不可靠，优先 C_Item.GetItemInfo 现代命名空间版
-- （SELL_PRICE = 第 11 个返回值），再兜 C_Item.GetItemSellPrice。
-- ★ 只缓存成功值：物品数据异步到货，未加载时返回 nil；把 nil 钉进缓存会让
--   产物「直接卖给NPC收益」永久停在 0。
local sellCache = {}   -- itemID → number（只缓存成功值）
local function NPCSellPrice(id)
    if sellCache[id] then return sellCache[id] end
    local p
    -- ① C_Item.GetItemInfo（现代命名空间）
    if C_Item and C_Item.GetItemInfo then
        local vals = { pcall(C_Item.GetItemInfo, id) }
        if vals[1] then
            local sell = vals[12]   -- vals[1]=pcall ok，其后依次 GetItemInfo 返回值（第 11 项 = sellPrice）
            if type(sell) == "number" and sell >= 0 then p = sell end
        end
    end
    -- ② 全局 GetItemInfo（老通道）
    if not p and type(GetItemInfo) == "function" then
        local vals = { pcall(GetItemInfo, id) }
        if vals[1] then
            local sell = vals[12]
            if type(sell) == "number" and sell >= 0 then p = sell end
        end
    end
    -- ③ C_Item.GetItemSellPrice（专用 API，直达）
    if not p and C_Item and C_Item.GetItemSellPrice then
        local ok, sell = pcall(C_Item.GetItemSellPrice, id)
        if ok and type(sell) == "number" and sell >= 0 then p = sell end
    end
    if p then sellCache[id] = p end
    return p
end

-- 客户端是否已公开该物品（optim 方案排除「未公开物品」材料的配方）：
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

-- 材料清单成本（2026-10-10 配方页「制作成本」列/提示框「成本」行共用）：
-- mats = {{id, cnt}, ...}；逐项比较可用单价，无价项计数。
-- 返回 total, unpriced（unpriced>0 = 部分材料没价，调用方加 ≈ 前缀）
local function MatListCost(mats)
    if type(mats) ~= "table" or #mats == 0 then return nil, 0 end
    local total, unpriced = 0, 0
    for _, m in ipairs(mats) do
        local id, cnt = m[1] or m.id, (m[2] or m.cnt or 1)
        local p = MatPrice(id)
        if p then total = total + p * cnt else unpriced = unpriced + 1 end
    end
    return total, unpriced
end

-- ── 提示框/配方页只读价格口（2026-10-10）───────────────────────────────────
-- 拍卖行单价（走 AHPrice 会话内缓存，重复查询零开销；无价 nil）
function RA.AHPriceOf(itemID)
    if not itemID then return nil end
    return AHPrice(itemID)
end

-- 卖店价（三通道，见 NPCSellPrice 注释；数据未加载时 nil，下次悬停重试）
function RA.NPCSellPriceOf(itemID)
    if not itemID then return nil end
    return NPCSellPrice(itemID)
end

-- 材料清单成本：返回 total, unpriced（调用方以 unpriced 决定 ≈ 前缀 / — 显示）
function RA.MatListCost(mats)
    return MatListCost(mats)
end

-- 产物 itemID 预热：走插件的物品加载通道，到货后 UI 重渲染即可取到卖店价
local function RequestProduct(id)
    local H = ns.ProfHost
    local dg = H and H.DG
    if dg and dg.RequestItem then pcall(dg.RequestItem, id) end
end

-- 真实价格快照时间（秒级）：价格插件 SavedState 存的是 epoch 时间戳
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

-- 是否查到过任何价格数据（一条都没有 = 价格插件未扫描，调用方降级）
function RA.HasPriceData()
    return priceCache.__any and true or false
end

-- 距上次拍卖行扫描的秒数（取不到 nil；板条箱页价格快照用）
function RA.SnapshotAge()
    return SnapshotSec()
end

-- ── 金额格式（金/银，铜抹到银）──────────────────────────────────────────────


-- 币种图标（|T|t 尺寸 0 = 跟随所在文本字号；2026-10-10 金/银/铜不用文字用图标）
local ICON_G = "|TInterface\\MoneyFrame\\UI-GoldIcon:0|t"
local ICON_S = "|TInterface\\MoneyFrame\\UI-SilverIcon:0|t"
local ICON_C = "|TInterface\\MoneyFrame\\UI-CopperIcon:0|t"

-- opt = "copper"：最小单位到铜（购物清单 / 花费卡）；默认抹到银（路线段落等保持紧凑）
-- 负值（2026-10-10 用户）：差价/净利为负时如实显示 - 前缀（不再钳成 0）
function RA.MoneyStr(copper, opt)
    copper = tonumber(copper)
    if copper and copper < 0 then
        return "-" .. RA.MoneyStr(-copper, opt)
    end
    if not copper or copper <= 0 then
        return "0" .. ICON_C
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
    local g = math.floor(copper / 10000)
    local s = math.floor(copper / 100) % 100
    local c = copper % 100
    if g > 0 then
        return format("%d%s%02d%s%02d%s", g, ICON_G, s, ICON_S, c, ICON_C)
    end
    if s > 0 then
        return format("%d%s%02d%s", s, ICON_S, c, ICON_C)
    end
    return format("%d%s", c, ICON_C)
end

-- ── 单次制作的升点概率 P（橙→黄→绿线性插值，与 ProfFollow.expPerPoint 同源）──
--   返回「这一次制作涨 1 技能点的概率」；调用方按 1/P 累计制作次数。

local function Gain(skill, c)
    if skill < c.learn or skill >= c.grey then return nil end
    if skill < c.yellow then return 1.0 end
    if skill < c.green then
        local span = c.green - c.yellow
        if span <= 0 then return G_YELLOW end
        local t = (skill - c.yellow) / span
        return 1.0 - t * (1.0 - G_YELLOW)
    end
    local span = c.grey - c.green
    if span <= 0 then return G_GREEN end
    local t = (skill - c.green) / span
    return G_YELLOW - t * (G_YELLOW - G_GREEN)
end

-- ── 候选集构建 ──────────────────────────────────────────────────────────────
-- rec 行字段序（Data_ProfRecipes.lua 头注释）：
--   1 spell / 2 itemID / 3 count / 4 cat / 5 kind / 6 effect / 7 learn /
--   8 yellow / 9 green / 10 grey / 11 is_new / 12 reagents / 13 formula / 14 source

local function LearnKnown(spell)
    if ns.ProfEconomy and ns.ProfEconomy.Known then return ns.ProfEconomy.Known(spell) end
    if type(IsSpellKnown) == "function" then
        local ok, v = pcall(IsSpellKnown, spell)
        if ok and v then return true end
    end
    if type(IsPlayerSpell) == "function" then
        local ok, v = pcall(IsPlayerSpell, spell)
        if ok and v then return true end
    end
    return false
end

function RA.SpellKnown(spell)
    return LearnKnown(spell)
end

local function ClientRecipe(seed,spell,slug)
    local rec={}; for k,v in pairs(seed) do rec[k]=v end
    local canonical
    if rec.mats or rec.learn then
        canonical={};for key,value in pairs(rec) do canonical[key]=value end
        canonical.spell=spell or seed.spell or seed[1];canonical.item=rec.makes or rec.item
        canonical.count=rec.count or 1;canonical.formula=rec.formula or rec.formulaID
    else
        canonical={spell=spell or seed[1],item=rec[2],count=rec[3] or 1,mats=rec[12],
            formula=rec[13] and rec[13][1],source=rec[14]}
    end
    if ns.ProfEconomy and ns.ProfEconomy.ResolveRecipe then canonical=ns.ProfEconomy.ResolveRecipe(canonical,slug) end
    if rec.mats or rec.learn then rec.mats=canonical.mats; rec.count=canonical.count; rec.makes=canonical.item
    else rec[12]=canonical.mats; rec[3]=canonical.count; rec[2]=canonical.item end
    rec.clientPending=canonical.clientPending
    rec.dataSource=canonical.dataSource
    rec.clientUnavailable=canonical.clientUnavailable
    return rec
end

-- opts = { start=起点技能, onlyAH=bool, learnedOnly=bool }
local function BuildCandidates(slug, opts)
    local _rf = ns.EnsureProfRecipes
    local Rg = _rf and _rf()[slug] or ns.ProfRecipes and ns.ProfRecipes[slug]
    local LV = ns.ProfLeveling and ns.ProfLeveling[slug]
    if not (Rg and type(Rg.rows)=="table" or LV and type(LV.rinfo)=="table") then return nil end
    Rg=Rg or {}
    local cands, recOf = {}, {}
    local specContext=specializationContext(slug,opts)
    local specSnapshot={specializationContext=specContext,specializationAbilities=specContext and specContext.abilities or {}}
    for _, seed in ipairs(Rg.rows or {}) do
        local rec=ClientRecipe(seed,nil,slug)
        local spell, learn, yellow, green, grey = rec[1], rec[7], rec[8], rec[9], rec[10]
        local reagents = rec[12]
        if type(spell) == "number" and type(learn) == "number"
           and type(grey) == "number" and grey > learn
           and type(reagents) == "table" and #reagents > 0 then
            local ok = not rec.clientUnavailable
            local economy=ns.ProfEconomy
            local recipe=economy and economy.Normalize(rec,slug,"rows")
            if recipe and economy.LearningEligibility and not economy.LearningEligibility(recipe,specSnapshot) then ok=false end
            if recipe and (recipe.cooldown or recipe.cooldownUnknown or recipe.clientPending or recipe.outputConflict) then ok=false end
            local formula=recipe and economy.FormulaFor(recipe,{allowLimitedFormulas=economy.AllowLimitedFormulas(opts)})
            if formula and not formula.usable then ok=false end
            local policy=ns.ProfEconomy and ns.ProfEconomy.Policy(opts.exclusions or ns.ProfEconomy.GetPolicies(slug),{key=slug..":"..spell,spell=spell})
            if policy then ok=false end
            local rt=ns.ProfRecipeRuntime and ns.ProfRecipeRuntime[spell]
            if rt and rt.cooldown then ok=false end
            -- 设置过滤：仅已学
            if ok and opts.learnedOnly and not LearnKnown(spell) then ok = false end
            -- 材料定价（含生死判定）
            if ok then
                local cost, unpriced = 0, false
                for _, m in ipairs(reagents) do
                    local p = MatPrice(m[1])
                    if p then
                        cost = cost + p * (m[2] or 1)
                    else
                        unpriced = true
                    end
                end
                -- 「只用拍卖行可购材料」不再在此处淘汰（2026-10-09 修缺口误报）：
                -- 无价配方保留进候选池并打 unpriced 标记，严格性由 Simulate 按
                -- allowUnpriced 控制 —— 缺口段会自动放宽，用已知材料估价回填。
                if ok then
                    local itemID = rec[2]
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
                        formula=formula,
                        base = base, cd = (rec[4] == "Transmutes") or nil,
                        unknown = unknown or nil,
                        learnO = math.max(1, math.min(learn, cY - 25)),
                    }
                    recOf[spell] = rec
                end
            end
        end
    end
    -- rinfo（2026-10-08）：路线引用但配方表没有的法术（附魔配方游离在 enchants
    -- 之外、魔棒两头都不在）并入候选池 —— 否则附魔 1→300 自动路线整段缺。
    -- 字段口径与上面 rows 候选一致（rinfo 是生成器落的纯数值兜底表）。
    if LV and type(LV.rinfo) == "table" then
        for spell, seed in pairs(LV.rinfo) do
            local ri=ClientRecipe(seed,spell,slug)
            if type(spell) == "number" and not recOf[spell]
               and type(ri.learn) == "number" and type(ri.grey) == "number"
               and ri.grey > ri.learn
               and type(ri.mats) == "table" and #ri.mats > 0 then
                local ok = not ri.clientUnavailable and not (opts.learnedOnly and not LearnKnown(spell))
                local economy=ns.ProfEconomy
                local recipe=economy and economy.FindRecipe(slug,spell)
                if recipe and economy.LearningEligibility and not economy.LearningEligibility(recipe,specSnapshot) then ok=false end
                if recipe and (recipe.cooldown or recipe.cooldownUnknown or recipe.clientPending or recipe.outputConflict) then ok=false end
                if economy and economy.Policy(opts.exclusions or economy.GetPolicies(slug),{key=slug..":"..spell,spell=spell}) then ok=false end
                local formula=recipe and economy.FormulaFor(recipe,{allowLimitedFormulas=economy.AllowLimitedFormulas(opts)})
                if formula and not formula.usable then ok=false end
                local cost, unpriced = 0, false
                if ok then
                    for _, m in ipairs(ri.mats) do
                        local p = MatPrice(m[1])
                        if p then
                            cost = cost + p * (m[2] or 1)
                        else
                            unpriced = true
                        end
                    end
                end
                if ok then
                    local y = (type(ri.yellow) == "number") and ri.yellow or ri.learn
                    local g = (type(ri.green) == "number") and ri.green or y
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
                        formula=formula,
                        base = base, unknown = unknown or nil,
                        learnO = math.max(1, math.min(ri.learn, y - 25)),
                    }
                    recOf[spell] = ri
                end
            end
        end
    end
    return cands, recOf
end

-- ── 贪心逐技能点模拟 ────────────────────────────────────────────────────────
-- allowUnpriced=false 时无价配方不参与（「只用拍卖行可购材料」的严格口径）；
-- 严格模拟产生的缺口由 FillGaps 放宽回填（2026-10-09 修缺口误报）。

local function Eligible(c, allowUnpriced)
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
local function MetricOf(scheme, c, g, paid)
    local f=c.formula
    local fee=f and not f.known and not (paid and paid[f.id or f.recipeKey]) and (f.cost or 0) or 0
    if scheme == "cheapest" then return c.cost / g+fee end
    if scheme == "crafts" then return 1 / g end
    if scheme == "optim" then return (c.base or 0) / g end
    return c.cost / g+fee
end

-- The reference scoring modes retain their own priority, but consume the same
-- observed finite auction budget across every attempted craft and formula.
local FixedPurchase
local function SimulateSupply(cands,start,cap,scheme,opts)
    local economy=ns.ProfEconomy
    if not economy or not economy.AuctionSupplyOf then return end
    local caps,finite={},false
    for _,c in ipairs(cands) do
        for _,m in ipairs(c.mats) do
            local supply=economy.AuctionSupplyOf(nil,m[1])
            if supply then caps[m[1]]=supply.quantity;finite=true end
        end
        local f=c.formula
        if f and not f.known and f.source=="ah" then
            local supply=economy.AuctionSupplyOf(nil,f.id)
            if supply then caps[f.id]=supply.quantity;finite=true end
        end
    end
    local steps,gaps,demands,paid={},{},{},{}
    local formulaUsed,formulaChoices,materialCosts={},{},{}
    local materialTotal,priceCache=0,{}
    local function quote(id,need,reserved)
        if need==0 then return 0,true end
        local limit=caps[id] and math.max(0,caps[id]-(reserved or 0)) or nil
        local key=id..":"..need..":"..tostring(limit)
        local known=priceCache[key]
        if known then return known[1],known[2] end
        local entries,possible=FixedPurchase(id,need,limit)
        local cost=0
        for _,entry in ipairs(entries) do
            cost=cost+entry.cost
            if entry.unpriced then possible=false end
        end
        priceCache[key]={cost,possible}
        return cost,possible
    end
    local cur,progress=math.max(1,start or 1),0
    local guard=0
    while cur<cap and guard<100000 do
        guard=guard+1
        local best,score,bestPlan
        for _,c in ipairs(cands) do
            if Usable(scheme,c,cur,false) then
                local f=c.formula;local key=f and (f.id or f.recipeKey)
                local books={false}
                if f and not f.known and not paid[key] then
                    books={}
                    local remaining=f.id and caps[f.id] and math.max(0,caps[f.id]-(formulaUsed[f.id] or 0)) or nil
                    local context={nonAuctionable={},allowLimitedFormulas=economy.AllowLimitedFormulas(opts)}
                    if f.id and economy.NonAuctionableItem then context.nonAuctionable[f.id]=economy.NonAuctionableItem(f.id) end
                    local chosen=economy.FormulaFor(f.recipe,context,remaining)
                    if chosen and chosen.usable then books[#books+1]=chosen end
                    if chosen and chosen.source=="ah" then
                        local alternative=economy.FormulaFor(f.recipe,context,0)
                        if alternative and alternative.usable and alternative.source=="vendor" then books[#books+1]=alternative end
                    end
                end
                for _,book in ipairs(books) do
                    local added={}
                    for _,m in ipairs(c.mats) do added[m[1]]=(added[m[1]] or 0)+m[2] end
                    if book and book.source=="ah" then added[book.id]=added[book.id] or 0 end
                    local nextCosts,nextTotal,enough={},materialTotal,true
                    for id,n in pairs(added) do
                        local reserve=(formulaUsed[id] or 0)+(book and book.source=="ah" and book.id==id and 1 or 0)
                        local cost,possible=quote(id,(demands[id] or 0)+n,reserve)
                        if not possible then enough=false;break end
                        nextCosts[id]=cost
                        nextTotal=nextTotal+cost-(materialCosts[id] or 0)
                    end
                    local g=GainOf(scheme,c,cur)
                    if enough and g and g>0 then
                        local incremental=nextTotal-materialTotal
                        local metric=scheme=="crafts" and 1/g or scheme=="optim" and (c.base or 0)/g
                            or incremental/g+(book and book.cost or 0)
                        if not best or metric<score-1e-9 or (math.abs(metric-score)<1e-9 and
                            (incremental<bestPlan.incremental or incremental==bestPlan.incremental and c.spell<best.spell)) then
                            best,score,bestPlan=c,metric,{book=book,added=added,costs=nextCosts,total=nextTotal,incremental=incremental}
                        end
                    end
                end
            end
        end
        if not best then gaps[#gaps+1]={cur,cap-1};break end
        for id,n in pairs(bestPlan.added) do demands[id]=(demands[id] or 0)+n end
        for id,cost in pairs(bestPlan.costs) do materialCosts[id]=cost end
        materialTotal=bestPlan.total
        local book=bestPlan.book
        if book then
            local key=book.id or book.recipeKey
            paid[key]=true;formulaChoices[key]=book
            if book.source=="ah" then formulaUsed[book.id]=(formulaUsed[book.id] or 0)+1 end
        end
        local from=cur
        local gain=GainOf(scheme,best,cur)
        progress=progress+gain;local whole=math.floor(progress+1e-7)
        cur=math.min(cap,cur+whole);progress=progress-whole
        local last=steps[#steps]
        if last and last[3]==best.spell then last[2]=cur;last[4]=last[4]+1
        else steps[#steps+1]={from,cur,best.spell,1,item=best.item} end
    end
    if cur<cap and #gaps==0 then gaps[#gaps+1]={cur,cap-1} end
    return steps,gaps,cur,formulaChoices,finite
end

local function Simulate(cands, start, cap, allowUnpriced, scheme)
    local steps, gaps = {}, {}
    local banned = {}
    local paid={}
    local cur = math.max(1, math.min(cap - 1, start or 1))
    local guard = 0

    while cur < cap do
        guard = guard + 1
        if guard > 4000 then break end

        -- 当前技能点上最优的配方
        local best, bestMetric
        for _, c in ipairs(cands) do
            if not banned[c.spell] and Usable(scheme, c, cur, allowUnpriced) then
                local g = GainOf(scheme, c, cur)
                if g then
                    local metric = MetricOf(scheme, c, g, paid)
                    if not best or metric < bestMetric - 1e-9
                       or (metric < bestMetric + 1e-9 and c.grey > best.grey) then
                        best, bestMetric = c, metric
                    end
                end
            end
        end

        if not best then
            -- 缺口：跳到下一个可学配方，或宣告到顶无解
            local nxt
            for _, c in ipairs(cands) do
                if not banned[c.spell] and Usable(scheme, c, cur, allowUnpriced) then
                    local lo = (scheme == "optim") and (c.learnO or c.learn) or c.learn
                    if lo > cur and (not nxt or lo < nxt) then nxt = lo end
                end
            end
            if nxt then
                gaps[#gaps + 1] = { cur, nxt - 1 }
                cur = nxt
            else
                if cur < cap then gaps[#gaps + 1] = { cur, cap - 1 } end
                cur = cap
            end
        else
            -- 以 best 一路做到它变灰 / 出现更优配方
            if best.formula then paid[best.formula.id or best.formula.recipeKey]=true end
            bestMetric=MetricOf(scheme,best,GainOf(scheme,best,cur),paid)
            local from = cur
            local crafts = 0
            while cur < cap do
                local g = Gain(cur, best)
                if not g then break end
                crafts = crafts + 1 / g
                cur = cur + 1
                local stop = false
                for _, c in ipairs(cands) do
                    if c ~= best and not banned[c.spell] and Usable(scheme, c, cur, allowUnpriced) then
                        local g2 = GainOf(scheme, c, cur)
                        if g2 and MetricOf(scheme, c, g2, paid) < bestMetric - 1e-9 then
                            stop = true
                            break
                        end
                    end
                end
                if stop then break end
            end
            local qty = math.max(1, math.ceil(crafts - 1e-9))
            local last = steps[#steps]
            if last and last[3] == best.spell and last[2] + 1 == from then
                last[2] = cur - 1
                last[4] = last[4] + qty
                last.cost = last.cost + best.cost * qty
            else
                steps[#steps + 1] = {
                    from, cur - 1, best.spell, qty,
                    cost = best.cost * qty, item = best.item,
                    unpriced = best.unpriced,
                }
            end
        end
    end
    return steps, gaps
end

-- 区间模拟（缺口回填用）：在 [a, b] 内放宽条件跑贪心，返回段列表与残余缺口。
local function SimulateRange(cands, a, b, scheme)
    local steps = {}
    local banned = {}
    local paid={}
    local cur = a
    local guard = 0
    while cur <= b do
        guard = guard + 1
        if guard > 1000 then break end
        local best, bestMetric
        for _, c in ipairs(cands) do
            if not banned[c.spell] and CanUse(scheme, c, cur)
               and not ((scheme == "optim") and (c.cd or c.unknown)) then
                local g = GainOf(scheme, c, cur)
                if g then
                    local metric = MetricOf(scheme, c, g, paid)
                    if not best or metric < bestMetric - 1e-9
                       or (metric < bestMetric + 1e-9 and c.grey > best.grey) then
                        best, bestMetric = c, metric
                    end
                end
            end
        end
        if not best then
            local nxt
            for _, c in ipairs(cands) do
                if not banned[c.spell] and not ((scheme == "optim") and (c.cd or c.unknown)) then
                    local lo = (scheme == "optim") and (c.learnO or c.learn) or c.learn
                    if lo > cur and lo <= b and (not nxt or lo < nxt) then nxt = lo end
                end
            end
            if not nxt then break end
            cur = nxt
        else
            if best.formula then paid[best.formula.id or best.formula.recipeKey]=true end
            bestMetric=MetricOf(scheme,best,GainOf(scheme,best,cur),paid)
            local from = cur
            local crafts = 0
            while cur <= b do
                local g = Gain(cur, best)
                if not g then break end
                crafts = crafts + 1 / g
                cur = cur + 1
                local stop = false
                for _, c in ipairs(cands) do
                    if c ~= best and not banned[c.spell] and CanUse(scheme, c, cur)
                       and cur <= b and not ((scheme == "optim") and (c.cd or c.unknown)) then
                        local g2 = GainOf(scheme, c, cur)
                        if g2 and MetricOf(scheme, c, g2, paid) < bestMetric - 1e-9 then
                            stop = true
                            break
                        end
                    end
                end
                if stop then break end
            end
            local qty = math.max(1, math.ceil(crafts - 1e-9))
            local to = math.min(cur - 1, b)
            local last = steps[#steps]
            if last and last[3] == best.spell and last[2] + 1 == from then
                last[2] = to
                last[4] = last[4] + qty
                last.cost = last.cost + best.cost * qty
            else
                steps[#steps + 1] = {
                    from, to, best.spell, qty,
                    cost = best.cost * qty, item = best.item,
                    unpriced = best.unpriced, est = true,
                }
            end
        end
    end
    -- 残余缺口：区间内没有任何段覆盖到的地方（真无解）
    local coverTo = a - 1
    for _, s in ipairs(steps) do
        if s[1] <= coverTo + 1 then coverTo = math.max(coverTo, s[2]) end
    end
    local resid = (coverTo < b) and { coverTo + 1, b } or nil
    return steps, resid
end

-- 相邻同配方段合并（回填段与主段在缺口边界拼回一条）
local function MergeSteps(steps)
    local out = {}
    for _, s in ipairs(steps) do
        local last = out[#out]
        if last and last[3] == s[3] and last[2] + 1 == s[1] then
            last[2] = s[2]
            last[4] = last[4] + s[4]
            last.cost = (last.cost or 0) + (s.cost or 0)
            if s.unpriced then last.unpriced = true end
            if s.est then last.est = true end
        else
            out[#out + 1] = s
        end
    end
    return out
end

-- 缺口回填：对每段缺口放宽「只用可购材料」跑区间模拟，能填的填、填不动的留缺口。
local function FillGaps(cands, steps, gaps, scheme)
    local out = {}
    local si = 1
    for _, g in ipairs(gaps) do
        while si <= #steps and steps[si][2] < g[1] do
            out[#out + 1] = steps[si]
            si = si + 1
        end
        local fills, resid = SimulateRange(cands, g[1], g[2], scheme)
        for _, s in ipairs(fills) do out[#out + 1] = s end
        if resid then out[#out + 1] = { gap = resid } end
    end
    while si <= #steps do
        out[#out + 1] = steps[si]
        si = si + 1
    end
    local newSteps, newGaps = {}, {}
    for _, it in ipairs(out) do
        if it.gap then
            newGaps[#newGaps + 1] = it.gap
        else
            newSteps[#newSteps + 1] = it
        end
    end
    return MergeSteps(newSteps), newGaps
end

-- ── 汇总：材料采购成本 / 材料聚合 / 制作次数 ─────────────────────────────
-- Aggregate demand before choosing vendor bundles. Fixed guide steps retain
-- their recipes/counts; purchase leftovers are shared across those steps.

FixedPurchase = function(id, need, auctionLimit)
    local db = ns.ProfItemPrices
    local offers = db and db.GetOffers and db.GetOffers(id) or {}
    local best, valid = nil, {}
    local function vendorEntry(offer, count, demand)
        local quantity = offer.quantity or offer.bundleSize
        return {id, count, id=id, count=count, need=demand,
            cost=count/quantity*offer.price, unit=offer.price/quantity,
            vendor=true, source="vendor", npcID=offer.npcID,
            url=offer.url, bundleSize=quantity, bundlePrice=offer.price,
            reference=offer.reference, estimated=offer.estimated, quoteSource=offer.source,
            priceSource=offer.priceSource, priceBasis=offer.priceBasis, verifiedAt=offer.verifiedAt}
    end
    local function auctionEntry(count, price)
        return {id, count, id=id, count=count, need=count, cost=(price or 0)*count,
            unit=price or 0, source="ah", vendor=false, unpriced=price == nil or nil}
    end
    for _, offer in ipairs(offers) do
        local quantity = offer.quantity or offer.bundleSize
        if offer.unlimited == true and type(offer.price) == "number" and offer.price >= 0
            and type(quantity) == "number" and quantity >= 1 and quantity == math.floor(quantity)
            and offer.available ~= false and offer.purchasable ~= false and not offer.hasExtendedCost
            and (not offer.currencyID or offer.currencyID == 0) then
            local count = math.ceil(need / quantity) * quantity
            local cost = count / quantity * offer.price
            if not best or cost < best.cost or cost == best.cost and count < best.count then
                best = vendorEntry(offer, count, need)
            end
            valid[#valid+1] = offer
        end
    end
    if best and best.cost == 0 then return {best}, true end
    local economy = ns.ProfEconomy
    local price = not (economy and economy.NonAuctionableItem and economy.NonAuctionableItem(id)) and AHPrice(id) or nil
    if auctionLimit == nil and economy and economy.AuctionSupplyOf then
        local supply = economy.AuctionSupplyOf(nil, id)
        auctionLimit = supply and supply.quantity
    end
    local limit = auctionLimit or math.huge
    local entries = best and {best} or {auctionEntry(need, price)}
    local cost, count = best and best.cost or math.huge, best and best.count or need
    if price then
        if need <= limit and (price*need < cost or price*need == cost and need < count) then
            entries, cost, count = {auctionEntry(need, price)}, price*need, need
        end
        -- Compare each quotation's full packs with an AH remainder. A mixed
        -- purchase must contain at least one real NPC transaction.
        for _, offer in ipairs(valid) do
            local quantity = offer.quantity or offer.bundleSize
            local least = math.max(1, math.ceil((need-limit)/quantity))
            local most = math.floor((need-1)/quantity)
            for _, packs in ipairs({least, most}) do
                local vendorCount = packs*quantity
                local remainder = need-vendorCount
                if packs >= least and packs <= most and remainder > 0 and remainder <= limit then
                    local mixedCost = packs*offer.price+remainder*price
                    if mixedCost < cost or mixedCost == cost and need < count then
                        entries = {vendorEntry(offer, vendorCount, vendorCount), auctionEntry(remainder, price)}
                        cost, count = mixedCost, need
                    end
                end
            end
        end
    end
    return entries, best ~= nil or price ~= nil and need <= limit
end

local function SupplySummary(result)
    local economy=ns.ProfEconomy
    if economy and economy.SummarizeAuctionSupply then economy.SummarizeAuctionSupply(result) end
    return result
end

local function SummarizeCore(steps, recOf, slug, formulaChoices,opts)
    local live={}
    for spell,rec in pairs(recOf) do live[spell]=ClientRecipe(rec,spell,slug) end
    recOf=live
    local total, crafts = 0, 0
    -- 产物收益（2026-10-09 四轮）：AH 变卖 / NPC 直卖两条口径
    local productAH, productNPC, productPartial = 0, 0, false
    local mats, firstAt = {}, {}
    local completeCost, referencePrices = true, nil
    for _, st in ipairs(steps) do
        local rec = recOf[st[3]]
        local ml = rec and (rec[12] or rec.mats) or nil
        st.cost = 0
        st.unpriced = (not st.checkpoint and (not ml or rec and rec.clientPending)) or nil
        if st.unpriced then completeCost = false end
        crafts = crafts + (st[4] or 0)
        -- 产物收益：产物 itemID（rec[2]）× 一次产量（rec[3]）× 制作次数（st[4]）
        local prod = rec and rec[2]
        if type(prod) == "number" and type(rec[3] or rec.count)=="number" then
            local outN = (st[4] or 0) * (rec[3] or rec.count)
            RequestProduct(prod)   -- 异步预热产物物品（卖店价要等物品数据到货）
            local ah = AHPrice(prod)
            if ah then
                productAH = productAH + ah * outN
            else
                productPartial = true
            end
            local sp = NPCSellPrice(prod)
            if sp then productNPC = productNPC + sp * outN end
        elseif not st.checkpoint then productPartial=true
        end
        if ml then
            for _, m in ipairs(ml) do
                local id = m[1]
                mats[id] = (mats[id] or 0) + (m[2] or 1) * (st[4] or 0)
                if not firstAt[id] or st[1] < firstAt[id] then firstAt[id] = st[1] end
            end
        end
    end
    local formulas,formulasTotal,formulaComplete={},0,true
    local economy=ns.ProfEconomy
    if economy and economy.CollectFormulas then
        formulas=economy.CollectFormulas(steps,slug,{allowLimitedFormulas=economy.AllowLimitedFormulas(opts)})
    end
    local reserved={}
    for i,f in ipairs(formulas) do
        local chosen=formulaChoices and formulaChoices[f.id or f.recipeKey]
        if chosen then
            local recipes=f.recipes
            f=economy.Copy(chosen);f.recipes=recipes;formulas[i]=f
        end
        formulasTotal=formulasTotal+(f.cost or 0)
        formulaComplete=formulaComplete and f.costComplete and f.usable
        if f.source=="ah" then reserved[f.id]=(reserved[f.id] or 0)+(f.count or 1) end
    end
    local list, purchaseOf = {}, {}
    for id, n in pairs(mats) do
        if n > 0 then
            local supply=economy and economy.AuctionSupplyOf and economy.AuctionSupplyOf(nil,id)
            local limit=supply and math.max(0,supply.quantity-(reserved[id] or 0)) or nil
            local entries = FixedPurchase(id, n, limit)
            purchaseOf[id] = entries
            for _, entry in ipairs(entries) do
                list[#list + 1] = entry
                total = total + entry.cost
                if entry.unpriced or entry.estimated and not entry.reference then completeCost=false end
                referencePrices = referencePrices or entry.reference
            end
        end
    end
    table.sort(list, function(a, b)
        local fa, fb = firstAt[a[1]] or math.huge, firstAt[b[1]] or math.huge
        if fa ~= fb then return fa < fb end
        if a[2] ~= b[2] then return a[2] > b[2] end
        return a[1] < b[1]
    end)
    local vendorTotal = 0
    for _, e in ipairs(list) do
        if e.vendor then vendorTotal = vendorTotal + e.cost end
    end
    -- Attribute the cash paid for each new pack to the first step that needs it.
    -- Later steps consume that pack's remainder without charging it a second time.
    local consumed = {}
    for _, st in ipairs(steps) do
        local rec = recOf[st[3]]
        for _, mat in ipairs(rec and (rec[12] or rec.mats) or {}) do
            local id, need = mat[1], (mat[2] or 1) * (st[4] or 0)
            for _, entry in ipairs(purchaseOf[id] or {}) do
                local before = consumed[entry] or 0
                local used = math.min(need, entry.need-before)
                if used > 0 then
                    need = need-used
                    consumed[entry] = before+used
                    if entry.unpriced then st.unpriced = true
                    elseif entry.vendor and entry.bundleSize then
                        local packs = math.ceil(consumed[entry] / entry.bundleSize) - math.ceil(before / entry.bundleSize)
                        st.cost = st.cost + packs * entry.bundlePrice
                    else st.cost = st.cost + used * entry.unit end
                end
            end
        end
    end
    local formulaAH,formulaVendor=0,0
    for _,f in ipairs(formulas) do
        if f.source=="vendor" then formulaVendor=formulaVendor+(f.cost or 0)
        elseif f.source=="ah" then formulaAH=formulaAH+(f.cost or 0) end
        local keys={};for _,r in ipairs(f.recipes or {}) do keys[r.key or r.profession..":"..r.spell]=true end
        for _,st in ipairs(steps) do
            if keys[(st.profession or slug)..":"..tostring(st[3])] then
                st.cost=(st.cost or 0)+(f.cost or 0);st.formulasTotal=(st.formulasTotal or 0)+(f.cost or 0)
                st.unpriced=st.unpriced or f.unpriced;break
            end
        end
        referencePrices=referencePrices or f.offer and f.offer.reference
    end
    return total, crafts, list, firstAt, vendorTotal, formulas, formulasTotal,
           productAH, productNPC, productPartial,
           {completeCost=completeCost and formulaComplete,formulaComplete=formulaComplete,referencePrices=referencePrices,
            formulaAHTotal=formulaAH,formulaVendorTotal=formulaVendor}
end

-- Freeze sale evidence at calculation time, alongside procurement. Cached and
-- executing plans retain this accounting until an explicit recalculation.
function RA.ApplyRecovery(result,slug,opts,snapshot)
    local recovery=ns.ProfRecovery
    if not result or not recovery or result.recoveryRevision==1 then return result end
    opts=ns.ProfEconomy.Copy(opts or {})
    local db=DungeonsForeverDB and DungeonsForeverDB.prof
    if opts.recoveryEnabled==nil then opts.recoveryEnabled=not db or db.recoveryEnabled~=false end
    if opts.recoveryFeePercent==nil then opts.recoveryFeePercent=db and db.recoveryFeePercent or nil end
    if not snapshot then snapshot=ns.ProfEconomy.Capture(slug,opts) end
    if not snapshot.recovery then recovery.Capture(snapshot,opts) end
    result.scheme=result.scheme or opts.scheme or "fixed"
    return recovery.Apply(result,snapshot) or result
end
function RA.ValidateRecovery(result,opts)
    local recovery=ns.ProfRecovery
    if result and recovery and recovery.Changed(result,opts) then
        result.stale=true;result.staleReason="recovery"
        result.recoveryStale=true
    end
    return result
end

-- 公开入口：固定路线复用同一套材料聚合/定价（steps = {起,止,spell,次数}）
function RA.SummarizeSteps(steps, slug, opts)
    opts = opts or {}
    local blocked,goalRequired
    steps,blocked,goalRequired=RA.FilterFixedSpecializations(slug,steps,opts)
    local economy,solver=ns.ProfEconomy,ns.ProfRouteSolver
    if economy and solver and economy.HasToolGoals(slug,opts)
        and not goalRequired and #blocked==0 then
        local planned=economy.Copy(opts)
        planned.fixedSteps=steps;planned.scheme="fixed";planned.start=steps[1] and steps[1][1] or opts.start or 1
        planned.target=opts.target or steps[#steps] and steps[#steps][2] or 300
        local result,job=solver.Compute(slug,planned)
        result.mode="fixed";result.scheme="fixed"
        return RA.StampSpecializations(RA.StampVendorQuotes(result,planned),slug,planned,job and job.snap)
    end
    local _rf = ns.EnsureProfRecipes
    local Rg = _rf and _rf()[slug] or ns.ProfRecipes and ns.ProfRecipes[slug]
    local LV = ns.ProfLeveling and ns.ProfLeveling[slug]
    if not (Rg and type(Rg.rows)=="table" or LV and type(LV.rinfo)=="table") then return nil end
    Rg=Rg or {}
    local recOf = {}
    for _, rec in ipairs(Rg.rows or {}) do recOf[rec[1]] = rec end
    if LV and type(LV.rinfo) == "table" then
        for spell, ri in pairs(LV.rinfo) do
            if not recOf[spell] then recOf[spell] = ri end
        end
    end
    local total, crafts, list, firstAt, vendorTotal, formulas, formulasTotal,
          productAH, productNPC, productPartial, quoteInfo =
        SummarizeCore(steps, recOf, slug,nil,opts)
    local result=RA.StampVendorQuotes(SupplySummary({
        steps = steps, mats = list, firstAt = firstAt,
        matTotal = total, formulas = formulas, formulasTotal = formulasTotal,
        total = total+formulasTotal, vendorTotal = vendorTotal+quoteInfo.formulaVendorTotal,
        ahTotal = total-vendorTotal+quoteInfo.formulaAHTotal,
        formulaAHTotal=quoteInfo.formulaAHTotal,formulaVendorTotal=quoteInfo.formulaVendorTotal,formulaRevision=1,
        formulaComplete=quoteInfo.formulaComplete,
        productAH = productAH, productNPC = productNPC, productPartial = productPartial,
        crafts = crafts,
        priced = true, completeCost = quoteInfo.completeCost, costComplete = quoteInfo.completeCost,
        referencePrices = quoteInfo.referencePrices,
        snapshotAge = SnapshotSec(),
        snapshotDays = priceCache.__minAge,
        stamp = time and time() or 0,
    }),opts)
    result.specializationBlocked=blocked
    result.specializationGoalRequired=goalRequired
    if #blocked>0 or goalRequired then
        result.feasible=false; result.targetReached=false
        result.diagnostics={{code="specializationFixed"}}
    end
    return RA.ApplyRecovery(RA.StampSpecializations(result,slug,opts),slug,opts)
end

-- Fixed guides share one retained quote across page, shopping list and HUD.
-- The generic SummarizeSteps stays fresh for explicit top-ups/quantity changes.
local function fixedCopy(value)
    if type(value)~="table" then
        if type(value)~="function" and type(value)~="userdata" then return value end
        return
    end
    local out={};for key,item in pairs(value) do out[key]=fixedCopy(item) end;return out
end
local function fixedStore()
    DungeonsForeverDB=DungeonsForeverDB or {}
    local db=DungeonsForeverDB;db.prof=db.prof or {};db.prof.fixedRouteCache=db.prof.fixedRouteCache or {}
    local character=ns.ProfEconomy.CharacterKey()
    local store=db.prof.fixedRouteCache[character]
    if type(store)~="table" then store={};db.prof.fixedRouteCache[character]=store end
    return store
end
function RA.ClearFixedSummary(slug) fixedStore()[slug]=nil end
function RA.FixedOnlyResult(slug,opts)
    opts=opts or {}
    local guide=ns.ProfLeveling and ns.ProfLeveling[slug] or {}
    local target=tonumber(opts.target) or 300
    local selected={}
    for _,step in ipairs(guide.steps or {}) do
        if step[1]>=target then break end
        local row=fixedCopy(step)
        if row[2]>target then
            row[4]=math.max(1,math.ceil(row[4]*(target-row[1])/(row[2]-row[1])-1e-9));row[2]=target
        end
        selected[#selected+1]=row
    end
    local result=RA.FixedSummary(slug,selected,opts)
    if result then return result end
    return {mode="fixed",scheme="fixed",target=target,start=1,steps=selected,mats={},formulas={},
        gaps={},total=0,matTotal=0,ahTotal=0,vendorTotal=0,crafts=0,priced=false,clientPending=true}
end
function RA.FixedSummary(slug,steps,opts)
    opts=opts or {}
    local keys={}
    for _,step in ipairs(steps or {}) do
        keys[#keys+1]=table.concat({tostring(step.profession or slug),tostring(step[1]),
            tostring(step[2]),tostring(step[3]),tostring(step[4])},":")
    end
    local signature=table.concat(keys,"|")
    local store=fixedStore();local record=store[slug]
    local result=record and record.signature==signature and record.result
    if not result then
        result=RA.SummarizeSteps(fixedCopy(steps),slug,opts)
        if not result then return end
        result.mode="fixed";result.scheme="fixed"
        result.target=opts.target or steps and steps[#steps] and steps[#steps][2]
        store[slug]={signature=signature,result=result}
    end
    local current=ns.ProfEconomy.Copy(opts)
    local db=DungeonsForeverDB.prof
    if current.recoveryEnabled==nil then current.recoveryEnabled=db.recoveryEnabled~=false end
    if current.recoveryFeePercent==nil then current.recoveryFeePercent=db.recoveryFeePercent end
    return RA.ValidateRecovery(RA.ValidateSpecializationPlan(RA.ValidateVendorQuotes(result,opts),slug,opts),current)
end

-- ── 对外入口 ────────────────────────────────────────────────────────────────
-- Compute(slug, opts) → result | nil
-- result = { steps, gaps, mats, firstAt, total, matTotal, formulas, formulasTotal,
--            vendorTotal, ahTotal, crafts, start, target, stamp, priced, filled }
-- steps[i] = {起, 止, spellID, 次数, cost=…, item=…, unpriced=…, est=…}
--   est=true = 缺口回填段：配方含无价材料，花费按已估价材料估算（未知按 0）
--   total = 材料采购支出 = ahTotal（拍卖行）+ vendorTotal（商人直售）。

-- ▸ 止点口径统一（2026-10-09，用户点名「42-59 其实升到 60 那一点也是这个配方做的，
--   所以需要改成 42-60」）：Simulate 内部存的是**最后能做的技能值**（段末 to），
--   而固定路线（Data_ProfLeveling）的段存的是**练到的技能值**（1–36 / 36–45 首尾相接）。
--   同一张表由 ProfessionUI 同时渲染两种路线 ⇒ 口径必须一致，否则固定路线数字相邻、
--   自动路线数字重叠错位。故**对外（专业页 / HUD）一律 +1** 转成「练到的技能值」。
--   段次数 qty 的积分本来就含段末那一点（qty == Σ 1/P over [from, to]），
--   所以止点显示 to+1 与 qty 自洽 —— 这正是用户要的那个 60。
--   ⚠️ 内部判据（MergeSteps / FillGaps 的 `last[2] + 1 == from`、衔接性、coverTo）
--   必须继续吃「最后能做」口径，转换只发生在最后一次浅拷贝上，两者互不影响。
local function ToReached(steps)
    if type(steps) ~= "table" then return steps end
    local out = {}
    for i, st in ipairs(steps) do
        local c = {}
        for k, v in pairs(st) do c[k] = v end
        c[2] = (tonumber(st[2]) or 0) + 1
        out[i] = c
    end
    return out
end

function RA.Compute(slug, opts)
    opts = opts or {}
    local cands, recOf = BuildCandidates(slug, opts)
    if not cands then return nil end
    -- 「只用拍卖行可购材料」= 严格模拟（无价配方不参与）；产生的缺口随后放宽回填
    -- 方案（2026-10-10）：未传/非法 = 最省钱（产品默认；调用方不传也拿到新口径）
    local scheme = opts.scheme
    if scheme == nil or not SCHEME_LABEL[scheme] then scheme = "cheapest" end
    -- 目标等级上限（2026-10-09 v2）：opts.target（如 200）→ 模拟与回填都 clamp 在内
    local cap = tonumber(opts.target) or CAP
    cap = math.max(2, math.min(CAP, math.floor(cap)))
    local supplySteps,supplyGaps,plannedTo,formulaChoices,finiteSupply=SimulateSupply(cands,opts.start,cap,scheme,opts)
    local steps,gaps
    if supplySteps then steps,gaps=supplySteps,supplyGaps
    else steps,gaps=Simulate(cands,opts.start,cap,allowUnpriced,scheme) end
    local filled = false
    if not supplySteps and not allowUnpriced and #gaps > 0 then
        steps, gaps = FillGaps(cands, steps, gaps, scheme)
        for _, st in ipairs(steps) do
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
    end
    local stepsOut = supplySteps or ToReached(steps)
    local total, crafts, mats, firstAt, vendorTotal, formulas, formulasTotal,
          productAH, productNPC, productPartial, quoteInfo =
        SummarizeCore(stepsOut, recOf, slug,formulaChoices,opts)
    return RA.StampVendorQuotes(SupplySummary({
        scheme = scheme,
        supplyConstrained=finiteSupply==true,plannedTo=plannedTo,
        targetReached=supplySteps and plannedTo>=cap or nil,
        partial=supplySteps and #stepsOut>0 and plannedTo<cap or nil,
        feasible=#stepsOut>0 or plannedTo and plannedTo>=cap or false,
        status=plannedTo and plannedTo<cap and (#stepsOut>0 and "incomplete" or "infeasible") or "complete",
        steps = stepsOut, gaps = gaps, mats = mats, firstAt = firstAt,
        total = total+formulasTotal, matTotal = total,
        formulas = formulas, formulasTotal = formulasTotal,
        vendorTotal = vendorTotal+quoteInfo.formulaVendorTotal, ahTotal = total-vendorTotal+quoteInfo.formulaAHTotal,
        formulaAHTotal=quoteInfo.formulaAHTotal,formulaVendorTotal=quoteInfo.formulaVendorTotal,formulaRevision=1,
        formulaComplete=quoteInfo.formulaComplete,
        productAH = productAH, productNPC = productNPC, productPartial = productPartial,
        crafts = crafts,
        start = math.max(1, math.min(CAP - 1, opts.start or 1)),
        target = cap,
        priced = true, completeCost = quoteInfo.completeCost, costComplete = quoteInfo.completeCost,
        referencePrices = quoteInfo.referencePrices,
        filled = filled,
        snapshotAge = SnapshotSec(),         -- 秒：真实扫描时间戳（TimeOfLast*Scan）
        snapshotDays = priceCache.__minAge,  -- 天：价格插件库内最近数据日差（回退用）
        stamp = time and time() or 0,
    }),opts)
end

-- 缓存（失效：RA.Invalidate() / 设置变更 / 手动重算 / 超时）
local cache = {}

function RA.Invalidate()
    if ns.ProfRecovery and ns.ProfRecovery.Invalidate then ns.ProfRecovery.Invalidate() end
    for k in pairs(cache) do cache[k] = nil end
    for k in pairs(priceCache) do
        if k ~= "__any" then priceCache[k] = nil end
    end
    priceCache.__any = nil
end

local priceWatchers = {}
function RA.OnPricesChanged(fn)
    if type(fn) == "function" then priceWatchers[#priceWatchers + 1] = fn end
end

local ahWatch = CreateFrame("Frame")
ahWatch:RegisterEvent("AUCTION_HOUSE_CLOSED")
ahWatch:SetScript("OnEvent", function()
    C_Timer.After(0, function()
        RA.Invalidate()
        for _, fn in ipairs(priceWatchers) do pcall(fn) end
    end)
end)

local function Fingerprint(opts)
    return string.format("%s|%s|%s|%s|%s|%s",
        tostring(opts.start), tostring(opts.onlyAH),
        tostring(opts.learnedOnly),
        tostring(opts.target and math.floor(tonumber(opts.target) or CAP)),
        tostring(opts.scheme),tostring(ns.ProfEconomy and ns.ProfEconomy.AllowLimitedFormulas(opts)))
end

-- Get(slug, opts) → result | nil（带缓存）
function RA.Get(slug, opts)
    opts = opts or {}
    local fp = Fingerprint(opts)
    local c = cache[slug]
    local now = (type(time) == "function") and time() or 0
    if c and c.fp == fp and (now - c.stamp) < CACHE_TTL then return c.res end
    local res = RA.Compute(slug, opts)
    cache[slug] = { fp = fp, res = res, stamp = now }
    return res
end

-- Route snapshots are retained until the player explicitly recalculates. Price,
-- recipe and skill events can mark a quote stale but never launch a new search.
do
    local E,S=ns.ProfEconomy,ns.ProfRouteSolver
    if E and S then
        local oldCompute,oldInvalidate=RA.Compute,RA.Invalidate
        local slots,results,active,watchers={},{},{},{}
        local revision=0
        local CACHE_VERSION=3
        local EMPTY_RESULT_REVISION=2
        local function stamp() return time and time() or 0 end
        local function serializable(value,seen)
            local kind=type(value)
            if kind=="number" or kind=="string" or kind=="boolean" then return value end
            if kind~="table" then return nil end
            seen=seen or {}; if seen[value] then return nil end
            seen[value]=true; local out={}
            for k,v in pairs(value) do
                if type(k)=="number" or type(k)=="string" then out[k]=serializable(v,seen) end
            end
            seen[value]=nil; return out
        end
        local function saved(character)
            DungeonsForeverDB=DungeonsForeverDB or {}
            local db=DungeonsForeverDB; db.prof=db.prof or {}; db.prof.routeCache=db.prof.routeCache or {}
            local char=character or E.CharacterKey(); local data=db.prof.routeCache[char]
            if type(data)~="table" or data.version~=CACHE_VERSION then
                data={version=CACHE_VERSION,routes={},active={}}; db.prof.routeCache[char]=data
            end
            data.routes=data.routes or {}; data.active=data.active or {}
            return data
        end
        function RA.Gain(sk,learn,yellow,green,grey)
            return E.Gain({learn=learn,yellow=yellow or learn,green=green or yellow or learn,grey=grey},sk)
        end
        function RA.OptionsFor(slug,start)
            local pd=ns.ProfModule
            local function setting(k,default)
                if pd and pd.Setting then local v=pd.Setting(k); if v~=nil then return v end end
                return default
            end
            local scheme=pd and pd.SettingRaw and pd.SettingRaw("autoScheme") or "cheapest"
            local target=300
            local db=DungeonsForeverDB and DungeonsForeverDB.prof
            if slug=="cooking" and db and db.cookingRoute=="fishing" then scheme="fishing" end
            if db and db.lvTarget then target=tonumber(db.lvTarget[slug]) or target end
            local follows=ns.ProfFollow and ns.ProfFollow.Following and ns.ProfFollow.Following(slug)
            local current=(E.Professions()[slug] or {}).cur
            local fromCurrent=follows or setting("autoFromCurrent",true)
            return {start=fromCurrent and (start or current or 1) or 1,fromCurrent=fromCurrent,
                target=target,scheme=scheme,onlyAH=setting("autoOnlyAH",false),
                learnedOnly=setting("autoLearnedOnly",false),allowSecondaryLeveling=setting("autoSecondaryLeveling",false),
                allowLimitedFormulas=setting("autoBuyLimitedFormulas",E.AllowLimitedFormulas()),
                autoCraftTools=setting("autoCraftTools",true),
                recoveryEnabled=setting("recoveryEnabled",true),recoveryFeePercent=setting("recoveryFeePercent",nil),
                secondaryProfession=E.GetRoutePartner(slug),
                engineeringSpecialization=E.GetEngineeringSpecialization and E.GetEngineeringSpecialization() or "none",
                exclusions=E.Copy(E.GetPolicies(slug))}
        end
        function RA.OnPlanChanged(fn) if type(fn)=="function" then watchers[#watchers+1]=fn end end
        local function options(slug,opts)
            opts=E.Copy(opts or RA.OptionsFor(slug))
            opts.allowLimitedFormulas=E.AllowLimitedFormulas(opts)
            opts.autoCraftTools=E.ToolPlanningEnabled(opts)
            if opts.recoveryEnabled==nil then
                local db=DungeonsForeverDB and DungeonsForeverDB.prof
                opts.recoveryEnabled=not db or db.recoveryEnabled~=false
            end
            if opts.recoveryFeePercent==nil then
                local db=DungeonsForeverDB and DungeonsForeverDB.prof
                opts.recoveryFeePercent=db and db.recoveryFeePercent or nil
            end
            if opts.scheme==nil then opts.scheme="cheapest" end
            if opts.scheme=="fishing" then
                if slug~="cooking" then opts.scheme="cheapest"
                else opts.allowSecondaryLeveling=false;opts.secondaryProfession=nil end
            end
            opts.target=tonumber(opts.target) or 300
            opts.exclusions=E.Copy(opts.exclusions or E.GetPolicies(slug))
            local following=ns.ProfFollow and ns.ProfFollow.Following and ns.ProfFollow.Following(slug)
            if opts.follow or following then opts.start=(E.Professions()[slug] or {}).cur or opts.start or 1 end
            local context=E.RouteContext(slug,opts)
            opts.targetUnlearned=context.unlearned
            opts.secondaryProfession=context.requiresPartner and context.partner or nil
            opts.partnerRequired=context.requiresPartner and not context.partnerValid or false
            opts.profession=slug
            if opts.engineeringSpecialization==nil then
                opts.engineeringSpecialization=E.GetEngineeringSpecialization and E.GetEngineeringSpecialization() or "none"
            end
            local spec=specializationContext(slug,opts)
            opts.specializationFingerprint=spec and E.SpecializationFingerprint(spec) or ""
            -- Non-cost modes retain their per-step priorities. Only their
            -- engineering task procurement uses the shared recursive ledger.
            if (spec and (#(spec.goals or {})>0 or slug=="engineering" and spec.selectionConflict and opts.target>=200)
                or E.HasToolGoals(slug,opts))
                and opts.scheme~="cheapest" and opts.scheme~="fishing" then
                opts.specializationRecipeScore=function(recipe,state,snapshot,incremental)
                    local gain=E.Gain(recipe,(state.skill or {})[recipe.profession] or 1)
                    if gain<=0 then return math.huge end
                    if opts.scheme=="crafts" then return 1/gain end
                    if opts.scheme=="optim" then
                        local base=0
                        for _,material in ipairs(recipe.mats or {}) do
                            base=base+(NPCSellPrice(material[1]) or 0)*material[2]
                        end
                        return base
                    end
                    return incremental/gain
                end
            end
            return opts
        end
        local function signature(opts)
            -- Live skill is an input snapshot, not a cache identity. Otherwise
            -- every skill gain/reopening would silently replace the saved route.
            local startMode=opts.fromCurrent==false and ("fixed:"..tostring(opts.start or 1)) or "current"
            local sig=table.concat({tostring(opts.scheme),tostring(opts.target),tostring(opts.learnedOnly or false),
                tostring(opts.onlyAH or false),tostring(opts.allowSecondaryLeveling or false),startMode,
                E.PolicyFingerprint(opts.exclusions),tostring(opts.targetUnlearned),tostring(opts.secondaryProfession or ""),
                tostring(opts.specializationFingerprint or ""),tostring(opts.recoveryEnabled~=false),
                tostring(opts.recoveryFeePercent or "auto"),tostring(opts.allowLimitedFormulas),E.ToolFingerprint(opts.profession,opts)},"|")
            -- Verified carry is a calculation input, like live skill. UI/HUD
            -- reads supply the selected settings without this frozen seed.
            -- Synthetic requests still distinguish their explicit input stock.
            if opts.snapshot and (opts.executionSourcePlanID or next(opts.executionInventory or {})) then
                local items={}
                for id,n in pairs(opts.executionInventory or {}) do
                    items[#items+1]=tostring(id)..":"..tostring(type(n)=="table" and n.count or n)
                end
                table.sort(items)
                sig=sig.."|execution:"..tostring(opts.executionSourcePlanID or "")..":"..table.concat(items,",")
            end
            return sig
        end
        local function identities(slug,opts)
            local char=E.CharacterKey(); local sig=signature(opts)
            local scope=char.."|"..slug
            -- Synthetic snapshots are intentionally isolated and never persisted.
            if opts.snapshot then scope=scope.."|"..tostring(opts.snapshot); sig=sig.."|"..tostring(opts.start) end
            return scope.."|"..sig,scope,slug.."|"..sig,sig,char
        end
        local function remember(j,res)
            if j.opts.snapshot or res.status=="searching" then return end
            local db=saved(j.char)
            db.routes[j.savedKey]={slug=j.slug,signature=j.signature,options=serializable(j.opts),
                result=serializable(res),savedAt=stamp()}
            db.active[j.slug]=j.savedKey
        end
        local function updateSearchState(slug,result)
            local execution=ns.ProfExecution
            local frozen=execution and execution.GetPlan and execution.GetPlan(slug)
            if not frozen then return end
            local char=E.CharacterKey();local planID=frozen.planID
            local job
            for _,candidate in pairs(slots) do
                if candidate.slug==slug and candidate.char==char and not candidate.invalid and candidate.planID==planID then job=candidate;break end
            end
            if frozen.scheme and frozen.scheme~="cheapest" and not job then frozen.searchState=nil;return end
            -- Selected settings can restore another scheme's cache and change
            -- active[scope]. Diagnostics belong to the frozen calculation ID.
            local source=job and (job.published or job.result) or result and result.planID==planID and result
            if not source then
                for _,candidate in pairs(results) do if candidate.planID==planID then source=candidate;break end end
            end
            if not source then
                for _,record in pairs(saved(char).routes) do
                    if record.slug==slug and record.result and record.result.planID==planID then source=record.result;break end
                end
            end
            source=source or frozen.searchState or frozen
            local status=source.status
            if job then
                status=job.status or status
                if job.finished and status=="searching" then status=source.status end
            elseif status=="searching" then
                -- A persisted execution snapshot is not a live coroutine.
                status="interrupted"
            end
            -- Only diagnostics follow the optimizer. Recipes, purchases, goals,
            -- segment identities and execution facts remain frozen.
            frozen.searchState={status=status,expanded=job and job.expanded or source.expanded,
                improvements=job and job.improvements or source.improvements,
                initialTotal=source.initialTotal,bestTotal=source.bestTotal or (source.feasible~=false and source.total or nil),
                initialNetTotal=source.initialNetTotal,bestNetTotal=source.bestNetTotal or source.netTotal,
                netSavings=source.netSavings,recoveryOptimized=source.recoveryOptimized,
                savings=source.savings,budgetLimited=job and job.budgetLimited or source.budgetLimited,
                searchComplete=source.searchComplete,revision=source.revision,
                searchTermination=source.searchTermination,searchCpuMs=source.searchCpuMs,searchCpuLimitMs=source.searchCpuLimitMs,
                running=job~=nil and not job.finished and status=="searching" and coroutine.status(job.co)~="dead"}
        end
        local function publish(j,res)
            if not res or j.invalid then return end
            local execution=ns.ProfExecution
            if execution and execution.NormalizePlan and res.planVersion~=2 then
                res=execution.NormalizePlan(j.slug,res) or res
            end
            if not res.recoveryRevision then res=RA.ApplyRecovery(res,j.slug,j.opts,j.snap) end
            if not j.planID then
                if j.opts.snapshot then j.planID="synthetic:"..j.key
                else
                    local db=saved(j.char)
                    db.nextPlanID=(tonumber(db.nextPlanID) or 0)+1
                    j.planID=j.char..":"..tostring(db.nextPlanID)
                end
            end
            res.planID=j.planID
            res.executionOptions=serializable(j.opts)
            revision=revision+1; res.revision=revision
            res.routeModel=CACHE_VERSION
            res.formulaRevision=1
            res.vendorQuoteRevision=VENDOR_QUOTE_REVISION
            res.vendorQuoteData=vendorQuoteData()
            RA.StampFormulaPolicy(res,j.opts)
            res.professionPolicy=1; res.targetUnlearned=j.opts.targetUnlearned
            res.secondaryProfession=j.opts.secondaryProfession
            RA.StampSpecializations(res,j.slug,j.opts,j.snap)
            if not j.opts.snapshot and RA.FormulaPolicyChanged(res) then
                j.invalid=true;j.finished=true
                res=RA.ValidateFormulaPolicy(res)
            end
            if not j.opts.snapshot and RA.ToolPolicyChanged(res,j.slug) then
                j.invalid=true;j.finished=true;res=RA.ValidateToolPolicy(res,j.slug)
            end
            if not j.opts.snapshot and RA.SpecializationPlanChanged(res,j.slug) then
                j.invalid=true; j.finished=true
                res=RA.ValidateSpecializationPlan(res,j.slug)
            end
            res.emptyResultRevision=EMPTY_RESULT_REVISION
            res.cacheSignature=j.signature; res.inputStart=res.start or j.opts.start
            if j.stale then res.stale=true; res.staleReason=j.staleReason end
            j.published=res; results[j.key]=res; active[j.scope]=j.key
            remember(j,res)
            if not j.opts.snapshot then updateSearchState(j.slug,res) end
            for _,fn in ipairs(watchers) do pcall(fn,j.slug,res) end
        end
        local function releaseJob(j)
            -- A queued callback may outlive replacement/completion. Drop its
            -- suspended coroutine now so its frontier and input snapshot can be
            -- collected even before the idle queue reaches that callback.
            for k in pairs(j) do j[k]=nil end
            j.invalid=true; j.finished=true; j.scheduled=false
        end
        local function schedule(j)
            if j.scheduled then return end; j.scheduled=true
            local function step()
                if j.invalid then j.scheduled=false; return true end
                local before=j.result; local done=S.Run(j,2)
                if j.result and (j.result~=j.published or j.result~=before) then publish(j,j.result) end
                if done then
                    j.scheduled=false
                    if j.finished or j.status=="error" or coroutine.status(j.co)=="dead" then
                        if slots[j.key]==j then slots[j.key]=nil end
                        releaseJob(j)
                    end
                    return true
                end
                return false
            end
            j.pump=step
            if ns.IdleJobs and ns.IdleJobs.Add then ns.IdleJobs.Add(step)
            elseif C_Timer and C_Timer.After then
                local function later() if not step() then C_Timer.After(0,later) end end
                C_Timer.After(0,later)
            end
        end
        local function compatible(result,opts)
            if RA.ToolPolicyChanged(result,opts.profession,opts) then return false end
            if RA.FormulaPolicyChanged(result,opts) then return false end
            if RA.SpecializationPlanChanged(result,opts.profession,opts) then return false end
            if opts.targetUnlearned then
                return result.professionPolicy==1 and result.targetUnlearned==true
                    and result.secondaryProfession==opts.secondaryProfession
            end
            return not result.targetUnlearned
        end
        local function incompatibility(result,opts)
            if RA.ToolPolicyChanged(result,opts.profession,opts) then return "toolPolicyChanged" end
            if RA.FormulaPolicyChanged(result,opts) then return "formulaPolicyChanged" end
            if RA.SpecializationPlanChanged(result,opts.profession,opts) then return "specializationChanged" end
            return (opts.allowSecondaryLeveling or result.secondaryProfession) and "pairingChanged" or "professionChanged"
        end
        local function sameRouteKind(result,opts)
            return (result.scheme=="fishing")== (opts.scheme=="fishing")
        end
        local function gate(slug,opts,status,code)
            -- A missing/changed pair cannot expose an old executable plan, even
            -- while a previous coroutine is still queued in IdleJobs.
            local char=E.CharacterKey()
            for key,j in pairs(slots) do
                if j.slug==slug and j.char==char and (opts.partnerRequired or not compatible(j.published or {},opts)) then
                    slots[key]=nil
                    if results[key] and results[key].status=="searching" then results[key]=nil end
                    if active[j.scope]==key then active[j.scope]=nil end
                    releaseJob(j)
                end
            end
            local view={planVersion=2,scheme=opts.scheme,status=status,start=opts.start or 1,target=opts.target,
                steps={},executionSteps={},actions={},mats={},formulas={},gaps={},total=0,matTotal=0,ahTotal=0,vendorTotal=0,crafts=0,
                feasible=false,priced=false,costComplete=false,completeCost=false,targetReached=false,
                diagnostics={{code=code}},professionPolicy=1,targetUnlearned=opts.targetUnlearned,
                secondaryProfession=opts.secondaryProfession,revision=revision,stamp=stamp()}
            if code=="specializationChanged" or code=="formulaPolicyChanged" or code=="toolPolicyChanged" then
                -- Keep the manual recalculation gate after cancelling an in-flight
                -- job; subsequent UI reads must not silently start a replacement.
                local key,scope=identities(slug,opts)
                RA.StampSpecializations(view,slug,opts)
                RA.StampFormulaPolicy(view,opts)
                results[key]=view; active[scope]=key
            end
            return view
        end
        local function legacyOptions(opts)
            local adjusted=E.Copy(opts)
            if opts.targetUnlearned then adjusted.learnedOnly=false end
            return adjusted
        end
        local function restore(slug,record,key,scope,opts)
            if type(record)~="table" or type(record.result)~="table" or record.result.routeModel~=CACHE_VERSION then return end
            if not compatible(record.result,opts) then return end
            if record.result.formulaRevision~=1 then return end
            local old=record.result
            local data=vendorQuoteData()
            local dataChanged=old.vendorQuoteData~=data
            local quoteChanged=old.vendorQuoteRevision~=VENDOR_QUOTE_REVISION or dataChanged
            if quoteChanged then
                -- Keep historical/frozen execution records intact, but never
                -- publish a previous merchant/cache price as a current quote.
                -- Replacing the purchase-price model requires explicit recalculation.
                local result=gate(slug,opts,"recalculate_required","vendorQuoteChanged")
                result.cached=true; result.stale=true; result.staleReason="vendor-quotes"
                result.vendorQuoteRevision=VENDOR_QUOTE_REVISION
                result.vendorQuoteData=data
                results[key]=result; active[scope]=key
                return result
            end
            if old.planVersion==2 then
                local unpriced=old.pricePending or old.referenceRoute
                for _,entry in ipairs(old.mats or {}) do if entry.unpriced then unpriced=true; break end end
                -- The new pricing rule excludes unresolved purchases entirely.
                -- Recompute these old plans once; keep fully priced plans cached.
                if unpriced then return end
            end
            if old.planVersion==2 and #(old.steps or {})==0 and not old.targetReached
                and (old.status=="incomplete" or old.status=="infeasible" or old.status=="error")
                and old.emptyResultRevision~=EMPTY_RESULT_REVISION then
                -- Repair legacy empty failures once, while preserving real saved
                -- routes and explicit stopped jobs. New failures remain cached.
                return
            end
            local result=serializable(record.result); result.cached=true
            RA.ValidateRecovery(result,opts)
            -- Old uptime timestamps are not valid persisted observations. Keep
            -- the plan visible, but clear that old evidence rather than invent
            -- a Unix time. New plans retain matching saved quantities on reload.
            if result.auctionSupplyRevision~=2 then
                E.SummarizeAuctionSupply(result,{prices={},auctionSupply={},auctionSupplyHistory={},priceObservedAt={}})
                result.stale=true;result.staleReason="supply-model"
            elseif E.AuctionSupplyChanged(result) then
                result.stale=true;result.staleReason="supply"
            end
            revision=math.max(revision,result.revision or 0)
            results[key]=result; active[scope]=key
            return result
        end
        local function start(slug,opts,identityOptions)
            local key,scope,savedKey,sig,char=identities(slug,identityOptions or opts)
            if opts.scheme~="cheapest" and not opts.specializationRecipeScore then
                local result
                if opts.scheme=="fishing" and ns.ProfFishing then result=ns.ProfFishing.Compute(opts)
                else result=oldCompute(slug,legacyOptions(opts)) end
                if not result then
                    result={scheme=opts.scheme,start=opts.start or 1,target=opts.target,steps={},executionSteps={},actions={},mats={},
                        total=0,matTotal=0,ahTotal=0,vendorTotal=0,crafts=0,feasible=false,priced=false,costComplete=false,
                        status="infeasible",diagnostics={{code="levelGap"}},stamp=stamp()}
                end
                result.status=result.status or "complete"
                local j={key=key,scope=scope,savedKey=savedKey,signature=sig,slug=slug,char=char,opts=opts,finished=true}
                publish(j,result); return result
            end
            local j=S.NewJob(slug,opts)
            j.key=key; j.scope=scope; j.savedKey=savedKey; j.signature=sig; j.char=char
            slots[key]=j
            j.published=RA.StampFormulaPolicy(RA.StampSpecializations(S.Result(j,nil,"searching"),slug,opts),opts); j.published.revision=revision
            results[key]=j.published; active[scope]=key
            schedule(j)
            return j.published
        end
        function RA.Compute(slug,opts)
            if slug=="first-aid" then return RA.FixedOnlyResult(slug,opts) end
            opts=options(slug,opts)
            if opts.partnerRequired then return gate(slug,opts,"selection_required","secondaryRequired") end
            if opts.scheme=="fishing" and ns.ProfFishing then return RA.ApplyRecovery(RA.StampSpecializations(RA.StampVendorQuotes(ns.ProfFishing.Compute(opts),opts),slug,opts),slug,opts) end
            if opts.scheme~="cheapest" and not opts.specializationRecipeScore then return RA.ApplyRecovery(RA.StampSpecializations(RA.StampVendorQuotes(oldCompute(slug,legacyOptions(opts)),opts),slug,opts),slug,opts) end
            local result,job=S.Compute(slug,opts)
            return RA.StampSpecializations(RA.StampVendorQuotes(result,opts),slug,opts,job and job.snap)
        end
        local function getCandidate(slug,opts,preserveExecution)
            opts=options(slug,opts)
            if opts.partnerRequired then return gate(slug,opts,"selection_required","secondaryRequired") end
            local key,scope,savedKey=identities(slug,opts)
            if results[key] then
                if not compatible(results[key],opts) then return gate(slug,opts,"recalculate_required",incompatibility(results[key],opts)) end
                return RA.ValidateRecovery(results[key],opts)
            end
            if not opts.snapshot then
                local db=saved(); local exact=db.routes[savedKey]
                if exact then local restored=restore(slug,exact,key,scope,opts); if restored then return restored end end
                local previousKey=db.active[slug]; local previous=previousKey and db.routes[previousKey]
                if previous and sameRouteKind(previous.result or {},opts) then
                    local restoredKey=E.CharacterKey().."|"..previousKey
                    local result=results[restoredKey]
                    if result and not compatible(result,opts) then result=nil end
                    result=result or restore(slug,previous,restoredKey,scope,opts)
                    if result then result.stale=true; result.settingsChanged=true; result.staleReason="settings"; return result end
                    if not compatible(previous.result or {},opts) then return gate(slug,opts,"recalculate_required",incompatibility(previous.result or {},opts)) end
                end
            end
            -- A changed setting does not replace the visible in-flight or cached
            -- route. The Recalculate button is the sole application point.
            local current=not opts.snapshot and active[scope] and results[active[scope]]
            if current and sameRouteKind(current,opts) then
                if not compatible(current,opts) then return gate(slug,opts,"recalculate_required",incompatibility(current,opts)) end
                current.stale=true; current.settingsChanged=true; current.staleReason="settings"; return current
            end
            if not preserveExecution then return start(slug,opts) end
        end
        function RA.Get(slug,opts)
            if slug=="first-aid" then
                local execution=ns.ProfExecution
                local frozen=execution and execution.GetPlan and execution.GetPlan(slug)
                if frozen and frozen.mode~="fixed" then return {mode="fixed",scheme="fixed",status="recalculate_required",steps={},mats={},formulas={},gaps={},feasible=false,diagnostics={{code="fixedOnlyChanged"}}} end
                return RA.FixedOnlyResult(slug,opts)
            end
            local recoveryOptions=options(slug,opts)
            local execution=not (opts and opts.snapshot) and ns.ProfExecution or nil
            local frozen=execution and execution.GetPlan and execution.GetPlan(slug)
            if RA.ToolPolicyChanged(frozen,slug,recoveryOptions) then return gate(slug,recoveryOptions,"recalculate_required","toolPolicyChanged") end
            if RA.SpecializationPlanChanged(frozen,slug,opts) then return RA.ValidateSpecializationPlan(frozen,slug,opts) end
            if RA.FormulaPolicyChanged(frozen,recoveryOptions) then
                return gate(slug,recoveryOptions,"recalculate_required","formulaPolicyChanged")
            end
            if RA.VendorQuotesChanged(frozen) then return RA.ValidateVendorQuotes(frozen,recoveryOptions) end
            local result=RA.ValidateVendorQuotes(getCandidate(slug,opts,frozen~=nil),recoveryOptions)
            if opts and opts.snapshot then return result end
            if result and (result.status=="selection_required" or result.status=="recalculate_required") then return result end
            if execution then
                if execution.PlanRecalculated then execution.PlanRecalculated(slug,result) end
                frozen=execution.GetPlan and execution.GetPlan(slug)
                if frozen then
                    local run=execution.GetRun and execution.GetRun(slug)
                    local settingsChanged=type(frozen.cacheSignature)=="string"
                        and frozen.cacheSignature~=signature(recoveryOptions)
                    if settingsChanged or result and result.settingsChanged then
                        frozen.stale=true;frozen.settingsChanged=true;frozen.staleReason="settings"
                    end
                    if run and result and result.revision~=frozen.revision then
                        run.newPlanAvailable=true;run.candidateRevision=result.revision
                    end
                    updateSearchState(slug,result)
                    return RA.ValidateRecovery(RA.ValidateSpecializationPlan(frozen,slug,opts),recoveryOptions)
                end
            end
            return RA.ValidateRecovery(result,recoveryOptions)
        end
        function RA.Recalculate(slug,opts)
            opts=options(slug,opts)
            -- Continuation starts at the actual skill, even when the selected
            -- route mode starts at 1. Keep that input override out of identity.
            local identityOptions=E.Copy(opts)
            RA.ClearFixedSummary(slug)
            local execution=ns.ProfExecution
            if not opts.snapshot and execution and execution.PrepareRecalculate then
                local inventory,sourcePlanID=execution.PrepareRecalculate(slug)
                if sourcePlanID then
                    opts.executionInventory=inventory or {}
                    opts.executionSourcePlanID=sourcePlanID
                    opts.start=(E.Professions()[slug] or {}).cur or opts.start
                    opts.fromCurrent=true
                end
            end
            local key,scope,savedKey,_,char=identities(slug,identityOptions)
            oldInvalidate()
            for k,j in pairs(slots) do if j.slug==slug and j.char==char then slots[k]=nil; releaseJob(j) end end
            for k in pairs(results) do
                if k:sub(1,#(char.."|"..slug.."|"))==char.."|"..slug.."|" then results[k]=nil end
            end
            active[scope]=nil
            if not opts.snapshot then
                local db=saved(); db.routes[savedKey]=nil; db.active[slug]=nil
            end
            if slug=="first-aid" then
                local result=RA.FixedOnlyResult(slug,opts)
                if not opts.snapshot and execution and execution.PlanRecalculated then execution.PlanRecalculated(slug,result) end
                return result
            end
            if opts.partnerRequired then return gate(slug,opts,"selection_required","secondaryRequired") end
            local result=start(slug,opts,identityOptions)
            if not opts.snapshot and execution and execution.PlanRecalculated then execution.PlanRecalculated(slug,result) end
            return result
        end
        function RA.Cancel(slug)
            for _,j in pairs(slots) do if j.slug==slug and not j.finished and coroutine.status(j.co)~="dead" then
                j.status="stopped"; j.result=S.Result(j,j.best,"stopped"); publish(j,j.result)
            end end
        end
        function RA.Continue(slug)
            for _,j in pairs(slots) do if j.slug==slug and not j.finished and (j.status=="paused" or j.status=="stopped") and coroutine.status(j.co)~="dead" then
                j.status="searching"; j.cpuUsed=0
                if j.result then j.result=S.Result(j,j.best,"searching"); publish(j,j.result) end
                schedule(j)
            end end
        end
        function RA.Pump(slug)
            for _,j in pairs(slots) do if (not slug or j.slug==slug) and j.pump then j.pump() end end
        end
        function RA.Invalidate(reason)
            oldInvalidate()
            reason=type(reason)=="string" and reason or "inputs"
            for _,record in pairs(fixedStore()) do
                if record.result then record.result.stale=true;record.result.staleReason=reason end
            end
            for _,j in pairs(slots) do j.stale=true; j.staleReason=reason end
            local notified={}
            for key,result in pairs(results) do
                result.stale=true; result.staleReason=reason
                local j=slots[key]; if j then notified[j.slug]=result end
            end
            local db=saved()
            for _,record in pairs(db.routes) do
                if record.result then record.result.stale=true; record.result.staleReason=reason end
                if record.slug then
                    local sk=db.active[record.slug]
                    if sk then local activeRecord=db.routes[sk]; notified[record.slug]=activeRecord and activeRecord.result end
                end
            end
            for slug,result in pairs(notified) do for _,fn in ipairs(watchers) do pcall(fn,slug,result) end end
        end
        RA.Start=RA.Get
    end
end
