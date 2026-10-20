-- =============================================================================
-- DungeonsForever · 专业页（界面层）
-- 渲染 13 个专业的总览 / 配方 / 采集 / 升级；只对无限服加载。
-- =============================================================================

local _, ns = ...

if not ns.LoadForeverPages then return end

local L = ns.L

local Host = ns.ProfHost
if not Host then return end

local DG = Host.DG
local MakeFS, NewButton = Host.MakeFS, Host.NewButton
local MakeOutline = Host.MakeOutline
local SetOutline, Unpack = Host.SetOutline, Host.Unpack
local C_GOLD, C_GREY = Host.C_GOLD, Host.C_GREY
local C_DIM, C_WHITE, C_TEXT = Host.C_DIM, Host.C_WHITE, Host.C_TEXT
local CONTENT_W = Host.CONTENT_W
local PAGE_INSET, ROW_CLASS = Host.PAGE_INSET, Host.ROW_CLASS
local FALLBACK_ICON = Host.FALLBACK_ICON

local D  = ns.ProfData
local R
local function RGet(k)
    if not R then
        local fn = ns.EnsureProfRecipes
        R = type(fn) == "function" and fn() or nil
        ns.OpenPerf.Mark("数据")
    end
    return R and R[k] or nil
end
local LV = ns.ProfLeveling
local GA = ns.ProfGathering
local RA = ns.ProfRouteAuto   -- 自动路线计算（Core/ProfRouteAuto.lua，先于本文件加载）
local CD = ns.CratesData      -- 板条箱 / 工匠文书目录（Core/Data/Data_Crates.lua）

-- 板条箱导航条目：在代码阶段挂进 ProfData（数据层的三语覆盖层是整表替换，
-- 挂在那里会被冲掉；本文件晚于所有数据文件加载，挂这里最稳）
if CD and D.pro and not D.pro.crates then
    D.order[#D.order + 1] = "crates"
    D.pro.crates = {
        name = L["板条箱"],
        icon = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\NAV\\CrateNav",
        kind = "crates",
        section = "crates",
    }
end

local PD = {}
ns.ProfModule = PD

function PD.AuctionatorStatusText()
    local bridge = ns.AuctionBridge
    local status = bridge and bridge.Status and bridge.Status()
    local state = status and status.state
    if state == "missing" then return L["未安装 Auctionator"] end
    if state == "disabled" then return L["Auctionator 已安装但未启用，请启用后重载界面。"] end
    if state == "loading" or (not state and not (RA and RA.Available and RA.Available())) then
        return L["Auctionator 正在初始化"]
    end
    return L["暂无有效拍卖行价格；请扫描或更新价格。"]
end

PD.CARD_INSET = PAGE_INSET
PD.CARD_TOP = 8
PD.NAV_PAD = 8
PD.NAV_X, PD.NAV_TOP = PD.CARD_INSET + PD.NAV_PAD, PD.CARD_TOP + PD.NAV_PAD
PD.NAV_W = ((type(GetLocale) == "function") and GetLocale() == "enUS") and 184 or 148
PD.NAV_FS, PD.NAV_ICON = 16, 20
PD.NAV_ITEM_H, PD.NAV_GROUP_H, PD.NAV_GAP = 26, 22, 3
PD.NAV_LV_FS = 14
PD.CARD_NAV_R = PD.CARD_INSET + PD.NAV_W + 2 * PD.NAV_PAD
PD.RIGHT_X = PD.CARD_NAV_R + (DG.GUTTER or 8) + 8
PD.RIGHT_W = CONTENT_W - PD.RIGHT_X - PD.CARD_INSET
-- ★ SUB_STEP = SUB_W + 8（2026-10-10 全局间距标准：按钮↔按钮 = 8，页签胶囊同款）
PD.SUB_Y, PD.SUB_H, PD.SUB_W, PD.SUB_STEP = PD.CARD_TOP + 8, 22, 70, 78
PD.BODY_TOP = PD.SUB_Y + PD.SUB_H + 8
PD.BODY_BOT = PD.CARD_INSET + 8
PD.FAC_ICON = {
    a = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\FACTION\\FactionIcon_Alliance",
    h = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\FACTION\\FactionIcon_Horde",
}
PD.TOOL_H, PD.TOOL_GAP, PD.TOOL_W = 22, 8, 72
PD.TOOL_BODY_GAP = 8
PD.ROW_H, PD.ROW_H1, PD.TEXT_H = 34, 24, 24

PD.SETTING_DEF = { greyPassed = true, hlCurrent = true }
-- 自动路线（2026-10-08）：总开关默认关，其余为过滤细则
PD.SETTING_DEF.autoRoute = false
PD.SETTING_DEF.autoOnlyAH = true        -- 只用拍卖行/商人能买到价格的材料的配方
PD.SETTING_DEF.autoLearnedOnly = false  -- 仅使用本角色已学的配方
PD.SETTING_DEF.autoScheme = "cheapest"  -- 自动路线方案：最省钱/材料成本/次数最少/乐观计数
PD.SETTING_DEF.autoSecondaryLeveling = false

-- 采集四类（2026-10-11）：开放「升级」页签，走静态推荐路线（无价格/概率，无从自动计算）
PD.GATHER_SLUGS = { mining = true, herbalism = true, skinning = true, fishing = true }
PD.SETTING_DEF.autoFromCurrent = true   -- 从当前技能开始算（关 = 从 1 全量）
PD.SETTING_TOG_MAX = 4
PD.SETTING_TOG_MAX = 10
local function ProfDB()
    DungeonsForeverDB = DungeonsForeverDB or {}
    DungeonsForeverDB.prof = DungeonsForeverDB.prof or {}
    return DungeonsForeverDB.prof
end

-- 记住上次离开的专业页（2026-10-10 用户）：每次渲染落库，重开/重载后由 PD.EnsureCur 还原
local function RememberLast()
    if PD.cur and PD.cur ~= "__index" then
        local db = ProfDB()
        db.lastSlug = PD.cur
        db.lastTab = PD.tab
    end
end
function PD.Setting(k)
    local v = ProfDB()[k]
    if v == nil then return PD.SETTING_DEF[k] and true or false end
    return v and true or false
end

-- 原始值读取（2026-10-11）：字符串型设置（autoScheme）必须走这里——
-- PD.Setting 是布尔口径（v and true or false），会把 "optim" 吃成 true，
-- 方案点击循环永远匹配不上、每次写回第一个方案（截图实锤 bug）。
function PD.SettingRaw(k)
    local v = ProfDB()[k]
    if v == nil then return PD.SETTING_DEF[k] end
    return v
end

-- Cooking keeps its fish route separate from the shared automatic-route scheme.
function PD.CookingFishingMode(slug)
    return (slug or PD.cur) == "cooking" and ProfDB().cookingRoute == "fishing"
end

function PD.CycleRouteScheme()
    if PD.CookingFishingMode() then return end
    local order = (RA and RA.SchemeOrder and RA.SchemeOrder()) or {}
    if #order == 0 then return end
    local current, nextIndex = PD.SettingRaw("autoScheme"), 1
    for i, key in ipairs(order) do
        if key == current then nextIndex = (i % #order) + 1; break end
    end
    ProfDB().autoScheme = order[nextIndex]
    if RA then RA.Invalidate() end
    PD.RequestRender()
    ns.PlaySound(1)
end

-- 采集页子模式（跨重载记忆，存 ProfDB.gatherMode）；非 mining 恒为采集
function PD.GatherMode(slug)
    if slug ~= "mining" then return "gather" end
        return (ProfDB().gatherMode == "smelt") and "smelt" or "gather"
end
function PD.IsGatherRoute()
    return PD.GATHER_SLUGS[PD.cur] and not (PD.cur == "mining" and PD.GatherMode("mining") == "smelt")
end

-- 目标等级（2026-10-09 v2，每专业独立记忆；nil / 300 = 全程）
function PD.LvTarget()
    if not PD.cur then return 300 end
    local db = ProfDB()
    local v = tonumber(db.lvTarget and db.lvTarget[PD.cur])
    if not v then return 300 end
    return math.max(1, math.min(300, math.floor(v)))
end

PD.LIST_PAD = 8
PD.COL_GAP = 12
local LV_SPLIT = ((type(GetLocale) == "function") and GetLocale() == "enUS") and 0.75 or 0.80
PD.COL_LW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP) * LV_SPLIT)
PD.COL_RW = PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP - PD.COL_LW

PD.SHOP_SPLIT = 0.62   -- 购物清单两栏（2026-10-09 三轮）：左列材料+图纸主表 / 右列金币卡
PD.SEC_CARD_MAX = 8
PD.SEC_PAD = 4
PD.SEC_PAD_X = 8
PD.SEC_IN = 8
PD.SEC_GAP = 8
PD.OV_GUT = PD.SEC_GAP + 2 * PD.SEC_PAD

PD.GRID_LW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP) / 2)
PD.GRID_RW = PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP - PD.GRID_LW

PD.IX_COLS = 3
PD.IX_GAP = 8
PD.IX_COLW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - (PD.IX_COLS - 1) * PD.IX_GAP) / PD.IX_COLS)
PD.IX_CARD_H = 46   -- 2026-10-10 用户：名称 fs16 + 副行 fs14，旧 38 装不下
PD.IX_ICON = 24
PD.IX_HEAD_H = 18
PD.IX_ROWW_GAP = 8
PD.IX_GROUP_GAP = 10

PD.MAT_FS = 13
PD.MAT_ICON_PX = 16
PD.MAT_ROW_W = PD.RIGHT_W - 2 * PD.LIST_PAD
PD.MAT_RIGHT_RESERVE = 132
PD.MAT_TAIL_MIN = 14       -- 末段「图标+截断名」至少再留给名称的宽（< 此值才退回纯 … 段）
PD.MAT_X = math.floor(PD.MAT_ROW_W * 0.40)
PD.MAT_W = PD.MAT_ROW_W - PD.MAT_RIGHT_RESERVE - PD.MAT_X - 8

-- 2026-10-10：名称列按本页实际名称现算（同升级页「四列全现算」口径）——
-- 名称列只留放得下本页最宽名称 / 副行的宽度，剩余全给材料列；0.40 分割只在加载期兜底。
-- 2026-10-10 用户（三轮）：0.38→0.30→0.20→0.16 行宽 —— 名字列压窄，材料列最宽显示更全
--   0.16 × 724 ≈ 115px 上限，下限同步 118→100（否则下限兜底会吃掉压缩效果）
PD.RECIPE_NAME_MIN, PD.RECIPE_NAME_MAX = 100, math.floor(PD.MAT_ROW_W * 0.16)
PD.RECIPE_NAME_PAD = 16     -- 名称列右界→材料列起点（2026-10-10 二轮 44→16：角标迁副行、32 回让作废；16 = 保住 6 字截断档的最低间距）
PD.RECIPE_BADGE_W = 26      -- 「新」角标占宽（副行「 新 」≈ 26；随副行参与列宽扫描，不再压名称行）
PD.RECIPE_PADL = 32         -- 配方行名称起点（20px 图标 + 边距，BindRow padL 的物品图标分支）
PD.SEARCH_EB_W, PD.SEARCH_W = 150, 180
PD.SEARCH_RESERVED = 190    -- 工具首行给搜索框让出的宽（框宽 + 间隙）

PD.LV_FS = 13
PD.TBL_ICON = 27.6   -- 2026-10-10 用户：24 × 1.15，路线行制作物图标放大 15%
PD.TBL_H = 42
PD.TBL_RNG_GAP = 12
PD.TBL_NAME_GAP = 8
PD.TBL_MAT_CNT_FS = 14
PD.TBL_BLK_GAP = 8
PD.TBL_MAT_RPAD = 6
PD.TBL_CNT_GAP = 8
PD.TBL_MARK_W = 16
PD.TBL_NAME_MIN, PD.TBL_NAME_MAX = 88, 150
PD.TBL_BLK_MAX = 5
PD.TBL_NAME_DY, PD.TBL_SRC_DY = 7, -8
PD.TBL_MAT_CNT_DY = -8
PD.ZEBRA_A = 0.045
PD.LV_STEP_X, PD.LV_STEP_W, PD.LV_RNG_X = 6, 34, 52
PD.LV_ICON_X = PD.LV_RNG_X + 90 + PD.TBL_RNG_GAP
PD.LV_NAME_X = PD.LV_ICON_X + PD.TBL_ICON + PD.TBL_NAME_GAP
PD.LV_CNT_W = 78
-- 路线固定五列：步骤 | 等级范围 | 配方 | 制作次数 | 成本。
PD.LV_COST_W, PD.LV_COST_R = 88, 6
PD.LV_COUNT_R = 110
PD.LV_COL_GAP = 16
PD.LV_NAME_W = PD.TBL_NAME_MIN
-- 2026-10-10 配方页右列（金/银/铜三段币串，铜级精度需三段宽；用户两轮 100→88）
PD.REC_COST_W = 88   -- 「制作成本」列
PD.REC_AH_W = 88     -- 「拍卖」列（制作成本左边）

-- 2026-10-11 采集路线三列行（gr3）：[等级区间 | 地点 | 图标+矿名]（用户可视化方案拍板）
PD.GR_LV_X = 6                      -- 第一列等级区间起点
PD.GR_LOC_X = 88                    -- 第二列地点起点（等级列预留 82px）
PD.GR_ICON_W = 20                   -- 第三列（图标+矿名）整体贴右缘：矿名右锚 -6，图标跟在名字左侧

PD.ROW_CAP = 300
PD.ROW_POOL_CAP = 140
PD.TOOL_MAX = 20

PD.TEXT_W = PD.RIGHT_W - 46

DG.PROF_SUBTABS = {
    { key = "overview", text = L["总览"] },
    { key = "trainer",  text = L["训练师"] },
    { key = "recipe",   text = L["配方"] },
    { key = "gather",   text = L["采集"] },
    { key = "leveling", text = L["升级"] },
    { key = "crate",    text = L["板条箱"] },
    { key = "writ",     text = L["工匠文书"] },
}

local function SetIcon(tex, name)
    if type(name) == "number" then
        tex:SetTexture(name)
    elseif type(name) == "string" and name ~= "" then
        if name:find("\\", 1, true) then
            tex:SetTexture(name)
        else
            tex:SetTexture("Interface\\Icons\\" .. name)
        end
    else
        tex:SetTexture(FALLBACK_ICON)
    end
end

local function SpellName(id)
    if not id then return nil end
    local nm
    if C_Spell and C_Spell.GetSpellInfo then
        local info = C_Spell.GetSpellInfo(id)
        nm = info and info.name
    end
    if (type(nm) ~= "string" or nm == "") and type(GetSpellInfo) == "function" then
        nm = GetSpellInfo(id)
    end
    if type(nm) == "string" and nm ~= "" then return nm end
    return format(L["法术 #%d"], id)
end

local function SpellIcon(id)
    if not id then return nil end
    if C_Spell and C_Spell.GetSpellInfo then
        local info = C_Spell.GetSpellInfo(id)
        if info and info.iconID then return info.iconID end
    end
    if type(GetSpellInfo) == "function" then
        return select(3, GetSpellInfo(id))
    end
    return nil
end

DG.ZoneName = function(id)
    if type(id) ~= "number" then return L["无数据"] end
    local m = C_Map
    local fn = m and m.GetAreaInfo
    if type(fn) == "function" then
        local ok, nm = pcall(fn, id)
        if ok and type(nm) == "string" and nm ~= "" then return nm end
    end
    return format(L["区域 #%d"], id)
end

-- ★ UTF-8 估宽 / 按「字」截断已上移 Hui.lua（ns.hui，双端通用，2026-10-03）——
--   副本掉落页的名称截断在泰坦端也要用，而本文件只对无限端加载。
--   这里留委托 + CharStep 别名（下面的 PD.Wrap 还在用）。
local CharStep = ns.hui.CharStep

-- ★ 量宽记忆化（2026-10-09 第二轮：点开配方页那一瞬间的卡顿）：
--   ns.hui.TextW 是**逐字符 UTF-8 解码 + 查表**的纯 Lua 循环，而配方页一帧要量
--   三千来次 —— 同一页里要量的文本高度重复（同一种皮出现在几百条配方里、「3×」
--   这种数量串满天飞）⇒ 按 (字号, 文本) 记忆化，命中率极高。
--   只影响耗时、不影响任何取值（TextW 对 (text, fs) 是纯函数）。
--   条数封顶，超了整表清空 —— 配方页的文本集合天然收敛，不会无限涨。
local _twMemo, _twN = {}, 0
PD.TextW = function(text, fs)
    if type(text) ~= "string" or fs == nil then return ns.hui.TextW(text, fs) end
    local m = _twMemo[fs]
    if not m then m = {}; _twMemo[fs] = m end
    local w = m[text]
    if w ~= nil then return w end
    w = ns.hui.TextW(text, fs)
    if _twN >= 8192 then
        _twMemo, _twN = {}, 0
        m = {}
        _twMemo[fs] = m
    end
    m[text] = w
    _twN = _twN + 1
    return w
end

PD.Fit = function(text, fs, width)
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
--   按 id 记忆化绝对安全。
--   ★★ 第十一刀（rev17）：记忆表再改成**正 / 负分离 + 正向跨渲染持久** ——
--   实机量到「一页 取名 1055 次 / 取名(引擎) 428 次 / 4.7ms」，而这一页的
--   名字在一局里至少被重问 5 遍（到货重扫 0.5/1.5/4/9s 各重渲一次 + 每次
--   切走再切回来），且那一页 `发包 0 次` ⇒ **名字本来就在客户端缓存里**，
--   428 次 GetItemInfo 全是白问。名字一旦到货就不会再变 ⇒ 正向结果完全该
--   跨渲染留着；只有「还没到货」那半边才需要下次渲染重问。
--   到货后的重扫（PD.SweepNames → PD.Render）靠清**负向**表自然拿到新名字。
--   ★ 只替换**配方页热路径**的 7 处调用点（一页 2000+ 次）。其它页面（升级 / 采集 /
--     营地 / 图纸行…）调用量小，绕记忆表没有收益；而且 harness 把它们的调用**写法**
--     钉死了（改了就是误伤断言，不是回归）。
-- ★★ 第十一刀（rev17）：正 / 负**分离** + 正向**跨渲染持久**。
--   · _nmPos / _icPos（正向：名字 / 图标**已到货**）—— **不随 Render 清**，
--     只在满 PD_MEMO_POS_CAP 时整表清（代价只是重问一遍）。
--   · _nmNeg / _icNeg（负向：**还没到货**）—— 每次 Render 开头清
--     （PD.ResetItemNameMemo），保证「到货重扫」永远能把占位刷成真名。
--   ★ hard = true 连正向一起清（只给离线冒烟的「造态」用：桩的假名会先落进
--     正向表，不硬清就看不出「未到货」那条路，断言会假绿）。
local PD_MEMO_POS_CAP = 32768
local _nmPos, _nmPosN = {}, 0
local _nmNeg, _nmN = {}, 0
local _icPos, _icPosN = {}, 0
local _icNeg, _icN = {}, 0
function PD.ResetItemNameMemo(hard)
    _nmNeg, _nmN = {}, 0
    _icNeg, _icN = {}, 0
    if hard then _nmPos, _nmPosN, _icPos, _icPosN = {}, 0, {}, 0 end
end
function PD.ItemName(id)
    if id == nil then return L["暂时没有客户端数据"], false end
    local hit = _nmPos[id]
    if hit ~= nil then return hit, true end
    if _nmNeg[id] then return L["暂时没有客户端数据"], false end
    -- ★ 动态取 DG.ItemName（**不要**在加载期抓成局部）：探针会在运行期替换
    --   DG.ItemName 来造态，抓成局部就把桩绕过了（离线审计探针会因此变哑）。
    --   ⚠️ 这一行是本文件唯一一处**故意**保留的 `DG.ItemName(` —— 别用全局替换。
    local nm, got = DG.ItemName(id)
    if got then
        if _nmPosN >= PD_MEMO_POS_CAP then _nmPos, _nmPosN = {}, 0 end
        _nmPos[id], _nmPosN = nm, _nmPosN + 1
        return nm, true
    end
    if _nmN >= 8192 then _nmNeg, _nmN = {}, 0 end
    _nmNeg[id], _nmN = true, _nmN + 1
    return nm, false
end

-- ★★ 材料图标记忆化（2026-10-09 第六轮；实机 /dfprofperf：列宽材料 17.9ms、
--   取名(引擎) 1586 次）。PD.MatCol 每行每个材料都算一次图标串，而
--   PD.MatIconTex → DG.ItemIcon → DG.ItemInfo(id)（= GetItemInfo）是**零缓存**的
--   引擎调用 —— 一页 300 行 × 平均 3 材料 ≈ 900 次，与物品名**同源**。
--   同一个 id 在一次渲染里图标不可能变 ⇒ 与 PD.ItemName 一样**正 / 负分离**：
--   真图标（正向表）跨渲染持久；FALLBACK_ICON 算「还没到货」进负向表，
--   每次 Render 开头清（PD.ResetItemNameMemo(hard) 可连正向一起清），
--   到货重扫自然拿到新图标。
function PD.ItemIcon(id)
    if id == nil then return FALLBACK_ICON end
    local hit = _icPos[id]
    if hit ~= nil then return hit end
    if _icNeg[id] then return FALLBACK_ICON end
    local tex = DG.ItemIcon(id)
    -- ★ FALLBACK_ICON = 「还没到货」⇒ 进负向表（下次 Render 再问）；
    --   真图标进正向表（跨渲染持久）。
    if tex ~= FALLBACK_ICON then
        if _icPosN >= PD_MEMO_POS_CAP then _icPos, _icPosN = {}, 0 end
        _icPos[id], _icPosN = tex, _icPosN + 1
        return tex
    end
    if _icN >= 8192 then _icNeg, _icN = {}, 0 end
    _icNeg[id], _icN = true, _icN + 1
    return tex
end

PD.Wrap = function(text, fs, width)
    local out = {}
    if type(text) ~= "string" or text == "" or not width then return out end
    -- |T...|t 贴图序列按整块处理（2026-10-10 币种图标）：不许从中间折行剁开，
    -- 宽度按「一个字号 + 2px 余量」估算；其余文本仍按 CharStep 逐字符走。
    local toks, pos = {}, 1
    while true do
        local s, e = string.find(text, "|T.-|t", pos)
        if not s then
            toks[#toks + 1] = { t = string.sub(text, pos) }
            break
        end
        if s > pos then toks[#toks + 1] = { t = string.sub(text, pos, s - 1) } end
        toks[#toks + 1] = { t = string.sub(text, s, e), icon = true }
        pos = e + 1
    end
    local line, w = "", 0
    for _, tk in ipairs(toks) do
        if tk.icon then
            local cw = fs + 2
            if w + cw > width and line ~= "" then
                out[#out + 1] = line
                line, w = "", 0
            end
            line, w = line .. tk.t, w + cw
        else
            local i, n = 1, #tk.t
            while i <= n do
                local ch, step, k = CharStep(tk.t, i)
                local cw = k * fs
                if w + cw > width and line ~= "" then
                    out[#out + 1] = line
                    line, w = "", 0
                end
                line = line .. ch
                w = w + cw
                i = i + step
            end
        end
    end
    if line ~= "" then out[#out + 1] = line end
    return out
end

PD.TIER_HEX = { "|cffffd100", "|cff40d940", "|cff8c8c8c" }
PD.TierText = function(a, b, c)
    return format("%s%s|r/%s%s|r/%s%s|r",
                  PD.TIER_HEX[1], tostring(a),
                  PD.TIER_HEX[2], tostring(b),
                  PD.TIER_HEX[3], tostring(c))
end

local function ColTextW(col)
    if col == 2 then
        if PD.gridSplit then return PD.GRID_RW end
        if PD.lvSplit then return PD.splitRW or PD.COL_RW end
        return PD.COL_RW
    end
    if col == 1 then
        if PD.gridSplit then return PD.GRID_LW end
        if PD.lvSplit then return PD.splitLW or PD.COL_LW end
        return PD.COL_LW
    end
    return PD.TEXT_W
end

local function PushText(rows, text, fs, color, col)
    for _, ln in ipairs(PD.Wrap(text, fs or 12, ColTextW(col))) do
        rows[#rows + 1] = { kind = "text", text = ln, fs = fs or 12, color = color, col = col }
    end
end

local function PushHead(rows, text, col, fs)
    rows[#rows + 1] = { kind = "head", text = text, col = col, fs = fs }
end

local function PushGap(rows, h, col)
    rows[#rows + 1] = { kind = "gap", h = h or 8, col = col }
end

local function MarkSec(rows, a, b, n)
    for i = a, b do
        if rows[i].kind ~= "gap" then rows[i].sec = n end
    end
end

PD.cur = nil
PD.tab = "overview"
PD.campView = "a"
PD.autoPage = "route"   -- 自动路线的子页：route = 路线 / shop = 购物清单
PD.toolKey = nil
PD.perkOpen = {}
PD.rows, PD.toolBtns = {}, {}
PD.specs = nil

-- ★★ 大列表分帧 + 顶部进度条：渲染只算版式，把「还没建的行」记进 PD.__pendRows，
--   随后按每帧预算逐批建。进度分母入队时就算好、只增不减；进度条复用主界面
--   最顶上那根。少于 PD.ROW_SYNC_MAX 行直接同步建完（闪一下比不闪更难受）。
PD.__pendRows = {}
PD.ROW_SYNC_MAX = 20
-- ★★ 视口优先（2026-10-09 第七刀；实机 /dfprofperf rep）。
--   行帧**已经在池里**的那些，原来一律在渲染这一帧里同步重绑：实机「上数据 300次 /
--   37~42ms」，而从别的页签切回配方页那一次更到「铺行 111.6ms」（那一帧还会顺手建出
--   每行 mn/mz 那几格材料帧）。现在只同步绑**首屏画得出来的那几十行**，其余进同一张
--   待建表，交由既有分帧器按每帧预算（DG.Loader.budgetMs）补齐 ⇒ 单帧硬卡被摊平，
--   而屏上第一屏内容**当帧就是对的**（行池里本来就画着上一页的东西，不是空白）。
--   ★ 判据必须**同时**吃「行帧已存在」：光看 `i <= syncN` 会把**还没建**的首屏行
--     拖回这一帧来 CreateFrame（首屏 30 行 ≈ 18ms 建帧，正是分帧要避开的那笔）。
PD.SYNC_ROWS_BUF = 6
function PD.SyncRows()
    local h = 0
    local sf = PD.scroll
    if sf and type(sf.GetHeight) == "function" then
        local ok, v = pcall(sf.GetHeight, sf)
        if ok and type(v) == "number" then h = v end
    end
    if h <= 0 then h = 420 end          -- 量不到（桩 / 没建好）就按 420px 兜底
    local per = PD.ROW_H1 or PD.ROW_H or 20
    if type(per) ~= "number" or per <= 0 then per = 20 end
    return math.ceil(h / per) + PD.SYNC_ROWS_BUF
end

function PD.SetRowHover(r, on)
    on = on and true or false
    r.__hlOn = on
    if on then
        if ns.hui and ns.hui.layer then
            local c4 = ns.hui.layer.L4
            r:SetBackdropColor(c4[1], c4[2], c4[3], c4[4] or 1)
        else
            r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG_HOVER)
        end
        r:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE_HOVER)
    elseif r.__z then
        r:SetBackdropColor(1, 1, 1, PD.ZEBRA_A)
        r:SetBackdropBorderColor(1, 1, 1, 0)
    else
        r:SetBackdropColor(1, 1, 1, 0)
        r:SetBackdropBorderColor(1, 1, 1, 0)
    end
end

function PD.SyncHover()
    if not PD.rows then return end
    for _, r in pairs(PD.rows) do
        local over = (r.IsMouseOver and r:IsMouseOver()) and true or false
        if over ~= r.__hlOn then PD.SetRowHover(r, over) end
    end
    if PD.ixRoot and PD.ixRoot:IsVisible() then
        for i = 1, #(PD.ixCards or {}) do
            local c = PD.ixCards[i]
            local over = (c.IsMouseOver and c:IsMouseOver()) and true or false
            if over ~= c.__hlOn then PD.SetCardHover(c, over) end
        end
    end
end

function PD.Row(i)
    local r = PD.rows[i]
    if r then return r end
    r = CreateFrame("Button", nil, PD.child, "BackdropTemplate")
    r:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    r:SetWidth(PD.RIGHT_W)
    r:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
    })
    r.__hlOn = false
    PD.SetRowHover(r, false)
    r:EnableMouse(true)
    r.icon = r:CreateTexture(nil, "ARTWORK")
    r.icon:SetSize(20, 20)
    r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.icon) end
    r.icon2 = r:CreateTexture(nil, "ARTWORK")
    r.icon2:SetSize(14, 14)
    r.icon2:Hide()
    r.icon3 = r:CreateTexture(nil, "ARTWORK")
    r.icon3:SetSize(14, 14)
    r.icon3:Hide()
    r.hsOwn = CreateFrame("Button", nil, r)
    r.hsOwn:EnableMouse(true)
    r.hsOwn:SetScript("OnClick", function(self)
        if self.__act then self.__act() end
        ns.PlaySound(1)
    end)
    r.hsOwn:Hide()
    r.hsTot = CreateFrame("Button", nil, r)
    r.hsTot:EnableMouse(true)
    r.hsTot:SetScript("OnClick", function(self)
        if self.__act then self.__act() end
        ns.PlaySound(1)
    end)
    r.hsTot:Hide()
    r.hsCraft = CreateFrame("Button", nil, r)
    r.hsCraft:EnableMouse(true)
    r.hsCraft:SetScript("OnClick", function(self)
        if self.__act then self.__act() end
        ns.PlaySound(1)
    end)
    r.hsCraft:Hide()
    r.icon4 = r:CreateTexture(nil, "ARTWORK")
    r.icon4:SetSize(14, 14)
    r.icon4:Hide()
    r.hsGap = CreateFrame("Button", nil, r)
    r.hsGap:EnableMouse(true)
    r.hsGap:SetScript("OnClick", function(self)
        if self.__act then self.__act() end
        ns.PlaySound(1)
    end)
    r.hsGap:Hide()
    -- 2026-10-11 采集路线三列行：第三列纯图标池（采药/采矿合并组一行多产物，名字退役）
    r.gic = {}
    for k = 1, 6 do
        local g = r:CreateTexture(nil, "ARTWORK")
        g:SetSize(20, 20)
        g:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(g) end
        g:Hide()
        r.gic[k] = g
    end
    r.blk = {}
    r.a = MakeFS(r, 13, C_TEXT, "LEFT")
    r.b = MakeFS(r, 11, C_GREY, "LEFT")
    r.c = MakeFS(r, 12, C_GOLD, "RIGHT")
    r.c2 = MakeFS(r, 12, C_GOLD, "RIGHT")
    r.d = MakeFS(r, 11, C_GREY, "RIGHT")
    r.e = MakeFS(r, 13, C_GOLD, "LEFT")
    r.f = MakeFS(r, PD.MAT_FS, C_TEXT, "LEFT")
    -- 2026-10-10 配方页表头（用户：表头文字统一 16 等大等高）：专用字串池 r.h1~h5，
    --   不借用数据列字串（行池跨页复用，借字会污染字号/颜色/锚点）
    r.h1 = MakeFS(r, 16, C_GREY, "LEFT")
    r.h2 = MakeFS(r, 16, C_GREY, "LEFT")
    r.h3 = MakeFS(r, 16, C_GREY, "RIGHT")
    r.h4 = MakeFS(r, 16, C_GREY, "RIGHT")
    r.h5 = MakeFS(r, 16, C_GREY, "RIGHT")
    r.h6 = MakeFS(r, 16, C_GREY, "LEFT")
    -- 2026-10-09 配方页两处热区（用户）：
    --   ① 材料列改「锚点分段链」—— 第 1 段沿用 r.f（保住「材料列左锚 = PD.MAT_X」那条
    --      既有不变量），第 2 段起是 r.mn[i]；每段配一格热区 r.mz[i]，悬停出该材料的物品提示框；
    --   ② 右下角那格的「商人：X」半段搬到 r.dv（r.d 只留前缀），热区只盖 r.dv ——
    --      悬停出商人明细 + 「点击：在地图上标记该 NPC」，点击落图。
    r.mn = {}
    r.mz = {}
    r.mcnt = {}   -- 2026-10-10 材料数量徽标池（数量压图标右下角，见 PD.MatCnt）
                  --   ★ 必须在工厂预建：桩铁律——非 __ 字段未赋值就索引会现造 function
    r.dv = MakeFS(r, 11, C_GREY, "RIGHT")
    r.dv:SetText("")
    r.dv:SetWordWrap(false)
    r.dv:Hide()
    -- 2026-10-09 四轮（用户）：「升级路线」每行要显示该配方的四档技能阈值
    --   （学 / 黄 / 绿 / 灰），并给出「当前技能等级落在哪一档」的位置。
    --   布局：色阶条占用**原来的来源行**（名字正下方），来源压成名字右侧的小卡片。
    --   ★ 全部在 Row 里一次建好，渲染期只摆位 / 改文本。
    --   ★ 帧上的自定义字段一律 __ 前缀（桩铁律：非 __ 字段未赋值就索引会现造 function）。
    r.__sbBg, r.__sbTx = {}, {}
    for k = 1, 4 do
        local bg = r:CreateTexture(nil, "ARTWORK")
        bg:SetColorTexture(1, 1, 1, 1)
        bg:Hide()
        r.__sbBg[k] = bg
        local tx = MakeFS(r, PD.SB_FS, C_WHITE, "CENTER")
        tx:SetText("")
        tx:SetWordWrap(false)
        tx:Hide()
        r.__sbTx[k] = tx
    end
    -- 2026-10-09 十一轮（用户）：「这个竖线，我希望显示两根，显示的位置是
    --   左边这个等级的位置」→ 两根线分别落在**本行技能区间**的两端
    --   （左 = st[1] / 右 = st[2]），不再只画「当前档位」那一根。
    --   落位口径见 PD.SBValPos（起点向下吸 / 终点向上吸，只停 0 / 1/4 / 1/2 / 3/4）。
    r.__sbPin = {}
    for k = 1, 2 do
        local p = r:CreateTexture(nil, "OVERLAY")
        p:SetWidth(2)
        p:SetColorTexture(1, 1, 1, 0.9)
        p:Hide()
        r.__sbPin[k] = p
    end
    r.__cardZone = CreateFrame("Button", nil, r)
    r.__cardZone:Hide()
    PD.WireTipZone(r.__cardZone, r)
    r.__costZone = CreateFrame("Button", nil, r)
    r.__costZone:Hide()
    PD.WireTipZone(r.__costZone, r)
    r.__cardBg = CreateFrame("Frame", nil, r)
    r.__cardBg:Hide()
    -- 2026-10-10 用户：来源小卡片改倒圆角（HUI 圆角原语，radius 4）；色片存帧上供 PaintCard 按来源类型改色
    r.__cardBg.__pieces = ns.hui.BuildRoundedBG(r.__cardBg, 4, { 1, 1, 1 }, "both", false, nil, true)
    -- 文本必须挂在 __cardBg 上：子 Frame 会整体画在父帧字体串之上，挂在 r 上会被圆角色片盖住
    r.__cardTx = MakeFS(r.__cardBg, 10, C_TEXT, "LEFT")
    r.__cardTx:SetText("")
    r.__cardTx:SetWordWrap(false)
    r.__cardTx:Hide()
    for _, f in ipairs({ r.a, r.b, r.c, r.c2, r.d, r.e, r.f }) do f:SetWordWrap(false) end
    -- 「直售」小徽标：spec.tag 出现时贴名称右侧
    r.tagBg = r:CreateTexture(nil, "BORDER")
    r.tagBg:SetColorTexture(0.30, 0.75, 0.45, 0.16)
    r.tagBg:Hide()
    r.tagFs = MakeFS(r, 10, { 0.42, 0.94, 0.62 }, "LEFT")
    r.tagFs:SetText("")
    r.tagFs:Hide()
    r.sep = r:CreateTexture(nil, "BACKGROUND")
    r.sep:SetHeight(1)
    r.sep:SetColorTexture(1, 1, 1, 0.055)
    r.bT = r:CreateTexture(nil, "BORDER")
    r.bT:SetHeight(1)
    r.bT:SetPoint("TOPLEFT", r, "TOPLEFT", 0, 0)
    r.bT:SetPoint("TOPRIGHT", r, "TOPRIGHT", 0, 0)
    r.bB = r:CreateTexture(nil, "BORDER")
    r.bB:SetHeight(1)
    r.bB:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 0, 0)
    r.bB:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", 0, 0)
    r.bL = r:CreateTexture(nil, "BORDER")
    r.bL:SetWidth(1)
    r.bL:SetPoint("TOPLEFT", r, "TOPLEFT", 0, 0)
    r.bL:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 0, 0)
    r.bR = r:CreateTexture(nil, "BORDER")
    r.bR:SetWidth(1)
    r.bR:SetPoint("TOPRIGHT", r, "TOPRIGHT", 0, 0)
    r.bR:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", 0, 0)
    r:SetScript("OnEnter", function(self)
        PD.SetRowHover(self, true)
        if self.__noTip then return end
        -- ★ lines 惰性求值（2026-10-09 第二轮）：一次渲染要建几百条 spec，
        --   每条 lines 都是 6 段 format 拼接 —— 而配方行有 it，OnEnter 走
        --   DG.ShowItemTip，__lines 从来不读。改成第一次真要读时才拼。
        if self.__lines == nil and self.__mkLines then
            self.__lines = self.__mkLines()
            self.__mkLines = nil
        end
        if self.__lines and (self.__linesFirst or not self.__it) then
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:ClearLines()
            for _, ln in ipairs(self.__lines) do
                if ln[1] and ln[1] ~= "" then
                    GameTooltip:AddLine(ln[1], ln[2] or 1, ln[3] or 1, ln[4] or 1, true)
                end
            end
            GameTooltip:Show()
        elseif self.__it then
            -- extra = 惰性价格段（函数先求值成行表再传；2026-10-10 修复 ipairs got function 教训）
            -- tipTitle（2026-10-11 工匠文书页）：覆写提示框首行为「工匠文书：X」
            local extra = self.__tipExtra
            if type(extra) == "function" then extra = extra() end
            DG.ShowItemTip(self, self.__it, extra, self.__tipTitle)
        end
    end)
    r:SetScript("OnLeave", function(self)
        PD.SetRowHover(self, false)
        GameTooltip:Hide()
    end)
    r:SetScript("OnClick", function(self, button)
        if button == "RightButton" and not self.__routePolicy then return end
        if button == "LeftButton" and self.__it
           and type(IsShiftKeyDown) == "function" and IsShiftKeyDown() then
            DG.ItemShiftClick(self, button)
            return
        end
        if self.__act then self.__act(self, button) end
        ns.PlaySound(1)
    end)
    r:EnableMouseWheel(true)
    r:SetScript("OnMouseWheel", function(self, delta)
        DG.WheelScroll(PD.scroll, PD.child, delta)
    end)
    PD.rows[i] = r
    return r
end

function PD.RowHeight(spec)
    if spec.h then return spec.h end
    if spec.kind == "gap" then return 6 end
    if spec.kind == "text" or spec.kind == "head" then return PD.TEXT_H end
    return PD.ROW_H
end

-- 单个待建行：建帧 + 摆位 + 上数据（行帧已在池里则跳过）。
-- ★ 间距行（kind == "gap"）也进待建表：行池按索引取用，跳号会在池里留空洞，
--   「末尾多余的隐藏一下」那条就数不准了；建出来立刻 Hide，与同步路径同观感。
PD.StealRowFrame = function(idx)
    if not PD.visMode then return nil end
    local sc = PD.scroll
    if not (sc and sc.GetVerticalScroll and sc.GetHeight) then return nil end
    local v = sc:GetVerticalScroll()
    local vh = sc:GetHeight()
    if type(v) ~= "number" or type(vh) ~= "number" or vh <= 0 then return nil end
    local vT, vB = v - 40, v + vh + 160
    local cnt = 0
    for j = 1, PD.ROW_CAP do
        if PD.rows[j] then cnt = cnt + 1 end
    end
    if cnt < (PD.ROW_POOL_CAP or 140) then return nil end
    local bestJ, bestD, nilJ
    for j = 1, PD.ROW_CAP do
        local rr = PD.rows[j]
        if rr then
            local gt = rr.__top
            if type(gt) ~= "number" then
                if not nilJ then nilJ = j end
            else
                local d
                if gt < vT then d = vT - gt
                elseif gt > vB then d = gt - vB
                else d = -1 end
                if d > vh and d > (bestD or 0) then bestJ, bestD = j, d end
            end
        end
    end
    local j = bestJ or nilJ
    if not j then return nil end
    local rr = PD.rows[j]
    PD.rows[j] = nil
    PD.rows[idx] = rr
    if PD.WipeRow then PD.WipeRow(rr) end
    return rr
end

function PD.RealizePendingRow(e)
    if not e then return end
    -- ★ 渲染代门控（TierUI 定式）：重排后旧代待建行直接丢弃，防把旧 spec
    --   绑回行池（同页重渲 / 滚动剔除高频触发时的时间窗）。
    if e.gen and e.gen ~= PD.__rowGen then return end
    local r = PD.rows[e.idx]
    if not r then
        r = PD.StealRowFrame(e.idx)
        if not r then
            local ok, made = pcall(PD.Row, e.idx)
            if not ok or not made then return end
            r = made
        end
    end
    if e.gap then
        r:Hide()
        return
    end
    r:ClearAllPoints()
    r:SetPoint("TOPLEFT", PD.child, "TOPLEFT", e.x, -e.top)
    r.__top = e.top
    r:SetSize(e.w, e.h)
    r:Show()
    PD.BindRow(r, e.spec, e.h)
end

-- 逐批建（每帧受载入档位的时间预算 + 单块数量闸夹住；与掉落页同一套闸）。
function PD.BuildPendRows()
    local list = PD.__pendRows
    if not list then
        PD.__pendRows = {}
        DG.Gate.Finish()
        return
    end
    local t0 = DG.__nowMs()
    local left = DG.LOOT_ROW_FRAME_CAP
    while #list > 0 and left > 0 do
        PD.RealizePendingRow(table.remove(list, 1))
        DG.Gate.Advance(1)
        left = left - 1
        local t1 = t0 and DG.__nowMs()
        if t1 and (t1 - t0) >= DG.Loader.budgetMs then break end
    end
    if #list > 0 then
        DG.PushStep(PD.BuildPendRows)
    else
        DG.Gate.Finish()
        if PD.DEMO_SAVE then PD.EndGateDemo() end
    end
end

-- 渲染收尾入口：量小同步建完（快速通道，不闪进度条）；量大交分帧器 + 进度条。
-- ★ 离线桩 / 没有可用 C_Timer 的环境由 DG.RunSteps 递归同步跑完 ——
--   「调用方返回时一切就绪」这条离线契约不破。
function PD.FlushPendingRows()
    local n = #PD.__pendRows
    if n == 0 then
        DG.Gate.Finish()
        return
    end
    if n < PD.ROW_SYNC_MAX then
        for k = 1, n do PD.RealizePendingRow(PD.__pendRows[k]) end
        PD.__pendRows = {}
        DG.Gate.Finish()
        if PD.DEMO_SAVE then PD.EndGateDemo() end
        return
    end
    DG.Gate.Begin(n)
    DG.PushStep(PD.BuildPendRows)
    DG.RunSteps()
end

-- ★ 滚动前沿续排（2026-10-12，DG.CullListRows 定式的专业页版）：
--   滚动/内容变化后重算视口，出视口的行立刻 Hide；进视口的行**停稳才补排**——
--   拖滑块/连滚途中只收不放（否则沿途每个瞬时视口都被实建进池，池长到全量，
--   剔除就白做了）。行池按索引取用，重入零成本；无几何信息（离线桩）直接返回。
function PD.CullRows()
    local sc = PD.scroll
    if not (sc and PD.visMode and PD.curRows) then return end
    local v = sc.GetVerticalScroll and sc:GetVerticalScroll()
    if type(v) ~= "number" then return end
    local viewH = sc.GetHeight and sc:GetHeight()
    if type(viewH) ~= "number" then return end
    local gt = sc.GetTop and sc:GetTop()
    if type(gt) ~= "number" then return end
    local vT, vB = v - 40, v + viewH + 160
    local rows, n = PD.curRows, PD.curN
    for i = 1, n do
        local spec = rows[i]
        if spec and spec.kind ~= "gap" and type(spec.__gtop) == "number" then
            local r = PD.rows[i]
            if (spec.__gtop + spec.__gh) > vT and spec.__gtop < vB then
                if r and r.__spec == spec and r.IsShown and not r:IsShown() then
                    r:Show()
                end
            elseif r and r.IsShown and r:IsShown() then
                r:Hide()
            end
        end
    end
    if PD.__cullTimer or not (C_Timer and C_Timer.NewTimer) then return end
    PD.__cullSeq = (PD.__cullSeq or 0) + 1
    local seq = PD.__cullSeq
    PD.__cullTimer = C_Timer.NewTimer(0.08, function()
        PD.__cullTimer = nil
        if not (PD.visMode and PD.curRows) then return end
        if seq ~= PD.__cullSeq then
            PD.CullRows()
            return
        end
        local need = true
        local sc = PD.scroll
        if sc and sc.GetVerticalScroll and sc.GetHeight then
            local v, vh = sc:GetVerticalScroll(), sc:GetHeight()
            if type(v) == "number" and type(vh) == "number" and vh > 0 then
                local lv = PD.__settleV
                if type(lv) == "number" and math.abs(v - lv) < vh * 0.3
                   and GetTime and (GetTime() - (PD.__lastSettle or 0)) < 1.5 then
                    need = false
                end
                if need then PD.__settleV = v end
            end
        end
        if need then
            if GetTime then PD.__lastSettle = GetTime() end
            PD.CullRowsSettle()
        else
            PD.CullRows()
        end
    end)
end

-- 停稳后的补排：按当前滚动位置把进视口且未就位的行排队（量小同步、量大走闸门）。
function PD.CullRowsSettle()
    local sc = PD.scroll
    if not (sc and PD.visMode and PD.curRows) then return end
    local v = sc.GetVerticalScroll and sc:GetVerticalScroll()
    if type(v) ~= "number" then return end
    local viewH = sc.GetHeight and sc:GetHeight()
    if type(viewH) ~= "number" then return end
    local vT, vB = v - 40, v + viewH + 160
    local rows, n = PD.curRows, PD.curN
    local pend = PD.__pendRows
    for i = 1, n do
        local spec = rows[i]
        if spec and spec.kind ~= "gap" and type(spec.__gtop) == "number" then
            local r = PD.rows[i]
            if (spec.__gtop + spec.__gh) > vT and spec.__gtop < vB then
                if not (r and r.__spec == spec) then
                    pend[#pend + 1] = { idx = i, spec = spec, x = spec.__gx,
                                        w = spec.__gw, top = spec.__gtop, h = spec.__gh,
                                        gen = PD.__rowGen }
                end
            end
        end
    end
    PD.FlushPendingRows()
end

function PD.PaintRows(rows)
    local y = { 0, PD.hasSecs and PD.SEC_PAD or 0 }
    local bb = {}
    local bgold = {}
    local zc = { 0, 0 }
    local n = #rows
    local truncated = 0
    if n > PD.ROW_CAP then truncated = n - PD.ROW_CAP; n = PD.ROW_CAP end
    local grid = PD.gridSplit and true or false
    local ROW_W = PD.RIGHT_W - 2 * PD.LIST_PAD
    local syncN = PD.SyncRows()          -- ★ 第七刀：本帧同步绑的行数上限
    -- ★ 视口优先（2026-10-12）：真机下只排/绑「滚动视口 + 上下缓冲」内的行，
    --   视口外的行 Hide、滚动到前沿再由 PD.CullRows 续排（行池按索引取用，
    --   槽位空洞安全）。离线桩的 GetVerticalScroll/GetHeight 返回 table ⇒
    --   vis = false = 旧全量路径，探针「调用方返回时一切就绪」契约不破。
    local vis, vTop, vBot = false, 0, 0
    do
        local sc = PD.scroll
        if sc and sc.GetVerticalScroll and sc.GetHeight and sc.GetTop then
            local v = sc:GetVerticalScroll()
            local vh = sc:GetHeight()
            -- ★ GetTop 判别器（DG.CullListRows 同款）：桩回 table、真机回数字。
            --   只看 GetVerticalScroll/GetHeight 分不出来——桩把这两个也回数字。
            local gt = sc:GetTop()
            if type(v) == "number" and type(vh) == "number" and vh > 0
               and type(gt) == "number" then
                vis = true
                vTop, vBot = v - 40, v + vh + 160
            end
        end
    end
    PD.visMode = vis
    PD.curRows, PD.curN = rows, n
    PD.__rowGen = (PD.__rowGen or 0) + 1
    local gen = PD.__rowGen
    for i = 1, n do
        local spec = rows[i]
        local h = PD.RowHeight(spec)
        local r = PD.rows[i]
        if spec.sec then
            local nxt
            for j = i + 1, n do
                local s2 = rows[j]
                if s2.kind ~= "gap" then nxt = s2 break end
            end
            spec._lastInSec = not (nxt and nxt.sec == spec.sec)
        end
        local span = (grid and spec.kind ~= "row") or spec.span == true
        if spec.kind == "gap" then
            if vis then
                if r and r.IsShown and r:IsShown() then r:Hide() end
            elseif r then
                r:Hide()
            else
                PD.__pendRows[#PD.__pendRows + 1] = { idx = i, gap = true, gen = gen }
            end
            if span then
                local ny = math.max(y[1], y[2]) + h
                y[1], y[2] = ny, ny
            else
                local col = (spec.col == 2) and 2 or 1
                y[col] = y[col] + h
            end
        else
            local col, x, w, top
            if span then
                top = math.max(y[1], y[2])
                x, w = PD.LIST_PAD, ROW_W
            else
                if spec.col == 2 then
                    col = 2
                elseif grid then
                    col = (y[2] < y[1]) and 2 or 1
                else
                    col = 1
                end
                top = y[col]
                if PD.lvSplit then
                    local lw = PD.splitLW or PD.COL_LW
                    local rw = PD.splitRW or PD.COL_RW
                    x = (col == 2) and (PD.LIST_PAD + lw + PD.OV_GUT) or PD.LIST_PAD
                    w = (col == 2) and rw or lw
                elseif grid then
                    x = (col == 2) and (PD.LIST_PAD + PD.GRID_LW + PD.COL_GAP) or PD.LIST_PAD
                    w = (col == 2) and PD.GRID_RW or PD.GRID_LW
                else
                    x, w = PD.LIST_PAD, ROW_W
                end
            end
            if spec.sec and spec.sec > 0 then
                w = w - PD.SEC_IN
            end
            if spec.kind == "row" and col and not spec.sec then
                zc[col] = zc[col] + 1
                spec.z = (zc[col] % 2 == 0)
            else
                spec.z = nil
            end
            -- ★★ 视口优先（第七刀）：行帧在池里 **且** 落在首屏预算内，才当帧同步重绑；
            --   其余（含池里已有但排到首屏之外的）一律进待建表 —— 它们这一轮不改
            --   观感，由分帧器后续补齐。
            spec.__gx, spec.__gw, spec.__gtop, spec.__gh = x, w, top, h
            if (not vis) or ((top + h) > vTop and top < vBot) then
                if r and ((not vis) or i <= syncN) then
                    r:ClearAllPoints()
                    r:SetPoint("TOPLEFT", PD.child, "TOPLEFT", x, -top)
                    r:SetSize(w, h)
                    r:Show()
                    PD.BindRow(r, spec, h)
                else
                    PD.__pendRows[#PD.__pendRows + 1] =
                        { idx = i, spec = spec, x = x, w = w, top = top, h = h, gen = gen }
                end
            elseif r and r.IsShown and r:IsShown() then
                r:Hide()
            end
            if spec.sec then
                local b = bb[spec.sec]
                if spec.goldSec then bgold[spec.sec] = true end
                if not b then
                    bb[spec.sec] = { x0 = x, y0 = top, x1 = x + w, y1 = top + h }
                else
                    b.x0 = math.min(b.x0, x)
                    b.y0 = math.min(b.y0, top)
                    b.x1 = math.max(b.x1, x + w)
                    b.y1 = math.max(b.y1, top + h)
                end
            end
            if span then
                y[1], y[2] = top + h + 2, top + h + 2
            else
                y[col] = top + h + 2
            end
        end
    end
    -- ★ 空洞安全（2026-10-09）：`#PD.rows` 遇空洞会提前截断 ⇒ 上一页尾部还在
    --   显示中的行藏不掉。改用 pairs 扫（集合与原来逐字相同，只是不再依赖 `#`）。
    -- ★ 2026-10-09 补：**正显示着的**越界行要「除内容」而不是只 Hide。
    --   切页那道闸（PD.Render 顶部）已经把全池抹过了，所以正常切页这里一个都不命中；
    --   真正命中它的是**同页内 `n` 变小**的路径 —— 配方页搜索 / 换分类、营地换阵营、
    --   路线换目标等级…… 这些不换页面身份（页签/专业/子页/设置页都没动），
    --   那道闸不响；只 Hide 的话行帧上还挂着上一批内容的材料列 / 商人半段。
    --   加 `IsShown()` 前置判断 ⇒ 反复重渲（到货重扫等）零额外开销（隐藏行一次都不抹）。
    for i, rr in pairs(PD.rows) do
        if i > n then
            if rr.IsShown and rr:IsShown() then PD.WipeRow(rr) else rr:Hide() end
        end
    end
    if PD.secCards then
        -- ★ 每次渲染先把两个卡池全收起来，再按需显示：原来靠「共用计数器 ci 裁后段」收尾，
        --   两个池子用得不一样多时就漏：总览/营地用普通卡池（secCards），购物清单只用金卡池（secGoldCards），
        --   ci 一算两边都从 3 起裁 ⇒ 总览/营地那两张普通卡留在购物清单页上。
        for i = 1, #PD.secCards do PD.secCards[i]:Hide() end
        for i = 1, #PD.secGoldCards do PD.secGoldCards[i]:Hide() end
    end
    if PD.hasSecs then
        -- 两个池子各用各的计数器（普通卡池 / 金卡池互不从属）
        local ciP, ciG = 0, 0
        for s = 1, (PD.secCount or 0) do
            local b = bb[s]
            if b then
                local gold = bgold[s] and true or false
                local idx
                if gold then ciG = ciG + 1; idx = ciG else ciP = ciP + 1; idx = ciP end
                local c = (gold and PD.secGoldCards or PD.secCards)[idx]
                if c then
                    local padL = PD.secPadL or PD.SEC_PAD_X
                    c:ClearAllPoints()
                    c:SetPoint("TOPLEFT", PD.child, "TOPLEFT",
                               b.x0 - padL, -(b.y0 - PD.SEC_PAD))
                    c:SetSize((b.x1 - b.x0) + padL + PD.SEC_PAD_X,
                              (b.y1 - b.y0) + 2 * PD.SEC_PAD)
                    c:Show()
                end
            end
        end
    end
    local h1 = math.max(y[1], y[2])
    if PD.wantIndexGrid and PD.ixRoot then
        PD.placeIndexGrid(h1)
        h1 = h1 + (PD.ixGridH or 0) + 8
    elseif PD.ixRoot then
        PD.ixRoot:Hide()
    end
    if PD.wantBonusTable and PD.bonusTable then
        PD.placeBonusTable(h1)
        if PD.bonusTitleNote then
            PD.bonusTitleNote:ClearAllPoints()
            PD.bonusTitleNote:SetPoint("TOPRIGHT", PD.child, "TOPRIGHT",
                                       -PD.LIST_PAD, -(h1 - 19))
            PD.bonusTitleNote:Show()
        end
        h1 = h1 + (PD.bonusTableH or 0) + 2 * PD.SEC_PAD + 8
    elseif PD.bonusTable then
        if PD.bonusTitleNote then PD.bonusTitleNote:Hide() end
        PD.bonusTable:Hide()
        if PD.bonusCard then PD.bonusCard:Hide() end
    end
    if PD.wantTrainerBoard and PD.trainerBoard then
        PD.placeTrainerBoard(h1)
        h1 = h1 + (PD.trainerBoardH or 0) + 2 * PD.SEC_PAD + 8
    elseif PD.trainerBoard then
        PD.trainerCard:Hide()
    end
    PD.child:SetHeight(math.max(h1, y[2]) + 10)
    if PD.UpdateVScroll then PD.UpdateVScroll() end   -- 滚动条随内容高度刷新
    PD.FlushPendingRows()
    return truncated
end

function PD.RowBorder(r, on)
    local show = on and true or false
    r.bT:SetShown(show)
    r.bB:SetShown(show)
    r.bL:SetShown(show)
    r.bR:SetShown(show)
    if not show then return end
    local cr, cg, cb = PD.NavAccent()
    r.bT:SetColorTexture(cr, cg, cb, 0.95)
    r.bB:SetColorTexture(cr, cg, cb, 0.95)
    r.bL:SetColorTexture(cr, cg, cb, 0.95)
    r.bR:SetColorTexture(cr, cg, cb, 0.95)
end

function PD.BindRow(r, spec, h)
    r.e:SetWidth(0) -- Clear the recipe-column width when this pooled row changes pages.
    if r.__costZone then r.__costZone:Hide() end
    r.__spec = spec
    r.__z = spec.z and true or false
    PD.SetRowHover(r, r.IsMouseOver and r:IsMouseOver())
    r.__it = spec.it
    r.__noTip = spec.noTip
    r.__lines = spec.lines
    r.__mkLines = spec.mkLines
    r.__linesFirst = spec.linesFirst
    r.__act = spec.act
    r.__routePolicy = spec.lvstep and spec.act and true or nil
    r.__tipTitle = spec.tipTitle   -- 提示框首行覆写（工匠文书行用；nil = 走物品名）
    r.__tipExtra = spec.tipExtra   -- 惰性价格段（配方行挂函数；行池复用靠这里整体重置）
    r.__named = false
    -- 行池跨页复用防护：配方页专属件先全部隐藏，配方分支里再按需亮起
    r.h1:Hide(); r.h2:Hide(); r.h3:Hide(); r.h4:Hide(); r.h5:Hide(); r.h6:Hide()
    PD.PaintDiffBar(r, nil)
    do
        local wantFs = spec.fs or (spec.kind == "head" and 16 or 13)
        local _, curFs = r.a:GetFont()
        if curFs ~= wantFs then
            r.a:SetFont(ns.FONT, wantFs,
                        ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE")
        end
    end
    do
        local auxFs = (spec.fs == 14) and 14 or nil
        local fl = ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE"
        local _, bfs = r.b:GetFont()
        local wb = auxFs or 11
        if bfs ~= wb then r.b:SetFont(ns.FONT, wb, fl) end
        local _, cfs = r.c:GetFont()
        local wc = auxFs or 12
        if cfs ~= wc then r.c:SetFont(ns.FONT, wc, fl) end
    end
    PD.ClearMats(r)
    PD.ClearMatSegs(r)
    -- ★★ 第十刀（rev16）：首屏之外的配方行，材料串在 FitRecipeCols 里只挂了
    --   待算标（那是「点开那一瞬间」最贵的一笔单点）。这里在**真绑上前**
    --   用同一个 PD.MAT_W 补算 —— 列宽此刻已定稿 ⇒ 与首屏那批逐字节一致。
    if spec._matsPending then PD.FinishSpecMats(spec) end
    PD.RowBorder(r, spec.cur)
    r.tagFs:Hide()
    r.tagBg:Hide()
    r.icon2:Hide()
    r.icon3:Hide()
    r.icon4:Hide()
    r.hsOwn:Hide()
    r.hsTot:Hide()
    r.hsCraft:Hide()
    r.hsGap:Hide()
    do
        local _, dfs = r.d:GetFont()
        if dfs ~= 11 then
            r.d:SetFont(ns.FONT, 11, ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE")
        end
    end

    local iconName = spec.icon
    local itemID = spec.it and spec.it[1]
    local showIcon = (spec.kind == "row" or spec.kind == "head") and (itemID or iconName) and true or false
    r.icon:SetShown(showIcon)
    -- 制作物热区默认收起：行池是跨页共用的，同一条行上一轮可能是升级行、这一轮是标题/文本行
    --   ⇒ 不收起就会留一个透明热区在旧位置吞鼠标（升级行分支里再按需 Show）。
    if r.__iconZone then r.__iconZone:Hide() end
    if r.__vs then
        for _, c in ipairs(r.__vs.cards) do c:Hide() end
        for _, z in ipairs(r.__vs.zones) do z:Hide() end
    end
    if r.__pct then r.__pct:Hide() end
    if showIcon then
        r.icon:SetSize(20, 20)
        r.icon:ClearAllPoints()
        r.icon:SetPoint("TOPLEFT", r, "TOPLEFT", 6, -math.floor((h - 20) / 2))
        SetIcon(r.icon, iconName or DG.ItemIcon(itemID))
    end

    if spec.kind == "head" then
        r.a:SetTextColor(Unpack(C_WHITE))
        r.a:SetText(spec.text or "")
        r.a:ClearAllPoints()
        if itemID or iconName then
            r.icon:SetSize(20, 20)
            r.icon:ClearAllPoints()
            r.icon:SetPoint("LEFT", r, "LEFT", 6, 0)
            SetIcon(r.icon, iconName or DG.ItemIcon(itemID))
            r.a:SetPoint("LEFT", r.icon, "RIGHT", 6, 0)
        else
            r.a:SetPoint("LEFT", r, "LEFT", 6, 0)
        end
        r.b:SetText(""); r.d:SetText(""); r.e:SetText(""); r.f:SetText("")
        if spec.right and spec.right ~= "" then
            r.c:SetTextColor(Unpack(C_GREY))
            r.c:SetText(spec.right)
            r.c:ClearAllPoints()
            r.c:SetWordWrap(false)
            r.c:SetPoint("RIGHT", r, "RIGHT", -6, 0)
        else
            r.c:SetText("")
        end
        r.c2:SetText("")
        if spec.tag then
            r.tagFs:SetTextColor(Unpack(spec.tag.color or { 0.42, 0.94, 0.62 }))
            r.tagFs:SetText(spec.tag.text or "")
            r.tagFs:ClearAllPoints()
            r.tagFs:SetPoint("LEFT", r.a, "LEFT", r.a:GetStringWidth() + 6, 0)
            r.tagBg:ClearAllPoints()
            r.tagBg:SetPoint("TOPLEFT", r.tagFs, "TOPLEFT", -4, 1)
            r.tagBg:SetPoint("BOTTOMRIGHT", r.tagFs, "BOTTOMRIGHT", 4, -1)
            r.tagFs:Show()
            r.tagBg:Show()
        end
        if r.__warn then
            r.__warn:Hide()
            r.__warn.__tipLines = nil
        end
        if spec.warn and spec.warn[1] then
            local wz = PD.WarnChip(r)
            wz:ClearAllPoints()
            wz:SetPoint("LEFT", r.a, "LEFT", r.a:GetStringWidth() + 8, 0)
            wz.__tipLines = spec.warn
            wz:Show()
        end
        r.sep:Hide()
        return
    end
    if spec.kind == "rechead" then
        -- 2026-10-10 配方页五列表头（fs16 等大等高）：配方 | 材料 | 拍卖 | 制作成本 | 难度
        --   ★ 全走专用字串池 r.h1~h5（20:45 b0272ae 口径）—— 不借 r.a/r.f/r.c2/r.e，
        --     行池跨页复用借字会污染字号/颜色/锚点；且本分支尾部清理链会清 r.c2，
        --     借位设字会被自己清掉（「拍卖」表头消失事故）。
        r.h1:SetText(L["配方"])
        r.h1:ClearAllPoints()
        r.h1:SetPoint("LEFT", r, "LEFT", 6, 0)
        r.h1:Show()
        r.h2:SetText(L["材料"])
        r.h2:ClearAllPoints()
        r.h2:SetPoint("LEFT", r, "LEFT", PD.MAT_X, 0)
        r.h2:Show()
        r.h3:SetText(L["拍卖"])
        r.h3:ClearAllPoints()
        r.h3:SetPoint("RIGHT", r, "RIGHT", -(6 + PD.DiffBarW() + PD.REC_COST_W), 0)
        r.h3:Show()
        r.h4:SetText(L["制作成本"])
        r.h4:ClearAllPoints()
        r.h4:SetPoint("RIGHT", r, "RIGHT", -(6 + PD.DiffBarW()), 0)
        r.h4:Show()
        r.h5:SetText(L["难度"])
        r.h5:ClearAllPoints()
        r.h5:SetPoint("RIGHT", r, "RIGHT", -6, 0)
        r.h5:Show()
        -- 2026-10-13 配方页排序（参考板条箱）：三态（升→降→取消）；拍卖列右半=拍卖、左半=差距+「差价」；表头文字随排序变色
        local SORT = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\NAV\\SortIcon"
        local X_ahR = -(6 + PD.DiffBarW() + PD.REC_COST_W)
        local function _act(col)
            return function()
                if PD.recipeSort ~= col then
                    PD.recipeSort, PD.recipeSortDesc = col, false
                elseif not PD.recipeSortDesc then
                    PD.recipeSortDesc = true
                else
                    PD.recipeSort, PD.recipeSortDesc = nil, false
                end
                PD.RequestRender()
            end
        end
        local function _ic(tex, on)
            SetIcon(tex, SORT)
            tex:SetSize(14, 14)
            if on then tex:SetVertexColor(1, 0.82, 0, 1)
            else tex:SetVertexColor(0.55, 0.57, 0.62, 1) end
            tex:SetShown(true)
        end
        local function _hc(fs, on)
            if on then fs:SetTextColor(1, 0.82, 0, 1)
            else fs:SetTextColor(Unpack(C_GREY)) end
        end
        local onAh = PD.recipeSort == "ah"
        _ic(r.icon, onAh)
        r.icon:SetPoint("RIGHT", r.h3, "LEFT", -3, 0)
        _hc(r.h3, onAh)
        r.hsTot:ClearAllPoints()
        r.hsTot:SetPoint("TOPRIGHT", r, "TOPRIGHT", X_ahR, 0)
        r.hsTot:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", X_ahR, 0)
        r.hsTot:SetWidth(48)
        r.hsTot.__act = _act("ah")
        r.hsTot:Show()
        local onGap = PD.recipeSort == "gap"
        _ic(r.icon4, onGap)
        r.h6:SetText(L["差价"])
        r.h6:ClearAllPoints()
        r.h6:SetPoint("RIGHT", r, "RIGHT", X_ahR - 58, 0)
        _hc(r.h6, onGap)
        r.h6:Show()
        r.icon4:SetPoint("RIGHT", r.h6, "LEFT", -2, 0)
        r.hsGap:ClearAllPoints()
        r.hsGap:SetPoint("TOPRIGHT", r, "TOPRIGHT", X_ahR - 58, 0)
        r.hsGap:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", X_ahR - 58, 0)
        r.hsGap:SetWidth(58)
        r.hsGap.__act = _act("gap")
        r.hsGap:Show()
        local onCost = PD.recipeSort == "cost"
        _ic(r.icon2, onCost)
        r.icon2:SetPoint("RIGHT", r.h4, "LEFT", -3, 0)
        _hc(r.h4, onCost)
        r.hsOwn:ClearAllPoints()
        r.hsOwn:SetPoint("TOPRIGHT", r, "TOPRIGHT", -(6 + PD.DiffBarW()), 0)
        r.hsOwn:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -(6 + PD.DiffBarW()), 0)
        r.hsOwn:SetWidth(60)
        r.hsOwn.__act = _act("cost")
        r.hsOwn:Show()
        local onDiff = PD.recipeSort == "diff"
        _ic(r.icon3, onDiff)
        r.icon3:SetPoint("RIGHT", r.h5, "LEFT", -3, 0)
        _hc(r.h5, onDiff)
        r.hsCraft:ClearAllPoints()
        r.hsCraft:SetPoint("TOPRIGHT", r, "TOPRIGHT", -6, 0)
        r.hsCraft:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -6, 0)
        r.hsCraft:SetWidth(40)
        r.hsCraft.__act = _act("diff")
        r.hsCraft:Show()
        r.b:SetText(""); r.c:SetText(""); r.c2:SetText(""); r.d:SetText(""); r.e:SetText(""); r.f:SetText(""); r.dv:SetText(""); r.dv:Hide()
        r.sep:Hide()
        return
    end
    if spec.kind == "text" then
        r.a:SetTextColor(Unpack(spec.color or C_TEXT))
        r.a:SetText(spec.text or "")
        r.a:ClearAllPoints()
        if spec.center then
            r.a:SetPoint("CENTER", r, "CENTER", 0, 0)
        else
            r.a:SetPoint("LEFT", r, "LEFT", 6, 0)
        end
        r.b:SetText(""); r.c:SetText(""); r.c2:SetText(""); r.d:SetText(""); r.e:SetText(""); r.f:SetText("")
        r.sep:Hide()
        return
    end
    r.sep:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 0, 0)
    r.sep:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", 0, 0)
    -- 2026-10-10 用户：斑马纹已承担行分隔 → 每行分割线退役（_lastInSec 全项目仅此一处消费）
    r.sep:Hide()

    -- Five execution columns; material details remain on recipe tooltips.
    if spec.kind == "lvhead" then
        local hout = ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE"
        local columns = {
            {r.a, L["步骤"], "LEFT", PD.LV_STEP_X},
            {r.d, L["等级范围"], "LEFT", PD.LV_RNG_X},
            {r.e, L["配方"], "LEFT", PD.LV_NAME_X},
            {r.c, L["制作次数"], "RIGHT", -PD.LV_COUNT_R},
            {r.c2, L["成本"], "RIGHT", -PD.LV_COST_R},
        }
        for _, column in ipairs(columns) do
            local text = column[1]
            text:SetTextColor(Unpack(C_GREY))
            text:SetFont(ns.FONT, 12, hout)
            text:SetText(column[2])
            text:ClearAllPoints()
            text:SetPoint(column[3], r, column[3], column[4], 0)
        end
        r.b:SetText(""); r.f:SetText("")
        PD.HideSkillBar(r)
        PD.PaintCard(r, nil)
        return
    end

    -- 2026-10-11 板条箱/工匠文书页左列表头（灰小字，锚点与列表行对齐：名左 6 / 成本右 6）
    --   act：表头右列左侧挂 14px 排序 TGA，整行可点切换排序；金 = 启用 / 灰 = 未启用
    --   （2026-10-11 修：字段是 act，此前误判 sortAct 恒 nil → 图标永不挂载）
    if spec.kind == "colhead" then
        r.a:SetTextColor(Unpack(C_GREY))
        r.a:SetText(spec.text or "")
        r.a:ClearAllPoints()
        r.a:SetPoint("LEFT", r, "LEFT", 6, 0)
        r.c:SetTextColor(Unpack(C_GREY))
        r.c:SetText(spec.right or "")
        r.c:ClearAllPoints()
        r.c:SetWordWrap(false)
        if spec.craftAct then
            r.c:SetPoint("TOPRIGHT", r, "TOPRIGHT", -6, -4)
        else
            r.c:SetPoint("RIGHT", r, "RIGHT", -6, 0)
        end
        r.c2:SetText("")
        r.icon:SetSize(14, 14)
        r.icon:ClearAllPoints()
        r.icon2:SetSize(14, 14)
        r.icon2:ClearAllPoints()
        if spec.ownAct then
            r.c2:SetTextColor(Unpack(C_GREY))
            r.c2:SetText(spec.ownRight or "")
            r.c2:ClearAllPoints()
            r.c2:SetWordWrap(false)
            if spec.craftAct then
                r.c2:SetPoint("TOPRIGHT", r, "TOPRIGHT", -PD.OwnR(), -4)
            else
                r.c2:SetPoint("RIGHT", r, "RIGHT", -PD.OwnR(), 0)
            end
            SetIcon(r.icon2, "Interface\\AddOns\\DungeonsForever\\Media\\icon\\NAV\\SortIcon")
            r.icon2:SetPoint("RIGHT", r.c2, "LEFT", -4, 0)
            if spec.ownOn then
                r.icon2:SetVertexColor(1, 0.82, 0, 1)
            else
                r.icon2:SetVertexColor(0.55, 0.57, 0.62, 1)
            end
            r.icon2:SetShown(true)
            r.hsOwn:ClearAllPoints()
            r.hsOwn:SetPoint("TOPRIGHT", r, "TOPRIGHT", -PD.OwnR(), 0)
            r.hsOwn:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -PD.OwnR(), 0)
            r.hsOwn:SetWidth(92)
            r.hsOwn.__act = spec.ownAct
            r.hsOwn:Show()
        else
            r.hsOwn:Hide()
        end
        if spec.act then
            SetIcon(r.icon, "Interface\\AddOns\\DungeonsForever\\Media\\icon\\NAV\\SortIcon")
            r.icon:SetPoint("RIGHT", r.c, "LEFT", -4, 0)
            if spec.sortOn then
                r.icon:SetVertexColor(1, 0.82, 0, 1)
            else
                r.icon:SetVertexColor(0.55, 0.57, 0.62, 1)
            end
            r.icon:SetShown(true)
            r.hsTot:ClearAllPoints()
            r.hsTot:SetPoint("TOPRIGHT", r, "TOPRIGHT", -6, 0)
            if spec.craftAct then
                r.hsTot:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -6, 17)
            else
                r.hsTot:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -6, 0)
            end
            r.hsTot:SetWidth(92)
            r.hsTot.__act = spec.act
            r.hsTot:Show()
        else
            r.hsTot:Hide()
        end
        r.b:SetText(""); r.d:SetText(""); r.e:SetText(""); r.f:SetText("")
        if spec.craftAct then
            r.d:SetTextColor(Unpack(C_GREY))
            do
                local _, dfs = r.d:GetFont()
                if dfs ~= 12 then
                    r.d:SetFont(ns.FONT, 12, ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE")
                end
            end
            r.d:SetText(spec.craftRight or "")
            r.d:ClearAllPoints()
            r.d:SetWordWrap(false)
            r.d:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -6, 4)
            SetIcon(r.icon3, "Interface\\AddOns\\DungeonsForever\\Media\\icon\\NAV\\SortIcon")
            r.icon3:SetSize(14, 14)
            r.icon3:ClearAllPoints()
            r.icon3:SetPoint("RIGHT", r.d, "LEFT", -4, 0)
            if spec.craftOn then
                r.icon3:SetVertexColor(1, 0.82, 0, 1)
            else
                r.icon3:SetVertexColor(0.55, 0.57, 0.62, 1)
            end
            r.icon3:SetShown(true)
            r.hsCraft:ClearAllPoints()
            r.hsCraft:SetPoint("TOPRIGHT", r, "TOPRIGHT", -6, -17)
            r.hsCraft:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -6, 0)
            r.hsCraft:SetWidth(92)
            r.hsCraft.__act = spec.craftAct
            r.hsCraft:Show()
        else
            r.hsCraft:Hide()
        end
        r.dv:Hide()
        PD.HideSkillBar(r)
        PD.PaintCard(r, nil)
        return
    end

    if spec.kind == "vs" then
        local vs = PD.VsBlock(r)
        local W = tonumber(spec.vw) or tonumber(PD.splitRW) or 160
        local cw = math.max(40, math.floor((W - 8) / 2))
        for k = 1, 2 do
            local d = spec.cards and spec.cards[k] or nil
            local c, z = vs.cards[k], vs.zones[k]
            if d then
                c:ClearAllPoints()
                if k == 1 then
                    c:SetPoint("TOPLEFT", r, "TOPLEFT", 0, 0)
                else
                    c:SetPoint("TOPRIGHT", r, "TOPRIGHT", 0, 0)
                end
                c:SetSize(cw, h)
                c.lab:SetText(d.lab or "")
                c.lab:SetTextColor(Unpack(d.win and C_WHITE or C_GREY))
                local pc = d.win and { 0.42, 0.94, 0.62 } or (d.priceOk and C_TEXT or C_GREY)
                c.price:SetTextColor(Unpack(pc))
                c.price:SetText(d.price or "—")
                c.nm:SetTextColor(Unpack(d.dim and C_GREY or C_TEXT))
                c.nm:SetText(d.name or "")
                if d.it then
                    c.ic:SetSize(22, 22)
                    SetIcon(c.ic, DG.ItemIcon(d.it))
                    c.ic:Show()
                else
                    c.ic:Hide()
                end
                if d.win then
                    c.badgeFs:SetText(L["最省"])
                    c.badge:Show()
                else
                    c.badge:Hide()
                end
                c:Show()
                z:ClearAllPoints()
                z:SetPoint("TOPLEFT", c, "TOPLEFT", 0, 0)
                z:SetPoint("BOTTOMRIGHT", c, "BOTTOMRIGHT", 0, 0)
                z.__tipLines = nil
                z.__tipExtra = d.tipExtra
                z.__act = nil
                z.__it = d.it and { d.it } or nil
                z:Show()
            else
                c:Hide()
                z:Hide()
            end
        end
        r.a:SetText(""); r.b:SetText(""); r.c:SetText(""); r.c2:SetText(""); r.d:SetText(""); r.e:SetText(""); r.f:SetText("")
        r.dv:SetText(""); r.dv:Hide()
        PD.HideSkillBar(r)
        PD.PaintCard(r, nil)
        return
    end

    -- 2026-10-11 采集路线三列行（gr3）：[等级区间 | 地点 | 图标+矿名]
    --   行池跨页复用：闲置字串全清 + 复用防护同 lvhead（技能条/来源卡片收起）；
    --   悬停明细按用户拍板不上，__it 保留 → 悬停行出矿石物品提示框。
    if spec.gr3 then
        r.a:SetTextColor(Unpack(C_GOLD))
        r.a:SetText(spec.lv or "")
        r.a:ClearAllPoints()
        r.a:SetPoint("LEFT", r, "LEFT", PD.GR_LV_X, 0)
        r.b:SetTextColor(Unpack(C_TEXT))
        r.b:SetText(spec.loc or "")
        r.b:ClearAllPoints()
        r.b:SetPoint("LEFT", r, "LEFT", PD.GR_LOC_X, 0)
        r.c:SetText(""); r.c2:SetText(""); r.d:SetText(""); r.f:SetText("")
        r.dv:Hide()
        local gcol = spec.nameColor
        if not gcol and spec.qItem then
            local gq = PD.QualCached(spec.qItem)
            if gq then gcol = { DG.QColor(gq) } end
        end
        if spec.icons then
            -- ★ 采药/采矿第三列只放图标（2026-10-11 用户）：名字退役，图标右起横排（右→左 4px 间距）
            r.e:SetText("")
            r.icon:Hide()
            for k = 1, #r.gic do
                local g, id = r.gic[k], spec.icons[k]
                if id then
                    g:Show()
                    g:ClearAllPoints()
                    if k == 1 then
                        g:SetPoint("RIGHT", r, "RIGHT", -6, 0)
                    else
                        g:SetPoint("RIGHT", r.gic[k - 1], "LEFT", -4, 0)
                    end
                    SetIcon(g, DG.ItemIcon(id))
                else
                    g:Hide()
                end
            end
        else
            r.e:SetText(spec.text or "")
            r.e:SetTextColor(Unpack(gcol or C_TEXT))
            r.e:ClearAllPoints()
            r.e:SetPoint("RIGHT", r, "RIGHT", -6, 0)
            r.icon:SetSize(PD.GR_ICON_W, PD.GR_ICON_W)
            r.icon:ClearAllPoints()
            r.icon:SetPoint("RIGHT", r.e, "LEFT", -6, 0)
            SetIcon(r.icon, iconName or DG.ItemIcon(itemID))
        end
        PD.HideSkillBar(r)
        PD.PaintCard(r, nil)
        return
    end

    if spec.lvstep then
        local colors = spec.passed and C_DIM or C_TEXT
        r.a:SetTextColor(Unpack(colors))
        r.d:SetTextColor(Unpack(colors))
        r.e:SetTextColor(Unpack(spec.passed and C_DIM or C_GOLD))
        r.c:SetTextColor(Unpack(spec.passed and C_DIM or C_GOLD))
        r.c2:SetTextColor(Unpack(spec.passed and C_DIM or C_GOLD))
        r.a:SetText(tostring(spec.stepIndex or ""))
        r.d:SetText(spec.rng or "")
        r.d:SetFont(ns.FONT, PD.LV_FS, ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE")
        r.e:SetText(spec.text or "")
        r.b:SetText("")
        r.c:SetText(spec.cnt or "")
        r.c2:SetText(spec.cost or "")
        r.f:SetText("")
        r.a:ClearAllPoints()
        r.a:SetPoint("LEFT", r, "LEFT", PD.LV_STEP_X, 0)
        r.d:ClearAllPoints()
        r.d:SetPoint("LEFT", r, "LEFT", PD.LV_RNG_X, PD.TBL_NAME_DY)
        r.e:ClearAllPoints()
        r.e:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X, PD.TBL_NAME_DY)
        r.e:SetWidth(PD.LV_NAME_W)
        r.c2:ClearAllPoints()
        r.c2:SetPoint("RIGHT", r, "RIGHT", -PD.LV_COST_R, 0)
        r.c:ClearAllPoints()
        r.c:SetPoint("RIGHT", r, "RIGHT", -PD.LV_COUNT_R, 0)
        r.icon:SetSize(PD.TBL_ICON, PD.TBL_ICON)
        r.icon:ClearAllPoints()
        r.icon:SetPoint("LEFT", r, "LEFT", PD.LV_ICON_X, 0)
        r.icon:SetDesaturated(spec.passed and true or false)
        if spec.sbVals then PD.PaintSkillBar(r, spec.sbVals, spec.sbLo, spec.sbHi, spec.passed)
        else PD.HideSkillBar(r) end
        PD.PaintCard(r, spec.card)
        local iz = PD.IconZone(r)
        iz.__it = itemID and { itemID } or nil
        iz.__tipLines = nil
        iz.__act = spec.act and function(zone, button)
            if button == "LeftButton" and IsShiftKeyDown and IsShiftKeyDown() then DG.ItemShiftClick(zone, button)
            else spec.act(zone, button) end
        end or nil
        iz.__tipExtra = spec.tipExtra
        iz:ClearAllPoints()
        iz:SetPoint("LEFT", r, "LEFT", PD.LV_ICON_X, 0)
        iz:SetSize(PD.LV_NAME_X - PD.LV_ICON_X + PD.LV_NAME_W, h)
        iz:SetShown(itemID and true or false)
        r.__cardZone:SetFrameLevel(iz:GetFrameLevel() + 1)
        local costZone = r.__costZone
        if costZone then
            costZone.__tipLines = {{L["成本"] .. ": " .. (spec.cost or "")},
                {L["成本为本步骤新增采购；已在中间产物步骤计入的费用不重复计入。"], 0.7, 0.7, 0.7}}
            costZone.__it, costZone.__act = nil, nil
            costZone:ClearAllPoints()
            costZone:SetPoint("RIGHT", r, "RIGHT", -PD.LV_COST_R, 0)
            costZone:SetSize(PD.LV_COST_W + 8, h)
            costZone:SetShown(spec.cost and spec.cost ~= "" or false)
        end
        return
    end

    local padL = showIcon and ((iconName and not itemID) and 28 or 32) or 6
    -- 2026-10-10 用户：配方/可制造名称按产物物品品质着色（无品质数据退回默认色）
    local ncol = spec.nameColor
    if not ncol and spec.qItem then
        local q = PD.QualCached(spec.qItem)
        if q then ncol = { DG.QColor(q) } end
    end
    r.a:SetTextColor(Unpack(ncol or C_TEXT))
    r.a:SetText(spec.text or "")
    -- 2026-10-10 用户：「新」角标从名称行尾移到副行（类型左边）；行尾版退役
    r.b:SetText((spec.is_new and L[" |cff40d940新|r"] .. " " or "") .. (spec.sub or ""))
    r.c:SetText(spec.right or "")
    r.c:SetTextColor(Unpack(spec.rightColor or C_GOLD))
    r.d:SetText(spec.right2 or "")
    if spec.right2 and spec.right2 ~= "" then
        local dfsW = (spec.fs == 14) and 14 or 12
        local _, dfs = r.d:GetFont()
        if dfs ~= dfsW then
            r.d:SetFont(ns.FONT, dfsW, ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE")
        end
    end
    if spec.right2Color then
        r.d:SetTextColor(Unpack(spec.right2Color))
    end
    r.e:SetText("")
    if spec.rightOwn and h > PD.ROW_H1 then
        r.c2:SetText(spec.rightOwn)
        r.c2:SetTextColor(Unpack(spec.rightOwnColor or C_TEXT))
        r.c2:ClearAllPoints()
        r.c2:SetWordWrap(false)
        r.c2:SetPoint("TOPRIGHT", r, "TOPRIGHT", -PD.OwnR(), -4)
    else
        r.c2:SetText("")
    end
    r.f:SetTextColor(Unpack(spec.matColor or C_TEXT))
    -- 有分段数据（配方页）就让分段链自己写各段；没有（附魔/可制造/商人兑换）照旧走整串
    if not spec.matSegs then r.f:SetText(spec.mats or "") end
    r.a:ClearAllPoints()
    r.c:ClearAllPoints()
    r.f:ClearAllPoints()
    if h <= PD.ROW_H1 then
        r.a:SetPoint("LEFT", r, "LEFT", padL, 0)
        r.b:SetText("")
        r.c:SetPoint("RIGHT", r, "RIGHT", -6, 0)
        r.d:SetText("")
        r.f:SetText("")
    else
        r.a:SetPoint("TOPLEFT", r, "TOPLEFT", padL, -4)
        r.b:ClearAllPoints()
        r.b:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", padL, 4)
        r.c:SetPoint("TOPRIGHT", r, "TOPRIGHT", -6, -4)
        r.d:ClearAllPoints()
        r.d:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -6, 4)
        r.f:SetPoint("LEFT", r, "LEFT", PD.MAT_X, 0)
        -- 2026-10-09：配方页材料列摆分段链（第 1 段的 SetPoint 由 PaintMatSegs 重写，
        --   与上面这行同值，不冲突）
        if spec.matSegs then PD.PaintMatSegs(r, spec.matSegs, spec.matColor) end
    end
    -- 2026-10-10 配方页右三列（仅双行配奉行）：难度四段色条（右上角，sbdiff=nil 即隐藏）
    --   → 制作成本（r.e 金）→ 拍卖（r.c2 白）；列位从右缘往左排，互相零间距（2026-10-10 用户）
    if h > PD.ROW_H1 and (spec.sbdiff or spec.costStr or spec.ahStr) then
        PD.PaintDiffBar(r, spec.sbdiff)
        if spec.costStr then
            r.e:SetText(spec.costStr)
            r.e:SetTextColor(Unpack(C_GOLD))
            r.e:ClearAllPoints()
            r.e:SetPoint("TOPRIGHT", r, "TOPRIGHT", -(6 + PD.DiffBarW()), -4)
            r.e:SetWordWrap(false)
        end
        if spec.ahStr then
            r.c2:SetText(spec.ahStr)
            r.c2:SetTextColor(Unpack(C_TEXT))
            r.c2:ClearAllPoints()
            r.c2:SetPoint("TOPRIGHT", r, "TOPRIGHT", -(6 + PD.DiffBarW() + PD.REC_COST_W), -4)
            r.c2:SetWordWrap(false)
        end
        if spec.pct then
            local chip = PD.PctChip(r)
            chip.fs:SetText(spec.pct.text)
            chip.fs:SetTextColor(Unpack(spec.pct.color))
            chip:ClearAllPoints()
            chip:SetPoint("TOPRIGHT", r.c2, "BOTTOMRIGHT", 0, -1)
            chip:SetHeight(15)
            chip:SetWidth(chip.fs:GetStringWidth() + 8)
            chip:SetFrameLevel(r:GetFrameLevel() + 2)
            chip:Show()
        elseif r.__pct then
            r.__pct:Hide()
        end
    end
    -- 右下角那格拆两半：前缀留在 r.d，恒居末位的「商人：X」搬到 r.dv ——
    --   热区只盖「商人」半段（用户：「鼠标在商人上面」）；两半用锚点链相接，不量宽。
    if spec.dval and h > PD.ROW_H1 then
        r.d:SetText(spec.dpre or "")
        r.dv:SetText(spec.dval)
        r.dv:SetTextColor(Unpack(C_GREY))
        r.dv:ClearAllPoints()
        r.dv:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -6, 4)
        r.dv:Show()
        r.d:ClearAllPoints()
        r.d:SetPoint("RIGHT", r.dv, "LEFT", 0, 0)
        local vz = PD.IconZone(r)
        vz.__it = nil
        vz.__tipLines = spec.vlines or PD.VendorLines(spec.src)
        vz.__act = spec.dact or PD.VendorAct(spec.src)
        vz:ClearAllPoints()
        vz:SetPoint("TOPLEFT", r.dv, "TOPLEFT", 0, 1)
        vz:SetPoint("BOTTOMRIGHT", r.dv, "BOTTOMRIGHT", 0, -1)
        vz:Show()
    end
    -- 「直售」小徽标贴名称右侧（HUD 药丸的页面版，2026-10-09 三轮）
    if spec.tag then
        r.tagFs:SetTextColor(Unpack(spec.tag.color or { 0.42, 0.94, 0.62 }))
        r.tagFs:SetText(spec.tag.text or "")
        r.tagFs:ClearAllPoints()
        r.tagFs:SetPoint("LEFT", r.a, "LEFT", r.a:GetStringWidth() + 6, 0)
        r.tagBg:ClearAllPoints()
        r.tagBg:SetPoint("TOPLEFT", r.tagFs, "TOPLEFT", -4, 1)
        r.tagBg:SetPoint("BOTTOMRIGHT", r.tagFs, "BOTTOMRIGHT", 4, -1)
        r.tagFs:Show()
        r.tagBg:Show()
    end
end

PD.BT_COL1 = 88
PD.BT_W_LAST = 236
PD.BT_H_HEAD = 28
PD.BT_LINE_H = 19
PD.BT_ROW_MIN = 34

function PD.BuildBonusTable(parent)
    local card = CreateFrame("Frame", nil, parent)
    PD.bonusCard = card
    ns.hui.BuildRoundedBG(card, 6, ns.hui.layer.L2, "both", true, 1)
    card:Hide()
    local root = CreateFrame("Frame", nil, card)
    PD.bonusTable = root
    local W = PD.RIGHT_W - 2 * PD.LIST_PAD - PD.SEC_IN
    root:SetSize(W, 10)
    PD.BT_W = W
    PD.BT_COLW = math.floor((W - PD.BT_COL1 - PD.BT_W_LAST) / 3)

    local heads = { L["专业"], format(L["技能 %d"], 20), format(L["技能 %d"], 140),
                    format(L["技能 %d"], 300), L["职业版对照 / 其他功能"] }
    for j, txt in ipairs(heads) do
        local fs = MakeFS(root, 14, C_GOLD, "LEFT")
        local x = (j == 1) and 0 or (PD.BT_COL1 + (j - 2) * PD.BT_COLW)
        fs:SetPoint("TOPLEFT", root, "TOPLEFT", x, -5)
        fs:SetText(txt)
    end
    local tipBtn = CreateFrame("Button", nil, root)
    tipBtn:EnableMouse(true)
    tipBtn:SetSize(PD.BT_W_LAST - 6, PD.BT_H_HEAD - 2)
    tipBtn:SetPoint("TOPLEFT", root, "TOPLEFT", PD.BT_COL1 + 3 * PD.BT_COLW, -2)
    tipBtn:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:ClearLines()
        GameTooltip:AddLine(L["职业版对照 / 其他功能"], 1, 0.82, 0)
        GameTooltip:AddLine(L["数值以 60 级为基准、随等级成长 —— 游戏内低等级看到的数字更小属正常缩放。"],
                            1, 1, 1, true)
        GameTooltip:Show()
    end)
    tipBtn:SetScript("OnLeave", function() GameTooltip:Hide() end)
    local rule = root:CreateTexture(nil, "ARTWORK")
    rule:SetHeight(1)
    if ns.hui and ns.hui.layer then
        local dv = ns.hui.layer.DIV
        rule:SetColorTexture(dv[1], dv[2], dv[3], dv[4] or 1)
    else
        rule:SetColorTexture(1, 0.75, 0.35, 0.35)
    end
    rule:SetPoint("TOPLEFT", root, "TOPLEFT", 0, -PD.BT_H_HEAD + 3)
    rule:SetPoint("RIGHT", root, "RIGHT", 0, 0)

    root.__rows = {}
    for k = 1, #(D.order or {}) do
        local r = CreateFrame("Button", nil, root)
        r:EnableMouse(true)
        r.icon = r:CreateTexture(nil, "ARTWORK")
        r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.icon) end
        r.icon:SetSize(15, 15)
        r.icon:SetPoint("LEFT", r, "LEFT", 0, 0)
        r.name = MakeFS(r, 14, C_TEXT, "LEFT")
        r.name:SetWordWrap(false)
        r.name:SetPoint("LEFT", r, "LEFT", 21, 0)
        r.cells = {}
        for j = 1, 3 do
            local fs = MakeFS(r, 14, C_TEXT, "LEFT")
            fs:SetWordWrap(true)
            fs:SetWidth(PD.BT_COLW - 6)
            fs:SetPoint("TOPLEFT", r, "TOPLEFT", PD.BT_COL1 + (j - 1) * PD.BT_COLW, -7)
            r.cells[j] = fs
        end
        local cx = PD.BT_COL1 + 3 * PD.BT_COLW
        r.cmp1 = MakeFS(r, 14, C_GREY, "LEFT")
        r.cmp1:SetWordWrap(true)
        r.cmp1:SetWidth(PD.BT_W_LAST - 10)
        r.cmp1:SetPoint("TOPLEFT", r, "TOPLEFT", cx, -7)
        r.cmp2 = MakeFS(r, 14, C_TEXT, "LEFT")
        r.cmp2:SetWordWrap(true)
        r.cmp2:SetWidth(PD.BT_W_LAST - 10)
        r.cmp2:SetPoint("TOPLEFT", r, "TOPLEFT", cx, -26)
        r.sep = r:CreateTexture(nil, "OVERLAY")
        r.sep:SetHeight(1)
        r.sep:SetColorTexture(1, 1, 1, 0.08)
        r.sep:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 0, 0)
        r.sep:SetPoint("RIGHT", r, "RIGHT", 0, 0)
        r.hl = r:CreateTexture(nil, "BACKGROUND")
        r.hl:SetAllPoints()
        if ns.hui and ns.hui.layer then
            local c4 = ns.hui.layer.L4
            r.hl:SetColorTexture(c4[1], c4[2], c4[3], c4[4] or 1)
        else
            r.hl:SetColorTexture(1, 1, 1, 0.04)
        end
        r.hl:Hide()
        r:SetScript("OnEnter", function(self)
            self.hl:Show()
            if self.__lines and #self.__lines > 0 then
                GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                GameTooltip:ClearLines()
                for _, ln in ipairs(self.__lines) do
                    if ln[1] and ln[1] ~= "" then
                        GameTooltip:AddLine(ln[1], ln[2] or 1, ln[3] or 1, ln[4] or 1, true)
                    end
                end
                GameTooltip:Show()
            end
        end)
        r:SetScript("OnLeave", function(self)
            self.hl:Hide()
            GameTooltip:Hide()
        end)
        root.__rows[k] = r
    end
    root:Hide()
    card:Hide()
end

local function btLines(fs, est)
    if fs.GetNumLines then
        local n = fs:GetNumLines()
        if type(n) == "number" and n > 0 then return n end
    end
    return est
end

function PD.FillBonusTable()
    local root = PD.bonusTable
    if not root then
        return
    end
    local used = 0
    local yCur = -PD.BT_H_HEAD
    local lastUsed = nil
    for _, slug in ipairs(D.order or {}) do
        local p = D.pro[slug]
        local camp = (p and p.camp) or {}
        local r = root.__rows[used + 1]
        if r and #camp > 0 then
            local t1, t2, t3, caps = {}, {}, {}, {}
            local buffTxt, cmpName = "", ""
            for _, c in ipairs(camp) do
                local lv = c[4] or 0
                local bucket, tag
                if lv == 20 then
                    bucket = t1
                elseif lv == 140 then
                    bucket = t2
                elseif lv == 300 then
                    bucket = t3
                elseif lv < 140 then
                    bucket, tag = t1, format("(%d)", lv)
                else
                    bucket, tag = t3, format("(%d)", lv)
                end
                bucket[#bucket + 1] = (c[2] or "?") .. (tag or "")
                if c[6] and c[6] ~= "" and buffTxt == "" then
                    buffTxt = c[6]
                    cmpName = c[9] or ""
                end
                if c[10] and c[10] ~= "" then caps[#caps + 1] = c[10] end
            end
            SetIcon(r.icon, p.icon)
            r.name:SetText(p.name or slug)
            r.cells[1]:SetText(table.concat(t1, "、"))
            r.cells[2]:SetText(table.concat(t2, "、"))
            r.cells[3]:SetText(table.concat(t3, "、"))
            if buffTxt ~= "" then
                r.cmp1:SetText(cmpName ~= "" and cmpName or L["营地增益"])
                r.cmp1:SetTextColor(Unpack(C_GREY))
                r.cmp2:SetText(format("|cff7fdc7f%s|r", buffTxt))
            elseif #caps > 0 then
                r.cmp1:SetText(L["功能"])
                r.cmp2:SetText(format("|cff7fdc7f%s|r", format(L["营火容量 %s"], table.concat(caps, "/"))))
            else
                r.cmp1:SetText(L["功能"])
                r.cmp2:SetText(format("|cff9a958a%s|r", camp[1][5] or ""))
            end
            local lines = {}
            for _, c in ipairs(camp) do
                lines[#lines + 1] = { c[2] or "?", 1, 0.82, 0 }
                if c[5] and c[5] ~= "" then
                    lines[#lines + 1] = { c[5], 0.88, 0.88, 0.88 }
                end
                if c[6] and c[6] ~= "" then
                    lines[#lines + 1] = { format(L["增益：%s"], c[6]), 0.5, 0.9, 0.5 }
                end
                if c[11] and #c[11] > 0 then
                    lines[#lines + 1] = { format(L["材料：%s"], PD.MatText(c[11])), 0.7, 0.7, 0.7 }
                end
                if c[12] and c[12][1] then
                    lines[#lines + 1] = { format(L["图纸：%s"], DG.ItemName(c[12][1])) }
                end
            end
            r.__lines = lines
            local plain = (r.cmp2:GetText():gsub("|cff%x%x%x%x%x%x", ""))
            plain = (plain:gsub("|r", ""))
            local need = btLines(r.cmp1, 1) + btLines(r.cmp2, #PD.Wrap(plain, 14, PD.BT_W_LAST - 10))
            for j = 1, 3 do
                local n = btLines(r.cells[j], #PD.Wrap(r.cells[j]:GetText(), 14, PD.BT_COLW - 6))
                if n > need then need = n end
            end
            local rowH = math.max(PD.BT_ROW_MIN, need * PD.BT_LINE_H + 10)
            r:SetPoint("TOPLEFT", root, "TOPLEFT", 0, yCur)
            r:SetSize(PD.BT_W, rowH)
            r.sep:Show()
            r:Show()
            yCur = yCur - rowH
            lastUsed = r
            used = used + 1
        elseif r then
            r:Hide()
        end
    end
    if lastUsed then lastUsed.sep:Hide() end
    -- 行池按 #D.order 建行，非营地条目只在被遍历到时才隐藏 —— 导航比营地行多时
    -- 尾部会留下从未被触碰的行（nil 态），这里统一收干净。
    for i = used + 1, #root.__rows do
        local r = root.__rows[i]
        if r then r:Hide() end
    end
    PD.bonusTableH = -yCur
    root:SetHeight(PD.bonusTableH)
end

function PD.placeBonusTable(y)
    PD.FillBonusTable()
    PD.bonusCard:ClearAllPoints()
    PD.bonusCard:SetPoint("TOPLEFT", PD.child, "TOPLEFT", 0, -y)
    PD.bonusCard:SetSize(PD.RIGHT_W - PD.SEC_PAD_X, (PD.bonusTableH or 0) + 2 * PD.SEC_PAD)
    PD.bonusCard:Show()
    PD.bonusTable:ClearAllPoints()
    PD.bonusTable:SetPoint("TOPLEFT", PD.bonusCard, "TOPLEFT", PD.LIST_PAD, -PD.SEC_PAD)
    PD.bonusTable:Show()
end

local TR_RANK_COLOR = { { 0.36, 0.79, 0.65 }, { 0.94, 0.62, 0.15 },
                        { 0.85, 0.35, 0.19 }, { 0.64, 0.18, 0.18 } }

function PD.BuildTrainerBoard(parent)
    local card = CreateFrame("Frame", nil, parent)
    PD.trainerCard = card
    ns.hui.BuildRoundedBG(card, 6, ns.hui.layer.L2, "both", true, 1)
    card:Hide()
    local root = CreateFrame("Frame", nil, card)
    PD.trainerBoard = root
    root:SetSize(PD.RIGHT_W - 2 * PD.LIST_PAD, 10)
    root.__chips = {}
    root.__fs = {}
end

local function TrRngLow(rng)
    return tonumber(rng:match("^(%d+)")) or 0
end

local function TrNameOf(t)
    local loc = (GetLocale() == "zhTW") and t.tw or t.zh
    return (loc and loc ~= "") and loc or t.en
end

local TR_ZONE_CACHE = {}
local function TrZoneOf(t)
    local cached = TR_ZONE_CACHE[t.map]
    if cached ~= nil then return cached or nil end
    local nm
    if C_Map and C_Map.GetMapInfo then
        local ok, info = pcall(C_Map.GetMapInfo, t.map)
        if ok and info then nm = info.name end
    end
    TR_ZONE_CACHE[t.map] = nm or false
    return nm
end

local function TrLocOf(t)
    local loc = GetLocale()
    if loc == "enUS" then return t.loc_en end
    local zh = (loc == "zhTW") and t.loc_tw or t.loc_zh
    if not zh then return t.loc_en end
    local sub = zh:match("^(.-) · ")
    if not sub then return zh end
    local zone = TrZoneOf(t)
    if not zone then return zh end
    return sub .. " · " .. zone
end

function PD.FillTrainerBoard()
    local root = PD.trainerBoard
    if not root then return 0 end
    local d = ns.ProfTrainers and ns.ProfTrainers[PD.cur]
    if not (d and d.list and #d.list > 0) then
        for _, c in ipairs(root.__chips) do c:Hide() end
        for _, f in pairs(root.__fs) do f:Hide() end
        return 0
    end
    local fac = PD.trFac or "all"
    local rngs, seen = {}, {}
    for _, t in ipairs(d.list) do
        local r = t.rng or "?"
        if not seen[r] then seen[r] = true; rngs[#rngs + 1] = r end
    end
    table.sort(rngs, function(a, b) return TrRngLow(a) < TrRngLow(b) end)
    local COLS = #rngs
    if COLS == 0 then return 0 end
    local W = PD.RIGHT_W - PD.SEC_PAD_X - 2 * PD.LIST_PAD
    local GAP = 8
    local COL_W = math.floor((W - (COLS - 1) * GAP) / COLS)
    if root.__bands then
        for i = COLS + 1, #root.__bands do root.__bands[i]:Hide() end
    end
    for _, f in pairs(root.__fs) do f:Hide() end
    for _, c in ipairs(root.__chips) do c:Hide() end
    local chipN, fsN = 0, 0
    local maxH = 0
    for ci, rng in ipairs(rngs) do
        local x0 = (ci - 1) * (COL_W + GAP)
        local rk = d.ranks and d.ranks[ci]
        local rc = TR_RANK_COLOR[ci] or TR_RANK_COLOR[#TR_RANK_COLOR]
        fsN = fsN + 1
        local h1 = root.__fs[fsN]
        if not h1 then h1 = MakeFS(root, 14, C_GOLD, "LEFT"); root.__fs[fsN] = h1 end
        h1:ClearAllPoints()
        h1:SetPoint("TOPLEFT", root, "TOPLEFT", x0, 0)
        local rkName = rk and (GetLocale() == "zhTW" and rk.tw or rk.zh) or nil
        h1:SetText((rkName and (rkName .. " ") or "") .. rng)
        h1:Show()
        fsN = fsN + 1
        local h2 = root.__fs[fsN]
        if not h2 then h2 = MakeFS(root, 13, C_GREY, "LEFT"); root.__fs[fsN] = h2 end
        h2:ClearAllPoints()
        h2:SetPoint("TOPLEFT", root, "TOPLEFT", x0, -22)
        if rk and (rk.sk or rk.lv) then
            h2:SetText(format("%s %s · %s %s", L["进阶"],
                rk.sk and tostring(rk.sk) or "-", L["角色等级"],
                rk.lv and tostring(rk.lv) or "-"))
        elseif rk and rk.cap then
            h2:SetText(format(L["上限 %d"], rk.cap))
        else
            h2:SetText("")
        end
        h2:Show()
        root.__bands = root.__bands or {}
        local band = root.__bands[ci]
        if not band then
            band = root:CreateTexture(nil, "ARTWORK")
            root.__bands[ci] = band
        end
        band:SetHeight(2)
        band:SetColorTexture(rc[1], rc[2], rc[3], 0.9)
        band:ClearAllPoints()
        band:SetPoint("TOPLEFT", root, "TOPLEFT", x0, -40)
        band:SetPoint("RIGHT", root, "TOPLEFT", x0 + COL_W, -40)
        band:Show()
        local yCur = -46
        for _, g in ipairs({ "A", "H", "B" }) do
            if fac == "all" or fac == g or g == "B" then
                local rows = {}
                for _, t in ipairs(d.list) do
                    if (t.rng or "?") == rng and (t.fac == g or (g == "B" and t.fac == "B"))
                        and (fac == "all" or fac == t.fac or t.fac == "B") then
                        rows[#rows + 1] = t
                    end
                end
                if #rows > 0 then
                    for _, t in ipairs(rows) do
                        chipN = chipN + 1
                        local c = root.__chips[chipN]
                        if not c then
                            c = CreateFrame("Button", nil, root)
                            c:EnableMouse(true)
                            root.__chips[chipN] = c
                            if ns.hui.HuiCardFX then ns.hui.HuiCardFX(c, 6, 3) end
                            c.n = MakeFS(c, 14, { 1, 1, 1 }, "LEFT")
                            c.l = MakeFS(c, 13, C_GREY, "LEFT")
                            c.xy = MakeFS(c, 13, { 0.71, 0.83, 0.96 }, "RIGHT")
                        end
                        if c.__huiCard then ns.hui.HuiCardState(c, "norm") end
                        c:SetSize(COL_W, 34)
                        c:ClearAllPoints()
                        c:SetPoint("TOPLEFT", root, "TOPLEFT", x0, yCur)
                        c.n:ClearAllPoints()
                        c.n:SetPoint("TOPLEFT", c, "TOPLEFT", 8, -4)
                        c.n:SetText(TrNameOf(t))
                        c.n:Show()
                        c.l:ClearAllPoints()
                        c.l:SetPoint("TOPLEFT", c, "TOPLEFT", 8, -20)
                        c.l:SetText(TrLocOf(t) or "")
                        c.l:Show()
                        c.xy:ClearAllPoints()
                        c.xy:SetPoint("TOPRIGHT", c, "TOPRIGHT", -8, -10)
                        c.xy:SetText(format("%g, %g", t.x, t.y))
                        c.xy:Show()
                        c.__tr = t
                        c:SetScript("OnClick", function()
                            PD.MarkVendorLoc({ nil, t.map, t.x, t.y })
                        end)
                        c:SetScript("OnEnter", function(self)
                            if self.__huiCard then ns.hui.HuiCardState(self, "hover") end
                            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                            GameTooltip:ClearLines()
                            GameTooltip:AddLine(t.en, 1, 0.82, 0)
                            local loc2 = TrLocOf(t)
                            if loc2 and loc2 ~= "" then GameTooltip:AddLine(loc2, 1, 1, 1) end
                            if t.note and t.note ~= "" then
                                GameTooltip:AddLine(t.note, 0.7, 0.7, 0.7)
                            end
                            GameTooltip:AddLine(L["点击：在地图上标记该 NPC"], 1, 0.82, 0)
                            GameTooltip:Show()
                        end)
                        c:SetScript("OnLeave", function(self)
                            if self.__huiCard then ns.hui.HuiCardState(self, "norm") end
                            GameTooltip:Hide()
                        end)
                        c:Show()
                        yCur = yCur - 38
                    end
                    yCur = yCur - 6
                end
            end
        end
        local colH = -yCur
        if colH > maxH then maxH = colH end
    end
    PD.trainerBoardH = maxH
    return maxH
end

function PD.placeTrainerBoard(y)
    local h = PD.FillTrainerBoard()
    if h <= 0 then
        if PD.trainerCard then PD.trainerCard:Hide() end
        PD.trainerBoardH = 0
        return
    end
    PD.trainerCard:ClearAllPoints()
    PD.trainerCard:SetPoint("TOPLEFT", PD.child, "TOPLEFT", 0, -y)
    PD.trainerCard:SetSize(PD.RIGHT_W - PD.SEC_PAD_X, h + 2 * PD.SEC_PAD)
    PD.trainerCard:Show()
    PD.trainerBoard:ClearAllPoints()
    PD.trainerBoard:SetPoint("TOPLEFT", PD.trainerCard, "TOPLEFT", PD.LIST_PAD, -PD.SEC_PAD)
    PD.trainerBoard:SetSize(PD.RIGHT_W - 2 * PD.LIST_PAD, h)
    PD.trainerBoard:Show()
end

local function ixCardSub(slug, p)
    if slug == "camping" then
        local n = 0
        for _, q in ipairs(D.order or {}) do
            local q2 = D.pro[q]
            if q2 and q2.camp then n = n + #q2.camp end
        end
        return format(L["物件 %d · 职业加成"], n)
    end
    if p.section == "gathering" then
        local g = GA and GA[slug]
        if slug == "skinning" then
            return format(L["档次 %d"], g and #g or 0)
        end
        return format(L["节点 %d"], g and #g or 0)
    end
    if slug == "fishing" then
        local g = GA and GA.fishing
        return format(L["区域 %d"], g and #g or 0)
    end
    return format(L["配方 %d 条"], p.recipes or 0)
end

local function ixGroupOf(p)
    if p.section == "crafting" then return 1 end
    if p.section == "gathering" then return 2 end
    if p.section == "camping" then return 4 end
    return 3
end

local IX_GROUP_LABELS

function PD.SetCardHover(c, on)
    on = on and true or false
    c.__hlOn = on
    -- HUI 主题：底色 L2 常露，悬停叠 L4 胶囊（卡中卡 +2 档惯例）；非 HUI 走旧 overlay
    if c.__hov then
        for _, t in ipairs(c.__hov) do t:SetShown(on) end
    elseif on then
        c:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG_HOVER)
        -- 已学卡（2026-10-10）：悬停/复原都保绿描边，别把绿冲回灰（非 HUI 回落路径）
        if c.__ixLearned then
            local r, g, b = PD.NavAccent()
            c:SetBackdropBorderColor(r, g, b, DG.LOOT_CARD_EDGE_HOVER)
        else
            c:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE_HOVER)
        end
    else
        c:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)
        if c.__ixLearned then
            local r, g, b = PD.NavAccent()
            c:SetBackdropBorderColor(r, g, b, DG.LOOT_CARD_EDGE)
        else
            c:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)
        end
    end
end

function PD.BuildIndexGrid(parent)
    IX_GROUP_LABELS = {
        L["制造专业 —— 每个角色选两个主要专业"],
        L["采集专业 —— 为制造专业提供材料"],
        L["次要专业 —— 每个角色三个都能学"],
        L["营地系统"],
    }
    local w = PD.RIGHT_W - 2 * PD.LIST_PAD
    local root = CreateFrame("Frame", nil, parent)
    root:SetSize(w, 10)
    PD.ixRoot = root

    PD.ixHeads = {}
    for gi = 1, 4 do
        local fs = MakeFS(root, 12, C_GOLD, "LEFT")
        fs:SetText(IX_GROUP_LABELS[gi])
        PD.ixHeads[gi] = fs
    end

    PD.ixCards = {}
    local byGroup = { {}, {}, {}, {} }
    for _, slug in ipairs(D.order or {}) do
        local p = D.pro[slug]
        if p then
            local gi = ixGroupOf(p)
            local c = CreateFrame("Button", nil, root, "BackdropTemplate")
            -- 总览索引卡（2026-10-11 色阶规整）：容器卡（L1）内的内卡提亮到 L2 实色，
            -- 悬停叠 L4 胶囊；非 HUI 回落旧直角底 + overlay 悬停。
            if ns.hui and ns.hui.layer and ns.hui.BuildRoundedBG and ns.hui.BuildCapsule then
                -- 2026-10-10 用户：已学专业卡要绿描边 —— border 片在此留引用，
                --   PaintIndexCards 直接 SetVertexColor；本路径没有 border 重画钩子，绿一次管全程。
                local _, bord = ns.hui.BuildRoundedBG(c, 6, ns.hui.layer.L2, "both", true, 1)
                c.__ixBorder = bord
                c.__hov = ns.hui.BuildCapsule(c, 6, ns.hui.layer.L4, 1, 2)
                for _, ht in ipairs(c.__hov) do ht:Hide() end
            else
                c:SetBackdrop({
                    bgFile = "Interface\\Buttons\\WHITE8x8",
                    edgeFile = "Interface\\Buttons\\WHITE8x8",
                    edgeSize = 1,
                })
            end
            PD.SetCardHover(c, false)
            c:EnableMouse(true)            c.icon = c:CreateTexture(nil, "ARTWORK")
            c.icon:SetSize(PD.IX_ICON, PD.IX_ICON)
            c.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
            if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(c.icon) end
            c.icon:SetPoint("LEFT", c, "LEFT", 7, 0)
            SetIcon(c.icon, p.icon)
            -- 2026-10-10 用户：名称 16 / 副行 14（旧 12/10）；右上角留等级字串（已学才显示）
            c.name = MakeFS(c, 16, C_TEXT, "LEFT")
            c.name:SetWordWrap(false)
            c.name:SetPoint("TOPLEFT", c, "TOPLEFT", PD.IX_ICON + 13, -4)
            c.name:SetText(p.name or slug)
            c.sub = MakeFS(c, 14, C_GREY, "LEFT")
            c.sub:SetWordWrap(false)
            c.sub:SetPoint("BOTTOMLEFT", c, "BOTTOMLEFT", PD.IX_ICON + 13, 3)
            c.sub:SetText(ixCardSub(slug, p))
            c.__slug = slug
            c.lv = MakeFS(c, 12, C_TEXT, "RIGHT")
            c.lv:SetPoint("TOPRIGHT", c, "TOPRIGHT", -7, -5)
            c.lv:Hide()
            c:SetScript("OnEnter", function(self) PD.SetCardHover(self, true) end)
            c:SetScript("OnLeave", function(self) PD.SetCardHover(self, false) end)
            c:SetScript("OnClick", function(self)
                ns.PlaySound(1)
                if slug == "camping" then
                    PD.Show("camping")
                    PD.campView = "bonus"
                else
                    PD.Show(slug)
                end
            end)
            c:SetScript("OnMouseWheel", function(_, delta)
                DG.WheelScroll(PD.scroll, PD.child, delta)
            end)
            byGroup[gi][#byGroup[gi] + 1] = c
            PD.ixCards[#PD.ixCards + 1] = c
        end
    end

    PD.ixNote = MakeFS(root, 10, C_GREY, "CENTER")
    PD.ixNote:SetText(L["营地档位对照表 →「营地系统」"])

    local y = 0
    for gi = 1, 4 do
        local head = PD.ixHeads[gi]
        head:ClearAllPoints()
        head:SetPoint("TOPLEFT", root, "TOPLEFT", 0, -y)
        y = y + PD.IX_HEAD_H
        local cards = byGroup[gi]
        local rows = math.ceil(#cards / PD.IX_COLS)
        for k, c in ipairs(cards) do
            local row = math.floor((k - 1) / PD.IX_COLS)
            local col = (k - 1) % PD.IX_COLS
            c:ClearAllPoints()
            c:SetPoint("TOPLEFT", root, "TOPLEFT",
                       col * (PD.IX_COLW + PD.IX_GAP), -(y + row * (PD.IX_CARD_H + PD.IX_ROWW_GAP)))
            c:SetSize(PD.IX_COLW, PD.IX_CARD_H)
        end
        if gi == 4 then
            PD.ixNote:ClearAllPoints()
            PD.ixNote:SetPoint("LEFT", root, "LEFT",
                               PD.IX_COLW + PD.IX_GAP + 8, -(y + math.floor(PD.IX_CARD_H / 2)))
        end
        y = y + rows * PD.IX_CARD_H + (rows - 1) * PD.IX_ROWW_GAP + PD.IX_GROUP_GAP
    end
    PD.ixGridH = y
    root:SetHeight(y)
    root:Hide()
end

function PD.placeIndexGrid(y)
    PD.ixRoot:ClearAllPoints()
    PD.ixRoot:SetPoint("TOPLEFT", PD.child, "TOPLEFT", PD.LIST_PAD, -y)
    PD.ixRoot:SetHeight(PD.ixGridH or 10)
    PD.ixRoot:Show()
    PD.PaintIndexCards()
end

-- 2026-10-10 用户：已学专业在总览卡上「绿名 + 右上角等级 + 绿描边」——与左侧页面按钮
--   同数据源（PD.ProfLearned）、同绿色（NavAccent）。每次总览落位重画，签名去重：
--   等级没变就不写任何 setter。恢复原描边 = 白 + α0.10（= Hui C_CARD_BORDER 真值）。
local IX_EDGE_NORM_A = 0.10
function PD.PaintIndexCards()
    local learned = PD.ProfLearned()
    for _, c in ipairs(PD.ixCards or {}) do
        local lv = c.__slug and learned[c.__slug] or nil
        local key = lv and (lv.cur .. "/" .. lv.max) or ""
        if c.__ixKey ~= key then
            c.__ixKey = key
            c.__ixLearned = lv and true or false
            local r, g, b = PD.NavAccent()
            if lv then
                c.name:SetTextColor(r, g, b, 1)
                c.lv:SetText(format("%d/%d", lv.cur, lv.max))
                c.lv:SetTextColor(r, g, b, 1)
                c.lv:Show()
            else
                c.name:SetTextColor(Unpack(C_TEXT))
                c.lv:Hide()
            end
            if c.__ixBorder then
                for _, t in ipairs(c.__ixBorder) do
                    if lv then
                        t:SetVertexColor(r, g, b)
                        t:SetAlpha(1)
                    else
                        t:SetVertexColor(1, 1, 1)
                        t:SetAlpha(IX_EDGE_NORM_A)
                    end
                end
            elseif c.SetBackdropBorderColor then
                if lv then
                    c:SetBackdropBorderColor(r, g, b, 1)
                else
                    c:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)
                end
            end
        end
    end
end

function PD.MakeCard(f)
    local c = CreateFrame("Frame", nil, f, "BackdropTemplate")
    if ns.hui and ns.hui.layer and ns.hui.BuildRoundedBG then
        ns.hui.BuildRoundedBG(c, 6, ns.hui.layer.L1, "both", true, 1)
    else
        c:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        c:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)
        c:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)
    end
    return c
end

function PD.Build(page)
    if PD.built or PD.building then return end
    PD.building = true
    PD.rows, PD.toolBtns, PD.setToggles = {}, {}, {}
    PD.perkOpen, PD.__pendRows = {}, {}
    ns.PhasedStart(26, coroutine.create(function()
    PD.page = page
    if not PD.trFac then
        if UnitFactionGroup and UnitFactionGroup("player") == "Horde" then
            PD.trFac = "H"
        else
            PD.trFac = "A"
        end
    end
    -- 商人选择弹窗：换页 / 收窗必须收起（锚着热区，内容一变就飘）
    page:HookScript("OnHide", function() PD.HideVendorPick() end)
    PD.navKey = {}
    coroutine.yield()

    PD.navCard = PD.MakeCard(page)
    PD.navCard:SetPoint("TOPLEFT", page, "TOPLEFT", PD.CARD_INSET, -PD.CARD_TOP)
    PD.navCard:SetPoint("BOTTOMRIGHT", page, "BOTTOMLEFT",
                        PD.CARD_NAV_R, PD.CARD_INSET)
    PD.listCard = PD.MakeCard(page)
    -- 分组标签宿主：标签是 page 的 FontString，永远画在子帧 navCard 之下
    -- （被实底卡整片盖住 = 分组名称看不见的根因）；挂到抬高的空帧上才可见。
    PD.navLabelHost = CreateFrame("Frame", nil, page)
    do
        local ok, lv = pcall(PD.navCard.GetFrameLevel, PD.navCard)
        PD.navLabelHost:SetFrameLevel((ok and type(lv) == "number" and lv or 0) + 2)
    end
    coroutine.yield()

    PD.nav = {}
    local navY = 0
    local function navEntry(key, text, icon)
        local bt = NewButton(page, text, PD.NAV_W, PD.NAV_ITEM_H, PD.NAV_FS)
        bt:SetPoint("TOPLEFT", page, "TOPLEFT", PD.NAV_X, -(PD.NAV_TOP + navY))
        local fs = bt:GetFontString()
        fs:ClearAllPoints()
        fs:SetPoint("LEFT", bt, "LEFT", 5 + PD.NAV_ICON + 5, 0)
        fs:SetJustifyH("LEFT")
        MakeOutline(bt, 1, 0.82, 0)
        SetOutline(bt, false, 1, 0.82, 0)
        bt.__huiKeepTextColor = true
        bt.__name = text
        bt.__icon = bt:CreateTexture(nil, "ARTWORK")
        bt.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(bt.__icon) end
        bt.__icon:SetSize(PD.NAV_ICON, PD.NAV_ICON)
        bt.__icon:SetPoint("LEFT", bt, "LEFT", 5, 0)
        SetIcon(bt.__icon, icon)
        bt.__lv = MakeFS(bt, PD.NAV_LV_FS, C_GREY, "RIGHT")
        bt.__lv:SetPoint("RIGHT", bt, "RIGHT", -6, 0)
        bt.__lv:Hide()
        bt:SetScript("OnClick", function() PD.Show(key) end)
        PD.nav[#PD.nav + 1] = bt
        PD.navKey[key] = bt
        navY = navY + PD.NAV_ITEM_H + PD.NAV_GAP
        return bt
    end

    -- 2026-10-10 用户：「全部专业」按钮退役（下方按钮自动上移补位）；
    --   __index 宫格页代码路径保留休眠（wantIndexGrid 恒 false），cur 不再落 "__index"。
    PD.navOrder = {}
    for _, g in ipairs({ { kind = "primary", label = L["主专业"] },
                         { kind = "secondary", label = L["次专业"] },
                         { kind = "system", label = L["营地系统"] },
                         { kind = "crates", label = L["声望"] } }) do
        local list = {}
        for _, slug in ipairs(D.order or {}) do
            local p = D.pro[slug]
            if p and p.kind == g.kind then list[#list + 1] = slug end
        end
        if #list > 0 then
            navY = navY + 4
            local lab = MakeFS(PD.navLabelHost, 11, C_GREY, "LEFT")
            lab:SetPoint("TOPLEFT", page, "TOPLEFT", PD.NAV_X + 5,
                         -(PD.NAV_TOP + navY + 6))
            lab:SetText(g.label)
            navY = navY + PD.NAV_GROUP_H
            for _, slug in ipairs(list) do
                local p = D.pro[slug]
                navEntry(slug, p.name or slug, p.icon)
                PD.navOrder[#PD.navOrder + 1] = slug
            end
        end
    end

    coroutine.yield()
    ns.hui.OnThemeChange(function() if PD.built then pcall(PD.PickNav) end end)

    PD.subBtns = {}
    for _, def in ipairs(DG.PROF_SUBTABS) do
        local bt = NewButton(page, def.text, PD.SUB_W, PD.SUB_H, 13)
        MakeOutline(bt, 1, 0.82, 0)
        bt.__huiKeepTextColor = true
        bt:Hide()
        bt:SetScript("OnClick", function() PD.SetTab(def.key) end)
        PD.subBtns[def.key] = bt
    end
    coroutine.yield()

    PD.trFacBtns = {}
    for i = 1, 2 do
        local k = (i == 1) and "A" or "H"
        local bt = NewButton(page, k == "A" and L["联盟"] or L["部落"], 64, PD.SUB_H, 13)
        MakeOutline(bt, 1, 0.82, 0)
        bt.__huiKeepTextColor = true
        local bfs = bt:GetFontString()
        if bfs then
            bfs:ClearAllPoints()
            bfs:SetPoint("LEFT", bt, "LEFT", 26, 0)
            bfs:SetJustifyH("LEFT")
            if k == "A" then
                bfs:SetTextColor(0.40, 0.62, 1.00, 1)
            else
                bfs:SetTextColor(1.00, 0.36, 0.26, 1)
            end
        end
        local bic = bt:CreateTexture(nil, "OVERLAY")
        bic:SetTexture(k == "A" and PD.FAC_ICON.a or PD.FAC_ICON.h)
        bic:SetSize(16, 16)
        bic:SetPoint("LEFT", bt, "LEFT", 7, 0)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(bic) end
        bt:Hide()
        bt:SetScript("OnClick", function()
            if PD.trFac ~= k then
                PD.trFac = k
                PD.RequestRender()
                ns.PlaySound(1)
            end
        end)
        PD.trFacBtns[k] = bt
    end
    coroutine.yield()

    local gear = NewButton(page, "", PD.SUB_H, PD.SUB_H, 13)
    MakeOutline(gear, 1, 0.82, 0)
    gear.__huiKeepTextColor = true
    gear.__icon = gear:CreateTexture(nil, "ARTWORK")
    gear.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(gear.__icon) end
    gear.__icon:SetSize(14, 14)
    gear.__icon:SetPoint("CENTER", gear, "CENTER", 0, 0)
    SetIcon(gear.__icon, ns.SET_ICON)
    -- 右缘口径（2026-10-10 用户截图实锤）：行栅格右缘 = 卡右缘 - LIST_PAD；
    --   帧级右锚（齿轮/搜索框/信息卡行/HUD按钮）必须内缩 LIST_PAD 与行栅格一线，
    --   直接用 RIGHT_X + RIGHT_W 会正好压在 listCard 描边上（UI_RULES §3.1）。
    gear:SetPoint("TOPRIGHT", page, "TOPLEFT",
                  PD.RIGHT_X + PD.RIGHT_W - PD.LIST_PAD, -PD.SUB_Y)
    gear:SetScript("OnClick", function()
        PD.setOpen = not PD.setOpen
        PD.RequestRender()
        ns.PlaySound(1)
    end)
    PD.setGear = gear
    coroutine.yield()

    PD.setToggles = {}
    PD.toolBtns = {}

    for i = 1, PD.TOOL_MAX do
        local bt = NewButton(page, "", PD.TOOL_W, PD.TOOL_H, 12)
        MakeOutline(bt, 1, 0.82, 0)
        bt.__huiKeepTextColor = true
        bt:Hide()
        bt:SetScript("OnClick", function(self)
            if self.__key and PD.onTool then PD.onTool(self.__key) end
            ns.PlaySound(1)
        end)
        PD.toolBtns[i] = bt
    end
    coroutine.yield()

    -- 升级页信息卡（2026-10-10 B1）：模式 / 总花费 / 目标等级 / 价格快照。
    -- 帧数纪律：Build 一次建好；显隐与内容由 PD.PaintLvTiles 每次渲染刷新。
    -- 目标等级直接在卡内编辑（EditBox 常驻 target 卡，编辑态盖住数值文本）。
    PD.LV_TILE_H, PD.LV_TILE_GAP = 38, 8

    -- HUD 与导入入口由 PickTabs 刷新文本/显隐，再由 PaintTool 统一排版。
    -- 它们实际占用的宽度必须与左侧动作共享，按钮增多时一起撑高工具区。
    local hudBtn = NewButton(page, "", 120, PD.SUB_H, 13)
    MakeOutline(hudBtn, 1, 0.82, 0)
    hudBtn.__huiKeepTextColor = true
    hudBtn:Hide()
    PD.hudBtn = hudBtn
    coroutine.yield()

    -- 一键导入通常在 HUD 左侧；窄宽度或长文案时允许换行。
    local impBtn = NewButton(page, L["一键导入购物清单"], 110, PD.SUB_H, 13)
    MakeOutline(impBtn, 1, 0.82, 0)
    impBtn.__huiKeepTextColor = true
    impBtn:Hide()
    PD.impBtn = impBtn
    coroutine.yield()
    PD.lvTiles = {}
    for _, td in ipairs({
        { key = "mode",   w = 200 },
        { key = "scheme", w = 150 },
        { key = "cost",   w = 250 },
        { key = "target", w = 150 },
        { key = "snap",   w = 0 },
    }) do
        local tf = CreateFrame("Button", nil, page, "BackdropTemplate")
        tf:SetSize(td.w, PD.LV_TILE_H)
        -- 倒圆角（2026-10-10）：走 HUI 圆角原语；border 片段存帧上供 PaintLvTiles 动态改色
        -- 倒圆角（2026-10-10）：走 HUI 圆角原语；border 片段存帧上供 PaintLvTiles 动态改色。
        -- 底色走主题层级 L2（2026-10-10 用户：原来是硬编码黑 0.35，不入主题；L2=页内卡片
        -- 标准档，随主题换色）。传活表引用，repaint 闭包在换肤时重读最新值。
        local _, bord = ns.hui.BuildRoundedBG(tf, 6, ns.hui.layer.L2, "both", true, 1)
        tf.__border = bord or {}
        if ns.hui and ns.hui.BuildCapsule then
            -- 悬停胶囊 L4 = L2 内卡 +2 档（UI_RULES 卡中卡阶梯）；进出由 TipOn 切显隐
            tf.__hov = ns.hui.BuildCapsule(tf, 8, ns.hui.layer.L4, 1, 2) or {}
            for _, t in ipairs(tf.__hov) do t:Hide() end
        end
        tf:Hide()
        tf.label = MakeFS(tf, 11, C_GREY, "LEFT")
        tf.label:SetPoint("TOPLEFT", tf, "TOPLEFT", 10, -6)
        tf.val = MakeFS(tf, 14, C_WHITE, "LEFT")
        tf.val:SetPoint("BOTTOMLEFT", tf, "BOTTOMLEFT", 10, 6)
        tf:EnableMouseWheel(true)
        tf:SetScript("OnMouseWheel", function(self, delta)
            DG.WheelScroll(PD.scroll, PD.child, delta)
        end)
        PD.lvTiles[td.key] = tf
    end
    coroutine.yield()
    -- 圆角边框动态改色（模式卡琥珀提醒 / 输入框金色描边共用）
    function PD.PaintTileBorder(f, c)
        for _, tex in ipairs(f.__border or {}) do
            if tex.__huiBorderStrip then
                tex:SetColorTexture(c[1], c[2], c[3], 1)
                tex:SetAlpha(c[4] or 1)
            else
                tex:SetVertexColor(c[1], c[2], c[3])
                tex:SetAlpha(c[4] or 1)
            end
        end
    end
    PD.lvTiles.mode:SetScript("OnClick", function()
        local on = not PD.Setting("autoRoute")
        ProfDB().autoRoute = on
        if not on and RA then RA.Invalidate() end
        PD.RequestRender()
        ns.PlaySound(1)
    end)
    -- 路线方案卡：点击循环选择方案，已有路线由「重新计算」应用。
    PD.lvTiles.scheme:SetScript("OnClick", PD.CycleRouteScheme)
    do
        local tf = PD.lvTiles.target
        local eb = CreateFrame("EditBox", nil, tf, "BackdropTemplate")
        local _, ebBord = ns.hui.BuildRoundedBG(eb, 6, ns.hui.layer.L3, "both", true, 1)
        eb.__border = ebBord or {}
        PD.PaintTileBorder(eb, { 1, 0.82, 0, 0.9 })
        eb:SetSize(64, 20)
        eb:SetPoint("BOTTOMLEFT", tf, "BOTTOMLEFT", 9, 5)
        eb:SetFont(ns.FONT, 13, ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE")
        eb:SetTextColor(1, 0.82, 0)
        eb:SetJustifyH("CENTER")
        eb:SetAutoFocus(false)
        eb:SetTextInsets(4, 4, 0, 0)
        eb:SetNumeric(true)
        eb:Hide()
        tf.eb = eb
        local function CloseTarget()
            PD.tgtEditing = nil
            eb:Hide()
            tf.val:Show()
        end
        local function ApplyTarget()
            if not PD.cur or not PD.tgtEditing then CloseTarget() return end
            local v = tonumber(eb:GetText()) or 300
            v = math.max(1, math.min(300, math.floor(v)))
            local db = ProfDB()
            db.lvTarget = db.lvTarget or {}
            local old = tonumber(db.lvTarget[PD.cur]) or 300
            CloseTarget()
            if old == v then return end
            -- 显式 if 而非 and/or 链（中段为 nil 会被 or 吃掉，300 就永远清不掉）
            if v >= 300 then db.lvTarget[PD.cur] = nil else db.lvTarget[PD.cur] = v end
            if RA then RA.Invalidate() end
            -- 目标等级改了 → 固定路线段落表随之变短/变长，HUD 要立刻按新目标重推指针
            -- （2026-10-11 用户：「hud 固定路线显示也需要 根据我设置等级 显示」）。
            -- HUD 的 1 秒轮询本可兜住，这里补一条即时推送，改完立刻对齐。
            local _pf = ns.ProfFollow
            if _pf and _pf.RefreshRoute then pcall(_pf.RefreshRoute, PD.cur) end
            PD.RequestRender()
        end
        local cancelled = nil
        eb:SetScript("OnEnterPressed", function(self) self:ClearFocus() end)
        eb:SetScript("OnEscapePressed", function(self)
            cancelled = true
            CloseTarget()
            self:ClearFocus()
        end)
        eb:SetScript("OnEditFocusLost", function()
            if cancelled then cancelled = nil return end
            ApplyTarget()
        end)
        tf:SetScript("OnClick", function()
            if PD.tgtEditing then return end
            local v = PD.LvTarget()
            eb:SetText(v >= 300 and "" or tostring(v))
            PD.tgtEditing = true
            tf.val:Hide()
            eb:Show()
            eb:SetFocus()
            ns.PlaySound(1)
        end)
    end
    coroutine.yield()

    -- 配方搜索框（2026-10-09）：配方页工具行右端，输入即按名称 / 材料过滤
    local sb = CreateFrame("Frame", nil, page)
    sb:SetSize(PD.SEARCH_W, PD.TOOL_H)
    sb:Hide()
    sb.label = MakeFS(sb, 12, C_GREY, "LEFT")
    sb.label:SetText(L["搜索"])
    sb.label:SetPoint("LEFT", sb, "LEFT", 0, 0)
    local seb = CreateFrame("EditBox", nil, sb, "BackdropTemplate")
    -- 底色 L2（2026-10-10 UI_RULES 卡中卡提亮）：搜索框坐在 L1 大卡（listCard）里，
    --   内卡必须比外层亮一档；白 10% 细边照卡片细边标准。
    local _, sebBord = ns.hui.BuildRoundedBG(seb, 6, ns.hui.layer.L2, "both", true, 1)
    seb.__border = sebBord or {}
    PD.PaintTileBorder(seb, { 1, 1, 1, 0.10 })
    seb:SetSize(PD.SEARCH_EB_W, PD.TOOL_H)
    -- 搜索框右对齐容器右缘（与内容栅格右缘一线），标签与输入框间距 8
    seb:SetPoint("RIGHT", sb, "RIGHT", 0, 0)
    sb.label:ClearAllPoints()
    sb.label:SetPoint("RIGHT", seb, "LEFT", -8, 0)
    seb:SetFont(ns.FONT, 12, ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE")
    seb:SetTextColor(1, 1, 1, 1)
    seb:SetJustifyH("LEFT")
    seb:SetAutoFocus(false)
    seb:SetTextInsets(5, 5, 0, 0)
    seb:SetMaxLetters(40)
    seb.ph = MakeFS(seb, 11, C_GREY, "LEFT")
    seb.ph:SetText(L["配方名 / 材料名"])
    seb.ph:SetPoint("LEFT", seb, "LEFT", 6, 0)
    seb.ph:Hide()
    local function SyncPh()
        local t = seb:GetText()
        if (t == nil or t == "") and not seb:HasFocus() then
            seb.ph:Show()
        else
            seb.ph:Hide()
        end
    end
    seb:SetScript("OnTextChanged", function(self)
        SyncPh()
        local t = string.lower(tostring(self:GetText() or ""))
        if t == (PD.searchQ or "") then return end
        PD.searchQ = t
        PD.RequestRender()
    end)
    seb:SetScript("OnEscapePressed", function(self)
        if self:GetText() ~= "" then self:SetText("") end
        self:ClearFocus()
        SyncPh()
    end)
    seb:SetScript("OnEnterPressed", function(self)
        self:ClearFocus()
        SyncPh()
        ns.PlaySound(1)
    end)
    seb:SetScript("OnEditFocusGained", function() seb.ph:Hide() end)
    seb:SetScript("OnEditFocusLost", function() SyncPh() end)
    sb.eb = seb
    PD.searchBox = sb
    coroutine.yield()

    local divider = page:CreateTexture(nil, "BORDER")
    divider:SetColorTexture(1, 1, 1, 0.12)
    divider:SetWidth(1)
    divider:Hide()
    PD.divider = divider
    coroutine.yield()

    local scroll = CreateFrame("ScrollFrame", nil, page)
    scroll:EnableMouseWheel(true)
    scroll:SetScript("OnMouseWheel", function(self, delta)
        DG.WheelScroll(PD.scroll, PD.child, delta)
    end)
    local child = CreateFrame("Frame", nil, scroll)
    child:SetSize(PD.RIGHT_W, 10)
    scroll:SetScrollChild(child)
    PD.scroll, PD.child = scroll, child
    coroutine.yield()

    -- ── 滚动条（2026-10-11 用户：配方页右缘加滚动条，样式对齐藏品页那套）──
    --   09:23 澄清：L4 只给滑块（用户「我只是让你改滑块的颜色」），轨道回退藏品同款 L2；
    --   宽度维持 1.5 倍（轨道 9 / 滑块 6），右缘锚不动，向左加宽整条覆盖在列上方。
    --   轨道 = L2 圆角胶囊 / 滑块 = L4 胶囊悬停提亮 L5，可拖拽；
    --   内容不足一屏或非配方页（设置展开也算）整条隐藏。
    local track = CreateFrame("Frame", nil, page, "BackdropTemplate")
    if ns.hui and ns.hui.BuildCapsule then
        ns.hui.BuildCapsule(track, 3, ns.hui.layer.L2)
    else
        track:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        track:SetBackdropColor(0, 0, 0, 0.25)
        track:SetBackdropBorderColor(1, 1, 1, 0.08)
    end
    track:SetWidth(9)
    track:SetPoint("TOPRIGHT", scroll, "TOPRIGHT", -1, -2)
    track:SetPoint("BOTTOMRIGHT", scroll, "BOTTOMRIGHT", -1, 2)
    track:SetFrameLevel((scroll:GetFrameLevel() or 0) + 10)
    track:Hide()
    local thumb = CreateFrame("Button", nil, track)
    thumb:SetWidth(6)
    thumb:EnableMouse(true)
    local tp = nil
    local tx = nil
    if ns.hui and ns.hui.BuildCapsule then
        tp = ns.hui.BuildCapsule(thumb, 2, ns.hui.layer.L4)
    else
        tx = thumb:CreateTexture(nil, "OVERLAY")
        tx:SetAllPoints()
        tx:SetColorTexture(1, 1, 1, 0.30)
    end
    thumb:SetScript("OnEnter", function()
        if tp then
            local L5 = ns.hui.layer.L5
            for _, t in ipairs(tp) do t:SetVertexColor(L5[1], L5[2], L5[3]) end
        elseif tx then
            tx:SetColorTexture(1, 1, 1, 0.45)
        end
    end)
    thumb:SetScript("OnLeave", function()
        if tp then
            local L4 = ns.hui.layer.L4
            for _, t in ipairs(tp) do t:SetVertexColor(L4[1], L4[2], L4[3]) end
        elseif tx then
            tx:SetColorTexture(1, 1, 1, 0.30)
        end
    end)
    thumb:SetPoint("TOP", track, "TOP", 0, -1)
    coroutine.yield()
    function PD.UpdateVScroll()
        local sc, ch = PD.scroll, PD.child
        if not (sc and ch) then return end
        if PD.setOpen then track:Hide() return end
        if PD.lvSplit then
            if not PD.divider then track:Hide() return end
            track:ClearAllPoints()
            track:SetPoint("TOPLEFT", PD.divider, "TOPLEFT", -4, -2)
            track:SetPoint("BOTTOMLEFT", PD.divider, "BOTTOMLEFT", -4, 2)
        elseif PD.tab == "recipe" then
            track:ClearAllPoints()
            track:SetPoint("TOPRIGHT", sc, "TOPRIGHT", -1, -2)
            track:SetPoint("BOTTOMRIGHT", sc, "BOTTOMRIGHT", -1, 2)
        else
            track:Hide()
            return
        end
        local viewH = sc:GetHeight()
        local contentH = ch:GetHeight()
        if contentH <= viewH + 2 or viewH <= 0 then track:Hide() return end
        track:Show()
        local trackH = track:GetHeight() - 2
        local maxScroll = contentH - viewH
        -- ★ GetVerticalScroll 桩回 table（视口剔除契约：非数字 = 离线全量路径），
        --   真机回数字；算术前必须过类型闸。
        local vpos = sc.GetVerticalScroll and sc:GetVerticalScroll() or 0
        if type(vpos) ~= "number" then vpos = 0 end
        local frac = math.min(1, math.max(0, vpos / maxScroll))
        local th = math.max(24, trackH * viewH / contentH)
        thumb:SetHeight(th)
        thumb:ClearAllPoints()
        thumb:SetPoint("TOP", track, "TOP", 0, -1 - frac * (trackH - th))
    end
    scroll:SetScript("OnVerticalScroll", function()
        PD.UpdateVScroll()
        if PD.CullRows then PD.CullRows() end
    end)
    thumb:SetScript("OnMouseDown", function(self, btn)
        if btn ~= "LeftButton" then return end
        local scale = UIParent and UIParent:GetEffectiveScale() or 1
        local cy0 = select(2, GetCursorPosition()) / scale
        local sc0 = PD.scroll:GetVerticalScroll()
        self:SetScript("OnUpdate", function(self)
            local cy = select(2, GetCursorPosition()) / scale
            local trackH = track:GetHeight() - 2
            local span = trackH - thumb:GetHeight()
            if span <= 0 then return end
            local maxScroll = PD.child:GetHeight() - PD.scroll:GetHeight()
            PD.scroll:SetVerticalScroll(math.min(maxScroll, math.max(0, sc0 + (cy0 - cy) / span * maxScroll)))
        end)
    end)
    thumb:SetScript("OnMouseUp", function(self)
        self:SetScript("OnUpdate", nil)
    end)
    thumb:SetScript("OnHide", function(self)
        self:SetScript("OnUpdate", nil)
    end)
    coroutine.yield()

    local hlAcc = 0
    child:SetScript("OnUpdate", function(_, el)
        hlAcc = hlAcc + el
        if hlAcc < 0.1 then return end
        hlAcc = 0
        PD.SyncHover()
    end)
    coroutine.yield()

    PD.BuildBonusTable(child)
    coroutine.yield()
    PD.BuildTrainerBoard(child)
    coroutine.yield()

    for i = 1, PD.SETTING_TOG_MAX do
        local tg = CreateFrame("CheckButton", nil, child)
        tg:SetSize(36, 20)
        tg:EnableMouse(true)
        ns.hui.ReskinToggle(tg)
        tg:SetScript("OnClick", function(self)
            if self.__key then
                ProfDB()[self.__key] = not PD.Setting(self.__key)
                self:SetChecked(PD.Setting(self.__key))
                if string.sub(self.__key, 1, 4) == "auto" and RA then
                    RA.Invalidate()   -- 过滤细则变了，自动路线缓存全部失效
                end
            end
            PD.RequestRender()
            ns.PlaySound(1)
        end)
        PD.setToggles[i] = tg
    end
    coroutine.yield()

    -- 设置行「?」帮助图标池：详细说明收到悬停提示框里，不再直铺在行下
    PD.setHelps = {}
    for i = 1, PD.SETTING_TOG_MAX do
        local hp = CreateFrame("Button", nil, child)
        hp:SetSize(16, 16)
        hp.text = MakeFS(hp, 12, C_GOLD, "CENTER")
        hp.text:SetAllPoints()
        hp.text:SetText("?")
        hp:SetScript("OnEnter", function(self)
            local ln = self.__tip
            if not ln then return end
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:ClearLines()
            for _, t in ipairs(ln) do
                if t[1] and t[1] ~= "" then
                    GameTooltip:AddLine(t[1], t[2] or 1, t[3] or 1, t[4] or 1, true)
                end
            end
            GameTooltip:Show()
        end)
        hp:SetScript("OnLeave", function() GameTooltip:Hide() end)
        hp:EnableMouseWheel(true)
        hp:SetScript("OnMouseWheel", function(_, delta)
            DG.WheelScroll(PD.scroll, PD.child, delta)
        end)
        hp:Hide()
        PD.setHelps[i] = hp
    end
    coroutine.yield()

    PD.bonusTitleNote = MakeFS(child, 14, C_GREY, "RIGHT")
    PD.bonusTitleNote:SetText(
        L["营地增益不与同类职业增益叠加、效果略低于职业版（如王者祝福 10% → 营地 8%）。"])
    PD.bonusTitleNote:Hide()
    coroutine.yield()

    PD.BuildIndexGrid(child)
    coroutine.yield()

    PD.secCards = {}
    for i = 1, PD.SEC_CARD_MAX do
        local c = CreateFrame("Frame", nil, child)
        -- 2026-10-11 色阶规整：分区卡是容器卡（L1）里的内卡，实色提亮到 L2（原白 3% overlay 与外层同级）
        ns.hui.BuildRoundedBG(c, 6, ns.hui.layer.L2, "both", true, 1)
        c:Hide()
        PD.secCards[i] = c
    end
    coroutine.yield()
    -- 金币卡（2026-10-09 三轮）：购物清单右栏「总共需要」组用金色底 highlight
    PD.secGoldCards = {}
    for i = 1, PD.SEC_CARD_MAX do
        local c = CreateFrame("Frame", nil, child)
        ns.hui.BuildRoundedBG(c, 6, ns.hui.layer.L3, "both", true, 1)
        c:Hide()
        PD.secGoldCards[i] = c
    end
    coroutine.yield()

    PD.ver = MakeFS(page, 11, C_GREY, "LEFT")
    PD.ver:SetPoint("BOTTOMLEFT", page, "BOTTOMLEFT", 10, 4)
    PD.built = true
    PD.building = false
    if PD.wantOpen then
        PD.wantOpen = nil
        PD.EnsureCur()
        PD.RequestRender()
    end
    PD.ver:SetText(format(L["专业数据 build %s · %s"],
                          tostring(D.build or "?"), tostring(D.updated or "?")))
    end))
end

local NAV_SKILL_SLUG = {
    [171] = "alchemy",     [164] = "blacksmithing", [333] = "enchanting",
    [202] = "engineering", [165] = "leatherworking", [197] = "tailoring",
    [186] = "mining",      [182] = "herbalism",     [393] = "skinning",
    [185] = "cooking",     [356] = "fishing",       [129] = "first-aid",
}

function PD.ProfLearned()
    local out = {}
    if type(GetProfessions) ~= "function" then return out end
    local ok, a, b, c, d, e, f = pcall(GetProfessions)
    if not ok then return out end
    local slots = { a, b, c, d, e, f }
    for i = 1, 6 do
        local idx = slots[i]
        if idx then
            local oki, _, _, cur, mx, _, _, sid = pcall(GetProfessionInfo, idx)
            local slug = NAV_SKILL_SLUG[sid]
            if oki and slug and cur and mx then
                out[slug] = { cur = tonumber(cur) or 0, max = tonumber(mx) or 0 }
            end
        end
    end
    return out
end

local function NavAccent()
    local a = ns.hui and ns.hui.ACCENT
    if a then return a[1], a[2], a[3] end
    return 0x46 / 255, 0xbf / 255, 0x72 / 255
end
PD.NavAccent = NavAccent

function PD.PickNav()
    local learned = PD.ProfLearned()
    local function paint(bt, sel, lv)
        -- ★ 签名不变就整颗按钮都不重画（见文件头 setter 去重说明）：换专业时
        --   只有「旧选中 + 新选中」两颗真的变了，其余十几颗原样却重写了一遍 setter。
        local key = (sel and "1" or "0") .. "|" .. (lv and (lv.cur .. "/" .. lv.max) or "")
        if bt.__pnKey == key then return end
        bt.__pnKey = key
        SetOutline(bt, sel, 1, 0.82, 0)
        if lv then
            if sel then
                bt:GetFontString():SetTextColor(Unpack(C_GOLD))
            else
                bt:GetFontString():SetTextColor(NavAccent())
            end
            bt.__lv:SetText(format("%d/%d", lv.cur, lv.max))
            bt.__lv:SetTextColor(NavAccent())
            bt.__lv:Show()
        else
            bt.__lv:Hide()
            bt:GetFontString():SetTextColor(Unpack(sel and C_GOLD or C_DIM))
        end
        bt.__icon:SetDesaturated(not sel and not lv)
    end
    for _, slug in ipairs(PD.navOrder or {}) do
        local bt = PD.navKey[slug]
        if bt then paint(bt, slug == PD.cur, learned[slug]) end
    end
    -- 板条箱导航图标：物品数据到货后换成板条箱物品本体图标（未到货前留自制图占位）
    local nbt = PD.navKey and PD.navKey.crates
    if nbt and not nbt.__itemIconDone and CD and CD.crates and CD.crates[1] then
        local tex = DG.ItemIcon(CD.crates[1].id)
        if tex and tex ~= FALLBACK_ICON then
            SetIcon(nbt.__icon, tex)
            nbt.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
            nbt.__itemIconDone = true
        end
    end
    -- 「全部专业」按钮已退役（2026-10-10 用户），navKey 里不再有 "__index"。
end

function PD.TabsFor(slug)
    if slug == "__index" then return { "overview" } end
    if slug == "crates" then return { "crate", "writ" } end
    local p = D.pro[slug]
    local out = { "overview" }
    if slug == "poisons" then out = {} end
    if not p then return out end
    local TRD = ns.ProfTrainers and ns.ProfTrainers[slug]
    if TRD and TRD.list and #TRD.list > 0 then out[#out + 1] = "trainer" end
    local r = RGet(slug)
    if r and ((r.rows and #r.rows > 0) or (r.enchants and #r.enchants > 0)
              or (r.crafted and #r.crafted > 0)) then
        out[#out + 1] = "recipe"
    end
    if GA and (GA[slug] or (slug == "fishing" and GA.fishing)) then out[#out + 1] = "gather" end
    if (LV and LV[slug]) or (PD.GATHER_SLUGS and PD.GATHER_SLUGS[slug]) then out[#out + 1] = "leveling" end
    return out
end

function PD.PickTabs()
    local tabs = PD.TabsFor(PD.cur)
    PD.avail = {}
    for _, t in ipairs(tabs) do PD.avail[t] = true end
    if not PD.avail[PD.tab] then PD.tab = tabs[1] or "overview" end
    local shown = 0
    for _, def in ipairs(DG.PROF_SUBTABS) do
        local bt = PD.subBtns[def.key]
        local on = PD.avail[def.key] and true or false
        local txt = def.text
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
                bt:SetText(def.text)
                SetOutline(bt, sel, 1, 0.82, 0)
                bt:GetFontString():SetTextColor(Unpack(sel and C_GOLD or C_GREY))
            end
        end
        if on then shown = shown + 1 end
    end
    if PD.setGear then
        -- ★ 设置按钮只属于升级页（2026-10-11 用户）：里面的设置只对升级路线生效，
        --   其它页签（总览/配方/采集）下整颗收起。
        local gon = (PD.tab == "leveling")
        if PD.setGear.__shown ~= gon then
            PD.setGear.__shown = gon
            PD.setGear:SetShown(gon)
        end
        if gon then
            SetOutline(PD.setGear, PD.setOpen and true or false, 1, 0.82, 0)
            local gc = PD.setOpen and ns.SET_ICON_ON or ns.SET_ICON_IDLE
            PD.setGear.__icon:SetVertexColor(gc[1], gc[2], gc[3])
        end
    end
    if PD.trFacBtns then
        local ton = (PD.tab == "trainer") and (not PD.setOpen)
        for _, k in ipairs({ "H", "A" }) do
            local bt = PD.trFacBtns[k]
            local sel = (PD.trFac == k)
            local key = (ton and "1" or "0") .. "|" .. (sel and "1" or "0")
            if bt.__trKey ~= key then
                bt.__trKey = key
                bt:SetShown(ton)
                if ton then
                    bt:ClearAllPoints()
                    local kx = (k == "H") and 0 or 1
                    bt:SetPoint("TOPLEFT", PD.page, "TOPLEFT",
                                PD.RIGHT_X + PD.RIGHT_W - PD.LIST_PAD - 64 - kx * 72,
                                -PD.SUB_Y)
                    SetOutline(bt, sel, 1, 0.82, 0)
                    local bf = bt:GetFontString()
                    if bf then
                        if sel then
                            if k == "A" then
                                bf:SetTextColor(0.40, 0.62, 1.00, 1)
                            else
                                bf:SetTextColor(1.00, 0.36, 0.26, 1)
                            end
                        else
                            bf:SetTextColor(0.55, 0.55, 0.55, 1)
                        end
                    end
                end
            end
        end
    end
    local pf = ns.ProfFollow
    -- 2026-10-10 用户：升级HUD入口只在升级页显示（设置展开时也收起），与 impBtn 条件对齐
    if pf and pf.PaintButton and PD.hudBtn then
        if PD.tab == "leveling" and not PD.setOpen and not PD.IsGatherRoute() then
            pcall(pf.PaintButton, PD.hudBtn, PD.cur)
        else
            PD.hudBtn:Hide()
        end
    end
    if pf and pf.PaintImportBtn and PD.impBtn then
        pcall(pf.PaintImportBtn, PD.impBtn, PD.cur)
    end
    -- 2026-10-10 B1：一键导入只在购物清单子页出现（路线页 / 设置页不占位）
    if PD.impBtn then
        local wantImp = PD.tab == "leveling" and PD.autoPage == "shop"
                        and (not PD.setOpen) and PD.cur ~= nil and PD.cur ~= "__index"
                        and LV[PD.cur] ~= nil and LV[PD.cur].steps ~= nil
        PD.impBtn:SetShown(wantImp and true or false)
    end
end

PD.TOOL_MIN_W, PD.TOOL_MAX_W = 56, 200
PD.TOOL_PADX = 18

function PD.ToolSize(text)
    local need = PD.TextW(text, 12) + PD.TOOL_PADX
    local w = math.ceil(math.max(PD.TOOL_MIN_W, math.min(PD.TOOL_MAX_W, need)))
    local shown = text
    if need > PD.TOOL_MAX_W then shown = PD.Fit(text, 12, PD.TOOL_MAX_W - PD.TOOL_PADX) end
    return w, shown
end

-- 返回每行留给左侧动作的宽度。先安放右侧入口，避免左侧按钮被独立锚定的入口遮住。
function PD.PlaceToolActions(yoff)
    yoff = yoff or 0
    local width = math.max(1, PD.RIGHT_W - PD.LIST_PAD)
    local limits, rows = {}, 0
    if PD.tab == "leveling" and not PD.setOpen then
        local row, used = 0, 0
        for _, name in ipairs({"hudBtn", "impBtn"}) do
            local bt = PD[name]
            if bt and bt:IsShown() then
                local text = bt:GetText() or ""
                if text == bt.__toolFittedText then text = bt.__toolFullText or text end
                bt.__toolFullText = text
                local w = math.min(width, math.ceil(PD.TextW(text, 13)) + 22)
                local gap = used > 0 and PD.TOOL_GAP or 0
                if used > 0 and used + gap + w > width then
                    row, used, gap = row + 1, 0, 0
                end
                local x = width - used - gap - w
                local shown = PD.Fit(text, 13, math.max(1, w - 22))
                local key = w .. "|" .. x .. "|" .. row .. "|" .. yoff .. "|" .. shown
                if bt.__toolActionKey ~= key then
                    bt.__toolActionKey = key
                    bt:SetSize(w, PD.TOOL_H)
                    bt:ClearAllPoints()
                    bt:SetPoint("TOPLEFT", PD.page, "TOPLEFT", PD.RIGHT_X + x,
                                -(PD.BODY_TOP + yoff + row * (PD.TOOL_H + PD.TOOL_GAP)))
                end
                -- PickTabs 的专业入口刷新会重新写入完整宽度/文本，不能只依赖落位签名。
                if bt:GetWidth() ~= w then bt:SetWidth(w) end
                if bt:GetText() ~= shown then bt:SetText(shown) end
                bt.__toolFittedText = shown
                used = width - x
                limits[row + 1] = math.max(0, x - PD.TOOL_GAP)
                rows = row + 1
            end
        end
    end
    return width, limits, rows
end

function PD.PaintTool(list, handler, yoff)
    PD.onTool = handler
    list = list or {}
    yoff = yoff or 0
    -- ★ 第八刀（rev14）：闸门内部计时。**运行期动态取**（PD.__pfT0/__pfMark 定义在
    --   文件尾探针区），探针关时 __pfT0 返回 nil ⇒ 热路径一次取样都不做。
    local _T0, _MK = PD.__pfT0, PD.__pfMark
    local _AD = PD.__pfAdd
    local n = math.min(#list, PD.TOOL_MAX)
    local width, limits, actionRows = PD.PlaceToolActions(yoff)
    local searchReserve = PD.SearchReserve()
    if searchReserve > 0 then
        limits[1] = math.max(0, (limits[1] or width) - searchReserve)
        actionRows = math.max(actionRows, 1)
    end
    local x, row = 0, 0
    for i = 1, PD.TOOL_MAX do
        local bt = PD.toolBtns[i]
        local def = (i <= n) and list[i] or nil
        if def then
            local w, text
            if def.plain then
                -- 纯文字标签（2026-10-11 用户：路线标题挂「重新计算」右侧同行）：
                -- 不吃 TOOL_MIN/MAX_W 钳制，按 12px 实测宽走
                w = math.ceil(PD.TextW(def.text, 12)) + 6
                text = def.text
            else
                w, text = PD.ToolSize(def.text)
            end
            -- 警告芯片在纯文字右侧，也属于本项宽度。长标题只能占一整行。
            local warnW = def.plain and def.warn and def.warn[1] and width >= 29 and 28 or 0
            w = math.min(w, math.max(1, width - warnW))
            text = PD.Fit(text, 12, math.max(1, w - (def.plain and 6 or PD.TOOL_PADX)))
            while x + w + warnW > (limits[row + 1] or width) do
                row, x = row + 1, 0
            end
            -- ★ 签名进「尺寸 + 落点 x + 行号 + 文案 + 选中」。落点 x 也必须进：
            --   前面任意一颗按钮变宽都会把后面所有按钮整体推挤一位。
            local key = "1|" .. w .. "|" .. x .. "|" .. row .. "|" .. yoff .. "|"
                        .. tostring(def.plain) .. "|" .. tostring(def.on) .. "|" .. text
            if bt.__ptk ~= key then
                bt.__ptk = key
                -- ★★ 第八刀（rev14）：把闸门切成四刀。实机 16 颗 = 21~26ms，
                --   而这里每一样按 bench 单价都是微秒级 ⇒ 必须实测找真凶
                --   （项目铁律：不准读代码猜耗时段）。_m0 为 nil 时 _MK 会自己早退。
                local _m0 = _T0 and _T0()
                local _g0 = _m0
                -- ★★ 第九刀（rev15）：先记「这颗粒此刻是不是已经显示着」。
                --   引擎 Show() 在帧已可见时是**空操作** ⇒ 不触发 OnShow 链；
                --   只有 Hide→Show 跃迁才吃那 ~1.5ms/颗。实机反面样本：切到
                --   leveling 时 3 颗本来就没被 Hide ⇒ 显示 0.0ms。
                if _AD then _AD("闸-已显", bt:IsShown() and 1 or 0) end
                bt:SetSize(w, PD.TOOL_H)
                if _MK then _MK("闸-尺寸", _m0) end
                _m0 = _T0 and _T0()
                bt:ClearAllPoints()
                bt:SetPoint("TOPLEFT", PD.page, "TOPLEFT", PD.RIGHT_X + x,
                            -(PD.BODY_TOP + yoff + row * (PD.TOOL_H + PD.TOOL_GAP)))
                if _MK then _MK("闸-锚点", _m0) end
                _m0 = _T0 and _T0()
                bt:SetText(text)
                if def.plain then
                    bt:EnableMouse(false)
                    SetOutline(bt, false, 1, 0.82, 0)
                    bt:GetFontString():SetTextColor(Unpack(C_WHITE))
                else
                    bt:EnableMouse(true)
                    SetOutline(bt, def.on and true or false, 1, 0.82, 0)
                    bt:GetFontString():SetTextColor(Unpack(def.on and C_GOLD or C_GREY))
                end
                if _MK then _MK("闸-文本", _m0) end
                _m0 = _T0 and _T0()
                bt:Show()
                if _MK then _MK("闸-显示", _m0) end
                if _MK then _MK("闸-合计", _g0) end
            end
            bt.__key = def.key
            -- 警告芯片逐帧管理（签名块外：warn 明细变化不重摆按钮）
            if def.plain then
                local wz = PD.WarnChip(bt, true)
                if warnW > 0 then
                    wz:ClearAllPoints()
                    wz:SetPoint("LEFT", bt, "RIGHT", 2, 0)
                    wz.__tipLines = def.warn
                    wz:Show()
                else
                    wz:Hide(); wz.__tipLines = nil
                end
            elseif bt.__warn then
                bt.__warn:Hide(); bt.__warn.__tipLines = nil
            end
            x = x + w + warnW + (def.gap or PD.TOOL_GAP)
        else
            if bt.__ptk ~= "0" then bt.__ptk = "0"; bt:Hide() end
            bt.__key = nil
        end
    end
    local rows = math.max((n > 0) and (row + 1) or 0, actionRows)
    PD.toolRows = rows
    return (rows > 0) and (rows * (PD.TOOL_H + PD.TOOL_GAP) + PD.TOOL_BODY_GAP) or 0
end

-- ── 升级页信息卡（2026-10-10 B1）：每次渲染按 PD.lvSummary 刷新内容 ──────
-- lvSummary 由 PD.RowsLeveling（路线 / 购物清单两个分支）在渲染期写入。
-- 信息卡悬停提示（PaintLvTiles / PaintGatherTiles 共用；进出由 __hov 胶囊切换）
function PD.TipTile(tf, lines)
    tf:SetScript("OnEnter", function()
        if tf.__hov then for _, t in ipairs(tf.__hov) do t:Show() end end
        GameTooltip:SetOwner(tf, "ANCHOR_RIGHT")
        GameTooltip:ClearLines()
        for _, ln in ipairs(lines) do
            if ln[1] and ln[1] ~= "" then
                GameTooltip:AddLine(ln[1], ln[2] or 1, ln[3] or 1, ln[4] or 1, true)
            end
        end
        GameTooltip:Show()
    end)
    tf:SetScript("OnLeave", function()
        if tf.__hov then for _, t in ipairs(tf.__hov) do t:Hide() end end
        GameTooltip:Hide()
    end)
end

-- 采集升级页信息卡：复用 lvTiles 帧，三卡 = 当前技能 / 路线进度 / 路线范围
function PD.PaintGatherTiles()
    local tiles = PD.lvTiles
    if PD.tab ~= "leveling" or PD.setOpen then
        for _, k in ipairs({ "snap", "target", "scheme", "cost", "mode" }) do tiles[k]:Hide() end
        return 0
    end
    tiles.snap:Hide()
    -- 制造页点击行为（切模式/切方案）不得残留到采集页
    tiles.mode:SetScript("OnClick", nil)
    tiles.scheme:SetScript("OnClick", nil)
    tiles.cost:SetScript("OnClick", nil)
    local _learned = PD.ProfLearned()
    local curLv = _learned and _learned[PD.cur] and _learned[PD.cur].cur or nil
    -- 当前进度：落在哪个推荐段/门槛档
    local g = GA and (GA[PD.cur] or (PD.cur == "fishing" and GA.fishing))
    local prog = "-"
    if g and #g > 0 and curLv then
        for i, t in ipairs(g) do
            local lo, hi
            if PD.cur == "fishing" then
                lo = t[2]
                hi = (g[i + 1] and g[i + 1][2] or lo + 1) - 1
                if hi < lo then hi = lo end
            elseif PD.cur == "skinning" then
                lo, hi = t[1][1], t[1][2]
            else
                lo = t[2]
                hi = (g[i + 1] and g[i + 1][2] or 301) - 1
                if hi < lo then hi = lo end
            end
            if curLv >= lo and curLv <= hi then
                prog = (hi > lo) and format(L["%d - %d"], lo, hi) or tostring(lo)
                break
            end
        end
    end
    if PD.cur == "fishing" and curLv then
        local guide = ns.ProfFishingRoutes
        for index, step in ipairs(guide and guide.fishingSteps or {}) do
            if curLv >= step.from and (curLv < step.to or (index == #guide.fishingSteps and curLv == step.to)) then
                prog = format(L["%d - %d"], step.from, step.to)
                break
            end
        end
    end
    tiles.mode.label:SetText(L["当前技能"])
    tiles.mode.val:SetText(curLv and tostring(curLv) or L["未学"])
    PD.TipTile(tiles.mode, { { L["读取角色当前的专业技能值"], 0.7, 0.7, 0.7 } })
    PD.PaintTileBorder(tiles.mode, { 1, 1, 1, 0.10 })
    tiles.scheme.label:SetText(L["路线进度"])
    local smelt = false
    tiles.scheme.val:SetText((PD.cur == "mining") and
        ((smelt and L["熔炼"] or L["采集"]) .. " " .. prog) or prog)
    if PD.cur == "mining" then
        tiles.scheme:SetScript("OnClick", function()
            ProfDB().gatherMode = smelt and "gather" or "smelt"
            PD.RequestRender()
            ns.PlaySound(1)
        end)
    else
        tiles.scheme:SetScript("OnClick", nil)
    end
    PD.TipTile(tiles.scheme, (PD.cur == "mining") and {
        { L["点击切换：采集 ⇄ 熔炼"], 0.9, 0.78, 0.35 },
        { smelt and L["列表中绿色高亮行 = 当前技能可练的熔炼区间"]
            or L["列表中绿色高亮行 = 推荐当前采集的区间"], 0.7, 0.7, 0.7 },
    } or { { L["列表中绿色高亮行 = 推荐当前采集的区间"], 0.7, 0.7, 0.7 } })
    PD.PaintTileBorder(tiles.scheme, (PD.cur == "mining") and { 1, 0.82, 0, 0.55 } or { 1, 1, 1, 0.10 })
    tiles.cost.label:SetText(L["路线范围"])
    tiles.cost.val:SetText("1 - 300")
    PD.TipTile(tiles.cost, { { L["静态推荐路线（全程显示）：按资料整理的采集区间推进，不含价格与概率，无需价格插件"], 0.7, 0.7, 0.7 } })
    PD.PaintTileBorder(tiles.cost, { 1, 1, 1, 0.10 })
    -- 三卡均分（五卡槽位用三卡：等宽 tw，余数不用；表达式序与制造页错开防锚重复）
    local tw = math.floor((PD.RIGHT_W - PD.LIST_PAD - 4 * PD.LV_TILE_GAP) / 5)
    local x = PD.RIGHT_X
    for _, k in ipairs({ "mode", "scheme", "cost" }) do
        local tf = tiles[k]
        tf:SetWidth(tw)
        tf:ClearAllPoints()
        tf:SetPoint("TOPLEFT", PD.page, "TOPLEFT", x, -PD.BODY_TOP)
        x = x + tf:GetWidth() + PD.LV_TILE_GAP
        tf:Show()
    end
    return PD.LV_TILE_H + 8
end

function PD.PaintLvTiles()
    local tiles = PD.lvTiles
    if not (tiles and tiles.mode) then return 0 end
    -- 采集专业升级页走独立三卡（当前技能/路线进度/路线范围）
    if PD.IsGatherRoute() then return PD.PaintGatherTiles() end
    if PD.tab ~= "leveling" or PD.setOpen then
        for _, k in ipairs({ "mode", "scheme", "cost", "target", "snap" }) do tiles[k]:Hide() end
        return 0
    end
    local s = PD.lvSummary or {}
    local fishRoute = PD.CookingFishingMode()
    local v = PD.LvTarget()
    local auto = s.auto and true or false
    local warnAuto = s.autoSetting and (not s.ahOK or s.feasible == false)
    local fixedOnly = (PD.cur == "poisons")
    if fixedOnly then
        tiles.mode:SetScript("OnClick", nil)
    else
        tiles.mode:SetScript("OnClick", function()
            if PD.CookingFishingMode() then
                ProfDB().cookingRoute = "standard"
                PD.exclusionsOpen = false
                PD.RequestRender()
                ns.PlaySound(1)
                return
            end
            local on = not PD.Setting("autoRoute")
            ProfDB().autoRoute = on
            if not on and RA then RA.Invalidate() end
            PD.RequestRender()
            ns.PlaySound(1)
        end)
    end
    local snapSec, snapDays = s.snapshotAge, s.snapshotDays
    local TipOn = PD.TipTile
    if fixedOnly then
        tiles.mode.label:SetText(L["模式"])
        tiles.mode.val:SetText(L["固定路线"])
        tiles.mode.val:SetTextColor(Unpack(C_WHITE))
        PD.PaintTileBorder(tiles.mode, { 1, 1, 1, 0.10 })
        TipOn(tiles.mode, { { L["固定路线：按资料整理的分段练法逐段冲技能"], 0.7, 0.7, 0.7 } })
    else
        tiles.mode.label:SetText(L["模式 · 点击切换"])
        tiles.mode.val:SetText(fishRoute and L["纯钓鱼"] or (auto and L["自动计算"] or L["固定路线"]))
        tiles.mode.val:SetTextColor(Unpack(auto and C_GOLD or C_WHITE))
        if warnAuto then
            PD.PaintTileBorder(tiles.mode, { 0.95, 0.75, 0.4, 0.9 })
        else
            PD.PaintTileBorder(tiles.mode, { 1, 1, 1, 0.10 })
        end
        local modeLines = {
            { fishRoute and L["鱼类自行钓取；其他材料只使用不限量商人货物。"]
                   or auto and L["自动计算：比较采购、自制与配方依赖"]
                   or L["固定路线：按资料整理的分段练法逐段冲技能"], 1, 0.82, 0 },
            { fishRoute and L["点击返回普通路线"] or L["点击在固定 / 自动之间切换"], 0.7, 0.7, 0.7 },
        }
        if warnAuto then
            modeLines[#modeLines + 1] = { L["计算结果尚不完整，请查看路线中的缺价或配方提示。"],
                                          0.95, 0.75, 0.4 }
        end
        TipOn(tiles.mode, modeLines)
    end
    -- 方案卡显示当前选择；s.scheme 保留已计算路线的方案，供费用和快照说明使用。
    local sch = PD.SettingRaw("autoScheme") or "cheapest"
    tiles.scheme.label:SetText(fishRoute and L["路线方案"] or L["路线方案 · 点击切换"])
    tiles.scheme.val:SetText(fishRoute and L["鱼类路线"] or ((RA and RA.SchemeLabel) and RA.SchemeLabel(sch) or L["最省钱"]))
    tiles.scheme:SetScript("OnClick", (not fishRoute and not fixedOnly) and PD.CycleRouteScheme or nil)
    tiles.scheme.val:SetTextColor(Unpack(C_WHITE))
    local schemeDesc = {
        cheapest = L["最省钱：比较材料采购、自制及未学图纸支出"],
        matcost = L["材料成本：只按材料价选配方"],
        crafts = L["次数最少：优先升点率高的配方，同分取便宜"],
        optim = L["乐观计数：材料不看市价，一律按卖店价值折算；次数固定按做一次涨一点统计、只是下限；快变黄前 25 点的配方也纳入可选；带冷却的转化配方和资料未收录的材料不进路线"],
    }
    local schemeLines = {}
    local sorder = (RA and RA.SchemeOrder and RA.SchemeOrder()) or {}
    for _, sk in ipairs(sorder) do
        local curK = (sk == sch)
        schemeLines[#schemeLines + 1] = { schemeDesc[sk] or sk,
                                          curK and 1 or 0.62, curK and 0.82 or 0.62,
                                          curK and 0 or 0.62 }
    end
    if fishRoute then
        schemeLines = {
            {L["1–225 参考烹饪指南；之后优先容易钓取的鱼。"], 1, 0.82, 0},
            {L["鱼类自行钓取；其他材料只使用不限量商人货物。"], 0.7, 0.7, 0.7},
            {L["鱼类不计金币成本；图纸仍按实际采购来源计费。"], 0.7, 0.7, 0.7},
        }
    elseif s.auto and s.scheme and sch ~= s.scheme then
        schemeLines[#schemeLines + 1] = {L["已保存路线；数据或设置已变化，点击重新计算更新。"], 0.95, 0.75, 0.4}
    end
    TipOn(tiles.scheme, schemeLines)
    tiles.cost.label:SetText(s.isSupplement and L["补料采购支出"] or s.partial and format(L["%d → %d 已计算支出"], s.start or 1, s.plannedTo or 1)
                              or format(L["1 → %d 预计总花费"], s.target or v))
    local costLines
    if s.status == "selection_required" or s.status == "recalculate_required" then
        tiles.cost.val:SetText(L["—"])
        tiles.cost.val:SetTextColor(Unpack(C_GREY))
        costLines = {{PD.PlanStatusText(s), 0.95, 0.75, 0.4}}
    elseif s.scheme == "optim" then
        tiles.cost.val:SetText(RA.MoneyStr(s.total or 0, "copper"))
        tiles.cost.val:SetTextColor(Unpack(C_GREY))
        costLines = { { L["乐观计数：花费按卖店价值粗算，不是拍卖行行情"], 0.7, 0.7, 0.7 } }
    elseif s.priced and s.total then
        tiles.cost.val:SetText(PD.PlanCostText(s))
        tiles.cost.val:SetTextColor(Unpack(C_GOLD))
        costLines = {}
        if s.recipes then
            costLines[#costLines + 1] = { format(L["配方 %d 种 · %d 次制作"], s.recipes, s.crafts or 0) }
            costLines[#costLines + 1] = { format(L["商人直售 %s"], RA.MoneyStr(s.vendorTotal or 0)), 0.7, 0.7, 0.7 }
        else
            costLines[#costLines + 1] = { format(L["材料 %d 种"], s.matsN or 0) }
        end
    else
        tiles.cost.val:SetText(L["—"])
        tiles.cost.val:SetTextColor(Unpack(C_GREY))
        costLines = { { PD.AuctionatorStatusText(), 0.7, 0.7, 0.7 } }
    end
    if (s.np or 0) > 0 then
        costLines[#costLines + 1] = { format(L["含无价材料 %d 种：花费为估算下限"], s.np),
                                      0.95, 0.75, 0.4 }
    end
    if s.planVersion == 2 then
        if s.completeCost == false then costLines[#costLines + 1] = { L["采购价格或图纸现货尚未全部核实，当前金额是已知支出。"], 0.95, 0.75, 0.4 } end
    end
    TipOn(tiles.cost, costLines)
    tiles.target.label:SetText(L["目标等级 · 点击修改"])
    tiles.target.val:SetText(v >= 300 and L["全程"] or tostring(v))
    tiles.target.val:SetTextColor(Unpack(C_WHITE))
    TipOn(tiles.target, { { L["每专业独立记忆；300 = 全程。点击修改"], 0.7, 0.7, 0.7 } })
    tiles.snap.label:SetText(s.planVersion == 2 and L["优化状态"] or L["价格快照"])
    local atxt
    if s.planVersion == 2 then
        atxt = PD.PlanStatusText(s)
    elseif s.scheme == "optim" then
        atxt = L["乐观计数 · 不依赖价格插件"]
    elseif s.priced and snapSec then
        -- 2026-10-11 用户：时间与插件名紧贴（去掉 ·）；超 24 小时直接显示 X 天前
        if snapSec < 60 then
            atxt = L["刚刚Auctionator"]
        elseif snapSec < 90 * 60 then
            atxt = format(L["%d 分钟前Auctionator"], math.max(1, math.floor(snapSec / 60 + 0.5)))
        elseif snapSec < 24 * 3600 then
            atxt = format(L["%d 小时前Auctionator"], math.max(1, math.floor(snapSec / 3600 + 0.5)))
        else
            atxt = format(L["%d 天前Auctionator"], math.floor(snapSec / 86400 + 0.5))
        end
    elseif s.priced and snapDays then
        atxt = (snapDays <= 0) and L["今天Auctionator"]
               or format(L["%d 天前Auctionator"], snapDays)
    elseif s.priced then
        atxt = L["快照年龄未知Auctionator"]
    end
    if atxt then
        tiles.snap.val:SetText(atxt)
        tiles.snap.val:SetTextColor(0.55, 0.85, 0.6, 1)
        local details = { { atxt, 0.7, 0.7, 0.7 } }
        local progress = PD.PlanProgressText(s)
        if progress then details[#details + 1] = {progress, 0.7, 0.7, 0.7} end
        local cached = PD.PlanCacheText(s)
        if cached then details[#details + 1] = {cached, 0.95, 0.75, 0.4} end
        if s.budgetLimited then details[#details + 1] = {L["已完成本轮计算，当前结果尚未证明最优。"], 0.95, 0.75, 0.4} end
        TipOn(tiles.snap, details)
    else
        tiles.snap.val:SetText(PD.AuctionatorStatusText())
        tiles.snap.val:SetTextColor(0.95, 0.75, 0.4, 1)
        TipOn(tiles.snap, { { PD.AuctionatorStatusText(),
                              0.7, 0.7, 0.7 } })
    end
    -- 四张信息卡均分（2026-10-10 用户定）：整行可用 = RIGHT_W - LIST_PAD，四卡等宽、
    --   缝 3*8；余数给快照卡，右缘钉在卡右缘-8（UI_RULES §3.1）。
    --   （此前的死宽 200/250/150 + min120 钳位曾把整行撑溢出 4px，勿回潮。）
    -- 五张信息卡均分（2026-10-10 用户：加路线方案卡，第二位）
    local layout = { "mode", "scheme", "cost", "target", "snap" }
    if fixedOnly then
        layout = { "mode", "cost", "target", "snap" }
        tiles.scheme:Hide()
    end
    local n = #layout
    local usable = PD.RIGHT_W - PD.LIST_PAD - (n - 1) * PD.LV_TILE_GAP
    local tw = math.floor(usable / n)
    local x = PD.RIGHT_X
    for i, k in ipairs(layout) do
        local tf = tiles[k]
        if i == n then
            tf:SetWidth(usable - (n - 1) * tw)
        else
            tf:SetWidth(tw)
        end
        tf:ClearAllPoints()
        tf:SetPoint("TOPLEFT", PD.page, "TOPLEFT", x, -PD.BODY_TOP)
        x = x + tf:GetWidth() + PD.LV_TILE_GAP
        tf:Show()
    end
    return PD.LV_TILE_H + 8
end

function PD.Layout(toolH)
    local top = PD.BODY_TOP + (toolH or 0)
    local bot = PD.BODY_BOT
    PD.scroll:ClearAllPoints()
    PD.scroll:SetPoint("TOPLEFT", PD.page, "TOPLEFT", PD.RIGHT_X, -top)
    PD.scroll:SetPoint("BOTTOMRIGHT", PD.page, "BOTTOMRIGHT", -PD.CARD_INSET, bot)
    PD.listCard:ClearAllPoints()
    PD.listCard:SetPoint("TOPLEFT", PD.page, "TOPLEFT",
                         PD.RIGHT_X - PD.LIST_PAD, -PD.CARD_TOP)
    PD.listCard:SetPoint("BOTTOMRIGHT", PD.page, "BOTTOMRIGHT",
                         -PD.CARD_INSET, PD.CARD_INSET)
    PD.listCard:Show()
    local splitW
    if PD.lvSplit then splitW = PD.splitLW or PD.COL_LW
    elseif PD.gridSplit then splitW = PD.GRID_LW end
    if splitW and not PD.hideDivider then
        local gut = PD.lvSplit and PD.OV_GUT or PD.COL_GAP
        local mx = PD.RIGHT_X + PD.LIST_PAD + splitW + gut / 2
        PD.divider:ClearAllPoints()
        PD.divider:SetPoint("TOPLEFT", PD.page, "TOPLEFT", mx, -top)
        PD.divider:SetPoint("BOTTOMLEFT", PD.page, "BOTTOMLEFT", mx, bot)
        PD.divider:Show()
    else
        PD.divider:Hide()
    end
end

PD.SWEEP_AT = { 0.5, 1.5, 4, 9 }

function PD.SweepNames()
    if PD.sweeping or not PD.notReady then return end
    PD.sweeping = true
    local got = false
    for _, id in ipairs(PD.notReady) do
        local _, ok = DG.ItemName(id)
        if ok then got = true; break end
    end
    PD.notReady = nil
    if got then
        -- 名称到货只重绘；已计算路线保留到用户明确重新计算。
        PD.RequestRender()
    end
    PD.sweeping = false
end

function PD.ScheduleSweep()
    if type(C_Timer) ~= "table" or type(C_Timer.After) ~= "function" then return end
    for _, t in ipairs(PD.SWEEP_AT) do
        C_Timer.After(t, function() PD.SweepNames() end)
    end
end

local C_ALLIANCE = { 0.40, 0.80, 0.94 }
local C_HORDE = { 1.00, 0.30, 0.25 }

function PD.RowsComprOverview(rows)
    local EM = ns.ExploreModule
    local tiers = EM and EM.BM_TIERS or nil
    PushGap(rows, 4, 1)
    if tiers and #tiers > 0 then
        PushHead(rows, L["提升技能"], 1)
        PushText(rows, L["未翻译的卷轴有四种，每一种需要的理解技能等级都更高。一种卷轴变灰之后就不会再提升技能：在技能到达它变灰的等级之前，换成下一种。"], 14)
        for _, t in ipairs(tiers) do
            local names = {}
            for _, id in ipairs(t.unc or {}) do
                names[#names + 1] = tostring(DG.ItemName(id) or "?")
            end
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H1, col = 1, fs = 14,
                text = t.tier,
                sub = table.concat(names, ", "),
                right = format("%s %d · %s %d", L["可破译于"], t.req or 0, L["变灰于"], t.gray or 0),
            }
        end
        PushGap(rows, PD.OV_GUT, 1)
    end
    local bundle = EM and EM.BM_BUNDLE or nil
    if bundle and #bundle > 0 then
        PushHead(rows, L["「一捆卷轴」开出率（17 捆样本）"], 1)
        for _, b in ipairs(bundle) do
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H1, col = 1, it = { b[1] }, qItem = b[1], fs = 14,
                text = PD.ItemName(b[1]),
                right = format("%d%%", b[2] or 0),
            }
        end
        PushGap(rows, PD.OV_GUT, 1)
    end
end

function PD.RowsOverview(rows)
    local p = D.pro[PD.cur]
    if not p then return end
    if PD.cur == "comprehension" then
        PD.RowsComprOverview(rows)
        return
    end
    PushGap(rows, 4, 1)


    local miles = p.miles or {}
    local hasPerks = p.perks and #p.perks > 0
    if #miles > 0 or hasPerks then
        PushHead(rows, L["传承"], 1)
        for _, m in ipairs(miles) do
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H1, col = 1, fs = 14, text = m[1] or "?",
                right = format(L["技能 %d · %d 点"], m[2] or 0, m[3] or 0),
            }
        end
        if #miles > 0 and hasPerks then PushGap(rows, 4, 1) end
        for _, pid in ipairs(p.perks or {}) do
            local pk = D.perks[pid]
            if pk then
                local open = PD.perkOpen[pid]
                local lines = { { pk[6] or "" } }
                if pk[8] then
                    for _, u in ipairs(pk[8]) do lines[#lines + 1] = { u, 0.9, 0.7, 0.4 } end
                end
                rows[#rows + 1] = {
                    kind = "row", col = 1, icon = pk[2], text = pk[1] or "?",
                    sub = (pk[6] or ""):sub(1, 90),
                    right = format(L["满级 %s"], tostring(pk[4])),
                    right2 = open and L["收起逐级文本"]
                                      or format(L["展开 %d 级文本"], #(pk[5] or {})),
                    lines = lines,
                    act = function()
                        PD.perkOpen[pid] = not PD.perkOpen[pid]
                        PD.RequestRender()
                    end,
                }
                if open and pk[5] then
                    for i, t in ipairs(pk[5]) do
                        rows[#rows + 1] = { kind = "text", col = 1,
                                            text = format("%d. %s", i, t), color = C_TEXT }
                    end
                end
            end
        end
        PushGap(rows, PD.OV_GUT, 1)
    end

    local lv = LV[PD.cur]
    local hasCampObjs = p.camp and #p.camp > 0
    local hasCampPts = lv and (lv.camps or lv.vendor) and true or false
    if hasCampObjs or hasCampPts then
        PushHead(rows, L["营地"], 1)
        for _, c in ipairs(p.camp or {}) do
            local lines = {}
            local function Add(label, v)
                if v and v ~= "" then lines[#lines + 1] = { label .. "：" .. v } end
            end
            Add(L["角色"], c[7])
            Add(L["增益"], c[6])
            Add(L["取代"], c[8])
            Add(L["互斥"], c[9])
            Add(L["容量"], c[10])
            if c[11] and #c[11] > 0 then
                lines[#lines + 1] = { format(L["材料：%s"], PD.MatText(c[11])), 0.7, 0.7, 0.7 }
            end
            if c[12] and c[12][1] then
                lines[#lines + 1] = { format(L["图纸：%s"], DG.ItemName(c[12][1])) }
            end
            rows[#rows + 1] = {
                kind = "row", col = 1, icon = c[3],
                text = c[2] or "?",
                sub = c[5] or "",
                right = format(L["技能 %d"], c[4] or 0),
                lines = lines,
            }
        end
        if hasCampObjs and hasCampPts then PushGap(rows, 4, 1) end
        for _, side in ipairs({ "a", "h" }) do
            local fc = (side == "a") and C_ALLIANCE or C_HORDE
            local camp = lv and lv.camps and lv.camps[side]
            local vd = lv and lv.vendor and lv.vendor[side]
            if vd then
                local loc = tostring(vd[3] or "")
                if camp then
                    loc = format("%s · %s · %s", tostring(camp[1] or ""),
                                 PD.CampZoneName(camp[6], tostring(camp[2] or "")),
                                 tostring(camp[3] or ""))
                end
                local lines = {
                    { L["点击：在地图上标记该 NPC"], 1, 0.82, 0 },
                    { format("%.1f, %.1f", vd[5] or 0, vd[6] or 0), 0.75, 0.75, 0.75 },
                }
                if camp then
                    lines[#lines + 1] = {
                        format(L["营地位置 %.1f, %.1f"], camp[4] or 0, camp[5] or 0),
                        0.75, 0.75, 0.75,
                    }
                end
                rows[#rows + 1] = {
                    kind = "row", col = 1, nameColor = fc, icon = PD.FAC_ICON[side],
                    text = format(L["军需官 · %s"], tostring(vd[1])),
                    sub = loc,
                    right = format("%.1f, %.1f", vd[5] or 0, vd[6] or 0),
                    lines = lines,
                    act = function() PD.MarkCampPoint(vd[7], vd[5], vd[6]) end,
                }
            elseif camp then
                rows[#rows + 1] = {
                    kind = "row", col = 1, nameColor = fc,
                    text = format(L["营地 · %s"], camp[3] or "?"),
                    sub = format("%s · %s", PD.CampZoneName(camp[6], tostring(camp[2] or "")), tostring(camp[1] or "")),
                    right = format("%.1f, %.1f", camp[4] or 0, camp[5] or 0),
                    lines = {
                        { L["点击：在地图上标记此位置"], 1, 0.82, 0 },
                        { format("%s %.1f, %.1f", tostring(camp[2] or ""), camp[4] or 0, camp[5] or 0), 0.75, 0.75, 0.75 },
                    },
                    act = function() PD.MarkCampPoint(camp[6], camp[4], camp[5]) end,
                }
            end
        end
        PushGap(rows, PD.OV_GUT, 1)
    end

    if p.steps and #p.steps > 0 then
        PushHead(rows, p.steps_title or L["怎么开始"], 1)
        if p.steps_note then PushText(rows, p.steps_note, 14, C_GREY, 1) end
        for i, st in ipairs(p.steps) do
            rows[#rows + 1] = {
                kind = "row", col = 1,
                text = format("%d. %s", i, st[1] or ""), sub = st[2] or "",
                lines = { { st[1] or "" }, { st[2] or "", 0.85, 0.85, 0.85 } },
            }
        end
        PushGap(rows, PD.OV_GUT, 1)
    end
    if p.racials and #p.racials > 0 then
        PushHead(rows, L["种族相关"], 1)
        for _, rc in ipairs(p.racials) do PushText(rows, "· " .. (rc[3] or ""), 14, nil, 1) end
        PushGap(rows, PD.OV_GUT, 1)
    end


    if PD.cur == "camping" and PD.campView == "bonus" then
        PushHead(rows, L["全部专业的营地物件档位对照"], nil, 16)
        rows[#rows].noSec = true
    end

    local secN = 0
    for _, sp in ipairs(rows) do
        if sp.kind == "head" and not sp.noSec then
            secN = secN + 1
            sp.sec = secN
        elseif sp.kind ~= "gap" then
            sp.sec = secN
        end
    end
    PD.secCount = secN
end

-- ★★ areaID → uiMapID：与探索页共用同一张静态表（Core/Data/Data_AreaMap.lua，生成物）。
--   无限服客户端没有 C_Map.GetMapInfoFromAreaID ⇒ 表里漏键 = 点军需官不落图。
local CAMP_AREA_MAP = ns.AreaMap or {}

local function MapIDAlive(mapID)
    if not mapID then return false end
    if not (C_Map and C_Map.GetMapInfo) then return true end
    local ok, mi = pcall(C_Map.GetMapInfo, mapID)
    return ok and mi ~= nil
end

function PD.MarkMapPoint(mapID, x, y)
    if not MapIDAlive(mapID) then
        if UIErrorsFrame and UIErrorsFrame.AddMessage then
            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame, L["未收录该位置的地图"], 1, 0.4, 0.4)
        end
        return
    end
    if UiMapPoint and UiMapPoint.CreateFromCoordinates and C_Map and C_Map.SetUserWaypoint then
        local pok, pt = pcall(UiMapPoint.CreateFromCoordinates, mapID, (x or 0) / 100, (y or 0) / 100)
        if pok and pt then
            pcall(C_Map.SetUserWaypoint, pt)
            if C_SuperTrack and C_SuperTrack.SetSuperTrackedUserWaypoint then
                pcall(C_SuperTrack.SetSuperTrackedUserWaypoint, false)
            end
        end
    end
    if C_Map and C_Map.OpenWorldMap then
        pcall(C_Map.OpenWorldMap, mapID)
    elseif OpenWorldMap then
        pcall(OpenWorldMap, mapID)
    end
end

function PD.MarkCampPoint(areaID, x, y)
    local mapID = areaID and CAMP_AREA_MAP[areaID] or nil
    if not MapIDAlive(mapID) then
        mapID = nil
        if areaID and C_Map and C_Map.GetMapInfoFromAreaID then
            local ok, mi = pcall(C_Map.GetMapInfoFromAreaID, areaID)
            mapID = ok and mi and mi.mapID or nil
        end
        if not MapIDAlive(mapID) then mapID = nil end
    end
    PD.MarkMapPoint(mapID, x, y)
end

-- 配方来源的商人落图：loc = ns.ProfVendors[npcID] = { 区域AreaID, 图uiMapID, x, y }。
--   mapID（定位源直接给的 uiMapID）先试；不行再 areaID → Data_AreaMap（与营地同口径）。
function PD.MarkVendorLoc(loc)
    if not loc then
        if UIErrorsFrame and UIErrorsFrame.AddMessage then
            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame, L["该商人的位置暂未收录"], 1, 0.4, 0.4)
        end
        return
    end
    local mapID = loc[2]
    if not MapIDAlive(mapID) then
        mapID = loc[1] and CAMP_AREA_MAP[loc[1]] or nil
    end
    PD.MarkMapPoint(mapID, loc[3], loc[4])
end

-- ★ 按玩家阵营过滤商人（2026-10-10 用户：联盟商人不得出现在部落的视野里）。
--   side 字段：'a'=仅联盟 / 'h'=仅部落 / nil=中立或未回填（双方可见）。
--   数据一条 side 都没回填时返回全量（旧数据兼容）；回填过就严格过滤，
--   过滤后为空是合法结果 —— 上层据此不显示商人段。
function PD.VendorListOf(src)
    local all = (src and src.vendors) or {}
    if #all == 0 then return all end
    local f
    if UnitFactionGroup then
        local ok, eng = pcall(UnitFactionGroup, "player")
        if ok and eng == "Alliance" then
            f = "a"
        elseif ok and eng == "Horde" then
            f = "h"
        end
    end
    if not f then return all end
    local out, known = {}, false
    for i = 1, #all do
        local v = all[i]
        if v.side then
            known = true
            if v.side == f then out[#out + 1] = v end
        else
            out[#out + 1] = v
        end
    end
    if not known then return all end
    return out
end

-- 配方/附魔来源 → 首个可定位的商人 { loc, name }。src = source 表。
function PD.VendorLocOf(src)
    local vs = PD.VendorListOf(src)
    if not vs then return nil end
    for _, v in ipairs(vs) do
        if v.id and ns.ProfVendors and ns.ProfVendors[v.id] then
            return ns.ProfVendors[v.id], v.name
        end
    end
    return nil
end

function PD.CampZoneName(areaID, fallback)
    local f = C_Map and C_Map.GetMapInfoFromAreaID
    if f and areaID then
        local ok, mi = pcall(f, areaID)
        if ok and mi and mi.name and mi.name ~= "" then return mi.name end
    end
    local g = C_Map and C_Map.GetAreaInfo
    if g and areaID then
        local ok, name = pcall(g, areaID)
        if ok and type(name) == "string" and name ~= "" then return name end
    end
    return fallback
end

function PD.MatIconTex(id, px)
    px = px or 14
    local ic = PD.ItemIcon(id)   -- ★ 记忆化：同一材料在一页里被算几十次
    if type(ic) == "number" then
        return format("|T%d:%d:%d|t", ic, px, px)
    end
    return format("|TInterface\\Icons\\%s:%d:%d|t", tostring(ic or FALLBACK_ICON), px, px)
end

-- 第 4 个返回值 segs = 分段表 {{ id = 物品ID|nil, text = 该段的完整串 }, ...}。
--   2026-10-09：配方页把材料列渲染成**锚点分段链**（每段一个字串 + 一格热区），
--   段间那两格空格跟着**后一段**走 ⇒ 与旧的 table.concat(out, "  ") 逐像素一致。
--   纯 … 段没有物品 id（不给热区）；末段「图标+截断名」仍带 id 出热区（2026-10-10）。
function PD.MatCol(list, fs, budget)
    if not list or #list == 0 then return "", 0, 0, nil end
    -- 2026-10-10 用户：材料和材料之间不要间距（gap 0），宽度全部留给内容
    local gap, px = 0, PD.MAT_ICON_PX
    local out, w, n, segs = {}, 0, 0, {}
    for i = 1, #list do
        local m = list[i]
        local name = PD.ItemName(m[1])
        -- 2026-10-10 用户：数量不再写「N×」前缀，改压在图标右下角（见 PaintMatSegs
        --   的数量徽标）⇒ 列宽公式里少掉每材料一次数字量宽，空间全给名称。
        local cw = px + PD.TextW(name, fs)
        if n > 0 and w + gap + cw > budget then
            -- 2026-10-10 用户（截图红框）：末段整段丢弃 = 材料列右缘留一截白 ——
            --   改画「图标 + 名称按剩余宽截断」（PD.Fit 自带 …，热区/徽标照挂）；
            --   只剩连图标都放不下的零头才退回纯 … 段（无 id 不给热区）。
            local avail = budget - w - gap - px
            if avail >= PD.MAT_TAIL_MIN then
                local piece2 = PD.MatIconTex(m[1], px) .. PD.Fit(name, fs, avail)
                out[#out + 1] = piece2
                segs[#segs + 1] = { id = m[1], cnt = m[2] or 1, text = piece2 }
            else
                out[#out + 1] = "…"
                segs[#segs + 1] = { text = "…" }
            end
            break
        end
        if n == 0 and cw > budget then
            name = PD.Fit(name, fs, budget - px)
            cw = px + PD.TextW(name, fs)
        end
        local piece = PD.MatIconTex(m[1], px) .. name
        out[#out + 1] = piece
        -- 段间空隙改由 PaintMatSegs 锚点 gap(10) 提供，段文本不再带前导空格
        --   （数量徽标要按「段左缘 = 图标左缘」定位，前导空格会把它推歪）。
        segs[#segs + 1] = { id = m[1], cnt = m[2] or 1, text = piece }
        w = w + (n > 0 and gap or 0) + cw
        n = n + 1
    end
    return table.concat(out, ""), w, n, segs
end

function PD.MatText(list, maxN)
    if not list or #list == 0 then return "" end
    local t = {}
    for i, m in ipairs(list) do
        if maxN and i > maxN then t[#t + 1] = "…"; break end
        t[#t + 1] = format("%d×%s%s", m[2] or 1, PD.MatIconTex(m[1]), DG.ItemName(m[1]))
    end
    return table.concat(t, "  ")
end

-- 制作物热区（升级行专用）：盖住「配方图标 + 配方名」，悬停出产物自己的物品提示框。
-- 与材料块热区同款四件事：悬停高亮 / 物品提示框 / 滚轮转发 / Shift 点击发链接。
-- ★ 提示框一律走 DG.ShowItemTip（带物品内容 ⇒ 暴雪原皮，不套本插件主题），
--   且不自拼 AddLine 文案 —— 用户明确要求「这个提示框不使用我们的主题」。
function PD.IconZone(r)
    if r.__iconZone then return r.__iconZone end
    local z = CreateFrame("Button", nil, r)
    z:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    PD.WireTipZone(z, r)
    r.__iconZone = z
    return z
end

function PD.WarnChip(r, plainTip)
    if r.__warn then return r.__warn end
    local z = CreateFrame("Button", nil, r)
    z:SetSize(26, 20)
    if plainTip then
        -- 工具行宿主是 Button（无 backdrop）⇒ WireTipZone 的 SetRowHover 会炸；
        -- 独立提示框通道：只弹文字，不接行悬停高亮
        z:SetScript("OnEnter", function(self)
            local lines = self.__tipLines
            if lines and lines[1] then
                GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                GameTooltip:ClearLines()
                for _, ln in ipairs(lines) do
                    if ln[1] and ln[1] ~= "" then
                        GameTooltip:AddLine(ln[1], ln[2] or 1, ln[3] or 1, ln[4] or 1, true)
                    end
                end
                GameTooltip:Show()
            end
        end)
        z:SetScript("OnLeave", function() GameTooltip:Hide() end)
    else
        PD.WireTipZone(z, r)
    end
    local tex = z:CreateTexture(nil, "OVERLAY", nil, 2)
    tex:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\WarnTri")
    tex:SetSize(18, 18)
    tex:SetPoint("CENTER", z, "CENTER", 0, 0)
    r.__warn = z
    return z
end

function PD.PctChip(r)
    if r.__pct then return r.__pct end
    local f = CreateFrame("Frame", nil, r)
    ns.hui.BuildRoundedBG(f, 4, ns.hui.layer.L2, "both", true, 1)
    local fs = MakeFS(f, 10, C_TEXT, "CENTER")
    fs:SetPoint("LEFT", f, "LEFT", 4, 0)
    fs:SetPoint("RIGHT", f, "RIGHT", -4, 0)
    fs:SetPoint("TOP", f, "TOP", 0, -2)
    fs:SetPoint("BOTTOM", f, "BOTTOM", 0, 2)
    f.fs = fs
    r.__pct = f
    return f
end

function PD.VsBlock(r)
    if r.__vs then return r.__vs end
    local base = tonumber(r.GetFrameLevel and r:GetFrameLevel()) or 0
    local cards, zones = {}, {}
    for k = 1, 2 do
        local c = CreateFrame("Frame", nil, r)
        c:SetFrameLevel(base + 2)
        ns.hui.BuildRoundedBG(c, 6, ns.hui.layer.L2, "both", true, 1)
        local host = CreateFrame("Frame", nil, c)
        host:SetFrameLevel(base + 3)
        host:SetPoint("TOPLEFT", c, "TOPLEFT", 0, 0)
        host:SetPoint("BOTTOMRIGHT", c, "BOTTOMRIGHT", 0, 0)
        local lab = MakeFS(host, 12, C_GREY, "LEFT")
        lab:SetPoint("TOPLEFT", host, "TOPLEFT", 8, -4)
        local ic = host:CreateTexture(nil, "OVERLAY", nil, 2)
        ic:SetSize(22, 22)
        ic:SetPoint("BOTTOMLEFT", host, "BOTTOMLEFT", 8, 6)
        ic:Hide()
        local nm = MakeFS(host, 12, C_TEXT, "LEFT")
        nm:SetWordWrap(false)
        nm:SetPoint("LEFT", ic, "RIGHT", 5, 0)
        nm:SetPoint("RIGHT", host, "RIGHT", -8, 0)
        local price = MakeFS(host, 14, C_GOLD, "RIGHT")
        price:SetPoint("TOPRIGHT", host, "TOPRIGHT", -8, -8)
        c.lab, c.ic, c.nm, c.price, c.host = lab, ic, nm, price, host
        local bd = CreateFrame("Frame", nil, host)
        bd:SetFrameLevel(base + 5)
        ns.hui.BuildRoundedBG(bd, 4, ns.hui.layer.L4, "both", true, 1)
        local bdFs = MakeFS(bd, 10, { 0.42, 0.94, 0.62 }, "CENTER")
        bdFs:SetPoint("CENTER", bd, "CENTER", 0, 0)
        bd:SetSize(32, 14)
        bd:SetPoint("TOPRIGHT", host, "TOPRIGHT", -4, 9)
        bd:Hide()
        c.badge, c.badgeFs = bd, bdFs
        cards[k] = c
        local z = CreateFrame("Button", nil, r)
        z:SetFrameLevel(base + 4)
        PD.WireTipZone(z, r)
        zones[k] = z
    end
    r.__vs = { cards = cards, zones = zones }
    return r.__vs
end

-- 一格物品热区的统一接线（制作物 / 需求材料共用）。
-- ★ 滚轮必须显式转发：热区是 EnableMouse 的，压在它上面时滚轮不保证冒泡到滚动容器
--   （本相册老坑：满屏都是热区 = 整页滚不动）。
function PD.WireTipZone(z, r)
    z:EnableMouseWheel(true)
    z:SetScript("OnEnter", function(self)
        PD.SetRowHover(r, true)
        local lines = self.__tipLines
        if lines then
            -- 文字提示框通道（商人热区）：与行级提示框同一套写法（同样吃本插件主题）
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:ClearLines()
            for _, ln in ipairs(lines) do
                if ln[1] and ln[1] ~= "" then
                    GameTooltip:AddLine(ln[1], ln[2] or 1, ln[3] or 1, ln[4] or 1, true)
                end
            end
            GameTooltip:Show()
        elseif self.__it and DG.ShowItemTip then
            -- 物品通道：DG.ShowItemTip 走 SetItemByID ⇒ 带物品内容 ⇒ 暴雪原皮（不套本插件主题）
            -- extra = 惰性价格段（函数先求值；行池热区也吃同一套）
            local extra = self.__tipExtra
            if type(extra) == "function" then extra = extra() end
            DG.ShowItemTip(self, self.__it, extra)
        end
    end)
    z:SetScript("OnLeave", function(self)
        PD.SetRowHover(r, false)
        GameTooltip:Hide()
    end)
    z:SetScript("OnClick", function(self, button)
        -- 自定义点击优先（商人热区 → 落图）；否则走物品的 Shift 点击发链接
        if self.__act then
            self.__act(self, button)
            return
        end
        DG.ItemShiftClick(self, button)
    end)
    z:SetScript("OnMouseWheel", function(self, delta)
        PD.HideVendorPick()   -- 弹窗锚着滚动内容，一滚就飘 ⇒ 轮到滚轮先收
        DG.WheelScroll(PD.scroll, PD.child, delta)
    end)
end

-- ── 配方页「锚点分段链」：材料列各段 + 右下角商人半段 ──────────────────────────
-- 为什么是锚点链而不是量宽：hotspot 必须与文字**逐像素**对齐，而 ns.hui.TextW 是估算器
--   （图标按 fs + 2 算、空格走步进表），拿它摆热区必然漂；锚点链把位置交给引擎算。
function PD.MatSeg(r, i)
    if i == 1 then return r.f end
    local fs = r.mn[i]
    if not fs then
        fs = MakeFS(r, PD.MAT_FS, C_TEXT, "LEFT")
        fs:SetWordWrap(false)
        r.mn[i] = fs
    end
    return fs
end

function PD.MatZone(r, i)
    local z = r.mz[i]
    if not z then
        z = CreateFrame("Button", nil, r)
        PD.WireTipZone(z, r)
        r.mz[i] = z
    end
    return z
end

-- 材料数量徽标池（2026-10-10 用户）：压在每段图标右下角。白字 + 黑描边 + 黑阴影，
--   任意图标底色上都可读。字串不截鼠标（fontstring 天然不吃输入），热区照常工作。
function PD.MatCnt(r, i)
    -- ★ 命名纪律：行池帧上的字段名必须先查重 —— `r.mc` 在行池出厂时已被占
    --   （是个函数，pairs 直接炸），数量徽标池用 r.mcnt。
    r.mcnt = r.mcnt or {}
    local c = r.mcnt[i]
    if not c then
        c = MakeFS(r, 10, C_WHITE, "RIGHT")
        local f, s = c:GetFont()
        c:SetFont(f, s, "OUTLINE")
        c:SetShadowColor(0, 0, 0, 1)
        c:SetShadowOffset(1, -1)
        c:SetWordWrap(false)
        r.mcnt[i] = c
    end
    return c
end

-- 收干净：行池跨专业/跨子页签复用 —— 不清就会留一串透明热区在旧位置吞鼠标（本相册老坑）。
function PD.ClearMatSegs(r)
    if r.f then r.f:SetText("") end
    -- ★ 2026-10-09 残留真凶：遍历必须用 pairs，不能用 `for j = 2, #r.mn`。
    --   r.mn **永远缺 index 1**（第 1 段材料走 r.f，分段从 mn[2] 起存），
    --   Lua 5.1 对带洞表的 # 是未定义行为 —— 实测 {nil,a,b} ⇒ #t 可能返回 0，
    --   于是这条循环一次都不跑：旧配方的分段字串既不清文本也不 Hide，
    --   行池复用重新 Show 行时整串复活 = 「配方→升级(购物清单)材料残留」。
    if r.mn then
        for _, fs in pairs(r.mn) do
            fs:SetText("")
            fs:Hide()
        end
    end
    if r.mz then
        for j = 1, #r.mz do r.mz[j]:Hide() end
    end
    -- 数量徽标同步清（2026-10-10）：与热区同一待遇，防行池复用残留旧数量
    if r.mcnt then
        for _, c in pairs(r.mcnt) do
            c:SetText("")
            c:Hide()
        end
    end
    -- ★ 2026-10-09：隐藏之外还要**清文本**。`r.dv`（「商人：X」半段）是唯一
    --   会带着上一页文本活下来的字串 —— 只要将来有任何一条路径把它 Show 出来
    --   而没先 SetText，露出的就是上一页的商人名。清掉是零成本保险。
    if r.dv then r.dv:SetText(""); r.dv:Hide() end
end

-- 摆材料分段链：每段一个字串（第 1 段 = r.f，左锚 PD.MAT_X），每段一格热区压在字串上。
--   热区靠「锚到字串的 TOPLEFT / BOTTOMRIGHT」取尺寸 ⇒ 零量宽。没有物品 id 的段
--   （末尾省略号）不给热区。段间空隙 = 锚点 gap 10（2026-10-10 起不再用前导空格）。
-- 2026-10-10 用户：名称/材料按物品品质着色。DG.QualOf 走 GetItemInfo（零缓存引擎调用），
--   整页重绘会问几百次 ⇒ 会话内正向缓存（nil 不缓存：数据到货后下次重绘自然拿到）。
local _qCache = {}
function PD.QualCached(id)
    if id == nil then return nil end
    local v = _qCache[id]
    if v == nil then
        v = DG.QualOf(id)
        if v ~= nil then _qCache[id] = v end
    end
    return v
end

function PD.PaintMatSegs(r, segs, color)
    local col = color or C_TEXT
    local prev
    for i = 1, #segs do
        local fs = PD.MatSeg(r, i)
        -- 2026-10-10 用户：材料名按材料品质着色（…纯段无 id 保持默认色）
        local scol = col
        if segs[i].id then
            local q = PD.QualCached(segs[i].id)
            if q then scol = { DG.QColor(q) } end
        end
        fs:SetTextColor(Unpack(scol))
        fs:SetText(segs[i].text or "")
        fs:ClearAllPoints()
        if i == 1 then
            fs:SetPoint("LEFT", r, "LEFT", PD.MAT_X, 0)
        else
            fs:SetPoint("LEFT", prev, "RIGHT", 0, 0)   -- 2026-10-10 用户：材料间零间距
        end
        fs:Show()
        prev = fs
        local z = PD.MatZone(r, i)
        if segs[i].id then
            z.__it = { segs[i].id }
            z.__tipLines = nil
            z.__act = nil
            z:ClearAllPoints()
            z:SetPoint("TOPLEFT", fs, "TOPLEFT", 0, 1)
            z:SetPoint("BOTTOMRIGHT", fs, "BOTTOMRIGHT", 0, -1)
            z:Show()
            -- 数量徽标（2026-10-10 用户）：数量压图标右下角，白字 + 黑描边 + 黑阴影；
            --   段文本不带前缀 ⇒ 段左缘即图标左缘，右缘钉在图标右缘内 1px。
            local c = PD.MatCnt(r, i)
            c:SetText(tostring(segs[i].cnt or 1))
            c:ClearAllPoints()
            c:SetPoint("BOTTOMRIGHT", fs, "BOTTOMLEFT", PD.MAT_ICON_PX - 1, 1)
            c:Show()
        else
            z:Hide()
            if r.mcnt and r.mcnt[i] then r.mcnt[i]:Hide() end
        end
    end
end

-- ── 升级路线行：四档技能色阶条 + 来源卡片（2026-10-09 四轮，用户）────────────
-- 四档语义（WoW 专业惯例）：学得(橙/必升) → 黄(大概率) → 绿(小概率) → 灰(不再提升)。
--   ★ 四档**等分**而不是按等级跨度：数据里 learn == yellow 极常见（如 150/150/162/175），
--     按真实跨度画「必升」那档宽度就是 0 —— 会缺一块。等分 + 落点竖线更稳。
PD.SB_H  = 12            -- 色阶条高
PD.SB_DY = -8            -- 色阶条 y（= 原来源行的位置）
PD.SB_FS = 11            -- 段内数字字号
PD.SB_EDGE = 4           -- 交界点数：四段等分 ⇒ 竖线只停 0 / 1/4 / 1/2 / 3/4（见 PD.SBValPos）
PD.CARD_PAD, PD.CARD_GAP = 3, 6   -- 2026-10-09 21:35 用户：卡片再缩小（内边距 4→3，bg 上下留白 ±1、热区 ±2）
PD.LV_CARD_FIXW = 44              -- 来源卡片固定宽兜底（开页 FitRecipeCols 按本页最长卡重算）
PD.SB_COL = {
    { 1.00, 0.50, 0.25 },   -- 1 橙：学得 / 必升
    { 1.00, 0.82, 0.00 },   -- 2 黄：大概率提升
    { 0.25, 0.75, 0.25 },   -- 3 绿：小概率提升
    { 0.55, 0.58, 0.64 },   -- 4 灰：不再提升
}
PD.SB_INK = {
    { 0.10, 0.06, 0.02 },
    { 0.12, 0.09, 0.00 },
    { 0.04, 0.12, 0.03 },
    { 1.00, 1.00, 1.00 },
}
PD.CARD_COL = {
    trainer = { 0.29, 0.33, 0.40 },
    drop    = { 0.42, 0.27, 0.66 },
    vendor  = { 0.54, 0.42, 0.12 },
}
PD.CARD_INK = {
    trainer = { 0.81, 0.85, 0.89 },
    drop    = { 0.91, 0.86, 1.00 },
    vendor  = { 1.00, 0.91, 0.66 },
}

-- 当前技能等级落在第几档（1 橙 / 2 黄 / 3 绿 / 4 灰）；没阈值数据返回 nil。
function PD.LvTier(skill, learn, yellow, green, grey)
    if not skill then return nil end
    if not (learn or yellow or green or grey) then return nil end
    if grey and skill >= grey then return 4 end
    if green and skill >= green then return 3 end
    if yellow and skill >= yellow then return 2 end
    return 1
end

-- 等级 → 条上横坐标比例（0 = 条左缘，1 = 条右缘）；算不出返回 nil。
--   口径：四段等分，**阈值 thr[k] 画在第 k 段的左交界 (k-1)/4**（段内数字仍画正中）。
--   本行技能区间 a–b 的两根竖线**分别向两侧吸附到交界**：
--     · a（起点）**向下吸** —— 吸到**已经跨过**的那道交界（最大的 ≤a 的阈值）。
--     · b（终点）**向上吸** —— 吸到**将要到达**的那道交界（最小的 ≥b 的阈值）。
--   例①（阈值 1/30/45/60，区间 36–45）：a=36 ⇒ 0.25；b=45 ⇒ 0.50。
--   例②（阈值 55/85/100/115，区间 85–106）：a=85 ⇒ 0.25；b=106 ⇒ 0.75（100–115 交界）。
--   ★ 两根都只落在 0 / 0.25 / 0.50 / 0.75 四点上（吸附，不做段内插值）。
--   up = true 走「向上吸」（终点 b）；否则「向下吸」（起点 a）。
function PD.SBValPos(skill, learn, yellow, green, grey, up)
    if not skill or type(learn) ~= "number" then return nil end
    if up then
        local thr = { learn, yellow, green, grey }
        local k = nil
        for j = 1, 4 do
            if type(thr[j]) == "number" and skill <= thr[j] then k = j break end
        end
        if not k then return 0.75 end
        -- 重复阈值（learn == yellow，数据里极常见）⇒ 吸到同一处的**最后一档**，
        -- 否则 150 会吸到第 1 档（0.00）、跑到起点 a 左边 —— 两根线交叉。
        while k < 4 and thr[k + 1] == thr[k] do k = k + 1 end
        return (k - 1) / 4
    end
    local t = PD.LvTier(skill, learn, yellow, green, grey)
    if not t then return nil end
    return (t - 1) / 4
end

-- 摆四档色阶条：条宽 = 名字列宽（PD.LV_NAME_W），四段等分，段内写该档阈值。
--   vals = { learn, yellow, green, grey }；lvLo / lvHi = 本行技能区间两端；
--   dim = 已过段落灰显。两根竖线 = 本行技能区间两端 a–b（见 PD.SBValPos）：
--   a 向下吸到已跨过的交界、b 向上吸到将要到达的交界 —— 只停 0 / 1/4 / 1/2 / 3/4。
function PD.PaintSkillBar(r, vals, lvLo, lvHi, dim)
    local seg = PD.LV_NAME_W / 4
    local a1, a2 = dim and 0.35 or 1, dim and 0.55 or 1
    for k = 1, 4 do
        local bg, tx = r.__sbBg[k], r.__sbTx[k]
        bg:ClearAllPoints()
        bg:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X + (k - 1) * seg, PD.SB_DY)
        bg:SetSize(seg, PD.SB_H)
        bg:SetColorTexture(Unpack(PD.SB_COL[k]))
        bg:SetAlpha(a1)
        bg:Show()
        tx:ClearAllPoints()
        tx:SetPoint("CENTER", bg, "CENTER", 0, 0)
        tx:SetTextColor(Unpack(PD.SB_INK[k]))
        tx:SetAlpha(a2)
        tx:SetText(vals[k] and tostring(vals[k]) or "")
        tx:Show()
    end
    -- 两根竖线：起点 a = lvLo（向下吸）/ 终点 b = lvHi（向上吸），落位走 PD.SBValPos。
    local lvs = { lvLo, lvHi }
    local xa = PD.SBValPos(lvs[1], vals[1], vals[2], vals[3], vals[4], false)
    local xb = PD.SBValPos(lvs[2], vals[1], vals[2], vals[3], vals[4], true)
    -- 数据里极少数行 learn > yellow（阈值非升序，~1%），会把 b 顶到 a 左边 ⇒ 夹住不交叉。
    if xa and xb and xb < xa then xb = xa end
    for k = 1, 2 do
        local p = r.__sbPin[k]
        local x = (k == 1) and xa or xb
        if x then
            p:ClearAllPoints()
            p:SetPoint("CENTER", r, "LEFT", PD.LV_NAME_X + x * PD.LV_NAME_W, PD.SB_DY)
            p:SetSize(2, PD.SB_H + 6)
            p:SetAlpha(dim and 0.35 or 1)
            p:Show()
        else
            p:Hide()
        end
    end
end

function PD.HideSkillBar(r)
    for k = 1, 4 do
        r.__sbBg[k]:Hide()
        r.__sbTx[k]:SetText("")
        r.__sbTx[k]:Hide()
    end
    for k = 1, 2 do r.__sbPin[k]:Hide() end
end

-- 来源卡片（第一列等级正下方）。悬停走 __tipLines 出明细；点击：商人 → 落图，
--   图纸 → 走 Shift 点击发物品链接（__it）。
function PD.PaintCard(r, card)
    local z, bg, tx = r.__cardZone, r.__cardBg, r.__cardTx
    if not card then
        z:Hide()
        bg:Hide()
        tx:SetText("")
        tx:Hide()
        z.__tipLines, z.__act, z.__it = nil, nil, nil
        return
    end
    -- 升级/中间产物标签放在等级范围正下方，宽度按本页最长标签统一。
    local x, w = PD.LV_RNG_X or 6, PD.LV_CARD_FIXW
    tx:ClearAllPoints()
    tx:SetPoint("CENTER", r, "LEFT", x + w / 2, PD.SB_DY)
    local col = PD.CARD_COL[card.kind] or PD.CARD_COL.trainer
    tx:SetTextColor(Unpack(PD.CARD_INK[card.kind] or PD.CARD_INK.trainer))
    tx:SetText(card.text or "")
    tx:Show()
    local th = tx:GetStringHeight()
    if (th or 0) <= 0 then th = 12 end
    local half = math.floor(th / 2) + 1
    bg:ClearAllPoints()
    bg:SetPoint("TOPLEFT", r, "LEFT", x, PD.SB_DY + half)
    bg:SetPoint("BOTTOMRIGHT", r, "LEFT", x + w, PD.SB_DY - half)
    for _, tex in ipairs(bg.__pieces or {}) do
        tex:SetVertexColor(col[1], col[2], col[3])
        tex:SetAlpha(1)
    end
    bg:Show()
    z.__tipLines = card.lines
    z.__act = card.act
    z.__it = card.fid and { card.fid } or nil
    z:ClearAllPoints()
    z:SetPoint("TOPLEFT", r, "LEFT", x, PD.SB_DY + half + 1)
    z:SetPoint("BOTTOMRIGHT", r, "LEFT", x + w, PD.SB_DY - half - 1)
    z:Show()
end

-- 卡片数据：来源只有两条主路径 —— 训练师直教 / 需图纸；图纸再分掉落 / 商人。
-- 训练师直教卡片（模块级常量：内容固定，全表共用一张；悬停口径与「图纸」卡片一致）
local TRAINER_CARD = {
    kind = "trainer", text = L["训练师"],
    lines = { { L["向训练师学习"], 0.81, 0.85, 0.89 } },
}

function PD.CardOf(rec, ri)
    if not rec then
        return (ri and ri.trainer) and TRAINER_CARD or nil
    end
    local fid = rec[13] and rec[13][1]
    if not fid then return TRAINER_CARD end
    local src = rec[14]
    local hasDrop = src and src.drops and #src.drops > 0
    local hasVendor = src and src.vendors and #src.vendors > 0
    local lines = { { format(L["图纸：%s"], DG.ItemName(fid)), 1, 0.82, 0.35 } }
    if hasDrop then
        lines[#lines + 1] = { format(L["掉落 %d 处"], #src.drops), 0.75, 0.75, 0.75 }
        local dl = PD.DropLines(src)
        for i = 1, #dl do lines[#lines + 1] = dl[i] end
    end
    local vl = PD.VendorLines(src)
    for i = 1, #vl do lines[#lines + 1] = vl[i] end
    return {
        kind = hasDrop and "drop" or (hasVendor and "vendor" or "drop"),
        text = L["图纸"], fid = fid, lines = lines,
        act = hasVendor and PD.VendorAct(src) or nil,
    }
end

function PD.RowBlk(r, j)
    local b = r.blk[j]
    if b then return b end
    b = {}
    b.ic = r:CreateTexture(nil, "ARTWORK")
    b.ic:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(b.ic) end
    b.ic:SetSize(PD.TBL_ICON, PD.TBL_ICON)
    b.nm = MakeFS(r, 12, C_TEXT, "LEFT")
    b.ct = MakeFS(r, PD.TBL_MAT_CNT_FS, C_GOLD, "LEFT")
    b.ct:SetFont(ns.FONT, PD.TBL_MAT_CNT_FS, "THICKOUTLINE")
    b.ct:SetShadowColor(0, 0, 0, 1)
    b.ct:SetShadowOffset(1, -1)
    b.nm:SetWordWrap(false)
    b.ct:SetWordWrap(false)
    -- 2026-10-09：材料块自己出一格热区（图标 + 数量角标那一格），悬停出该材料的
    -- 物品提示框。只有升级行会建块（配方页材料是文本列）⇒ 这些帧只服务升级页。
    b.zone = CreateFrame("Button", nil, r)
    b.zone:Hide()
    PD.WireTipZone(b.zone, r)
    r.blk[j] = b
    return b
end

function PD.ClearMats(r)
    for j = 1, #r.blk do
        local b = r.blk[j]
        b.ic:Hide()
        b.nm:Hide()
        b.ct:Hide()
        if b.zone then b.zone:Hide() end
    end
end

-- ── 整行「除内容」（切页时用，2026-10-09） ────────────────────────────────────
-- ★ 为什么不是只 Hide 一下：行帧是**跨页共用**的，内容（材料块 / 分段链 /
--   制作物热区 / 直售徽标 / 新角标）是「上一轮绑过就一直留着」的。只 Hide 行帧，
--   真机里父帧隐藏确实会带走整棵子树；但只要有任何一条路径（分帧补建、同索引
--   复用、第三方皮肤重建）在**没重新 BindRow** 的情况下把行 Show 出来，
--   露出的就是上一页的内容 —— 这正是「材料残留」这个报障的形态。
--   切页时把内容也抹干净 ⇒ 即使被重新 Show，也是一行空白，不会出现「上一页的材料」。
-- ★ 只在**页面身份变化**时调（PD.Render 顶部那道闸），同页重渲零成本。
function PD.WipeRow(r)
    if not r then return end
    r.__spec = nil
    -- ★ 合并成一行写：`df_mut_check.py` 的两条变异锚点钉的是**行首 4 空格 +
    --   单条语句 + 换行**那个字节序列（BindRow 里那一处）。这里若照抄一行
    --   `    PD.ClearMatSegs(r)`，锚点会变成 2 命中 ⇒ 变异检查误报锚点不唯一。
    PD.ClearMats(r); PD.ClearMatSegs(r)
    if r.icon then r.icon:Hide() end
    if r.gic then for _, g in ipairs(r.gic) do g:Hide() end end   -- 采集纯图标池跨页残留
    local iz = r.__iconZone; if iz then iz:Hide() end
    if r.__vs then
        for _, c in ipairs(r.__vs.cards) do c:Hide() end
        for _, z in ipairs(r.__vs.zones) do z:Hide() end
    end
    if r.__pct then r.__pct:Hide() end
    if r.__warn then r.__warn:Hide(); r.__warn.__tipLines = nil end
    if r.sep then r.sep:Hide() end
    if r.tagFs then r.tagFs:Hide() end
    if r.tagBg then r.tagBg:Hide() end
    if r.dv then r.dv:SetText(""); r.dv:Hide() end   -- 商人半段跨页残留（板条箱等无 dval 页会踩）
    -- 2026-10-09 四轮：四档色阶条与来源卡片也要一起收（行池跨页复用）。
    if r.__sbBg then PD.HideSkillBar(r) end
    if r.__cardZone then PD.PaintCard(r, nil) end
    if r.__costZone then r.__costZone:Hide() end
    if r.a then r.a:SetText("") end
    if r.b then r.b:SetText("") end
    if r.c then r.c:SetText("") end
    if r.d then r.d:SetText("") end
    if r.e then r.e:SetText("") end
    r:Hide()
end

function PD.PackMats(list, budget)
    local out, total, n = {}, 0, 0
    if not list or #list == 0 or not budget or budget <= 0 then return out, 0, false end
    for i = 1, #list do
        if n >= PD.TBL_BLK_MAX then break end
        local cnt = list[i][2] or 1
        local w = math.max(PD.TBL_ICON, PD.TextW(format("%d", cnt), PD.TBL_MAT_CNT_FS))
        local step = w + ((n > 0) and PD.TBL_BLK_GAP or 0)
        if total + step + PD.TBL_MARK_W > budget then
            return out, total, true
        end
        total = total + step
        out[#out + 1] = { id = list[i][1], cnt = cnt, w = w }
        n = n + 1
    end
    return out, total, n < #list
end

function PD.PaintMats(r, blocks, cut, grey)
    local n = blocks and #blocks or 0
    -- 2026-10-09 v2：升级页单栏化后行宽 = 整幅（PD.LV_ROW_W 由 RowsLeveling 现算），
    -- 旧值 PD.COL_LW 只是分栏时代的行宽代理，保留作兜底。
    local W = PD.LV_ROW_W or PD.COL_LW
    local right = W - PD.TBL_MAT_RPAD
    if cut then
        local b = PD.RowBlk(r, n + 1)
        b.ic:Hide()
        b.ct:SetText("")
        b.ct:Hide()
        b.nm:SetTextColor(Unpack(grey and C_DIM or C_TEXT))
        b.nm:SetText("…")
        b.nm:ClearAllPoints()
        b.nm:SetPoint("RIGHT", r, "RIGHT", -(W - right), PD.TBL_NAME_DY)
        b.nm:Show()
        b.zone:Hide()
        right = right - PD.TBL_MARK_W - PD.TBL_BLK_GAP
    end
    for k = n, 1, -1 do
        local blk = blocks[k]
        local b = PD.RowBlk(r, k)
        SetIcon(b.ic, DG.ItemIcon(blk.id))
        b.ic:SetDesaturated(grey and true or false)
        b.ic:ClearAllPoints()
        b.ic:SetPoint("RIGHT", r, "RIGHT", -(W - right), 0)
        b.nm:Hide()
        b.ct:SetTextColor(Unpack(grey and C_DIM or C_GOLD))
        b.ct:SetText(format("%d", blk.cnt))
        b.ct:ClearAllPoints()
        b.ct:SetPoint("RIGHT", r, "RIGHT", -(W - right), PD.TBL_MAT_CNT_DY)
        b.zone.__it = { blk.id }
        b.zone:ClearAllPoints()
        b.zone:SetPoint("RIGHT", r, "RIGHT", -(W - right), 0)
        b.zone:SetSize(PD.TBL_ICON, PD.TBL_ICON)
        b.ic:Show(); b.ct:Show(); b.zone:Show()
        right = right - blk.w - PD.TBL_BLK_GAP
    end
    for k = n + (cut and 1 or 0) + 1, #r.blk do
        local b = r.blk[k]
        b.ic:Hide(); b.nm:Hide(); b.ct:Hide(); b.zone:Hide()
    end
end

function PD.LevelSrc(rec)
    if not rec then return nil, nil end
    local src = rec[14]
    local fid = rec[13] and rec[13][1]
    if not fid then return L["向训练师学习"], nil end
    local detail
    if src and src.drops and #src.drops > 0 then
        detail = format(L["图纸：%s · 掉落 %d 处"], DG.ItemName(fid), #src.drops)
    end
    return L["需图纸 · 商人出售"], detail
end

-- 来源拆段：与 SourceText 同序、同「 · 」分隔，但把「商人：X」单独标出来（vendor = true）。
--   2026-10-09 配方页要给「商人」那一段单开热区（用户：「如果鼠标在商人上面，就显示
--   点击定位在地图上标记商人位置」）—— 量宽会漂，所以靠**锚点链**把商人那半拆到 r.dv，
--   热区直接盖 r.dv，位置由引擎算。
--   ★ 顺序铁律：skill → drops → vendors，商人**恒为最后一段**，拆段链就吃这一点。
function PD.SourceParts(s)
    local out = {}
    if not s then return out end
    if s.skill then out[#out + 1] = { text = format(L["技能 %s"], tostring(s.skill)) } end
    if s.drops and #s.drops > 0 then
        out[#out + 1] = { text = format(L["掉落 %d 处"], #s.drops) }
    end
    if s.vendors and #s.vendors > 0 then
        local vs = PD.VendorListOf(s)
        if #vs > 1 then
            out[#out + 1] = { text = format(L["商人：%s 等 %d 人"], (vs[1] and vs[1].name) or "?", #vs), vendor = true }
        elseif #vs == 1 then
            local v = vs[1]
            out[#out + 1] = { text = format(L["商人：%s"], (v and v.name) or "?"), vendor = true }
        end
    end
    return out
end

function PD.SourceText(s)
    local p = PD.SourceParts(s)
    if #p == 0 then return nil end
    local t = {}
    for i = 1, #p do t[i] = p[i].text end
    return table.concat(t, " · ")
end

-- 商人出售的来源 → tooltip 里的商人明细行（名字已随语言本地化，区域为中文串）。
--   返回 lines 追加内容；可定位时末行是「点击标记」提示。
function PD.VendorLines(s)
    local out = {}
    if not (s and s.vendors and #s.vendors > 0) then return out end
    local vs = PD.VendorListOf(s)
    if #vs == 0 then return out end
    for i = 1, #vs do
        local v = vs[i]
        if v and (v.name or v.zone) then
            local nm = format(L["商人：%s"], tostring(v.name or "?"))
            if v.zone and v.zone ~= "" then nm = nm .. " · " .. tostring(v.zone) end
            out[#out + 1] = { nm, 0.75, 0.75, 0.75 }
        end
    end
    local loc = PD.VendorLocOf(s)
    if loc then
        out[#out + 1] = { L["点击：在地图上标记该 NPC"], 1, 0.82, 0 }
    end
    return out
end

function PD.DropLines(s)
    local out = {}
    if not (s and s.drops and #s.drops > 0) then return out end
    for i = 1, #s.drops do
        local dd = s.drops[i]
        if dd and (dd.npc or dd.zone) then
            local nm = format(L["掉落：%s"], tostring(dd.npc or "?"))
            if dd.zone and dd.zone ~= "" then nm = nm .. " · " .. tostring(dd.zone) end
            out[#out + 1] = { nm, 0.75, 0.75, 0.75 }
        end
    end
    return out
end

-- 可定位商人条目（阵营过滤后）：弹窗与直落共用 —— { { loc, name, zone }, ... }
function PD.VendorEntries(s)
    local out = {}
    local vs = PD.VendorListOf(s)
    for i = 1, #vs do
        local v = vs[i]
        if v.id and ns.ProfVendors and ns.ProfVendors[v.id] then
            out[#out + 1] = { loc = ns.ProfVendors[v.id], name = v.name, zone = v.zone }
        end
    end
    return out
end

-- 商人行的点击动作：可定位 0 人 → 提示「暂未收录」；1 人 → 直接落图（老行为）；
--   多人 → 弹选择窗（2026-10-10 用户：点谁标谁），同一热区再点一次 = 收起。
function PD.VendorAct(s)
    return function(zone)
        local ents = PD.VendorEntries(s)
        if #ents == 0 then
            PD.MarkVendorLoc(nil)
        elseif #ents == 1 then
            PD.HideVendorPick()
            PD.MarkVendorLoc(ents[1].loc)
        else
            PD.VendorPickToggle(zone, ents)
        end
    end
end

function PD.DropEntries(s)
    local out = {}
    if not (s and s.drops) then return out end
    for _, dd in ipairs(s.drops) do
        local locs = dd.id and ns.ProfNPCLocs and ns.ProfNPCLocs[dd.id] or nil
        if locs then
            for _, loc in ipairs(locs) do
                out[#out + 1] = {
                    loc = loc,
                    name = tostring(dd.npc or "?"),
                    zone = PD.CampZoneName(loc[1], tostring(dd.zone or "")),
                }
            end
        end
    end
    return out
end

function PD.DropAct(s)
    return function(zone)
        local ents = PD.DropEntries(s)
        if #ents == 0 then
            PD.MarkVendorLoc(nil)
        elseif #ents == 1 then
            PD.HideVendorPick()
            PD.MarkVendorLoc(ents[1].loc)
        else
            PD.HideVendorPick()
            PD.VendorPickToggle(zone, ents, L["选择要标记的 NPC"])
        end
    end
end

function PD.DropLines(s)
    local out = {}
    if not (s and s.drops and #s.drops > 0) then return out end
    for i = 1, math.min(#s.drops, 8) do
        local dd = s.drops[i]
        if dd and (dd.npc or dd.zone) then
            local nm = format(L["掉落：%s"], tostring(dd.npc or "?"))
            if dd.zone and dd.zone ~= "" then nm = nm .. " · " .. tostring(dd.zone) end
            if dd.chance then
                nm = nm .. format(L[" · %d%%"], math.floor(dd.chance * 100 + 0.5))
            end
            out[#out + 1] = { nm, 0.75, 0.75, 0.75 }
        end
    end
    if #s.drops > 8 then
        out[#out + 1] = { format(L["…等 %d 处"], #s.drops), 0.6, 0.6, 0.6 }
    end
    if #PD.DropEntries(s) > 0 then
        out[#out + 1] = { L["点击：在地图上标记该 NPC"], 1, 0.82, 0 }
    end
    return out
end

-- ── 商人选择弹窗（单例懒建）────────────────────────────────────────────
--   父 = PD.page（不进滚动子帧：滚轮 / 换页 / 收窗统一 Hide 兜位）；
--   点关盾 = 弹窗开着时全页挡一层（层级钉弹窗下 1），点它收窗 / 滚轮收窗+滚页（2026-10-10 用户）；
--   锚 = 被点热区的 BOTTOMRIGHT —— 热区本就贴行右缘，弹窗往左下伸展不溢卡；
--   行悬停 = BuildCapsule 胶囊（与总览卡同款），点击 = 落图 + 收起。
local PICK_W, PICK_ROW_H, PICK_GAP, PICK_PAD = 210, 24, 2, 6

function PD.HideVendorPick()
    local pick = PD.vendorPick
    if not pick then return end
    if pick:IsShown() then pick:Hide() end
    if pick.__shield then pick.__shield:Hide() end
end

function PD.VendorPickToggle(zone, ents, title)
    local pick = PD.vendorPick
    if pick and pick:IsShown() and pick.__zone == zone then
        pick:Hide()
        return
    end
    if not (ns.hui and ns.hui.layer and ns.hui.BuildRoundedBG) then
        -- 无主题兜底：不裸建窗，退回直落第一个（老行为）
        PD.MarkVendorLoc(ents[1].loc)
        return
    end
    if not pick then
        pick = CreateFrame("Button", nil, PD.page, "BackdropTemplate")
        pick:EnableMouse(true)
        pick:SetFrameLevel(515)
        -- 点关盾（2026-10-10 用户：点别处 / 滚轮自动收窗）：弹窗开着时全页挡一层，
        --   点它 = 收窗；滚轮 = 收窗 + 照常滚页。层级在 Show 时钉到弹窗正下方
        --   （forever 引擎同层次序不可靠 ⇒ 显式 SetFrameLevel，不赌创建次序）。
        --   收窗时随弹窗一起 Hide ⇒ 平时不挡任何交互（行热区/页签照常）。
        local shield = CreateFrame("Frame", nil, PD.page)
        shield:EnableMouse(true)
        shield:EnableMouseWheel(true)
        shield:SetAllPoints(PD.page)
        shield:SetScript("OnMouseDown", function() PD.HideVendorPick() end)
        shield:SetScript("OnMouseWheel", function(self, delta)
            PD.HideVendorPick()
            DG.WheelScroll(PD.scroll, PD.child, delta)
        end)
        pick.__shield = shield
        ns.hui.BuildRoundedBG(pick, 6, ns.hui.layer.L3, "both", true, 1)
        pick.title = MakeFS(pick, 11, C_GOLD, "LEFT")
        pick.title:SetPoint("TOPLEFT", pick, "TOPLEFT", PICK_PAD + 4, -PICK_PAD)
        pick.__rows = {}
        PD.vendorPick = pick
    end
    local rows = pick.__rows
    for k = 1, #ents do
        local e = ents[k]
        local r = rows[k]
        if not r then
            r = CreateFrame("Button", nil, pick, "BackdropTemplate")
            r:SetHeight(PICK_ROW_H)
            r.txt = MakeFS(r, 11, C_TEXT, "LEFT")
            r.txt:SetWordWrap(false)
            r.txt:SetPoint("LEFT", r, "LEFT", 6, 0)
            r.txt:SetPoint("RIGHT", r, "RIGHT", -6, 0)
            if ns.hui.BuildCapsule then
                r.__hov = ns.hui.BuildCapsule(r, 4, ns.hui.layer.L5, 0, 2)
                for _, ht in ipairs(r.__hov) do ht:Hide() end
            end
            r:SetScript("OnEnter", function(self)
                if self.__hov then
                    for _, ht in ipairs(self.__hov) do ht:Show() end
                end
            end)
            r:SetScript("OnLeave", function(self)
                if self.__hov then
                    for _, ht in ipairs(self.__hov) do ht:Hide() end
                end
            end)
            rows[k] = r
        end
        r.txt:SetText(e.zone and e.zone ~= ""
                      and (tostring(e.name or "?") .. " · " .. tostring(e.zone))
                      or tostring(e.name or "?"))
        r:SetScript("OnClick", function()
            PD.HideVendorPick()
            PD.MarkVendorLoc(e.loc)
        end)
        r:ClearAllPoints()
        if k == 1 then
            r:SetPoint("TOPLEFT", pick, "TOPLEFT", PICK_PAD, -(PICK_PAD + 18))
        else
            r:SetPoint("TOPLEFT", rows[k - 1], "BOTTOMLEFT", 0, -PICK_GAP)
        end
        r:SetPoint("RIGHT", pick, "RIGHT", -PICK_PAD, 0)
        r:Show()
    end
    for k = #ents + 1, #rows do
        rows[k]:Hide()
    end
    pick:SetWidth(PICK_W)
    pick:SetHeight(PICK_PAD + 18 + #ents * PICK_ROW_H + (#ents - 1) * PICK_GAP + PICK_PAD)
    pick.title:SetText(title or L["选择要标记的商人"])
    pick:ClearAllPoints()
    pick:SetPoint("TOPRIGHT", zone, "BOTTOMRIGHT", 0, -4)
    if pick.__shield then
        pick.__shield:SetFrameLevel(pick:GetFrameLevel() - 1)
        pick.__shield:Show()
    end
    pick:Show()
end

-- The catalogue remains browsable without learning/opening a profession. Only
-- fields actually returned by the client replace its reference information.
function PD.RecipeData(row, kind, slug)
    local E = ns.ProfEconomy
    if E and E.Normalize then
        local resolved = E.Normalize(row, slug or PD.cur, kind or "rows")
        if resolved then return resolved end
    end
    local r
    if kind == "enchants" then
        r = {spell=row[14], item=row[15], count=1, mats=row[9], learn=row[5], yellow=row[6], green=row[7], grey=row[8]}
    elseif kind == "crafted" then
        r = {spell=row[1], item=row[2], count=row[3], mats=row[8], learn=row[4], yellow=row[5], green=row[6], grey=row[7]}
    else
        r = {spell=row[1], item=row[2], count=row[3], mats=row[12], learn=row[7], yellow=row[8], green=row[9], grey=row[10]}
    end
    if E and E.ResolveRecipe then return E.ResolveRecipe(r, slug or PD.cur) end
    r.dataSource = "catalogue"
    r.clientPending = type(r.mats) ~= "table" or (r.item and not r.count)
    return r
end

function PD.RecipeSourceText(r, short)
    if r and r.clientUnavailable then return L["客户端已确认不可用"] end
    local source = r and r.dataSource
    if source == "client" then return L["客户端数据"] end
    if source == "mixed" then return L["客户端与参考资料"] end
    return short and L["参考资料"] or L["参考资料；客户端尚未核验"]
end

function PD.RecipeOutputText(r)
    local lo, hi = r and tonumber(r.outputMin), r and tonumber(r.outputMax)
    if r and r.variableOutput and lo and hi and lo > 0 and hi > lo then
        return format(L["每次产量：%d–%d；按最低产量计算，实际多产可减少后续材料需求。"], lo, hi)
    end
    if r and r.variableOutput and r.outputBasis=="reference" then
        return format(L["随机产量范围暂未读取；按已有资料每次 %d 件估算。"], r.count or r[3] or 1)
    end
end

function PD.RecipeSourceLines(lines, r)
    lines = lines or {}
    lines[#lines + 1] = {PD.RecipeSourceText(r), 0.65, 0.75, 0.85}
    if r and r.clientUnavailable then
        lines[#lines + 1] = {L["此记录仅供查阅，不参与自动路线。"], 0.95, 0.75, 0.4}
    end
    local output = PD.RecipeOutputText(r)
    if output then lines[#lines + 1] = {output, 0.65, 0.75, 0.85} end
    return lines
end

function PD.RecipeVisible(spell, slug)
    local E = ns.ProfEconomy
    if E and E.ResolveRecipe then
        local resolved = E.ResolveRecipe({spell=spell}, slug or PD.cur)
        return not resolved.clientUnavailable
    end
    return true
end

function PD.EnchantSpec(en)
    local resolved = PD.RecipeData(en, "enchants")
    local original = en
    en = {}; for key, value in pairs(original) do en[key] = value end
    en[9] = resolved.mats
    if resolved.item then en[15] = resolved.item end
    en[5], en[6], en[7], en[8] = resolved.learn, resolved.yellow, resolved.green, resolved.grey
    local clientPending = resolved.clientPending
    local matCol, _, _, matSg = PD.MatCol(en[9], PD.MAT_FS, PD.MAT_W)
    local costStr, total, unpriced, ah
    if en[9] and #en[9] > 0 then
        total, unpriced = RA.MatListCost(en[9])
        if total <= 0 or unpriced >= #en[9] then
            costStr = "—"
        else
            costStr = (unpriced > 0 and "≈" or "") .. RA.MoneyStr(total, "copper")
        end
    end
    local ahStr
    if en[15] then
        ah = RA.AHPriceOf and RA.AHPriceOf(en[15])
        ahStr = ah and RA.MoneyStr(ah, "copper") or "—"
    else
        ahStr = "—"
    end
    local spec
    if en[13] and #en[13] > 0 then
        local t = {}
        for _, b in ipairs(en[13]) do t[#t + 1] = b[3] or "" end
        spec = table.concat(t, " / ")
    end
    local vsEn = (en[10] and PD.VendorListOf(en[10])) or {}
    local hasVendor = #vsEn > 0
    local drEn = (en[10] and en[10].drops) or {}
    local base = en[10] and L["图纸"] or L["训练师"]
    local dpre, dval, dact, vlines
    if hasVendor then
        dpre = base
        if #vsEn > 1 then
            dval = format(L["商人：%s 等 %d 人"], tostring(vsEn[1] and vsEn[1].name or "?"), #vsEn)
        else
            dval = format(L["商人：%s"], tostring(vsEn[1] and vsEn[1].name or "?"))
        end
        dact = PD.VendorAct(en[10])
        vlines = PD.VendorLines(en[10])
    elseif #drEn > 0 then
        dpre = base
        dval = format(L["掉落 %d 处"], #drEn)
        dact = PD.DropAct(en[10])
        vlines = PD.DropLines(en[10])
    end
    local lines = PD.RecipeSourceLines({ { en[1] or "" } }, resolved)
    if en[4] and en[4] ~= "" then lines[#lines + 1] = { en[4] } end
    if en[10] then lines[#lines + 1] = { PD.SourceText(en[10]) or "", 0.7, 0.7, 0.7 } end
    if vlines then
        for _, ln in ipairs(vlines) do lines[#lines + 1] = ln end
    end
    if en[9] and #en[9] > 0 then
        lines[#lines + 1] = { format(L["材料：%s"], PD.MatText(en[9])), 0.7, 0.7, 0.7 }
    end
    if spec then lines[#lines + 1] = { format(L["适用：%s"], spec), 0.6, 0.9, 0.6 } end
    return {
        kind = "row", is_new = en[11], _mats = en[9],
        icon = SpellIcon(en[14]),
        qItem = (type(en[15]) == "number") and en[15] or nil,
        text = en[2] or en[1] or "?",
        sub = table.concat({ tostring(en[3] or ""), tostring(en[4] or ""),
                             spec or "" }, " · "),
        mats = clientPending and L["客户端数据待读取"] or matCol,
        matSegs = matSg,
        right = not (en[5] or en[6] or en[7] or en[8])
                and format("%s · %s", format(L["学 %s"], tostring(en[5])),
                           PD.TierText(en[6], en[7], en[8])) or nil,
        right2 = clientPending and L["客户端数据待读取"] or ((not dval) and (base .. " · " .. PD.RecipeSourceText(resolved, true)) or nil),
        src = en[10],
        dpre = dpre,
        dval = dval,
        dact = dact,
        vlines = vlines,
        costStr = costStr,
        ahStr = ahStr,
        pct = PD.AhPct(ah, total),
        ahVal = ah,
        costVal = total,
        diffVal = tonumber(en[5]),
        gapVal = (ah and total) and (ah - total) or nil,
        sbdiff = (en[5] or en[6] or en[7] or en[8]) and { en[5], en[6], en[7], en[8] } or nil,
        tipExtra = ((type(en[15]) == "number") and en[15])
                   and function() return PD.RecipeSourceLines(PD.PriceTipLines(en[15], en[9]), resolved) end or nil,
        lines = lines,
        act = dact,
    }
end

-- ---- 配方搜索（2026-10-09）：按配方名 / 副行 / 材料名过滤当前列表 ----
function PD.SearchReserve()
    if PD.tab == "recipe" and not PD.setOpen then return PD.SEARCH_RESERVED end
    return 0
end

function PD.SearchHit(s)
    local q = PD.searchQ
    if not q or q == "" then return true end
    local name = tostring(s.text or "")
    if name ~= "" and string.find(string.lower(name), q, 1, true) then return true end
    local sub = tostring(s.sub or "")
    if sub ~= "" and string.find(string.lower(sub), q, 1, true) then return true end
    for _, m in ipairs(s._mats or {}) do
        local nm = tostring(PD.ItemName(m[1]) or "")
        if nm ~= "" and string.find(string.lower(nm), q, 1, true) then return true end
    end
    return false
end

function PD.SearchFilter(list)
    local q = PD.searchQ
    if not q or q == "" then return list end
    local f = {}
    for _, s in ipairs(list) do
        if PD.SearchHit(s) then f[#f + 1] = s end
    end
    return f
end

-- 名称列按本页现算：量出本页最宽名称 / 副行，名称列只留放得下的宽度，剩余全给材料列
-- ★★ 第十刀（rev16）：材料串**按需算**。
--   实机把「数据 20.8ms」一元分解成 扫描 7.6 + 建spec 3.3 + 列宽材料 9.8，
--   而「材料串 9.1ms」整个包在「列宽材料」里 ⇒ FitRecipeCols 那 300 行里
--   93% 的时间掉在**本帧根本画不到**的行上（列表封顶 300 条，本帧只同步绑
--   首屏那几十行，其余交分帧器补齐）。材料串完全可以等**真被绑上前**再算：
--   列宽（PD.MAT_W）在 FitRecipeCols 里已定稿、此后不变，两条路径用的是
--   同一个值 ⇒ 结果逐字节一致，变的只是「哪一帧出这笔钱」。
function PD.FinishSpecMats(s)
    if s and s._mats then
        s._matsPending = nil
        -- ★ PD.MatCol 返回 (col, w, n, segs)：segs 是**第 4 个**返回值。
        --   写成 `local sg` + `s.mats, sg = ...` 会把第 2 个（数字 w）当成
        --   matSegs 传进 PD.PaintMatSegs ⇒ 「attempt to get length of
        --   local 'segs' (a number value)」，配方页整页崩。
        local sg
        s.mats, _, _, sg = PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)
        s.matSegs = sg
    end
    return s
end

function PD.FitRecipeCols(list, maxW)
    -- ★ maxW 可由调用方传入（PD.ScanRecipe 的轻量全量扫描）—— 那一趟不建 spec，
    --   口径与本函数逐条量完全一致（同样只量名称 / 副行 / 新角标）。不传则自扫兜底。
    if maxW == nil then
        maxW = 0
        for _, s in ipairs(list) do
            local w = PD.TextW(s.text or "", 13)
            -- 2026-10-10 用户：角标迁副行 ⇒ 角标宽记到副行一侧（名称行不再背 26px）
            local sw = PD.TextW(s.sub or "", 11) + (s.is_new and PD.RECIPE_BADGE_W or 0)
            if sw > w then w = sw end
            if w > maxW then maxW = w end
        end
    end
    local nameW = math.floor(math.max(PD.RECIPE_NAME_MIN,
                   math.min(PD.RECIPE_NAME_MAX, maxW + 6)))
    PD.RECIPE_NAME_W = nameW
    PD.MAT_X = nameW + PD.RECIPE_NAME_PAD
    -- 2026-10-10 用户：右三列互相**零间距**（列与列不留缝），材料列吃满全部差值；
    --   右保留 = 难度条 + 拍卖列 + 成本列 + 右缘 6
    PD.MAT_W = PD.MAT_ROW_W - (6 + PD.DiffBarW() + PD.REC_AH_W + PD.REC_COST_W) - PD.MAT_X - 8
    -- ★★ 第十刀（rev16）：「材料串」是这一页最贵的一笔单点（实机 9.1ms / 300 行），
    --   而本帧只同步绑首屏那几十行（PD.SyncRows）⇒ 只给它们现算，其余挂待算标，
    --   等 PD.BindRow 真绑到它时再用同一个 PD.MAT_W 补算（见 PD.FinishSpecMats）。
    local keep = PD.SyncRows()
    local idx = 0
    for _, s in ipairs(list) do
        idx = idx + 1
        if s._mats then
            if idx <= keep then
                PD.FinishSpecMats(s)
            else
                s._matsPending = true
            end
        end
        -- 2026-10-10 用户（二轮）：PAD 44→16 后预算改双口径 —— 通常随列宽（MAT_X-8-32）；
        --   名称列被 MIN/MAX 钳住的页退回 nameW-6，短名页不因压缩新增截断。
        --   角标已迁副行 ⇒ 不再扣 BADGE_W（实机字宽 ≈ 估宽 0.85，留有余量不压材料列）。
        if s.text and s.text ~= "" then
            s.text = PD.Fit(s.text, 13, math.max(PD.MAT_X - 8 - PD.RECIPE_PADL,
                                                 (PD.RECIPE_NAME_W or 0) - 6))
        end
    end
end

-- ── 配方页难度四段色条（2026-10-10 用户）─────────────────────────────────────
--   四段 = 学(橙) / 黄 / 绿 / 灰 阈值色阶（复用升级页 SB_COL 色板）；
--   ★ 段宽恒定按三位数（"000"）量宽 —— 「难度条宽度永远一致以三位数为主」，
--     否则 1 位数和 3 位数的行条宽不一，右缘对不齐。
--   2026-10-10 用户：每段再压缩（内衬 10→3），省出的宽度让给材料列。
local function DiffSegW()
    return (PD.TextW and PD.TextW("000", PD.SB_FS) or 24) + 3
end
function PD.DiffBarW()
    return DiffSegW() * 4 + 6
end

-- 行右上角画四段色阶条（vals = {学, 黄, 绿, 灰}）。段帧惰性建（配方行不一定都画）。
function PD.PaintDiffBar(r, vals)
    if not vals then
        if r.__dbBg then
            for k = 1, 4 do r.__dbBg[k]:Hide() r.__dbTx[k]:Hide() end
        end
        return
    end
    r.__dbBg = r.__dbBg or {}
    r.__dbTx = r.__dbTx or {}
    local seg = DiffSegW()
    local col = PD.SB_COL or { { 1, .5, .2 }, { 1, .9, .2 }, { .4, 1, .3 }, { .55, .55, .55 } }
    local ink = PD.SB_INK or { { 0, 0, 0 }, { 0, 0, 0 }, { 0, 0, 0 }, { 1, 1, 1 } }
    local right = 6
    for k = 4, 1, -1 do                       -- 从右往左落位（右缘贴死，向左延伸）
        local bg = r.__dbBg[k]
        if not bg then
            bg = r:CreateTexture(nil, "ARTWORK")
            bg:SetColorTexture(1, 1, 1, 1)
            bg:Hide()
            r.__dbBg[k] = bg
            local tx = MakeFS(r, PD.SB_FS, C_WHITE, "CENTER")
            tx:SetText("")
            tx:SetWordWrap(false)
            tx:Hide()
            r.__dbTx[k] = tx
        end
        bg:ClearAllPoints()
        -- 2026-10-10 用户：双行配奉行 → 色条锚右上角（顶 -4，与右上列同位带），
        --   不放行垂直中线 —— 中线正好压住右下来源行文字
        bg:SetPoint("TOPRIGHT", r, "TOPRIGHT", -right, -4)
        bg:SetSize(seg, PD.SB_H)
        bg:SetColorTexture(col[k][1], col[k][2], col[k][3], 0.95)
        bg:Show()
        local tx = r.__dbTx[k]
        tx:ClearAllPoints()
        tx:SetPoint("CENTER", bg, "CENTER", 0, 0)
        tx:SetTextColor(ink[k][1], ink[k][2], ink[k][3])
        tx:SetText(vals[k] and tostring(vals[k]) or "")
        tx:Show()
        right = right + seg
    end
end

-- ── 提示框价格段（2026-10-10 用户）：悬停配方行 → 物品提示框底部追加五行 ──
--   拍卖: AH单价 ／ 卖店: NPC卖店价 ／ 成本: 材料合计 ／ 差价: 拍卖−成本 ／
--   AH5%: floor(拍卖×0.95)−成本（扣佣净利）。
--   ★ 惰性（悬停那一刻才算，RA 内部会话内缓存重复悬停零开销）；负值整行红。
local TIP_RED = { 1, 0.3, 0.25 }
function PD.PriceTipLines(itemID, mats)
    local lines = {}
    if not itemID then return lines end
    local ah = RA.AHPriceOf and RA.AHPriceOf(itemID) or nil
    local sell = RA.NPCSellPriceOf and RA.NPCSellPriceOf(itemID) or nil
    local cost, unpriced, nMats
    if mats and #mats > 0 then
        cost, unpriced = RA.MatListCost(mats)
        nMats = #mats
    end
    lines[#lines + 1] = { format(L["拍卖: %s"], ah and RA.MoneyStr(ah, "copper") or "—") }
    lines[#lines + 1] = { format(L["卖店: %s"], sell and RA.MoneyStr(sell, "copper") or "—") }
    local costTxt = "—"
    local approx = false
    if cost and nMats then
        if cost <= 0 or unpriced >= nMats then
            costTxt = "—"
        else
            approx = unpriced > 0
            costTxt = (approx and "≈" or "") .. RA.MoneyStr(cost, "copper")
        end
    end
    lines[#lines + 1] = { format(L["成本: %s"], costTxt) }
    -- 差价 / AH5%：拍卖价与成本都可算才出（部分无价带 ≈ 前缀）；负值整行红
    if ah and cost and nMats and cost > 0 then
        local pre = approx and "≈" or ""
        local diff = ah - cost
        local net = math.floor(ah * 0.95) - cost
        local l4 = format(L["差价: %s"], pre .. RA.MoneyStr(diff, "copper"))
        local l5 = format(L["AH5%%: %s"], pre .. RA.MoneyStr(net, "copper"))
        if diff < 0 then
            lines[#lines + 1] = { l4, unpack(TIP_RED) }
        else
            lines[#lines + 1] = { l4 }
        end
        if net < 0 then
            lines[#lines + 1] = { l5, unpack(TIP_RED) }
        else
            lines[#lines + 1] = { l5 }
        end
    end
    return lines
end

local AH_PCT_RED = { 1, 0.32, 0.28 }
local AH_PCT_GREEN = { 0.36, 0.85, 0.55 }
function PD.AhPct(ah, cost)
    if not ah or not cost or cost <= 0 then return nil end
    local v = math.floor((ah - cost) / cost * 100 + 0.5)
    if v == 0 then return { text = "0%", color = { 0.75, 0.75, 0.75 } } end
    if v > 0 then return { text = "+" .. v .. "%", color = AH_PCT_RED } end
    return { text = tostring(v) .. "%", color = AH_PCT_GREEN }
end

PD.KIT_STAT_PATS = {
    { "Stamina value by (%d+)", "耐力" },
    { "Spell Power value by (%d+)", "法术强度" },
    { "Attack Power value by (%d+)", "攻击强度" },
    { "Defense Skill by (%d+)", "防御技能" },
    { "[Aa]rmor value by (%d+)", "护甲" },
    { "defense value.-by (%d+)", "防御技能" },
}
function PD.KitSub(sub, desc)
    if not sub or not sub:find("^永久附着") then return sub end
    local found = {}
    if desc and desc ~= "" then
        for _, it in ipairs(PD.KIT_STAT_PATS) do
            local v = desc:match(it[1])
            if v then
                found[#found + 1] = { pos = desc:find(it[1]), txt = L[it[2]] .. "+" .. v }
            end
        end
    end
    if #found == 0 then return sub end
    table.sort(found, function(a, b) return a.pos < b.pos end)
    local parts = {}
    local lv = sub:match("，(%d+)%s*[级級]")
    if lv then parts[#parts + 1] = format(L["要求%d级"], tonumber(lv)) end
    for _, f in ipairs(found) do parts[#parts + 1] = f.txt end
    return table.concat(parts, " ")
end

function PD.RecipeSpec(r)
    local catalogue = r
    local meta = ns.ProfRecipeMeta and ns.ProfRecipeMeta[r[1]]
    local runtime = ns.ProfRecipeRuntime and ns.ProfRecipeRuntime[r[1]]
    local resolved = PD.RecipeData(r, "rows")
    r = {}
    for key, value in pairs(catalogue) do r[key] = value end
    r[2], r[3], r[12] = resolved.item, resolved.count, resolved.mats
    r[7], r[8], r[9], r[10] = resolved.learn, resolved.yellow, resolved.green, resolved.grey
    local clientPending = resolved.clientPending
    local station = meta and ({ forge = L["熔炉"], blackForge = L["黑铁熔炉"], moltenFoundry = L["熔火铸造厂"] })[meta.station]
    -- 2026-10-10 用户：商人按玩家阵营过滤后显示（多人时「X 等 N 人」）
    local vs = (r[14] and PD.VendorListOf(r[14])) or {}
    local hasVendor = #vs > 0
    -- 2026-10-09 20:45 终版（b0272ae）：右下来源行简化 —— 前缀只有「图纸/训练师」，
    --   有商人时 dval="商人：X"（BindRow 锚链 + r.dv 热区照旧）；
    --   删掉旧版 SourceParts 拼接（技能/掉落前缀与色条、base 串叠印）。
    local base = clientPending and L["客户端数据待读取"] or (r[13] and L["图纸"] or L["训练师"])
    base = base .. " · " .. PD.RecipeSourceText(resolved, true)
    local dpre, dval
    if hasVendor then
        dpre = base
        if #vs > 1 then
            dval = format(L["商人：%s 等 %d 人"], tostring(vs[1] and vs[1].name or "?"), #vs)
        else
            dval = format(L["商人：%s"], tostring(vs[1] and vs[1].name or "?"))
        end
    end
    -- 2026-10-10 用户：「制作成本」列（铜级精度；口径与提示框成本行一致）
    local costStr, total, unpriced, ah
    if r[12] and #r[12] > 0 then
        total, unpriced = RA.MatListCost(r[12])
        if total <= 0 or unpriced >= #r[12] then
            costStr = "—"
        else
            costStr = (unpriced > 0 and "≈" or "") .. RA.MoneyStr(total, "copper")
        end
    end
    -- 2026-10-10 用户：「拍卖」列 = 产物拍卖行单价（RA.AHPriceOf 会话内缓存；取不到 —）
    local ahStr
    if r[2] and RA.AHPriceOf then
        ah = RA.AHPriceOf(r[2])
        ahStr = ah and RA.MoneyStr(ah, "copper") or "—"
    end
    return {
        kind = "row", is_new = r[11], it = { r[2] }, qItem = r[2], row = r, _mats = r[12],
        text = PD.ItemName(r[2]),
        -- 2026-10-10 提示框价格段：惰性挂函数（悬停那一刻才算价，数据迟到重悬停即见）
        tipExtra = function()
            local lines = PD.RecipeSourceLines(PD.PriceTipLines(r[2], r[12]), resolved)
            if station then lines[#lines + 1] = { format(L["制作场地：%s"], station), 0.7, 0.7, 0.7 } end
            if clientPending then lines[#lines + 1] = { L["请打开对应专业面板读取数据"], 0.95, 0.75, 0.4 } end
            if meta and meta.outputConflict and resolved.outputConflict and not (runtime and runtime.count) then
                lines[#lines + 1] = { L["参考产量存在冲突；当前按目录值显示，客户端读取后覆盖。"], 0.95, 0.75, 0.4 }
                lines[#lines + 1] = { format(L["目录产量 %d · 法术详情产量 %d"], meta.listedCount, meta.detailCount), 0.7, 0.7, 0.7 }
            elseif runtime and runtime.count and not resolved.variableOutput then
                lines[#lines + 1] = { format(L["客户端每次产量：%d"], runtime.count), 0.55, 0.85, 0.6 }
            end
            if meta and meta.availabilityUnknown and not resolved.clientAvailable then lines[#lines + 1] = { L["学习方式尚未确认；已学习后才参与计算。"], 0.95, 0.75, 0.4 } end
            return lines
        end,
        sub = station or PD.KitSub(tostring(r[5] or ""), r[6]),
        -- ★ mats 不在这里算（2026-10-09 第二轮）：紧随其后的 PD.FitRecipeCols 会用
        --   **定稿列宽**把 s.mats 整个重算一遍，这里那次是纯白做（每条一次材料串
        --   重排 = 材料个数 × 数次逐字符量宽）。
        mats = clientPending and L["客户端数据待读取"] or nil,
        -- 2026-10-09 20:14：有阈值行（sbdiff）难度全交色条 → right 置 nil 防叠印；
        --   无阈值行保持原文字兜底
        right = not ((r[7] or r[8] or r[9] or r[10]))
                and format("%s · %s", format(L["学 %s"], tostring(r[7])),
                           PD.TierText(r[8], r[9], r[10])) or nil,
        -- 20:45 终版：右下 = 图纸/训练师（有商人时进 dpre，dval=商人：X 走锚链）
        right2 = (not dval) and base or nil,
        src = r[14],
        dpre = dpre,
        dval = dval,
        costStr = costStr,
        ahStr = ahStr,
        pct = PD.AhPct(ah, total),
        ahVal = ah,
        costVal = total,
        diffVal = tonumber(r[7]),
        gapVal = (ah and total) and (ah - total) or nil,
        -- 2026-10-10 配方页难度四段色条：阈值取配方行 7..10（学/黄/绿/灰）
        sbdiff = (r[7] or r[8] or r[9] or r[10]) and { r[7], r[8], r[9], r[10] } or nil,
        -- ★ lines 也改惰性（配方行有 it ⇒ PD.Row 的 OnEnter 走 DG.ShowItemTip，
        --   __lines 从来不读）。真要读时才拼这一串文案。
        mkLines = function()
            local lines = {}
            if r[6] and r[6] ~= "" then lines[#lines + 1] = { r[6] } end
            local mt = PD.MatText(r[12], 4)
            lines[#lines + 1] = { format(L["材料：%s"], mt ~= "" and mt or L["无"]) }
            lines[#lines + 1] = { format(L["技能：学 %s · %s"], tostring(r[7]),
                                         PD.TierText(r[8], r[9], r[10])) }
            if r[15] and #r[15] > 0 then
                lines[#lines + 1] = { format(L["改版前材料：%s"], PD.MatText(r[15])), 0.9, 0.7, 0.4 }
            end
            if hasVendor then
                for _, ln in ipairs(PD.VendorLines(r[14])) do lines[#lines + 1] = ln end
            end
            if r[16] and r[16] ~= "" then
                lines[#lines + 1] = { format(L["套装：%s"], r[16]), 0.64, 0.21, 0.93 }
            end
            if r[17] and r[17] ~= "" then
                lines[#lines + 1] = { format(L["护甲类型：%s"], r[17]), 0.7, 0.7, 0.7 }
            end
            return lines
        end,
        act = hasVendor and PD.VendorAct(r[14]) or nil,
    }
end

function PD.CraftedSpec(c)
    local resolved = PD.RecipeData(c, "crafted")
    local original = c
    c = {}; for key, value in pairs(original) do c[key] = value end
    c[8], c[3], c[2] = resolved.mats, resolved.count, resolved.item
    c[4], c[5], c[6], c[7] = resolved.learn, resolved.yellow, resolved.green, resolved.grey
    local clientPending = resolved.clientPending
    local mats = PD.MatText(c[8], 4)
    local matCol, _, _, matSg = PD.MatCol(c[8], PD.MAT_FS, PD.MAT_W)
    local green = c[6]
    if not green and c[5] and c[7] then
        green = math.floor((c[5] + c[7]) / 2)
    end
    local fid = tonumber(c[9])
    local base = nil
    if fid then
        base = L["图纸"]
    else
        local LV = ns.ProfLeveling and ns.ProfLeveling[PD.cur]
        local ri = LV and LV.rinfo and LV.rinfo[c[1]]
        if ri and ri.trainer then
            base = L["训练师"]
        else
            local learn = LV and LV.learn
            if learn then
                for _, id in ipairs(learn) do
                    if id == c[1] then base = L["训练师"] break end
                end
            end
        end
    end
    local costStr, total, unpriced, ah
    if c[8] and #c[8] > 0 then
        total, unpriced = RA.MatListCost(c[8])
        if total <= 0 or unpriced >= #c[8] then
            costStr = "—"
        else
            costStr = (unpriced > 0 and "≈" or "") .. RA.MoneyStr(total, "copper")
        end
    end
    local ahStr
    if c[2] and RA.AHPriceOf then
        ah = RA.AHPriceOf(c[2])
        ahStr = ah and RA.MoneyStr(ah, "copper") or "—"
    end
    return {
        kind = "row", is_new = c[10], it = { c[2] }, qItem = c[2], _mats = c[8], craft = c,
        text = DG.ItemName(c[2]),
        sub = "",
        mats = clientPending and L["客户端数据待读取"] or matCol,
        matSegs = matSg,
        right = not (c[4] or c[5] or green or c[7])
                and format("%s · %s", format(L["学 %s"], tostring(c[4])),
                           PD.TierText(c[5], green, c[7])) or nil,
        right2 = clientPending and L["客户端数据待读取"] or ((base and base .. " · " or "") .. PD.RecipeSourceText(resolved, true)),
        costStr = costStr,
        ahStr = ahStr,
        pct = PD.AhPct(ah, total),
        ahVal = ah,
        costVal = total,
        diffVal = tonumber(c[4]),
        gapVal = (ah and total) and (ah - total) or nil,
        sbdiff = (c[4] or c[5] or green or c[7]) and { c[4], c[5], green, c[7] } or nil,
        tipExtra = function() return PD.RecipeSourceLines(PD.PriceTipLines(c[2], c[8]), resolved) end,
        lines = {
            { format(L["材料：%s"], clientPending and L["客户端数据待读取"] or (mats ~= "" and mats or L["无"])) },
            fid and { format(L["图纸：%s"], DG.ItemName(fid)), 1, 0.82, 0.35 } or nil,
        },
    }
end

function PD.FavorSpec(f, d)
    local out = f[5] and DG.ItemName(f[5])
    local reward = (out and out ~= "" and out) or f[4] or ""
    local mats = nil
    if d and d.rows then
        local want = f[5] or f[1]
        for _, r in ipairs(d.rows) do
            if r[2] == want then
                if r[12] and #r[12] > 0 then mats = r[12] end
                break
            end
        end
    end
    if (not mats) and d and d.crafted then
        local want = f[5] or f[1]
        for _, c in ipairs(d.crafted) do
            if c[8] and #c[8] > 0 and (c[2] == want or c[9] == tostring(f[1])) then
                mats = c[8]
                break
            end
        end
    end
    local costStr
    if mats then
        local total, unpriced = RA.MatListCost(mats)
        if total <= 0 or unpriced >= #mats then
            costStr = "—"
        else
            costStr = (unpriced > 0 and "≈" or "") .. RA.MoneyStr(total, "copper")
        end
    end
    local ahStr
    if RA.AHPriceOf then
        local ah = RA.AHPriceOf(f[5] or f[1])
        ahStr = ah and RA.MoneyStr(ah, "copper") or "—"
    end
    return {
        kind = "row", it = { f[1] }, qItem = f[1], _mats = mats,
        text = DG.ItemName(f[1]),
        right = format(L["技能 %s"], tostring(f[2])),
        right2 = format(L["商人青睐 %s"], tostring(f[3])),
        costStr = costStr,
        ahStr = ahStr,
        tipExtra = function() return PD.PriceTipLines(f[1], mats) end,
        lines = { { format(L["交出：%s"], DG.ItemName(f[1])) },
                  { (reward ~= "" and format(L["换得：%s"], reward))
                    or format(L["换得：%s"], tostring(f[4])), 1, 0.82, 0 },
                  { format(L["所需：技能 %s · 商人青睐 %s"], tostring(f[2]), tostring(f[3])),
                    0.7, 0.7, 0.7 } },
    }
end

function PD.RecipeTool(d)
    if not d then return {}, nil end
    local tool = {}
    local function on(k) return PD.toolKey == k end
    if d.rows and #d.rows > 0 then
        tool[#tool + 1] = { key = "all", text = format(L["全部 %d"], #d.rows), on = on("all") }
        for _, g in ipairs(d.groups or {}) do
            tool[#tool + 1] = { key = g[1], text = format("%s %d", g[2] or g[1], g[4] or 0),
                                on = on(g[1]) }
        end
    end
    if d.enchants and #d.enchants > 0 then
        if d.rows and #d.rows > 0 then
            tool[#tool + 1] = { key = "__enchant", text = format(L["附魔 %d"], #d.enchants),
                                on = on("__enchant") }
        else
            local gc, og = {}, {}
            for _, e in ipairs(d.enchants) do
                local g = tostring(e[3] or "")
                if g == "" then g = L["其他"] end
                if not gc[g] then gc[g] = 0; og[#og + 1] = g end
                gc[g] = gc[g] + 1
            end
            tool[#tool + 1] = { key = "all", text = format(L["全部 %d"], #d.enchants), on = on("all") }
            for _, g in ipairs(og) do
                tool[#tool + 1] = { key = g, text = format("%s %d", g, gc[g]), on = on(g) }
            end
        end
    end
    if d.crafted and #d.crafted > 0 then
        tool[#tool + 1] = { key = "__crafted", text = format(L["可制造 %d"], #d.crafted),
                            on = on("__crafted") }
    end
    if d.favor and #d.favor > 0 then
        tool[#tool + 1] = { key = "__favor", text = format(L["商人兑换 %d"], #d.favor),
                            on = on("__favor") }
    end
    if #tool > PD.TOOL_MAX then
        local keep = PD.TOOL_MAX - 1
        local rest = 0
        for i = keep + 1, #tool do rest = rest + 1 end
        for i = #tool, keep + 1, -1 do table.remove(tool, i) end
        tool[#tool + 1] = { key = "__rest", text = format(L["其他 %d"], rest), on = on("__rest") }
    end
    local valid = false
    for _, t in ipairs(tool) do if t.on then valid = true end end
    if not valid then
        PD.toolKey = tool[1] and tool[1].key or "all"
        if tool[1] then tool[1].on = true end
    end
    return tool, function(k) PD.toolKey = k; PD.RequestRender() end
end

-- ★ limit（2026-10-09 第二轮）：建 spec 是要花钱的 —— 每条都要拼 6 段文案、重排
--   材料串、建 lines 表。列表封顶只画 PD.ROW_CAP 条，所以**只为画出来的那些建**。
--   「过滤后到底多少条」由 PD.ScanRecipe 的轻量扫描给出（不建 spec）。
function PD.RecipeList(limit, q)
    local d = RGet(PD.cur)
    local out = {}
    if not d then return out end
    local key = PD.toolKey
    local cap = limit or PD.ROW_CAP
    if cap < 1 then return out end
    if key == "__enchant" then
        for _, e in ipairs(d.enchants or {}) do
            if PD.RecipeVisible(e[14]) then out[#out + 1] = PD.EnchantSpec(e) end
            if #out >= cap then break end
        end
        return out
    end
    if d.enchants and #d.enchants > 0 and not (d.rows and #d.rows > 0)
       and key ~= "__crafted" and key ~= "__favor" and key ~= "__rest" then
        local want
        if key ~= "all" then want = tostring(key) end
        for _, e in ipairs(d.enchants or {}) do
            local g = tostring(e[3] or "")
            if g == "" then g = L["其他"] end
            if ((not want) or g == want) and PD.RecipeVisible(e[14]) then
                out[#out + 1] = PD.EnchantSpec(e)
                if #out >= cap then break end
            end
        end
        return out
    end
    if key == "__crafted" then
        for _, c in ipairs(d.crafted or {}) do
            if PD.RecipeVisible(c[1]) then out[#out + 1] = PD.CraftedSpec(c) end
            if #out >= cap then break end
        end
        return out
    end
    if key == "__favor" then
        for _, f in ipairs(d.favor or {}) do
            out[#out + 1] = PD.FavorSpec(f, d)
            if #out >= cap then break end
        end
        return out
    end
    -- ★ 搜索必须在**建 spec 之前**生效（2026-10-09 第二轮修正）：先按 PD.RawHit 过
    --   原始行，命中的才建 spec —— 不然「点开那一瞬间」还是要为全量 511 条建一遍。
    --   口径与 PD.ScanRecipe 完全共用（PD.EffKeyFilter + PD.RawHit），不许各写一套。
    --   ★ 旧的 `any` 回退（key 一条都没命中 ⇒ 不过滤）已折进 PD.EffKeyFilter。
    local fk = PD.EffKeyFilter(d)
    local __ri = 0
    for _, r in ipairs(d.rows or {}) do
        __ri = __ri + 1
        if (not fk) or r[4] == fk then
            if PD.RawHit(r, q) then
                out[#out + 1] = PD.RecipeSpec(r)
                if #out >= cap then break end
            end
        end
        if __ri % 32 == 0 and coroutine.running and coroutine.running() then coroutine.yield() end
    end
    return out
end

-- ★ 原始行命中搜索词吗（2026-10-09 第二轮）：**不建 spec** 的轻量判定。
--   配方页主列表必须按搜索词过滤，但过滤得发生在**建 spec 之前** —— 否则
--   「点开那一瞬间」又要为全量 511 条建一遍 spec（已量过 = 整帧 82% 的耗时）。
--   口径与 PD.SearchHit 逐字一致（名称 → 副行 → 材料名；q 已小写化）。
function PD.RawHit(r, q)
    if not PD.RecipeVisible(r[1]) then return false end
    if not q or q == "" then return true end
    local nm = PD.ItemName(r[2])
    if nm and nm ~= "" and string.find(string.lower(tostring(nm)), q, 1, true) then
        return true
    end
    local sub = tostring(r[5] or "")
    if sub ~= "" and string.find(string.lower(sub), q, 1, true) then return true end
    local resolved = PD.RecipeData(r, "rows")
    for _, m in ipairs(resolved.mats or {}) do
        local mn = PD.ItemName(m[1])
        if mn and mn ~= "" and string.find(string.lower(tostring(mn)), q, 1, true) then
            return true
        end
    end
    return false
end

-- ★ 本页的「有效分类过滤」（2026-10-09 第二轮）：按 PD.toolKey 过滤**一条都没命中**
--   时退回不过滤 —— 与旧 PD.RecipeList 的 any 回退同口径。返回值即要用的 key
--   （nil = 不过滤）。PD.ScanRecipe 与 PD.RecipeList 共用，两边口径不许各写一套。
function PD.EffKeyFilter(d)
    local key = PD.toolKey
    if not key or key == "all" then return nil end
    for _, r in ipairs(d.rows or {}) do
        if r[4] == key then return key end
    end
    return nil
end

-- ★ 配方页「轻量全量扫描」（2026-10-09 第二轮：点开配方页那一瞬间仍卡）：
--   渲染前只需要两件事 —— ① 过滤后到底多少条（抬头文案 + 截断提示）② 名称列最宽
--   多少（定列宽）。原来这两件事都是**先把全量 511 条建成完整 spec 再量**，而列表
--   封顶只画 300 条 ⇒ 剩下 211 条的部位纯白做（实测占整帧 82%）。
--   这里改成对**原始行**直接取三个字段量宽：名称 / 副行 / 新角标 —— 不建 spec、
--   不拼任何文案、不碰材料串。判定口径与 PD.SearchHit 逐字一致（含 q 已在
--   OnTextChanged 里小写化这一点）。
--   ★ 只覆盖 d.rows 主路径；附魔 / 制造品 / 声望三类特殊列表规模小，返回 nil
--     让调用方走原路径（PD.SearchFilter + PD.RecipeList 全量）。
function PD.ScanRecipe()
    local d = RGet(PD.cur)
    if not d then return 0, 0 end
    local key = PD.toolKey
    if key == "__enchant" or key == "__crafted" or key == "__favor" then
        return nil
    end
    if not (d.rows and #d.rows > 0) then return nil end
    local q = (PD.searchQ and PD.searchQ ~= "") and PD.searchQ or nil
    local fk = PD.EffKeyFilter(d)

    local n, maxW = 0, 0
    for _, r in ipairs(d.rows or {}) do
        if (not fk) or r[4] == fk then
            if PD.RawHit(r, q) then
                n = n + 1
                -- ★★ 2026-10-09 第六轮：**只给画得出来的行量宽**。
                --   列宽（maxW → PD.RECIPE_NAME_W）只要放得下**真正画出来的**那些
                --   行就够了；第 301 条往后根本不进列表 ⇒ 给它们量宽是纯白做
                --   （实测每次点开白量 211 次 ItemName + 422 次 TextW）。
                --   计数 n 仍然**精确**（抬头要显示真实总数）。
                if n <= PD.ROW_CAP then
                    -- 与 PD.FitRecipeCols 的自扫逐字同口径：名称可为空（名字还没到货）
                    -- 时也照样把「新角标 + 副行」计入最宽值。
                    local nm = PD.ItemName(r[2])
                    local w = (nm and nm ~= "" and PD.TextW(nm, 13)) or 0
                    -- 2026-10-10 用户：角标迁副行 ⇒ 角标宽记到副行一侧（与 FitRecipeCols 同口径）
                    local sw = PD.TextW(PD.KitSub(tostring(r[5] or ""), r[6]), 11) + (r[11] and PD.RECIPE_BADGE_W or 0)
                    if sw > w then w = sw end
                    if w > maxW then maxW = w end
                end
            end
        end
    end
    return n, maxW
end

function PD.RowsRecipe(rows)
    local d = RGet(PD.cur)
    if not d then return end
    local realN, maxW = PD.ScanRecipe()
    local list
    if realN then
        -- 主路径：只为画得出来的那些建 spec（列宽用轻量扫描的全量结果）
        list = PD.RecipeList(math.min(realN, PD.ROW_CAP), PD.searchQ)
    else
        -- 附魔 / 制造品 / 声望：规模小，保持原路径
        list = PD.SearchFilter(PD.RecipeList())
        realN, maxW = #list, nil
    end
    if PD.recipeSort then
        local kf = ({ ah = "ahVal", cost = "costVal", diff = "diffVal", gap = "gapVal" })[PD.recipeSort]
        if kf then
            local desc = PD.recipeSortDesc
            table.sort(list, function(a, b)
                local ka, kb = a[kf], b[kf]
                if ka and kb then
                    if desc then return ka > kb end
                    return ka < kb
                end
                if ka or kb then return ka ~= nil end
                return false
            end)
        end
    end
    PD.FitRecipeCols(list, maxW)
    if realN == 0 and PD.searchQ and PD.searchQ ~= "" then
        PushGap(rows)
        PushText(rows, format(L["没有名称或材料匹配「%s」的配方 —— 换个关键词再试试。"],
                              PD.searchQ), 12, C_GOLD)
        return
    end
    local trunc = 0
    if realN > PD.ROW_CAP then trunc = realN - PD.ROW_CAP end
    -- 2026-10-10 用户：五列表头行（配方|材料|拍卖|制作成本|难度），搜索无结果时不列
    if realN > 0 then
        rows[#rows + 1] = { kind = "rechead", h = 26, col = 1, noTip = true }
    end
    for i = 1, #list do rows[#rows + 1] = list[i] end
    if trunc > 0 then
        PushGap(rows)
        PushText(rows, format(
            L["列表只画前 %d 条，还有 %d 条没显示 —— 用上方分类缩小范围。"],
            PD.ROW_CAP, trunc), 12, C_GOLD)
    end
end

function PD.ZoneText(list, maxN)
    if not list or #list == 0 then return L["无数据"] end
    local t = {}
    for i, z in ipairs(list) do
        if maxN and i > maxN then t[#t + 1] = "…"; break end
        t[#t + 1] = format("%s(%d)", DG.ZoneName(z[1]), z[2] or 0)
    end
    return table.concat(t, "  ")
end

DG.FISH_FIELD_LABEL = {
    L["所需技能"], L["技能加成"], L["持续（分钟）"], L["等级"],
    L["学会后解锁"], L["标注新增"], L["可作为钓具"], L["需求"],
}
DG.FISH_GROUPS = {
    { key = "spells", text = L["钓鱼法术"] },
    { key = "lures",  text = L["鱼饵"] },
    { key = "food",   text = L["钓鱼食物"] },
    { key = "items",  text = L["钓鱼物品"] },
    { key = "titles", text = L["钓鱼称号"] },
}

function PD.RowsFishing(rows)
    local p = D.pro.fishing
    local zones = GA and GA.fishing
    if zones and #zones > 0 then
        PushHead(rows, format(L["可钓区域（%d 处）"], #zones))
        for _, z in ipairs(zones) do
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H1, text = DG.ZoneName(z[1]),
                right = format(L["技能 %s"], tostring(z[2])),
            }
        end
        PushGap(rows)
    end

    if p and p.ranks and #p.ranks > 0 then
        PushHead(rows, L["技能等级（怎么把上限提上去）"])
        for _, rk in ipairs(p.ranks) do
            local note = rk[3] or ""
            local book = rk[4]
            if book then note = note:gsub("{book}", (DG.ItemName(book))) end
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H1,
                it = book and { book } or nil,
                text = rk[1] or "?", right = format(L["技能 %s"], tostring(rk[2])),
                lines = { { rk[1] or "" }, { note } },
            }
            if note ~= "" then PushText(rows, "· " .. note, 11, C_GREY) end
        end
        PushGap(rows)
    end

    if not (p and p.fishing) then return end
    for _, grp in ipairs(DG.FISH_GROUPS) do
        local list = p.fishing[grp.key]
        if list and #list > 0 then
            PushHead(rows, format(L["%s（%d 条）"], grp.text, #list))
            local isSpell = (grp.key == "spells")
            local isTitle = (grp.key == "titles")
            for _, e in ipairs(list) do
                local id, icon, sub = e[1], e[3], e[5]
                local nm
                if isSpell then
                    nm = SpellName(id)
                elseif not isTitle then
                    nm = DG.ItemName(id)
                end
                if type(nm) ~= "string" or nm == "" then nm = e[2] end
                local lines = {}
                if e[4] and e[4] ~= "" then lines[#lines + 1] = { e[4] } end
                if sub and sub ~= "" then lines[#lines + 1] = { sub, 0.7, 0.7, 0.7 } end
                for i = 6, 13 do
                    local v = e[i]
                    if v ~= nil and v ~= false and v ~= 0 and v ~= "" then
                        if type(v) == "table" then
                            local t = {}
                            for _, x in ipairs(v) do t[#t + 1] = tostring(x) end
                            v = table.concat(t, " / ")
                        end
                        if v ~= "" then
                            lines[#lines + 1] = { format("%s：%s",
                                DG.FISH_FIELD_LABEL[i - 5], tostring(v)), 0.6, 0.9, 0.6 }
                        end
                    end
                end
                rows[#rows + 1] = {
                    kind = "row", is_new = e[11],
                    it = (id and not isSpell and not isTitle) and { id } or nil,
                    icon = (icon ~= "" and icon) or nil,
                    text = nm or (id and format(L["法术 #%d"], id)) or "?",
                    sub = sub or "", right = (e[6] and format(L["技能 %s"], tostring(e[6]))) or "",
                    right2 = e[9] and format(L["等级 %s"], tostring(e[9])) or "",
                    lines = lines,
                }
            end
            PushGap(rows)
        end
    end
end

function PD.RowsGather(rows)
    if PD.cur == "fishing" then
        PD.RowsFishing(rows)
        return
    end
    local g = GA and GA[PD.cur]
    if not g then return end
    if PD.cur == "skinning" then
        PushHead(rows, L["剥皮档次（等级区间 → 产出 → 分布）"])
        for _, t in ipairs(g) do
            local items = {}
            for _, id in ipairs(t[2] or {}) do items[#items + 1] = DG.ItemName(id) end
            rows[#rows + 1] = {
                kind = "row",
                text = format(L["等级 %s - %s"], tostring(t[1][1]), tostring(t[1][2])),
                sub = table.concat(items, "  "),
                right2 = PD.ZoneText(t[3], 3),
                lines = { { format(L["产出：%s"], table.concat(items, "  ")) },
                          { format(L["分布：%s"], PD.ZoneText(t[3])) } },
            }
        end
        return
    end
    PushHead(rows, L["节点表（所需技能 → 产出 → 分布）"])
    for _, n in ipairs(g) do
        local head = n[1] and n[1][1]
        local items = {}
        for _, id in ipairs(n[1] or {}) do items[#items + 1] = DG.ItemName(id) end
        local nm, got = DG.ItemName(head)
        if not got then nm = head and format(L["物品 #%d"], head) or "?" end
        rows[#rows + 1] = {
            kind = "row", it = head and { head } or nil, text = nm,
            sub = table.concat(items, "  "),
            right = format(L["技能 %d"], n[2] or 0),
            right2 = PD.ZoneText(n[3], 3),
            lines = { { format(L["产出：%s"], table.concat(items, "  ")) },
                      { format(L["分布：%s"], PD.ZoneText(n[3])) } },
        }
    end
end

function PD.FishingAreaName(area)
    if not area then return L["无数据"] end
    local name = area.name
    if not name and area.zoneID and DG.ZoneName then name = DG.ZoneName(area.zoneID) end
    name = name and (L[name] or name) or L["无数据"]
    return name
end

function PD.FishingAreaDetail(area)
    local parts = {}
    if area.minSkill then parts[#parts + 1] = format(L["最低钓鱼技能 %d"], area.minSkill) end
    local safe = area.noGetaway or area.avoidGetaway
    if safe then parts[#parts + 1] = format(L["不脱钩技能 %d（含加成）"], safe) end
    if area.note then parts[#parts + 1] = L[area.note] or area.note end
    return table.concat(parts, " · ")
end

-- A guide's zone is enough to open its map; a waypoint needs actual coordinates.
function PD.ShowFishingArea(area)
    if not area then return end
    local mapID = area.mapID or (ns.AreaMap and ns.AreaMap[area.zoneID])
    if not mapID then return end
    if type(area.x) == "number" and type(area.y) == "number" then
        PD.MarkMapPoint(mapID, area.x, area.y)
    elseif C_Map and C_Map.OpenWorldMap then
        pcall(C_Map.OpenWorldMap, mapID)
    elseif OpenWorldMap then
        pcall(OpenWorldMap, mapID)
    elseif WorldMapFrame and WorldMapFrame.SetMapID then
        if WorldMapFrame.Show then pcall(WorldMapFrame.Show, WorldMapFrame) end
        pcall(WorldMapFrame.SetMapID, WorldMapFrame, mapID)
    end
end

function PD.RowsFishAreas(rows, fish, areas, col)
    local names, combined, seen = {}, {}, {}
    local function addArea(area)
        if type(area) ~= "table" then return end
        local key = tostring(area.zoneID or area.mapID or area.name) .. ":" .. tostring(area.name or "")
        if not seen[key] then seen[key] = true; combined[#combined + 1] = area end
    end
    for _, entry in ipairs(fish or {}) do
        local id = entry.id or entry[1]
        if id then names[#names + 1] = format("%s ×%s", DG.ItemName(id), tostring(entry.count or entry.need or entry[2] or 0)) end
        for _, area in ipairs(entry.areas or {}) do addArea(area) end
    end
    for _, area in ipairs(areas or {}) do addArea(area) end
    if #names > 0 then
        PushText(rows, format(L["自行钓取：%s"], table.concat(names, "、")), 11, {0.42, 0.84, 0.95}, col)
    end
    for _, area in ipairs(combined) do
        local selected = area
        local mapID = selected.mapID or (ns.AreaMap and ns.AreaMap[selected.zoneID])
        local detail = PD.FishingAreaDetail(selected)
        rows[#rows + 1] = {
            kind = "row", h = detail ~= "" and PD.ROW_H or PD.ROW_H1, col = col,
            text = format(L["钓鱼区域：%s"], PD.FishingAreaName(selected)), sub = detail,
            right = mapID and L["点击地图"] or nil,
            lines = {{PD.FishingAreaName(selected)}, {detail, 0.7, 0.7, 0.7},
                {L["钓鱼加成包含鱼竿、鱼饵和装备；达到不脱钩技能更稳定。"], 0.7, 0.7, 0.7}},
            act = mapID and function() PD.ShowFishingArea(selected) end or nil,
        }
    end
end

function PD.RowsFishingLevelRoute(rows, curLv)
    local guide = ns.ProfFishingRoutes
    local steps = guide and guide.fishingSteps
    if not steps or #steps == 0 then return false end
    PushHead(rows, L["钓鱼升级路线（优先推荐水域）"])
    PushText(rows, L["成功钓获鱼类可提升技能；技能越高，通常需要更多次成功钓获。"], 11, C_GREY)
    PushText(rows, L["推荐按鱼类与技能选择水域；可留在低级水域练满，无需到点强制换区。"], 11, C_GREY)
    PushText(rows, L["钓鱼加成包含鱼竿、鱼饵和装备；达到不脱钩技能更稳定。"], 11, C_GREY)
    PushGap(rows)
    for index, step in ipairs(steps) do
        local lo, hi = step.from or step[1], step.to or step[2]
        local active = curLv and curLv >= lo and (curLv < hi or (index == #steps and curLv == hi))
        local fish = {}
        for _, id in ipairs(step.fishIDs or {}) do fish[#fish + 1] = DG.ItemName(id) end
        rows[#rows + 1] = {
            kind = "row", h = PD.ROW_H, text = format(L["%d – %d"], lo, hi),
            sub = #fish > 0 and table.concat(fish, "、") or nil,
            nameColor = active and {0.4, 0.9, 0.45} or nil,
            right = active and L["◆ 推荐当前就练这一档"] or nil,
        }
        if step.note then PushText(rows, L[step.note] or step.note, 11, C_GREY) end
        PD.RowsFishAreas(rows, nil, step.areas)
        PushGap(rows, 4)
    end
    return true
end

-- ── 采集升级路线（2026-10-11）：mining/herbalism/skinning/fishing ──────────
-- 静态推荐路线（无价格/概率，无从自动计算）：按技能区间/门槛推进 + 当前技能绿色定位。
function PD.RowsGatherRoute(rows)
    local slug = PD.cur
    local g = GA and (GA[slug] or (slug == "fishing" and GA.fishing))
    if not g or #g == 0 then return end
    local _learned = PD.ProfLearned()
    local curLv = _learned and _learned[slug] and _learned[slug].cur or nil
    local GR_GREEN = { 0.4, 0.9, 0.45 }  -- 当前可练段绿色（采集/熔炼共用）

    if PD.GatherMode(slug) == "smelt" then
        PD.RowsLeveling(rows)
        return
    end
    if slug == "fishing" then
        if PD.RowsFishingLevelRoute(rows, curLv) then return end
        -- 按门槛分档：{门槛, {区域...}}
        PushHead(rows, format(L["钓鱼升级路线（%d 处水域）"], #g))
        PushText(rows, L["成功钓获鱼类可提升技能；技能越高，通常需要更多次成功钓获。"], 11, C_GREY)
        PushGap(rows)
        local bands = {}
        for _, ed in ipairs(g) do
            local b = bands[#bands]
            if b and b[1] == ed[2] then b[2][#b[2] + 1] = ed[1]
            else bands[#bands + 1] = { ed[2], { ed[1] } } end
        end
        for bi, band in ipairs(bands) do
            local nxt = bands[bi + 1]
            local active = curLv and curLv >= band[1] and (not nxt or curLv < nxt[1])
            local names = {}
            for _, zid in ipairs(band[2]) do
                names[#names + 1] = DG.ZoneName(zid) or format("#%d", zid)
            end
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H1,
                text = format(L["技能 %d 起"], band[1]),
                sub = table.concat(names, "、"),
                nameColor = active and { 0.4, 0.9, 0.45 } or nil,
                lines = { { active and L["◆ 推荐当前就练这一档"] or
                    (nxt and format(L["练到 %d 换下一档"], nxt[1]) or L["练满为止"]),
                    0.62, 0.62, 0.62 } },
            }
        end
        return
    end

    -- mining / herbalism / skinning：三列行 [等级 | 地点 | 图标+矿名]（2026-10-11 用户可视化方案拍板）
    PushHead(rows, L["采集升级路线（全程）"])
    if curLv then
        PushText(rows, format(L["当前技能 %d，绿色为推荐段：采到区间上缘再换下一段。"], curLv), 11, C_GREY)
    else
        PushText(rows, L["未学到该专业，先找训练师学习；学习后这里显示当前位置。"], 11, C_GREY)
    end
    PushGap(rows)
    local function GrSameSeg(a, b)
        if #a ~= #b then return false end
        for k = 1, #a do if a[k] ~= b[k] then return false end end
        return true
    end
    -- ★ 剥皮等级列按上游口径（2026-10-11 用户拍板）：节点表档位是野兽等级，
    --   显示改映射为剥皮技能区间：1；10-100；105-150；155-200；205-250；255-300。
    local SKIN_SKILL = { [1] = { 1, 1 }, [11] = { 10, 100 }, [21] = { 105, 150 }, [31] = { 155, 200 }, [41] = { 205, 250 }, [51] = { 255, 300 } }
    local gi = 1
    -- ★ 采药/采矿区间合并（2026-10-11 用户拍板，对齐上游分组）：档位按区间并组——
    --   组内产物取并集、分布取并集（按节点数保留前 6），整组一行，等级列=区间（t[5]）。
    --   （取代旧「采药同档合并」：同档条目本就落同组，天然并掉。）
    local HERB_GRP = { { 1, 50 }, { 50, 100 }, { 100, 150 }, { 150, 205 }, { 205, 230 }, { 230, 270 }, { 270, 300 } }
    local MINE_GRP = { { 1, 65 }, { 65, 125 }, { 125, 175 }, { 175, 245 }, { 245, 300 } }
    if slug == "herbalism" or slug == "mining" then
        local grp = (slug == "herbalism") and HERB_GRP or MINE_GRP
        local function GrpOf(s)
            local cur
            for _, rg in ipairs(grp) do
                if rg[1] <= s then cur = rg else break end
            end
            return cur or grp[1]
        end
        local merged = {}
        for _, t in ipairs(g) do
            local last = merged[#merged]
            if last and last[5] == GrpOf(t[2]) then
                local seen = {}
                for _, id in ipairs(last[1]) do seen[id] = true end
                for _, id in ipairs(t[1]) do
                    if not seen[id] then last[1][#last[1] + 1] = id end
                end
                local zs = {}
                for _, z in ipairs(last[3]) do zs[z[1]] = math.max(zs[z[1]] or 0, z[2]) end
                for _, z in ipairs(t[3]) do zs[z[1]] = math.max(zs[z[1]] or 0, z[2]) end
                local zl = {}
                for zid, cnt in pairs(zs) do zl[#zl + 1] = { zid, cnt } end
                table.sort(zl, function(a, b) return a[2] > b[2] end)
                for k = #zl, 7, -1 do zl[k] = nil end   -- 与单档口径一致：最多 6 处
                last[3] = zl
                last[4] = true
            else
                merged[#merged + 1] = { t[1], t[2], t[3], nil, GrpOf(t[2]) }
            end
        end
        g = merged
    end
    while gi <= #g do
        local t = g[gi]
        local lo, hi, ids, zones
        if slug == "skinning" then
            local rng = SKIN_SKILL[t[1][1]] or { t[1][1], t[1][2] }
            lo, hi, ids, zones = rng[1], rng[2], t[2], t[3]
        else
            lo, ids, zones = t[2], t[1], t[3]
            if t[5] then
                lo, hi = t[5][1], t[5][2]   -- 区间合并组：等级列=整组区间
            else
                hi = (g[gi + 1] and g[gi + 1][2] or 301) - 1
                if hi < lo then hi = lo end   -- 同起点双段（如采矿 230 两种矿）不再反转
            end
        end
        -- ★ 用户拍板「合并」：相邻段产物与分布一致 → 并成一行，等级区间贯通
        while not t[5] and g[gi + 1] do
            local nx = g[gi + 1]
            if not (GrSameSeg(ids, (slug == "skinning") and nx[2] or nx[1])
                    and PD.ZoneText(zones) == PD.ZoneText(nx[3])) then break end
            if slug == "skinning" then
                if nx[1][1] ~= t[1][2] + 1 then break end   -- 野兽档相邻才并
                hi = (SKIN_SKILL[nx[1][1]] or { nil, nx[1][2] })[2]
            else
                hi = (g[gi + 2] and g[gi + 2][2] or 301) - 1
                if hi < lo then hi = lo end -- 防反转
            end
            gi = gi + 1
        end
        local active = curLv and curLv >= lo and curLv <= hi
        local headId = ids[1]
        -- 合并行（t[4]）把并集里所有产物名列出来（如 1~14 宁神花、银叶草、地根草）；单产物行只显示行主名
        local nm
        if t[4] then
            local nms = {}
            for _, id in ipairs(ids) do
                local on = DG.ItemName(id)
                nms[#nms + 1] = (type(on) == "string" and on ~= "") and on or format(L["物品 #%d"], id)
            end
            nm = table.concat(nms, "、")
        else
            nm = DG.ItemName(headId)
            if not (type(nm) == "string" and nm ~= "") then nm = format(L["物品 #%d"], headId) end
        end
        rows[#rows + 1] = {
            kind = "row", h = PD.ROW_H1, gr3 = true,
            it = { headId }, qItem = headId,
            lv = (hi > lo) and format(L["%d - %d"], lo, hi) or tostring(lo),
            loc = format(L["大多在 %s"], PD.ZoneText(zones)),
            text = nm,
            -- ★ 采药/采矿第三列只放图标（2026-10-11 用户）；剥皮仍走图标+名字
            icons = (slug == "herbalism" or slug == "mining") and ids or nil,
            nameColor = active and GR_GREEN or nil,
        }
        gi = gi + 1
    end
end

-- ── 固定路线 · 目标裁剪 / 聚合（2026-10-09 v2）─────────────────────────────
-- 跨目标的段：止点裁到目标，制作数量按 (目标−起)/(止−起) 比例折算（ceil）。
local function ClipFixedSteps(steps, target)
    if not target or target >= 300 then
        return steps, false
    end
    local out, clipped = {}, false
    for _, st in ipairs(steps or {}) do
        local a, b = st[1], st[2]
        if a > target then break end
        local nb, nq = math.min(b, target), st[4] or 0
        local isClip = b > target
        if isClip then
            nq = math.max(1, math.ceil(nq * (target - a) / (b - a) - 1e-9))
            clipped = true
        end
        local cp = {}
        for k, v in pairs(st) do cp[k] = v end
        cp[2], cp[4], cp._clip = nb, st.checkpoint and 0 or nq, isClip or nil
        out[#out + 1] = cp
    end
    return out, clipped
end

-- 固定路线聚合（材料数量和采购费用）：走 RA 的同一套价格层；无价格层时退回数量清单
local function FixedShopData(target)
    local lv = LV[PD.cur]
    local steps, clipped = ClipFixedSteps(lv.steps or {}, target)
    local blocked, goalRequired
    if RA and RA.FilterFixedSpecializations then
        steps, blocked, goalRequired = RA.FilterFixedSpecializations(PD.cur, steps, {target=target})
    end
    if RA and RA.SummarizeSteps then
        local sum = RA.SummarizeSteps(steps, PD.cur,
                                      { learnedOnly = PD.Setting("autoLearnedOnly") })
        if sum then
            sum.mode = "fixed"
            sum.target = target
            sum.clipped = clipped
            if goalRequired or (blocked and #blocked>0) then
                sum.feasible, sum.specializationBlocked, sum.status = false, true, "recalculate_required"
                sum.message = L["固定攻略存在专精缺口，请切换自动计算。"]
            end
            return sum
        end
    end
    -- 兜底（非无限服等没有价格层的场合）：数据表预聚合的全量清单，只显示数量
    return { mode = "fixed", target = target, mats = {}, clientPending = true,
             steps = lv.steps or {}, priced = false }
end

local function CountUnpriced(sum)
    local n = 0
    for _, e in ipairs(sum.mats or {}) do if e.unpriced then n = n + 1 end end
    return n
end

function PD.PlanStatusText(plan)
    if not plan then return L["正在计算升级路线…"] end
    if plan.specializationBlocked==true or plan.specializationGoalRequired
       or (type(plan.specializationBlocked)=="table" and #plan.specializationBlocked>0) then
        return plan.message or L["固定攻略存在专精缺口，请切换自动计算。"]
    end
    if plan.status=="recalculate_required" then
        for _,diagnostic in ipairs(plan.diagnostics or {}) do
            if (diagnostic.code=="vendorQuoteChanged" or diagnostic.code=="specializationChanged")
               and ns.ProfEconomy and ns.ProfEconomy.DiagnosticText then
                return ns.ProfEconomy.DiagnosticText(diagnostic)
            end
        end
    end
    local search=plan.searchState
    if search then
        if search.status=="searching" then return L["后台优化中"] end
        if search.status=="stopped" or search.status=="paused" then return L["优化已停止"] end
        if search.status=="interrupted" then return L["优化已中断；执行计划已保存，可重新计算。"] end
        if search.status=="error" then return L["计算发生错误，请重新计算。"] end
        if search.status=="complete" then
            return search.budgetLimited and L["已完成本轮计算，当前结果尚未证明最优。"]
                or L["后台优化已结束，继续执行已保存计划。"]
        end
        if search.status=="incomplete" then return L["资料或价格不完整"] end
        if search.status=="infeasible" then return L["当前限制下没有可行路线"] end
    end
    if plan.scheme == "fishing" and not plan.partial and plan.status == "complete" then return L["纯钓鱼路线已生成"] end
    if plan.optimal and plan.supplyComplete ~= false then return L["当前价格与期望模型内最优"] end
    if plan.partial then
        return format(L["已计算至 %d；后续路线待补全"], plan.plannedTo or plan.start or 1)
    end
    if plan.pricePending and PD.PlanHasSteps(plan) then return L["参考路线已生成；材料价格待补全"] end
    if plan.feasible == false and PD.PlanHasSteps(plan) then
        return L["可先完成已计算步骤；后续路线待补全"]
    end
    local status = {
        searching = L["后台优化中"], paused = L["优化已停止"],
        stopped = L["优化已停止"], infeasible = L["当前限制下没有可行路线"],
        incomplete = L["资料或价格不完整"], complete = L["当前找到的最低支出"],
        error = L["计算发生错误，请重新计算。"],
        selection_required = L["请选择搭配的主专业"],
        recalculate_required = L["搭配专业已更改，点击重新计算应用。"],
    }
    return status[plan.status] or L["正在计算升级路线…"]
end

function PD.PlanProgressText(plan)
    local search=plan and plan.searchState
    if search then
        if search.expanded==nil then return nil end
        if search.bestTotal~=nil then
            return format(L["已比较 %d 个状态；后台当前最低支出 %s"],search.expanded,RA.MoneyStr(search.bestTotal))
        end
        if search.expanded>0 then return format(L["已比较 %d 个状态"],search.expanded) end
        return nil
    end
    if not plan or plan.expanded == nil then return nil end
    if plan.expanded == 0 and plan.initialTotal == nil then return nil end
    if plan.initialTotal == nil then return format(L["已比较 %d 个状态"], plan.expanded or 0) end
    local savings = plan.savings
    if savings == nil and plan.initialTotal and plan.total then
        savings = math.max(0, plan.initialTotal - plan.total)
    end
    return format(L["已比较 %d 个状态；较初始方案节省 %s"], plan.expanded or 0, RA.MoneyStr(savings or 0))
end

function PD.PlanCacheText(plan)
    if plan and plan.stale then return L["已保存路线；数据或设置已变化，点击重新计算更新。"] end
end

function PD.PlanSupplyText(plan)
    local unknown = plan and tonumber(plan.auctionSupplyUnknown)
    if unknown and unknown > 0 then
        local text = format(L["有 %d 种拍卖行物品数量未知，暂按价格估算；请在拍卖师处执行一次完整扫描后重新计算。"], unknown)
        -- Identify the selected purchases still lacking evidence. Candidate
        -- recipes and NPC purchases are not missing auction observations.
        local names, seen, count = {}, {}, 0
        for _, list in ipairs({plan.mats or {}, plan.formulas or {}}) do
            for _, entry in ipairs(list) do
                local id = tonumber(entry.id or entry[1])
                local auction = entry.source == "ah" or entry.source == "auction"
                if auction and not entry.vendor and not entry.known and id and not seen[id]
                    and entry.supplyObserved ~= true and tonumber(entry.availableCount) == nil then
                    seen[id] = true; count = count + 1
                    if #names < 3 then
                        local name, loaded = PD.ItemName(id)
                        if not name or name == "" or loaded == false then name = "#" .. tostring(id) end
                        names[#names + 1] = name
                    end
                end
            end
        end
        if count > #names then
            text = text .. " " .. format(L["数量未知物品：%s，另有 %d 种（详见购物清单）。"], table.concat(names, " / "), count - #names)
        elseif #names > 0 then
            text = text .. " " .. format(L["数量未知物品：%s。"], table.concat(names, " / "))
        end
        return text
    end
end

function PD.AuctionSupplyText(entry)
    if entry.vendor or entry.source == "vendor" or entry.source == "npc" then return end
    local source = entry.source or entry.sourceType
    if source ~= "ah" and source ~= "auction" then return end
    local available = tonumber(entry.availableCount)
    if available then
        local need = entry.count or entry.need or entry[2] or 0
        if entry.supplySource == "auctionator-update" then
            return format(L["扫描汇总估计：%d 件；本路线购买 %d 件。"], available, need)
        end
        if available < need then
            return format(L["拍卖行已读取数量不足：可购 %d 件，需要 %d 件。"], available, need)
        end
        if entry.supplyComplete == false then
            return format(L["拍卖行已读取：%d 件（结果未全部读取）；本路线购买 %d 件。"], available, need)
        end
        return format(L["拍卖行数量快照：%d 件；本路线购买 %d 件。"], available, need)
    end
    if entry.supplyObserved == false then return L["拍卖行可购数量未知，当前仅按价格估算。"] end
end

-- Quantity and price clocks are deliberately separate: a later price-only update
-- must never make an older quantity look newly observed. Uptime timestamps from
-- old route caches are not valid persisted observations.
function PD.AuctionObservationText(observedAt)
    local stamp = tonumber(observedAt)
    if not stamp or stamp ~= stamp or stamp < 1000000000 or stamp == math.huge then
        return L["观测时间未知"]
    end
    if type(date) == "function" then
        local ok, value = pcall(date, "%Y-%m-%d %H:%M", stamp)
        if ok and type(value) == "string" then return value end
    end
    return tostring(math.floor(stamp))
end

function PD.AuctionSupplyLines(entry)
    local source = entry.source or entry.sourceType
    local auction = not entry.vendor and (source == "ah" or source == "auction")
    local lines = {}
    local function add(text, warn)
        lines[#lines + 1] = {text, warn and 0.95 or 0.7, warn and 0.75 or 0.7, warn and 0.4 or 0.7}
    end
    if auction then
        local text = PD.AuctionSupplyText(entry)
        if text then add(text) end
        if tonumber(entry.availableCount) then
            add(format(L["数量观测：%s"], PD.AuctionObservationText(entry.supplyObservedAt)))
            if entry.supplySource == "client-auction-results" then
                add(L["数量来源：客户端拍卖结果"])
            elseif entry.supplySource == "auctionator-update" then
                add(L["数量来源：Auctionator 最近更新（扫描汇总估计）"])
            else
                add(L["数量来源：旧路线记录（范围未核实）"])
            end
            if entry.supplyComplete == true then
                add(L["扫描范围：完整结果"])
            elseif entry.supplyComplete == false and entry.supplySource ~= "auctionator-update" then
                add(L["扫描范围：部分结果，仅代表已读取数量"])
            else
                add(L["扫描范围：未核实"])
            end
            add(entry.supplyOwnerExcluded == true and L["已排除本人拍卖"] or L["是否包含本人拍卖：未核实"])
            local stamp = tonumber(entry.supplyObservedAt)
            local now = type(time) == "function" and time() or nil
            if stamp and stamp >= 1000000000 and now and now - stamp > 2 * 86400 then
                add(L["数据较旧（超过两天）；仍按保存数量规划，请扫描后更新。"], true)
            end
            add(L["最近观测数量不保证当前仍在售，也不保证全部可按最低价格购买。"])
            if type(entry.supplyObservedPrice) == "number" then
                add(format(L["数量观测时最低单价：%s"], RA.MoneyStr(entry.supplyObservedPrice, "copper")))
            end
        elseif entry.supplyObserved == false then
            add(L["请在拍卖师处执行一次完整扫描，以保存最近数量。"], true)
        end
        local history = tonumber(entry.supplyHistoryQuantity)
        if history and history >= 0 then
            add(format(L["Auctionator 当日最高数量：%d（仅供参考，不限制路线）"], history))
            add(format(L["历史数量日期：%s"], PD.AuctionObservationText(entry.supplyHistoryObservedAt)))
        end
    end
    if auction or type(entry.ahPrice) == "number" then
        add(format(L["拍卖行价格观测：%s"], PD.AuctionObservationText(entry.priceObservedAt)))
    end
    return lines
end

function PD.PlanHasSteps(plan)
    return plan and type(plan.steps) == "table" and #plan.steps > 0 or false
end
function PD.PlanCostText(plan)
    if plan.completeCost==false and (plan.total or 0)==0 then return L["材料价格待补全"] end
    return (plan.completeCost==false and "≥" or "")..RA.MoneyStr(plan.total or 0,"copper")
end

function PD.CopyPlanSummary(plan)
    if not plan or plan.planVersion ~= 2 then return end
    local s = PD.lvSummary or {}
    for _, key in ipairs({"planVersion", "status", "optimal", "feasible", "completeCost",
                           "revision", "partial", "plannedTo", "targetReached", "start", "target",
                           "expanded", "improvements", "initialTotal", "savings", "searchComplete", "budgetLimited", "searchState",
                           "stale", "cached", "settingsChanged", "referencePrices", "pricePending", "referenceRoute",
                           "auctionSupplyUnknown", "auctionSupplyObserved", "supplyComplete",
                           "formulasTotal", "formulaTotal", "formulaComplete", "formulaBlocked"}) do s[key] = plan[key] end
    s.ahOK = true -- Vendor-only plans do not need Auctionator.
    s.priced = plan.total ~= nil and plan.feasible ~= false
    PD.lvSummary = s
end

function PD.StepRecipe(st)
    if st.recipe then
        local live = {}
        for key, value in pairs(st.recipe) do live[key] = value end
        live.makes = live.item
        return live
    end
    local slug = st.profession or PD.cur
    local data = RGet(slug)
    for _, rec in ipairs(data and data.rows or {}) do
        if rec[1] == st[3] then
            local resolved = PD.RecipeData(rec, "rows", slug)
            local live = {}
            for key, value in pairs(rec) do live[key] = value end
            live[12], live[3], live[2] = resolved.mats, resolved.count, resolved.item
            live[7], live[8], live[9], live[10] = resolved.learn, resolved.yellow, resolved.green, resolved.grey
            live.clientPending, live.dataSource = resolved.clientPending, resolved.dataSource
            live.outputMin, live.outputMax, live.variableOutput = resolved.outputMin, resolved.outputMax, resolved.variableOutput
            live.outputBasis = resolved.outputBasis
            return live
        end
    end
    for _, kind in ipairs({"crafted", "enchants"}) do
        for _, rec in ipairs(data and data[kind] or {}) do
            if (kind == "enchants" and rec[14] or rec[1]) == st[3] then
                local resolved = PD.RecipeData(rec, kind, slug)
                resolved.makes = resolved.item
                return resolved
            end
        end
    end
    local leveling = LV and LV[slug]
    local rec = leveling and leveling.rinfo and leveling.rinfo[st[3]]
    if rec then
        local live = {}
        for key, value in pairs(rec) do live[key] = value end
        live.spell, live.item, live.count = st[3], live.makes, live.count or 1
        local E = ns.ProfEconomy
        if E and E.ResolveRecipe then live = E.ResolveRecipe(live, slug) end
        live.makes = live.item
        return live
    end
end
function PD.IsSpecializationQuest(st) return st and st.kind=="specialization_quest" end
function PD.SpecializationQuest(st) return st.quest or st.specializationGoal or st.goal or st end
function PD.SpecializationQuestName(st)
    local goal = PD.SpecializationQuest(st)
    local name = goal.abilityID==20222 and L["地精工程学"] or L["侏儒工程学"]
    return format(L["%s入门任务"], name)
end
function PD.SpecializationQuestSource(st)
    local goal = PD.SpecializationQuest(st)
    local npc = goal.npcName and L[goal.npcName] or ("NPC #" .. tostring(goal.npcID or "?"))
    local place = goal.zone and L[goal.zone] or ""
    if goal.x and goal.y then place = place .. format(" (%.1f, %.1f)", goal.x, goal.y) end
    local quest = goal.questName and ("《" .. L[goal.questName] .. "》 ") or ""
    return npc .. (place~="" and (" · " .. place) or "") .. " · " .. quest .. "#" .. tostring(goal.questID or "?")
end
function PD.SpecializationQuestPrerequisites(st)
    local ids={}
    for _,id in ipairs(PD.SpecializationQuest(st).prerequisiteQuestIDs or {}) do ids[#ids+1]="#"..tostring(id) end
    if #ids>0 then return format(L["先完成前置任务并与导师对话：%s"],table.concat(ids,", ")) end
end
function PD.SpecializationQuestProgressText(st)
    local E=ns.ProfEconomy
    local progress=E and E.SpecializationQuestProgress and E.SpecializationQuestProgress(PD.SpecializationQuest(st))
    if progress and progress.readyForTurnIn then return L["任务可交付"] end
    if progress and progress.inLog then return L["任务已接取"] end
end
function PD.StepRole(st)
    if PD.IsSpecializationQuest(st) then return L["专精入门任务"] end
    if st.checkpoint or st[3] == 0 then return L["实地采矿"] end
    local tags = st.tags or {}
    local leveling = tags.leveling or st.role == "level" or st.role == "both"
    local material = tags.material or st.role == "material" or st.role == "both"
    if not leveling and not material then
        material = st.reason == "material"
        leveling = not material
    end
    if leveling and material then return L["升级&中间产物"] end
    return material and L["中间产物"] or L["升级"]
end

function PD.StepRange(st)
    return format(L["%s – %s"], tostring(st[1]), tostring(st[2]))
end

function PD.PurchaseSource(entry)
    if entry.vendor or entry.source == "vendor" or entry.source == "npc" then return L["NPC购买"] end
    return L["拍卖行"]
end
function PD.StepName(st)
    if PD.IsSpecializationQuest(st) then return PD.SpecializationQuestName(st) end
    return (st.checkpoint or st[3] == 0) and L["实地采矿"] or SpellName(st[3])
end

function PD.PolicyMode(profession, spell)
    local E = ns.ProfEconomy
    local policies = E and E.GetPolicies and E.GetPolicies(PD.cur, true) or {}
    local pro = policies[profession]
    return type(pro) == "table" and (pro[spell] or pro[tostring(spell)]) or policies[profession .. ":" .. spell]
end

function PD.ChangeRecipePolicy(profession, spell, forceBan)
    local E = ns.ProfEconomy
    if not (E and E.SetPolicy) then return end
    local mode = PD.PolicyMode(profession, spell)
    local nextMode
    if forceBan or mode == nil then nextMode = "ban"
    elseif mode == "ban" then nextMode = "level" end
    E.SetPolicy(PD.cur, profession, spell, nextMode, true)
    PD.policyDirty = PD.policyDirty or {}
    PD.policyDirty[PD.cur] = true
    PD.RequestRender()
end

function PD.RowsExclusions(rows)
    local E = ns.ProfEconomy
    PushHead(rows, L["管理排除"])
    PushText(rows, L["点击配方切换：允许 → 完全禁止制作 → 仅不用来冲级 → 允许。"], 11, C_GREY)
    PushText(rows, L["修改后点击「重新计算」应用；禁止制作会同时影响高级配方的材料来源。"], 11, C_GREY)
    local entries, seen = {}, {}
    local function add(profession, spell)
        if not spell or spell == 0 then return end
        local key = profession .. ":" .. spell
        if not seen[key] then entries[#entries + 1] = {profession, spell}; seen[key] = true end
    end
    for _, st in ipairs(PD.autoSnapshotSlug == PD.cur and PD.autoSnapshot and PD.autoSnapshot.steps or {}) do add(st.profession or PD.cur, st[3]) end
    for profession, policies in pairs(E and E.GetPolicies and E.GetPolicies(PD.cur, true) or {}) do
        if type(policies) == "table" then for spell in pairs(policies) do add(profession, tonumber(spell)) end
        elseif type(profession) == "string" then
            local pro, spell = profession:match("^([^:]+):(%d+)$")
            if pro then add(pro, tonumber(spell)) end
        end
    end
    table.sort(entries, function(a, b) return a[1] == b[1] and a[2] < b[2] or a[1] < b[1] end)
    if #entries == 0 then PushText(rows, L["先计算一条路线，再点击路线配方设置排除。"], 12, C_GREY) end
    for _, entry in ipairs(entries) do
        local profession, spell = entry[1], entry[2]
        local mode = PD.PolicyMode(profession, spell)
        local pro = D.pro[profession]
        rows[#rows + 1] = {
            kind = "row", h = PD.ROW_H,
            text = SpellName(spell), icon = SpellIcon(spell),
            sub = pro and pro.name or profession,
            right = mode == "ban" and L["完全禁止制作"] or (mode == "level" and L["仅不用来冲级"] or L["允许"]),
            lines = {{L["完全禁止制作：可用购买或其他配方替代产物。"]},
                     {L["仅不用来冲级：只按后续材料需求制作，实际涨点仍计入。"], 0.7, 0.7, 0.7}},
            act = function() PD.ChangeRecipePolicy(profession, spell) end,
        }
    end
end

function PD.RoutePairContext()
    local E = ns.ProfEconomy
    if not (E and E.RouteContext) then return nil end
    local learned = PD.ProfLearned and PD.ProfLearned() or {}
    local current = learned[PD.cur] and learned[PD.cur].cur
    local opts = RA and RA.OptionsFor and RA.OptionsFor(PD.cur, current)
              or {allowSecondaryLeveling = PD.Setting("autoSecondaryLeveling")}
    return E.RouteContext(PD.cur, opts)
end

function PD.RowsRoutePartner(rows, context)
    if not context then return end
    local first = #rows + 1
    local function spanRows()
        for index = first, #rows do rows[index].span = true end
    end
    if context.unlearned and PD.Setting("autoLearnedOnly") then
        PushText(rows, L["此专业尚未学习，已忽略「仅使用已学习的配方」。"], 11, C_GREY)
    end
    if not context.requiresPartner then spanRows(); return end
    local E, target = ns.ProfEconomy, PD.cur
    local learned = PD.ProfLearned and PD.ProfLearned() or {}
    local function skillText(slug)
        local actual = learned[slug]
        if actual then
            return format(L["已学 · 技能 %d/%d"], actual.cur or 1, actual.max or actual.cur or 1)
        end
        return L["未学 · 从 1 开始"]
    end
    local selected = context.partnerValid and context.partner or nil
    local pro = selected and D.pro[selected]
    rows[#rows + 1] = {
        kind = "row", h = PD.ROW_H, col = 1,
        text = selected and format(L["搭配专业：%s"], pro and pro.name or selected)
                        or L["请选择搭配的主专业"],
        icon = pro and pro.icon,
        sub = selected and skillText(selected) or L["未学专业开启联合升级时，请先选择另一个主专业。"],
        right = selected and L["点击更改"] or nil,
        act = function()
            if PD.partnerPicker == target then PD.partnerPicker = nil
            else PD.partnerPicker = target end
            PD.exclusionsOpen = false
            PD.RequestRender()
        end,
    }
    if not selected or PD.partnerPicker == target then
        PushText(rows, L["仅使用目标专业和所选专业计算；选择后点击「重新计算」。"], 11, C_GREY)
        for _, slug in ipairs(E and E.PartnerCandidates and E.PartnerCandidates(target) or {}) do
            local candidate, partner = D.pro[slug], slug
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H, col = 1,
                text = candidate and candidate.name or partner,
                icon = candidate and candidate.icon,
                sub = skillText(partner),
                right = selected == partner and L["已选择"] or L["选择"],
                act = function()
                    if E and E.SetRoutePartner then E.SetRoutePartner(target, partner) end
                    PD.partnerUIRevision = (PD.partnerUIRevision or 0) + 1
                    PD.partnerPicker = nil
                    PD.exclusionsOpen = false
                    PD.RequestRender()
                end,
            }
        end
    end
    PushGap(rows, 4)
    spanRows()
end

function PD.PlanDiagnostics(rows, plan)
    -- Failed search branches are not a list of errors in the chosen route.
    -- Group the few actionable causes so they cannot bury the actual steps.
    local groups, order, seen = {}, {}, {}
    local hasSteps = PD.PlanHasSteps(plan)
    local branchOnly = {excluded=true, notLearned=true, cooldown=true,
        cooldownUnknown=true, availabilityUnknown=true, clientUnavailable=true,
        professionMissing=true, skillRequired=true, materialUnavailable=true,
        formulaUnavailable=true, auctionSupplyLimited=true,
        levelGap=true, clientDataPending=true, outputConflict=true,
        characterLevelRequired=true, batchDependency=true, batchSkillGap=true}
    local function add(diagnostic, blocking)
        local key = type(diagnostic) == "table" and diagnostic.code or tostring(diagnostic)
        if not key then return end
        -- These codes describe rejected candidates. A selected route can only
        -- be blocked by them when the solver explicitly marks its next stage.
        if hasSteps and not blocking and branchOnly[key] then return end
        if not hasSteps and plan.feasible and (key == "excluded"
           or key == "notLearned" or key == "cooldown" or key == "availabilityUnknown") then return end
        local identity = key
        if type(diagnostic) == "table" then
            for _, field in ipairs({"recipe", "spell", "item", "profession", "detail"}) do
                identity = identity .. ":" .. tostring(diagnostic[field] or "")
            end
        end
        if seen[identity] then return end
        seen[identity] = true
        local group = groups[key]
        if group then group.count = group.count + 1
        else groups[key] = {diagnostic = diagnostic, count = 1}; order[#order + 1] = key end
    end
    local blockers = plan.blockingDiagnostics or {}
    if hasSteps or #blockers == 0 then
        for _, diagnostic in ipairs(plan.diagnostics or {}) do add(diagnostic) end
    end
    for _, diagnostic in ipairs(blockers) do add(diagnostic, true) end
    local priority = {solverError=1, characterLevelRequired=2, professionMissing=3,
        vendorPriceUnknown=4, materialPriceUnknown=4, vendorEstimate=4, vendorQuoteChanged=4, materialUnavailable=5, levelGap=6, clientDataPending=7, outputConflict=8,
        excluded=8, notLearned=9}
    table.sort(order, function(a,b)
        local pa, pb = priority[a] or 20, priority[b] or 20
        return pa == pb and a < b or pa < pb
    end)
    local shown = 0
    for _, key in ipairs(order) do
        if shown >= 5 then break end
        local group = groups[key]
        local diagnostic = group.diagnostic
        local E = ns.ProfEconomy
        local message = E and E.DiagnosticText and E.DiagnosticText(diagnostic)
                     or (type(diagnostic) == "string" and diagnostic or (type(diagnostic) == "table" and diagnostic.message))
        if message then
            if group.count > 1 then message = format(L["%s（同类 %d 项）"], message, group.count) end
            PushText(rows, message, 11, {0.95, 0.75, 0.4})
            shown = shown + 1
        end
    end
    if #order > shown then PushText(rows, format(L["另有 %d 类限制；调整设置后重新计算。"], #order - shown), 11, C_GREY) end
end

function PD.RowsLeveling(rows)
    local lv = LV[PD.cur]
    if not lv then PD.lvSummary = nil; PD.lvRouteHead = nil return end
    PD.lvRouteHead = nil   -- 2026-10-11 用户：路线标题改工具行渲染（重新计算右侧），逐次刷新

    local _learned = PD.ProfLearned()
    local curLv = _learned and _learned[PD.cur] and _learned[PD.cur].cur or nil
    local greyOn = PD.Setting("greyPassed")

    -- ── 自动路线：设置开启 + 价格插件可用 + 算出结果 ──
    -- 乐观计数方案不依赖价格插件（2026-10-10）：其余方案仍要求 RA.Available()
    local fishRoute = PD.CookingFishingMode and PD.CookingFishingMode() or false
    local scheme = fishRoute and "fishing" or PD.SettingRaw("autoScheme")
    local autoOn = (PD.cur ~= "poisons") and (fishRoute or PD.Setting("autoRoute")) and RA
                    and (fishRoute or scheme == "cheapest" or scheme == "optim" or RA.Available()) and true or false
    local target = PD.LvTarget()
    local res
    if autoOn then
        local opts = {
            start = (PD.Setting("autoFromCurrent") and curLv) and math.max(1, curLv) or 1,
            onlyAH = PD.Setting("autoOnlyAH"),
            learnedOnly = PD.Setting("autoLearnedOnly"),
            target = target,   -- 2026-10-09 v2：模拟与缺口回填都 clamp 在目标内
            scheme = scheme,
            allowSecondaryLeveling = PD.Setting("autoSecondaryLeveling"),
        }
        if RA.OptionsFor then opts=RA.OptionsFor(PD.cur,curLv); opts.target=target end
        res = RA.Get(PD.cur, opts)
        if res and res.planVersion ~= 2 and not res.priced and scheme ~= "optim" then res = nil end
    end
    local auto = (autoOn and res) and true or false
    if res and res.planVersion == 2 then PD.autoSnapshot = res; PD.autoSnapshotSlug = PD.cur end
    local pairContext = autoOn and not fishRoute and PD.RoutePairContext() or nil
    PD.RowsRoutePartner(rows, pairContext)
    if pairContext and pairContext.requiresPartner and not pairContext.partnerValid then
        PD.lvSummary = {target = target, auto = true, autoSetting = true, scheme = scheme, ahOK = true}
        PD.CopyPlanSummary(res)
        return
    end
    if res and (res.status == "selection_required" or res.status == "recalculate_required") then
        PD.lvSummary = {target = target, auto = true, autoSetting = true, scheme = scheme, ahOK = true}
        PD.CopyPlanSummary(res)
        PushText(rows, PD.PlanStatusText(res), 12, {0.95, 0.75, 0.4})
        return
    end
    if PD.exclusionsOpen and autoOn then
        PD.lvSummary = {target = target, auto = autoOn, autoSetting = fishRoute or PD.Setting("autoRoute"), total = res and res.total}
        PD.CopyPlanSummary(res)
        PD.RowsExclusions(rows)
        return
    end
    if PD.autoPage=="history" then
        local execution=ns.ProfExecution
        local history=execution and execution.GetHistory and execution.GetHistory(PD.cur) or {}
        PD.lvSummary={target=target,auto=auto,autoSetting=fishRoute or PD.Setting("autoRoute"),scheme=res and res.scheme,ahOK=true}
        PushHead(rows,L["制作记录"])
        for i,run in ipairs(history) do
            local label=run.status=="active" and L["当前执行计划"] or L["历史执行计划"]
            PushText(rows,format(L["%s · 已成功制作%d次"],label,run.attemptsDone or 0),12,C_GREY)
            for _,entry in ipairs(execution.GetRecipeTotals(PD.cur,run.planID)) do
                if entry.casts>0 then
                    local count=0;for _,n in pairs(entry.confirmedOutputs or {}) do count=count+n end
                    rows[#rows+1]={kind="row",h=PD.ROW_H,col=1,text=PD.StepName({0,0,entry.spell,0,profession=entry.profession}),
                        right=format(L["成功制作%d次"],entry.casts),sub=format(L["已确认产出%d件；%d次制作产出待确认。"],count,entry.pendingOutputs or 0)}
                end
            end
            if i<#history then PushGap(rows,6) end
        end
        return
    end
    if autoOn and (scheme == "cheapest" or fishRoute) and not PD.PlanHasSteps(res) then
        PD.lvSummary = {target = target, auto = true, autoSetting = true, scheme = scheme, ahOK = true,
                        total = res and res.total, priced = res and res.total ~= nil}
        PD.CopyPlanSummary(res)
        PushHead(rows, res and PD.PlanStatusText(res) or L["正在计算升级路线…"])
        local progress = PD.PlanProgressText(res)
        if progress then PushText(rows, progress, 11, C_GREY) end
        local supply = PD.PlanSupplyText(res)
        if supply then PushText(rows, supply, 11, C_GREY) end
        local cached = PD.PlanCacheText(res)
        if cached then PushText(rows, cached, 11, {0.95, 0.75, 0.4}) end
        if res then PD.PlanDiagnostics(rows, res) end
        return
    end

    local execution = ns.ProfExecution
    local run = execution and execution.GetRun and execution.GetRun(PD.cur)
    if run and not run.archived then
        PushText(rows, format(L["制作记录：已成功制作 %d 次；进度按执行计划保存。"], run.attemptsDone or 0), 11, C_GREY)
    elseif auto and res and res.executionVersion ~= 1 then
        PushText(rows, L["此路线缺少执行记录信息，请重新计算后启用进度跟踪。"], 11, {0.95, 0.75, 0.4})
    end

    if PD.autoPage == "supplement" then
        local data = execution and execution.GetSupplement and execution.GetSupplement(PD.cur)
        PD.lvSummary = {target=target, auto=auto, autoSetting=fishRoute or PD.Setting("autoRoute"),
            scheme=res and res.scheme, ahOK=true, isSupplement=true,
            total=data and data.total, priced=data and data.total~=nil and data.feasible~=false}
        if not data then
            PushHead(rows, L["补料清单"])
            PushText(rows, L["HUD会显示追加需求；点击「计算补料」生成递归制材及采购清单。"], 11, C_GREY)
        elseif data.inFlight or data.status == "searching" then
            PushText(rows, L["正在计算补料…"], 12, C_GREY)
        elseif data.stale or data.status == "stale" then
            PushText(rows, L["进度已变化，请重新计算补料"], 12, {0.95,0.75,0.4})
        elseif data.feasible == false then
            PushText(rows, L["当前限制下无法补齐材料"], 12, {0.95,0.75,0.4})
            PD.PlanDiagnostics(rows, data)
        else
            local shop = {}
            for key,value in pairs(data) do shop[key]=value end
            shop.mode = "supplement"
            PD.RowsAutoShop(rows, shop)
            if data.feasible == false then PD.PlanDiagnostics(rows, data) end
        end
        return
    end

    -- ── 购物清单子页（2026-10-09 v2）：固定 / 自动共用 ──
    if PD.autoPage == "shop" then
        local data = auto and res or FixedShopData(target)
        PD.lvSummary = {
            target = target, auto = auto,
            scheme = auto and res.scheme or nil,
            autoSetting = fishRoute or PD.Setting("autoRoute"),
            ahOK = fishRoute or ((RA and RA.Available()) and true or false),
            priced = (data.priced and true) or false,
            total = data.total, snapshotAge = data.snapshotAge,
            snapshotDays = data.snapshotDays,
            matsN = #(data.mats or {}), np = CountUnpriced(data),
        }
        PD.CopyPlanSummary(res)
        PD.RowsAutoShop(rows, data)
        return
    end

    local recOf = {}
    local rr = RGet(PD.cur)
    if rr and rr.rows then
        for _, r in ipairs(rr.rows) do recOf[r[1]] = r end
    end
    -- rinfo（2026-10-08）：配方表没有的路线法术（附魔配方/魔棒）兜底 ——
    -- 生成器只落数值（learn 颜色区间/材料/产物），显示名走 SpellName。
    local rin = lv.rinfo
    for spell, ri in pairs(rin or {}) do
        if not recOf[spell] then recOf[spell] = ri end
    end

    -- 固定路线：按目标等级裁剪；自动路线已带 target
    local steps, clipped
    if auto then
        steps = res.steps
    else
        steps, clipped = ClipFixedSteps(lv.steps or {}, target)
    end
    local fixedBlocked, fixedGoalRequired
    if not auto and RA and RA.FilterFixedSpecializations then
        steps, fixedBlocked, fixedGoalRequired = RA.FilterFixedSpecializations(PD.cur, steps, {target=target})
        if fixedGoalRequired or (fixedBlocked and #fixedBlocked>0) then
            PushText(rows, L["固定攻略存在专精缺口，请切换自动计算。"], 12, {0.95, 0.75, 0.4})
            for _, gap in ipairs(fixedBlocked or {}) do
                PushText(rows, format(L["专精缺口：%s – %s"], tostring(gap.from or "?"), tostring(gap.to or "?")), 11, C_GREY)
            end
        end
    end
    -- 固定路线材料采购费用；无价时明确标记。
    local fixedSum = (not auto) and RA and RA.SummarizeSteps(steps, PD.cur,
                          { learnedOnly = PD.Setting("autoLearnedOnly") }) or nil

    -- 顶部信息卡供数（2026-10-10 B1）：PaintLvTiles 读 PD.lvSummary
    PD.lvSummary = {
        target = target, auto = auto,
        scheme = auto and res.scheme or nil,
        autoSetting = fishRoute or PD.Setting("autoRoute"),
        ahOK = fishRoute or ((RA and RA.Available()) and true or false),
        priced = auto or ((fixedSum and fixedSum.priced) and true or false),
        total = auto and res.total or (fixedSum and fixedSum.total),
        snapshotAge = auto and res.snapshotAge or (fixedSum and fixedSum.snapshotAge),
        snapshotDays = auto and res.snapshotDays or (fixedSum and fixedSum.snapshotDays),
        recipes = auto and #res.steps or nil,
        crafts = auto and (res.crafts or 0) or nil,
        vendorTotal = auto and res.vendorTotal or (fixedSum and fixedSum.vendorTotal),
        referencePrices = auto and res.referencePrices or (fixedSum and fixedSum.referencePrices),
        matsN = (not auto) and fixedSum and #(fixedSum.mats or {}) or nil,
        np = auto and CountUnpriced(res) or (fixedSum and CountUnpriced(fixedSum)) or 0,
    }
    PD.CopyPlanSummary(res)
    if fishRoute then
        PushText(rows, L["鱼类自行钓取；其他材料只使用不限量商人货物。"], 11, C_GREY)
        PushText(rows, L["鱼类不计金币成本；图纸仍按实际采购来源计费。"], 11, C_GREY)
        PushText(rows, L["鱼类为待钓数量；未达区域门槛时，先提升钓鱼技能或使用加成。"], 11, C_GREY)
        PushText(rows, L["钓鱼区域和概率为经典服指南参考；Forever 客户端能读取的配方字段优先。"], 11, C_GREY)
        if target>225 then PushText(rows, L["225 以上须先解锁大师级烹饪；蚌肉大餐任务另需非鱼材料，不属于本路线的制作材料。"], 11, C_GREY) end
    end
    if res and res.planVersion == 2 then
        PushText(rows, PD.PlanStatusText(res), 11, C_GREY)
        local progress = PD.PlanProgressText(res)
        if progress then PushText(rows, progress, 11, C_GREY) end
        local supply = PD.PlanSupplyText(res)
        if supply then PushText(rows, supply, 11, C_GREY) end
        local cached = PD.PlanCacheText(res)
        if cached then PushText(rows, cached, 11, {0.95, 0.75, 0.4}) end
        PushText(rows, L["点击配方管理排除；右键直接设为完全禁止制作，重新计算后应用。"], 11, C_GREY)
    end

    -- One row is one actual execution batch. Its cost is the batch total.
    local cntOf, costOf, cardOf = {}, {}, {}
    local rngW = PD.TextW(L["等级范围"], PD.LV_FS)
    local cntW = PD.TextW(L["制作次数"], PD.LV_FS)
    local costW = PD.TextW(L["成本"], PD.LV_FS)
    local stepW = PD.TextW(L["步骤"], PD.LV_FS)
    local cardNeed = 0
    for index, st in ipairs(steps or {}) do
        local rec = PD.StepRecipe(st) or recOf[st[3]]
        if not rec and rin then rec = rin[st[3]] end
        local riM
        if rec and (rec.mats or rec.learn) then riM = rec; rec = nil end
        local yellow = (rec and tonumber(rec[8])) or (riM and tonumber(riM.yellow))
        local certain = yellow and st[2] <= yellow
        local count = certain and format(L["%d 次制作"], st[4] or 0)
                              or format(L["~%s 次制作"], tostring(st[4] or 0))
        local cost = ""
        if auto or fixedSum then
            cost = (st.unpriced or st.cost == nil) and L["价格未知"]
                   or ((st.est and "≈" or "") .. RA.MoneyStr(st.cost))
        end
        if clipped and st._clip then count = count .. format(L[" · 按目标 %d 折算"], target) end
        if PD.IsSpecializationQuest(st) then count = L["交付任务物品"]
        elseif st.checkpoint or st[3] == 0 then count, cost = L["实地采矿"], "" end
        cntOf[st], costOf[st] = count, cost
        rngW = math.max(rngW, PD.TextW(PD.StepRange(st), PD.LV_FS))
        cntW = math.max(cntW, PD.TextW(count, PD.LV_FS))
        costW = math.max(costW, PD.TextW(cost, PD.LV_FS))
        stepW = math.max(stepW, PD.TextW(tostring(st.stepIndex or st.index or index), PD.LV_FS))
        local label = PD.StepRole(st)
        local pro = D.pro[st.profession or PD.cur]
        local cd = {text=label,kind="trainer",lines={{label},
            {(pro and pro.name) or st.profession or "", 0.7, 0.7, 0.7}}}
        local output = PD.RecipeOutputText(riM or rec)
        if output then cd.lines[#cd.lines + 1] = {output, 0.65, 0.75, 0.85} end
        if PD.IsSpecializationQuest(st) then
            cd.lines[#cd.lines+1] = {PD.SpecializationQuestSource(st)}
            local prerequisites=PD.SpecializationQuestPrerequisites(st)
            if prerequisites then cd.lines[#cd.lines+1] = {prerequisites} end
            local progress=PD.SpecializationQuestProgressText(st)
            if progress then cd.lines[#cd.lines+1] = {progress} end
            cd.lines[#cd.lines+1] = {L["实际学会对应专精后才完成此步骤。"]}
        elseif st.checkpoint or st[3] == 0 then
            cd.lines[#cd.lines+1] = {L["达到目标技能后重新计算"]}
        end
        cardOf[st] = cd
        cardNeed = math.max(cardNeed, PD.TextW(label, 10) + 2 * PD.CARD_PAD)
    end
    local rowW = PD.RIGHT_W - 2 * PD.LIST_PAD
    PD.LV_ROW_W = rowW
    PD.LV_STEP_W = math.ceil(stepW)
    PD.LV_RNG_X = PD.LV_STEP_X + PD.LV_STEP_W + PD.LV_COL_GAP
    PD.LV_CARD_FIXW = math.ceil(cardNeed)
    PD.LV_ICON_X = PD.LV_RNG_X + math.ceil(math.max(rngW, cardNeed)) + PD.TBL_RNG_GAP
    PD.LV_NAME_X = PD.LV_ICON_X + PD.TBL_ICON + PD.TBL_NAME_GAP
    PD.LV_CNT_W, PD.LV_COST_W = math.ceil(cntW), math.ceil(costW)
    PD.LV_COST_R = PD.TBL_MAT_RPAD
    PD.LV_COUNT_R = PD.LV_COST_R + PD.LV_COST_W + PD.LV_COL_GAP
    PD.LV_NAME_W = math.max(60, rowW - PD.LV_NAME_X - PD.LV_COUNT_R
                               - PD.LV_CNT_W - PD.LV_COL_GAP)

    local function FitName(s)
        return PD.Fit(s, PD.LV_FS, PD.LV_NAME_W)
    end
    local function FitR(s) return PD.Fit(s, 13, PD.COL_RW - 66) end

    if autoOn and not auto then
        -- 价格插件开了但没价格数据（未装/未扫描）→ 固定路线照常 + 顶部提示
        PushHead(rows, L["自动路线不可用"])
        PushText(rows, PD.AuctionatorStatusText(),
                 12, C_GREY)
        PushGap(rows, 4)
    end

    if steps and #steps > 0 then
        if auto then
            local warn = {}
            for _, st in ipairs(res.steps or {}) do
                if st.est then
                    warn[#warn + 1] = { format(L["缺口 %d–%d 已按估价回填（配方含无价材料，花费为下限）"],
                                          st[1], st[2]), 0.95, 0.75, 0.4 }
                end
            end
            for _, g in ipairs(res.gaps or {}) do
                warn[#warn + 1] = { format(L["缺口：%d–%d 无符合筛选的配方（可放宽设置重算）"], g[1], g[2]),
                                    0.95, 0.55, 0.45 }
            end
            local np = CountUnpriced(res)
            if np > 0 then
                warn[#warn + 1] = { format(L["含无价材料 %d 种：花费为估算下限"], np), 0.95, 0.75, 0.4 }
            end
            -- 2026-10-11 用户：标题移出滚动列表 → 工具行「重新计算」右侧（PD.lvRouteHead，
            -- PaintTool plain 分支渲染；悬停警告明细走 WarnChip plainTip 通道）
            PD.lvRouteHead = {
                text = format(fishRoute and L["%d → %d 纯钓鱼烹饪路线"] or L["%d → %d 自动路线（材料采购）"], res.start or 1, res.partial and res.plannedTo or res.target or target),
                warn = (#warn > 0) and warn or nil,
            }
            PushGap(rows, 4)
        else
            local warn = {}
            if PD.cur == "mining" then
                PushText(rows, L["固定路线的制作次数来自参考指南；材料和产量优先读取客户端，缺失时使用参考资料。"], 11, C_GREY)
            end
            if fixedSum and not fixedSum.priced then
                warn[#warn + 1] = { PD.AuctionatorStatusText(), 0.7, 0.7, 0.7 }
            elseif fixedSum then
                local np = CountUnpriced(fixedSum)
                if np > 0 then
                    warn[#warn + 1] = { format(L["含无价材料 %d 种：花费为估算下限"], np), 0.95, 0.75, 0.4 }
                end
            end
            if clipped then
                warn[#warn + 1] = { format(L["目标 %d 之后的段落已省略，跨目标段的制作数量按比例折算。"], target),
                                    0.7, 0.7, 0.7 }
            end
            local hd = { kind = "head", text = format(L["1 → %d 分段路线"], target) }
            if #warn > 0 then hd.warn = warn end
            rows[#rows + 1] = hd
            PushGap(rows, 4)
        end
        rows[#rows + 1] = { kind = "lvhead", h = 18, col = 1, noTip = true }
        for index, st in ipairs(steps) do
            local rec = PD.StepRecipe(st) or recOf[st[3]]
            local ri = nil
            if rec and (rec.mats or rec.learn) then
                ri = rec
                rec = nil
            elseif not rec then
                ri = rin and rin[st[3]] or nil
            end
            local mats = (rec and rec[12]) or (ri and ri.mats) or {}
            local nm = PD.StepName(st)
            local src = PD.LevelSrc(rec)
            if not rec and ri then
                -- rinfo 兜底配方（配方表没有的路线法术）：无图纸概念，训练师直教
                src = ri.trainer and L["向训练师学习"] or nil
            end
            if st.profession and st.profession ~= PD.cur then
                local pro = D.pro[st.profession]
                src = (pro and pro.name or st.profession) .. " · " .. (st.reason == "secondary" and L["联合升级"] or L["制作材料"])
            elseif st.reason == "material" then src = L["制作材料"] end
            if PD.IsSpecializationQuest(st) then src = PD.SpecializationQuestSource(st)
            elseif st.checkpoint or st[3] == 0 then src = L["不预先计入尚未采到的矿石"] end
            if (rec and rec.clientPending) or (ri and ri.clientPending) then src = L["客户端数据待读取"] end
            local segLo = tonumber(st[1])
            local segHi = tonumber(st[2])
            local stepLv = _learned and _learned[st.profession or PD.cur]
            local actualLv = stepLv and stepLv.cur or curLv
            local over = (actualLv ~= nil and segHi ~= nil and segHi < actualLv) or nil
            if PD.IsSpecializationQuest(st) then
                local E = ns.ProfEconomy
                over = (E and E.SpecializationKnown and E.SpecializationKnown(PD.SpecializationQuest(st).abilityID)==true) or nil
            end
            local passed = (greyOn and over) or nil
            rows[#rows + 1] = {
                kind = "row", h = PD.TBL_H, col = 1, lvstep = true,
                passed = passed, over = over,
                it = (rec and rec[2]) and { rec[2] }
                     or ((ri and ri.makes) and { ri.makes } or nil),
                icon = PD.IsSpecializationQuest(st) and SpellIcon(PD.SpecializationQuest(st).abilityID)
                    or (((not rec) and ri and not ri.makes) and SpellIcon(st[3]) or nil),
                tipExtra = (rec and rec[2])
                           and function() return PD.PriceTipLines(rec[2], rec[12]) end
                           or ((ri and ri.makes and ri.mats)
                               and function() return PD.PriceTipLines(ri.makes, ri.mats) end
                               or nil),
                -- 2026-10-09：行级提示框退役（用户：「每行有个鼠标提示框，这个提示框不要了」）
                -- → 由制作物 / 需求材料各自的物品提示框承担（PD.IconZone / PD.RowBlk）。
                noTip = true,
                stepIndex = st.stepIndex or st.index or index,
                rng = PD.StepRange(st),
                text = FitName(nm),
                src = src,
                cnt = cntOf[st] or format(L["~%s 次制作"], tostring(st[4])),
                cost = costOf[st] or "",
                role = PD.StepRole(st),
                _mats = mats,
                -- 2026-10-09 四轮：四档技能阈值（学 / 黄 / 绿 / 灰）+ 当前落点档次 +
                --   来源卡片。阈值取配方行 7..10；rinfo 兜底配方没有阈值 ⇒ 不画条。
                sbVals = (rec and (rec[7] or rec[8] or rec[9] or rec[10]))
                         and { rec[7], rec[8], rec[9], rec[10] }
                         or (ri and (ri.yellow or ri.grey))
                            and { ri.learn, ri.yellow, ri.green, ri.grey } or nil,
                -- 2026-10-09 十一轮：两根竖线 = 本行技能区间两端（左侧「36 – 45」那两个数）。
                sbLo = segLo, sbHi = segHi,
                card = cardOf[st],
                act = auto and st[3] ~= 0 and function(_, button)
                    local profession = st.profession or PD.cur
                    if button == "RightButton" then PD.ChangeRecipePolicy(profession, st[3], true)
                    else PD.exclusionsOpen = true; PD.RequestRender() end
                end or nil,
            }
            if fishRoute then
                PD.RowsFishAreas(rows, st.fishing or st.fishMaterials, st.fishingAreas, 1)
            end
        end
    end
    if PD.Setting("hlCurrent") and curLv ~= nil then
        for _, spec in ipairs(rows) do
            if spec.lvstep and spec.over == nil then
                spec.cur = true
                break
            end
        end
    end
    if res and res.planVersion == 2 then PD.PlanDiagnostics(rows, res) end
    -- 2026-10-09 v2：旧右栏（要准备的材料 / 半成品 / 商人直卖 / 购物清单跳转提示）
    -- 整体退役 —— 内容全部收进「购物清单」子页（RowsAutoShop，固定 / 自动共用）。
end

-- ── 自动路线 · 购物清单子页（2026-10-08）────────────────────────────────────
-- 材料聚合 + 底部合计（金额唯一出处，路线页不再放合计）+ 一键导入拍卖行插件
-- ── 购物清单子页（2026-10-09 v2）：固定 / 自动共用 ─────────────────────────
-- 顶部汇总块 = 预计总花费 + 一键导入按钮 + 材料合计（原底部「合计」行整体上移）；
-- 主表 = 材料 | ×采购数量·单价 | 小计。
-- data：auto → RA.Compute 结果；fixed → FixedShopData 聚合。无价格数据只显示数量。
-- ── 购物清单子页（2026-10-09 三轮定稿 B 版 · 四轮修订）：经典两栏 ───────────
-- 左列（宽，SHOP_SPLIT=0.62）：材料四列表（材料 | ×数量·单价 | 小计；商人直售材料
--   名称旁「直售」徽标）；
-- 右列（窄）：材料采购金币卡（总共需要 + 采购来源分类合计 + 一键导入）
--   + 产物收益卡（产物丢拍卖行 / 直接卖给NPC / 净花费）。
--   四轮：半成品 / 商人直卖两段退役（用户定稿）。
-- data：auto → RA.Compute 结果；fixed → FixedShopData 聚合。无价格数据只显示数量。
function PD.VendorPriceSourceText(source)
    if source == "client" then return L["购买价格来源：客户端"] end
    if source == "wowhead" then return L["购买价格来源：Wowhead"] end
end

function PD.FormulaStockText(entry)
    if entry.unlimited and entry.limited then return L["商人库存：固定售卖及限量刷新"] end
    if entry.unlimited then return L["商人库存：固定售卖（不限量）"] end
    if entry.limited then return L["商人库存：限量刷新"] end
    if entry.stockUnknown or #(entry.vendorOffers or {}) > 0
       or (entry.sources and #(entry.sources.vendors or {}) > 0) then
        return L["商人库存：性质尚未核实"]
    end
end

-- 图纸继续使用配方页的 NPC 过滤、位置表和地图选择器。
-- 不用物品卖店价代替购买报价；无报价与未核实库存分别展示。
function PD.RowsFormulaShop(rows, data)
    local formulas = data.formulas or {}
    PushHead(rows, format(L["图纸（%d 种）"], #formulas), 1)
    if #formulas == 0 then
        PushText(rows, L["没有需要购买的图纸。"], 11, C_GREY, 1)
        return
    end
    local function money(value)
        return type(value) == "number" and RA.MoneyStr(value, "copper") or L["价格未知"]
    end
    local function sourceRow(text, lines, act)
        rows[#rows + 1] = {kind = "row", h = PD.ROW_H1, col = 1, fs = 11,
            text = text, lines = lines, act = act}
    end
    for _, entry in ipairs(formulas) do
        local id, count = entry.id, entry.count or 1
        local src = entry.sources or (entry.recipe and entry.recipe.source) or {}
        local recipes, names = entry.recipes or {entry}, {}
        for _, recipe in ipairs(recipes) do
            local slug = recipe.profession or entry.profession or PD.cur
            local profession = D.pro and D.pro[slug]
            local spell = recipe.spell or entry.spell
            local name = recipe.name or recipe.recipeName
            if not name and spell then name = PD.StepName({0, 0, spell}) end
            names[#names + 1] = (profession and profession.name or slug or "?") .. " · " .. tostring(name or "?")
        end
        local priceLine = format(L["拍卖行：%s · NPC：%s"], money(entry.ahPrice), money(entry.vendorPrice))
        local stock = PD.FormulaStockText(entry)
        local lines = {{priceLine}, {format(L["需要：%d"], count)},
            {format(L["用于配方：%s"], table.concat(names, " / ")), 0.7, 0.7, 0.7}}
        for _, line in ipairs(PD.AuctionSupplyLines(entry)) do lines[#lines + 1] = line end
        if stock then lines[#lines + 1] = {stock, 0.95, 0.75, 0.4} end
        if entry.limited then lines[#lines + 1] = {L["限量商人报价仅作参考，不能保证到访时有货。"], 0.95, 0.75, 0.4} end
        if entry.blocked or entry.usable == false then
            lines[#lines + 1] = {L["此图纸尚未取得且没有可靠购买来源；固定路线仅供参考。"], 1, 0.5, 0.4}
        end
        for _, offer in ipairs(entry.vendorOffers or {}) do
            local quantity = offer.quantity or offer.bundleSize or 1
            local unit = offer.unit or (type(offer.price) == "number" and offer.price / quantity)
            local name = offer.name or offer.npcName
            if not name then
                for _, vendor in ipairs(PD.VendorListOf(src)) do
                    if vendor.id == offer.npcID then name = vendor.name; break end
                end
            end
            name = name or (offer.npcID and format(L["商人 NPC #%d"], offer.npcID)) or L["商人"]
            local limited=offer.limited or offer.unlimited==false or offer.stockStatus=="limited"
                or type(offer.stock)=="number" and offer.stock>=0
            local stockText = offer.unlimited and L["固定售卖（不限量）"]
                or (limited and L["限量刷新"] or L["库存性质尚未核实"])
            lines[#lines + 1] = {format(L["%s：%s · %s"], name, money(unit), stockText), 0.7, 0.7, 0.7}
            local priceSource = PD.VendorPriceSourceText(offer.priceSource)
            if priceSource then lines[#lines + 1] = {priceSource, 0.7, 0.7, 0.7} end
        end
        local selected = entry.source or entry.sourceType
        local tag = selected == "vendor" and L["NPC购买"]
            or ((selected == "ah" or selected == "auction") and L["拍卖行"] or L["尚无购买来源"])
        rows[#rows + 1] = {kind = "row", h = PD.ROW_H, col = 1, it = id and {id} or nil,
            text = PD.Fit(id and DG.ItemName(id) or L["未知图纸"], 13, (PD.splitLW or PD.COL_LW) - 130),
            sub = format(L["用于配方：%s"], table.concat(names, " / ")),
            tag = {text = tag}, right = format("×%d", count),
            right2 = (entry.unpriced or type(entry.cost) ~= "number") and L["价格未知"] or money(entry.cost),
            lines = lines, tipExtra = function() return lines end}
        PushText(rows, priceLine, 11, C_GREY, 1)
        if stock then PushText(rows, stock, 11, C_GREY, 1) end
        if entry.limited then PushText(rows, L["限量商人报价仅作参考，不能保证到访时有货。"], 11, C_GREY, 1) end
        local parts = PD.SourceParts(src)
        local hasSource = false
        for _, part in ipairs(parts) do
            if not part.vendor then
                sourceRow(part.text, {{part.text}})
                hasSource = true
            end
        end
        if entry.questOnly then sourceRow(L["仅任务来源"], {{L["仅任务来源"]}}); hasSource = true end
        for _,quest in ipairs(src.quests or {}) do
            local title=quest.name or (quest.id and ("#"..quest.id)) or L["任务"]
            local drop={drops={{id=quest.npcID,npc=quest.npc or title,zone=quest.zone}}}
            local entries=PD.DropEntries(drop)
            local act=quest.loc and function() PD.MarkVendorLoc(quest.loc) end
                or (#entries>0 and PD.DropAct(drop) or nil)
            sourceRow(format(L["任务：%s"],title).." · "..(act and L["点击定位"] or L["暂无坐标"]),
                {{title}},act)
            hasSource=true
        end
        if #PD.VendorListOf(src) > 0 then
            local text
            for _, part in ipairs(parts) do if part.vendor then text = part.text end end
            local loc = PD.VendorLocOf(src)
            sourceRow((text or L["商人"]) .. " · " .. (loc and L["点击定位"] or L["暂无坐标"]),
                      PD.VendorLines(src), loc and PD.VendorAct(src) or nil)
            hasSource = true
        end
        if src.drops and #src.drops > 0 then
            local locs = PD.DropEntries(src)
            sourceRow(format(L["掉落 %d 处"], #src.drops) .. " · " .. (#locs > 0 and L["点击定位"] or L["暂无坐标"]),
                      PD.DropLines(src), #locs > 0 and PD.DropAct(src) or nil)
            hasSource = true
        end
        if not hasSource then sourceRow(L["来源尚未收录 · 暂无坐标"], {{L["来源尚未收录 · 暂无坐标"]}}) end
        if entry.blocked or entry.usable == false then
            PushText(rows, L["此图纸尚未取得且没有可靠购买来源；固定路线仅供参考。"], 11, {1, 0.5, 0.4}, 1)
        end
    end
end

function PD.RowsAutoShop(rows, data)
    if data.mode=="supplement" and RA and RA.ValidateVendorQuotes then
        local execution=ns.ProfExecution
        local base=execution and execution.GetPlan and execution.GetPlan(PD.cur)
        if base then
            local current=RA.ValidateVendorQuotes(base)
            if RA.ValidateSpecializationPlan then current=RA.ValidateSpecializationPlan(current,PD.cur) end
            if current.status=="recalculate_required" then data=current end
        end
    end
    if RA and RA.ValidateVendorQuotes then data=RA.ValidateVendorQuotes(data) end
    if RA and RA.ValidateSpecializationPlan then data=RA.ValidateSpecializationPlan(data,PD.cur) end
    if data.status=="recalculate_required" then
        PushText(rows,PD.PlanStatusText(data),12,{0.95,0.75,0.4})
        PD.PlanDiagnostics(rows,data)
        return
    end
    local mode = data.mode or "auto"
    local mats = data.mats or {}
    local lw = PD.splitLW or PD.COL_LW
    local priced = (data.planVersion == 2 and data.total ~= nil and data.feasible ~= false) or (data.priced and true) or false

    local title
    if mode == "supplement" then
        title = L["补料清单"]
    elseif mode == "auto" then
        title = L["购物清单（自动路线）"]
    else
        title = format(L["购物清单（固定路线 1–%d）"], data.target or 300)
    end
    -- ── 左列：材料主表 ──
    PushHead(rows, title, 1)
    if #mats == 0 and #(data.fishMaterials or {}) == 0 then PushText(rows, L["没有需要准备的材料。"], 12, C_GREY, 1) end
    if #(data.fishMaterials or {}) > 0 then
        PushHead(rows, L["自行钓取（不计入采购）"], 1)
        PushText(rows, L["鱼类不计金币成本；图纸仍按实际采购来源计费。"], 11, C_GREY, 1)
        for _, fish in ipairs(data.fishMaterials) do PD.RowsFishAreas(rows, {fish}, nil, 1) end
        PushGap(rows, 4, 1)
    end
    PushHead(rows, format(L["材料（%d 种）"], #mats), 1)
    local firstAt = data.firstAt or {}
    for _, e in ipairs(mats) do
        local id, n = e.id or e[1], e.count or e[2]
        local fa = firstAt[id]
        local seg
        if fa then
            for _, st in ipairs(data.executionSteps or data.steps or {}) do
                if st[1] <= fa and fa <= st[2] then seg = st break end
            end
        end
        local sub
        if seg then sub = format(L["首用于 %d–%d 段"], seg[1], seg[2]) end
        -- 商人直售材料：名称旁打绿色「直售」徽标（HUD 药丸样式），sub 不再写文字（2026-10-09 四轮）
        local tag = { text = PD.PurchaseSource(e) }
        local right, right2
        if priced and not e.unpriced then
            right = format(L["×%d · %s"], n or 0, RA.MoneyStr(e.unit, "copper"))
            right2 = RA.MoneyStr(e.cost, "copper")
        else
            right = format("×%d", n or 0)
            right2 = e.unpriced and L["价格未知"] or nil
        end
        local tip = { { format(L["需要：%d"], e.need or n or 0) },
                      e.unpriced
                          and { e.vendor and L["NPC购买价格尚未配置。"] or L["价格未知（Auctionator 无记录）"], 0.95, 0.75, 0.4 }
                          or { format(L["约 %s"], RA.MoneyStr(e.cost, "copper")), 1, 0.82, 0 },
                      { sub or "", 0.7, 0.7, 0.7 } }
        for _, line in ipairs(PD.AuctionSupplyLines(e)) do tip[#tip + 1] = line end
        if e.vendor then
            tip[#tip + 1] = { L["商人直售（军需官处直购，无需拍卖行）"], 0.42, 0.94, 0.62 }
            if e.npcID then tip[#tip + 1] = { format(L["商人 NPC #%d"], e.npcID), 0.7, 0.7, 0.7 } end
            if e.bundleSize then tip[#tip + 1] = { format(L["每组 %d 件"], e.bundleSize), 0.7, 0.7, 0.7 } end
            local priceSource = PD.VendorPriceSourceText(e.priceSource or e.quoteSource)
            if priceSource then tip[#tip + 1] = { priceSource, 0.7, 0.7, 0.7 } end
            if e.reference and e.verifiedAt then tip[#tip + 1] = { format(L["报价核验：%s"], tostring(e.verifiedAt)), 0.7, 0.7, 0.7 } end
        end
        rows[#rows + 1] = {
            kind = "row", h = PD.ROW_H, col = 1, it = { id },
            text = PD.Fit(DG.ItemName(id), 13, lw - 130),
            sub = sub,
            tag = tag,
            right = right,
            right2 = right2,
            lines = tip,
        }
    end
    -- 单独分组，材料数量、材料价格和图纸价格都可独立检查。
    if data.formulas then PD.RowsFormulaShop(rows, data) end

    -- ── 右列：金币卡（sec 组 + 金色底）──
    local totalN = 0
    for _, e in ipairs(mats) do totalN = totalN + (e.count or e[2] or 0) end
    -- 快照年龄：秒级真实扫描时间戳优先，天级库差回退
    local snapSec, snapDays = data.snapshotAge, data.snapshotDays
    -- 2026-10-10 用户：右列两张金卡整体下移 8（h=8>4 不进金卡底色标记，纯位移）
    PushGap(rows, 8, 2)
    PushHead(rows, L["总共需要"], 2)
    if priced then
        PushText(rows, PD.PlanCostText(data), 20, C_GOLD, 2)
    else
        PushText(rows, PD.AuctionatorStatusText(), 12, C_GREY, 2)
    end
    PushText(rows, format(L["共 %d 种材料 · 合计 %d 件"], #mats, totalN), 11, C_GREY, 2)
    if #(data.fishMaterials or {}) > 0 then
        local totalFish = 0
        for _, fish in ipairs(data.fishMaterials) do totalFish = totalFish + (fish.count or fish.need or 0) end
        PushText(rows, format(L["另需自行钓取 %d 种鱼 · 合计 %d 条"], #data.fishMaterials, totalFish), 11, C_GREY, 2)
    end
    if #(data.formulas or {}) > 0 then
        PushText(rows, format(L["另需 %d 种未学图纸"], #data.formulas), 11, C_GREY, 2)
        local formulaTotal = data.formulasTotal or data.formulaTotal
        if type(formulaTotal) == "number" then
            local amount=data.formulaComplete==false and (formulaTotal==0 and L["价格未知"] or ("≥"..RA.MoneyStr(formulaTotal,"copper")))
                or RA.MoneyStr(formulaTotal,"copper")
            PushText(rows, format(L["图纸支出：%s"], amount), 11, C_GREY, 2)
        end
        if data.formulaComplete == false or data.formulaBlocked then
            PushText(rows, L["图纸获取尚未全部确认；当前总额只包含已知支出。"], 11, {0.95, 0.75, 0.4}, 2)
        end
    end
    local vendorOnly = #mats > 0 or #(data.formulas or {}) > 0
    for _, entry in ipairs(mats) do
        if not (entry.vendor or entry.source == "vendor" or entry.source == "npc") then vendorOnly = false; break end
    end
    for _, entry in ipairs(data.formulas or {}) do
        if entry.source ~= "vendor" and entry.source ~= "npc" then vendorOnly = false; break end
    end
    local atxt
    if data.planVersion == 2 then
        atxt = PD.PlanStatusText(data)
    elseif vendorOnly then
        -- Vendor quotes have no Auctionator scan age.
    elseif snapSec then
        if snapSec < 60 then
            atxt = L["价格快照：刚刚（Auctionator）"]
        elseif snapSec < 90 * 60 then
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
    if atxt then PushText(rows, atxt, 11, C_GREY, 2) end
    local progress = PD.PlanProgressText(data)
    if progress then PushText(rows, progress, 11, C_GREY, 2) end
    local supply = PD.PlanSupplyText(data)
    if supply then PushText(rows, supply, 11, C_GREY, 2) end
    local cached = PD.PlanCacheText(data)
    if cached then PushText(rows, cached, 11, {0.95, 0.75, 0.4}, 2) end
    if priced then
        -- 材料与图纸采购分类合计：拍卖行 / 商人，相加 = 总共需要。
        rows[#rows + 1] = { kind = "row", h = PD.ROW_H1, col = 2,
                            text = L["拍卖行购入"], right = RA.MoneyStr(data.ahTotal or 0, "copper") }
        rows[#rows + 1] = { kind = "row", h = PD.ROW_H1, col = 2,
                            text = L["商人直售购入"], right = RA.MoneyStr(data.vendorTotal or 0, "copper") }
        if data.completeCost == false then
            PushText(rows, L["采购价格或图纸现货尚未全部核实，当前金额是已知支出。"], 11, {0.95, 0.75, 0.4}, 2)
        end
        local np = CountUnpriced(data)
        if np > 0 then
            PushText(rows, format(L["含无价材料 %d 种：总花费为估算下限"], np), 11,
                     { 0.95, 0.75, 0.4 }, 2)
        end
    end
    rows[#rows + 1] = {
        kind = "row", h = PD.ROW_H1, col = 2,
        text = L["一键导入 Auctionator →"],
        lines = { { L["点击在 Auctionator 生成购物清单；同名清单会被覆盖"], 1, 0.82, 0 } },
        act = function() PD.ShopImport(data) end,
    }
    -- 金币卡组打 sec + goldSec → PaintRows 用金色底卡片包住（含头行与导入行之间的 gap）
    PD.hasSecs = true
    for i = #rows, 1, -1 do
        local sp = rows[i]
        if sp.kind == "gap" and sp.col == 2 and sp.h <= 4 then
            sp.sec = 1
            sp.goldSec = true
        elseif sp.kind ~= "gap" and sp.col == 2 then
            sp.sec = 1
            sp.goldSec = true
        else
            break
        end
    end
    PD.secCount = 1

    -- ── 右列：产物收益卡（2026-10-09 四轮；第二张金卡，与金币卡净距 8）──
    if priced then
        -- 与上方金币卡之间的净距 = 卡片净距标准 8（PD.SEC_GAP，2026-09-24 定稿）。
        -- 相邻两张 sec 金卡：上卡底边 = 行底 + SEC_PAD，下卡顶边 = 行顶 − SEC_PAD，
        -- 之间还有一次行推进 +2 ⇒ 净距 = gap + 2 − 2*SEC_PAD。要净距 = SEC_GAP
        -- 即 gap = SEC_GAP + 2*SEC_PAD − 2 = 14 —— 别在这里另写死间距数。
        -- （PD.OV_GUT = SEC_GAP + 2*SEC_PAD 只用于跨列外槽；拿它当本处间距净距会变 10。）
        PushGap(rows, PD.SEC_GAP + 2 * PD.SEC_PAD - 2, 2)
        PushHead(rows, L["产物收益"], 2)
        -- 产物丢拍卖行收益 / 直接卖给NPC收益（数据层 SummarizeCore 按产物 itemID × 产量 × 次数累计）
        rows[#rows + 1] = { kind = "row", h = PD.ROW_H1, col = 2,
                            text = L["产物丢拍卖行收益"],
                            right = RA.MoneyStr(data.productAH or 0, "copper") }
        rows[#rows + 1] = { kind = "row", h = PD.ROW_H1, col = 2,
                            text = L["直接卖给NPC收益"],
                            right = RA.MoneyStr(data.productNPC or 0, "copper") }
        -- 净花费 = 总共需要 − 产物丢拍卖行收益（负数 = 倒卖还净赚）
        local net = (data.total or 0) - (data.productAH or 0)
        if net >= 0 then
            rows[#rows + 1] = { kind = "row", h = PD.ROW_H1, col = 2,
                                text = L["净花费（产物丢拍卖行）"],
                                right = RA.MoneyStr(net, "copper") }
        else
            rows[#rows + 1] = { kind = "row", h = PD.ROW_H1, col = 2,
                                text = L["净花费（产物丢拍卖行）"],
                                right = format(L["净赚 %s"], RA.MoneyStr(-net, "copper")) }
        end
        if data.productPartial then
            PushText(rows, L["部分产物无拍卖行价格：收益为估算下限"], 11,
                     { 0.95, 0.75, 0.4 }, 2)
        end
        PushGap(rows, 2, 2)
        -- 第二张金卡组标记（金币卡 = 组 1，本卡 = 组 2；组间 gap=OV_GUT 断链）
        for i = #rows, 1, -1 do
            local sp = rows[i]
            if sp.kind == "gap" and sp.col == 2 and sp.h <= 4 then
                sp.sec = 2
                sp.goldSec = true
            elseif sp.kind ~= "gap" and sp.col == 2 then
                sp.sec = 2
                sp.goldSec = true
            else
                break
            end
        end
        PD.secCount = 2
    end
end

-- 材料购物清单导入拍卖行插件（固定 / 自动共用）
function PD.ShopImport(data)
    if data and data.mode=="supplement" and RA and RA.ValidateVendorQuotes then
        local execution=ns.ProfExecution
        local base=execution and execution.GetPlan and execution.GetPlan(PD.cur)
        if base and RA.ValidateVendorQuotes(base).status=="recalculate_required" then return end
        if base and RA.ValidateSpecializationPlan and RA.ValidateSpecializationPlan(base,PD.cur).status=="recalculate_required" then return end
    end
    if RA and RA.ValidateVendorQuotes then data=RA.ValidateVendorQuotes(data) end
    if data and RA and RA.ValidateSpecializationPlan then data=RA.ValidateSpecializationPlan(data,PD.cur) end
    if not data or data.status=="selection_required" or data.status=="recalculate_required"
        or data.feasible==false or data.inFlight or (data.mode=="supplement" and data.stale) then return end
    local AB = ns.AuctionBridge
    if not (AB and AB.DoImport) then return end
    if data.professionPolicy == 1 then
        local context = PD.RoutePairContext()
        if context then
            local partner = context.requiresPartner and context.partner or nil
            if (context.requiresPartner and not context.partnerValid)
               or (data.targetUnlearned == true) ~= context.unlearned
               or data.secondaryProfession ~= partner then return end
        end
    end
    local p = D.pro[PD.cur]
    local items = {}
    for _, e in ipairs(data.mats or {}) do
        if not e.vendor and not e.unpriced and (data.planVersion ~= 2 or e.source == "ah" or e.source == "auction") then
            local nm = DG.ItemName(e.id or e[1])
            if nm then items[#items + 1] = { name = nm, need = e.need or e.count or e[2] } end
        end
    end
    for _, entry in ipairs(data.formulas or {}) do
        if entry.id and not entry.vendor and not entry.known and not entry.unpriced and not entry.blocked and entry.usable ~= false
           and (entry.source == "ah" or entry.source == "auction") then
            local name = DG.ItemName(entry.id)
            if name then items[#items + 1] = {name = name, need = entry.count or 1} end
        end
    end
    AB.DoImport(p and p.name or "?", items)
end

-- ── 升级页签工具行（2026-10-10 B1 改版）：模式 / 总花费 / 目标等级 / 价格快照
--    收进顶部信息卡（PD.PaintLvTiles）；工具行只剩 视图切换 + 重算。 ──────
function PD.LevelTool()
    local fishRoute = PD.CookingFishingMode and PD.CookingFishingMode() or false
    local list = {
        -- 间距走默认 TOOL_GAP=8（2026-10-10 标准：按钮↔按钮/组↔组全 8，
        -- 对齐掉落页显示方式切换组 LOOT_VIEW_GAP 同款口径），不写死 2/14。
        { key = "page_route", text = L["路线"],     on = PD.autoPage ~= "shop" and PD.autoPage ~= "supplement" and PD.autoPage ~= "history" },
        { key = "page_shop",  text = L["购物清单"], on = PD.autoPage == "shop" },
        { key = "recalc",     text = L["重新计算"] },
    }
    if PD.policyDirty and PD.policyDirty[PD.cur] then list[3].text = L["重新计算（应用排除）"] end
    local execution = ns.ProfExecution
    local run = execution and execution.GetRun and execution.GetRun(PD.cur)
    if run and not run.archived then
        list[#list + 1] = {key="page_supplement", text=L["补料清单"], on=PD.autoPage=="supplement"}
        list[#list + 1] = {key="calculate_supplement", text=L["计算补料"]}
    end
    if execution and execution.GetHistory and #execution.GetHistory(PD.cur)>0 then
        list[#list+1]={key="page_history",text=L["制作记录"],on=PD.autoPage=="history"}
    end
    if PD.cur == "cooking" then
        list[#list + 1] = {key = "cooking_fishing", text = fishRoute and L["普通路线"] or L["纯钓鱼"], on = fishRoute}
    end
    if PD.cur == "poisons" then
        local keep = {}
        for _, b in ipairs(list) do
            if b.key ~= "recalc" then keep[#keep + 1] = b end
        end
        list = keep
    else
        if fishRoute or PD.Setting("autoRoute") then
            local pairContext = not fishRoute and PD.RoutePairContext() or nil
            if pairContext and pairContext.requiresPartner then
                list[#list + 1] = {key = "partner", text = L["搭配专业"], on = PD.partnerPicker == PD.cur}
            end
            list[#list + 1] = {key = "exclusions", text = PD.exclusionsOpen and L["返回路线"] or L["管理排除"], on = PD.exclusionsOpen}
            if PD.exclusionsOpen then list[#list + 1] = {key = "restore_all", text = L["全部恢复"]} end
            local plan = PD.autoSnapshotSlug == PD.cur and PD.autoSnapshot or nil
            if plan and (plan.searchState or plan).status == "searching" then
                list[#list + 1] = {key = "stop_search", text = L["停止优化"]}
            end
        end
        if PD.cur == "mining" then list[#list + 1] = {key = "gather_mode", text = L["切换到采集路线"]} end
    end
    return list, function(k)
        if k == "cooking_fishing" then
            ProfDB().cookingRoute = fishRoute and "standard" or "fishing"
            PD.exclusionsOpen, PD.partnerPicker = false, nil
        elseif k == "page_route" then
            PD.autoPage = "route"
        elseif k == "page_shop" then
            PD.autoPage = "shop"
        elseif k == "page_supplement" then
            PD.autoPage = "supplement"
            PD.exclusionsOpen=false
        elseif k == "page_history" then
            PD.autoPage = "history"
            PD.exclusionsOpen=false
        elseif k == "calculate_supplement" then
            PD.exclusionsOpen=false
            if execution and execution.CalculateSupplement then
                execution.CalculateSupplement(PD.cur, function()
                    if PD.cur then PD.RequestRender() end
                end)
            end
            PD.autoPage = "supplement"
        elseif k == "recalc" then
            local E = ns.ProfEconomy
            if E and E.ApplyPolicies then E.ApplyPolicies(PD.cur)
            elseif RA then RA.Invalidate() end
            if PD.policyDirty then PD.policyDirty[PD.cur] = nil end
            if RA and RA.Recalculate then
                local learned = PD.ProfLearned and PD.ProfLearned() or {}
                local current = learned[PD.cur] and learned[PD.cur].cur
                local opts = RA.OptionsFor and RA.OptionsFor(PD.cur, current) or nil
                RA.Recalculate(PD.cur, opts)
            end
        elseif k == "exclusions" then
            PD.exclusionsOpen = not PD.exclusionsOpen
            PD.partnerPicker = nil
        elseif k == "partner" then
            if PD.partnerPicker == PD.cur then PD.partnerPicker = nil
            else PD.partnerPicker = PD.cur end
            PD.exclusionsOpen = false
        elseif k == "restore_all" then
            local E = ns.ProfEconomy
            if E and E.ResetPolicies then E.ResetPolicies(PD.cur) end
            PD.policyDirty = PD.policyDirty or {}; PD.policyDirty[PD.cur] = true
        elseif k == "stop_search" then
            if RA and RA.Cancel then RA.Cancel(PD.cur) end
        elseif k == "gather_mode" then
            ProfDB().gatherMode = "gather"
            PD.exclusionsOpen = false
        end
        PD.RequestRender()
    end
end

function PD.RowsSettings(rows)
    PushHead(rows, L["升级页设置"])
    PushGap(rows, 2)
    PushText(rows, L["这里的开关只作用于「升级」页签里的制作路线（升级路线表），不影响其他页签。"], 11, C_GREY)
    PushGap(rows, 4)
    if PD.cur=="engineering" then
        local E=ns.ProfEconomy
        if E and E.GetEngineeringSpecialization and E.SetEngineeringSpecialization then
            PushHead(rows, L["工程专精计划（本角色）"])
            PushText(rows, L["默认不计划专精；已学会的专精始终可用。目标达到 200 时，所选专精包含入门任务。"], 11, C_GREY)
            local choice=E.GetEngineeringSpecialization()
            local context=E.GetEngineeringSpecializationContext and E.GetEngineeringSpecializationContext()
            if context and (context.actual=="goblin" or context.actual=="gnomish") then
                local actual=context.actual=="goblin" and L["地精工程学"] or L["侏儒工程学"]
                PushText(rows,format(L["当前专精：%s"],actual),11,C_GREY)
            end
            if context and context.selectionConflict then
                PushText(rows,L["所选专精与已学专精不同；请调整选择后重新计算。"],11,{0.95,0.75,0.4})
            end
            for _, option in ipairs({{"none",L["不开启新专精"]},{"goblin",L["地精工程学"]},{"gnomish",L["侏儒工程学"]}}) do
                local value=option[1]
                rows[#rows+1]={kind="row",h=28,col=1,noTip=true,text=(choice==value and "● " or "○ ")..option[2],
                    act=function()
                        E.SetEngineeringSpecialization(value)
                        PD.engineeringUIRevision=(PD.engineeringUIRevision or 0)+1
                        PD.RequestRender()
                    end}
            end
            PushText(rows,L["改变选择后请重新计算；不会替换正在执行的旧计划。"],11,C_GREY)
            PushGap(rows,6)
        end
    end
    local defs = {
        { k = "greyPassed", name = L["已过段落灰显"],
          desc = L["上限低于当前技能的段落（如 42 级时的 1~15）整行灰显"],
          d1 = L["开启后：段名、出处、数量文字变暗，配方与材料图标去饱和，不再作为下一个要关注的制作目标；"],
          d2 = L["关闭后：所有段落恢复常规配色，不做灰显处理。"] },
        { k = "hlCurrent", name = L["当前段落高亮"],
          desc = L["上下限跨着当前技能的段落（如下一个要练的 15~58）加一圈主题色外框"],
          d1 = L["开启后：下一个要练的段落四周显示一圈主题绿描边，一眼定位当前制作路线；外框只是描边，不影响行内容与点击。"],
          d2 = L["关闭后：不显示外框，该段落样式与其他行一致。"] },
        { k = "autoRoute", name = L["自动计算路线（材料采购）"],
          desc = L["关闭显示固定参考路线；开启比较商人、拍卖行和自制材料。"],
          d1 = L["不使用背包或银行库存，只计算路线需要采购的材料。"],
          d2 = L["路线与购物清单在「升级」页签顶部的按钮切换。"] },
        { k = "autoOnlyAH", name = L["只使用拍卖行可购材料的配方"],
          desc = L["材料在拍卖行/商人都查不到价格时，该配方不参与计算（商人直售材料不受限）"],
          d1 = L["开启：路线更可靠，但可能出现无配方可用的缺口区间。"],
          d2 = L["关闭：可查看含缺价材料的方案，但不会把未知费用计为零。"] },
        { k = "autoLearnedOnly", name = L["仅使用已学习的配方"],
          desc = L["只在本角色已学会的配方中挑选；未学专业不受此限制。"],
          d1 = L["开启：路线里的每一段都能立刻开做。"],
          d2 = L["关闭：允许使用未学配方，计入材料与所需图纸采购成本。"] },
        { k = "autoFromCurrent", name = L["从当前技能开始计算"],
          desc = L["开启 = 只算当前技能到 300 的路线；关闭 = 从 1 全量重算整条路线（预估全程花费）"],
          d1 = L["开启：适合练级中途打开手册直接照着做。"],
          d2 = L["关闭：查看从零开始的最优路线与总花费。"] },
        { k = "autoSecondaryLeveling", name = L["允许联合升级另一主专业"],
          desc = L["总支出更低时，将另一主专业升到制作所需材料的最低等级。"],
          d1 = L["默认关闭：仍可使用另一主专业当前能制作的材料。"],
          d2 = L["开启后计入另一专业所需的材料费用，最高 300；查看未学专业时需先选择搭配主专业。"] },
    }
    if PD.cur == "poisons" then
        local keep = { greyPassed = true, hlCurrent = true }
        local filt = {}
        for _, d in ipairs(defs) do
            if keep[d.k] then filt[#filt + 1] = d end
        end
        defs = filt
    elseif PD.SettingRaw("autoScheme") == "cheapest" then
        local filt = {}
        for _, d in ipairs(defs) do if d.k ~= "autoOnlyAH" then filt[#filt + 1] = d end end
        defs = filt
    end
    for _, d in ipairs(defs) do
        rows[#rows + 1] = {
            kind = "row", h = 40, col = 1,
            text = d.name,
            togKey = d.k,
            help = { { d.name }, { d.desc, 0.7, 0.7, 0.7 }, { d.d1, 0.7, 0.7, 0.7 }, { d.d2, 0.7, 0.7, 0.7 } },
        }
        PushGap(rows, 6)
    end
end

function PD.PlaceSettingsToggles(rows)
    local n = math.min(#(rows or {}), PD.ROW_CAP)
    local ti = 0
    for i = 1, n do
        local spec = rows[i]
        local rr = PD.rows[i]
        if PD.setOpen and spec.togKey and rr then
            ti = ti + 1
            local tg = PD.setToggles[ti]
            tg:ClearAllPoints()
            tg:SetPoint("RIGHT", rr, "RIGHT", -8, 0)
            tg:SetFrameLevel((rr:GetFrameLevel() or 0) + 10)
            tg:SetChecked(PD.Setting(spec.togKey))
            tg.__key = spec.togKey
            tg:Show()
            local hp = PD.setHelps[ti]
            if hp then
                hp:ClearAllPoints()
                hp:SetPoint("LEFT", rr.a, "RIGHT", 6, -1)
                hp:SetFrameLevel((rr:GetFrameLevel() or 0) + 10)
                hp.__tip = spec.help
                hp:SetShown(spec.help and true or false)
            end
        end
    end
    for j = ti + 1, #PD.setToggles do PD.setToggles[j]:Hide() end
    for j = ti + 1, #PD.setHelps do PD.setHelps[j]:Hide() end
end

-- ══ 板条箱 / 工匠文书（2026-10-11）══════════════════════════════════════
-- 左列 = 目录行（单选，金描边 = RowBorder），右列 = 选中条目详情。
-- 价格走 RA 只读口（价格插件扫描）；名字 / 图标运行期由客户端给出。

PD.CRATE_SPLIT = 0.60
PD.CRATE_OWN_R = 100
PD.OWN_SHIFT = 0.08
function PD.OwnR()
    local lw = tonumber(PD.splitLW) or tonumber(PD.COL_LW) or 0
    return PD.CRATE_OWN_R + math.floor(lw * PD.OWN_SHIFT)
end
PD.crateSel = nil       -- 选中箱（crate.id）
PD.writSel = nil        -- 选中文书（writ.quest）
PD.crateSort = "total"
PD.writSort = "total"
PD.plunderSel = nil
PD.plunderSort = "cost"
PD.recipeSort = nil
PD.recipeSortDesc = false

local PLUNDER_CATS = {
    ingot = L["锭与石材"], herb = L["草药"], leather = L["皮革"],
    enchant = L["附魔材料"], potion = L["药水与药剂"], food = L["食物"],
    bandage = L["绷带"], device = L["炸弹与装置"], gear = L["武器与护甲"],
    other = L["其他"], mismatch = L["数据不一致"],
}

local CRATE_TIERS = { L["学徒"], L["熟练"], L["专家"], L["工匠"] }
local CRATE_GREEN = { 0.25, 0.85, 0.25 }

local function CrateOptCost(itemId, qty)
    local p = RA.AHPriceOf and RA.AHPriceOf(itemId) or nil
    if not p then return nil end
    return p * (qty or 1)
end

local function CrateSnapText()
    if not (RA.HasPriceData and RA.HasPriceData()) then
        return PD.AuctionatorStatusText()
    end
    local sec = RA.SnapshotAge and RA.SnapshotAge() or nil
    if not sec then return L["价格快照年龄未知（Auctionator）"] end
    if sec >= 48 * 3600 then
        return L["价格快照数据过期，距离上次扫描超过 2 天上限，需要重新扫描"]
    end
    if sec < 60 then return L["价格快照：刚刚（Auctionator）"] end
    if sec < 90 * 60 then
        return format(L["价格快照 %d 分钟前（Auctionator）"], math.max(1, math.floor(sec / 60 + 0.5)))
    end
    if sec < 48 * 3600 then
        return format(L["价格快照 %d 小时前（Auctionator）"], math.max(1, math.floor(sec / 3600 + 0.5)))
    end
    return format(L["价格快照 %d 天前（Auctionator）"], math.floor(sec / 86400 + 0.5))
end

local function CrateMetaRow(rows, label, val, valOk, fs)
    rows[#rows + 1] = {
        kind = "row", col = 2, h = PD.ROW_H1, fs = fs,
        text = label,
        right = valOk and RA.MoneyStr(val) or "—",
        rightColor = valOk and C_TEXT or C_GREY,
    }
end

function PD.CrateRows(rows)
    local list = CD.crates or {}
    if not PD.crateSel and list[1] then PD.crateSel = list[1].id end
    local sel = PD.crateSel
    local owns, bests = {}, {}
    for i, c in ipairs(list) do
        local own = RA.AHPriceOf and RA.AHPriceOf(c.id) or nil
        local mat
        for _, o in ipairs(c.opts or {}) do
            local v = CrateOptCost(o[1], o[2])
            if v and (not mat or v < mat) then mat = v end
        end
        owns[i] = own
        bests[i] = (own and mat) and (own + mat) or nil
    end
    local mode = PD.crateSort
    local order = {}
    for i = 1, #list do order[i] = i end
    if mode then
        local key = (mode == "own") and owns or bests
        table.sort(order, function(a, b)
            local ca, cb = key[a], key[b]
            if ca and cb then return ca < cb end
            if ca or cb then return ca ~= nil end
            return (list[a].id or 0) < (list[b].id or 0)
        end)
    end
    rows[#rows + 1] = { kind = "colhead", col = 1, h = PD.TEXT_H,
                        text = L["名称"], right = L["总价格"], ownRight = L["自身价格"],
                        sortOn = (mode == "total"), ownOn = (mode == "own"),
                        act = function()
                            PD.crateSort = (mode ~= "total") and "total" or nil
                            PD.RequestRender()
                        end,
                        ownAct = function()
                            PD.crateSort = (mode ~= "own") and "own" or nil
                            PD.RequestRender()
                        end }
    for _, i in ipairs(order) do
        local c = list[i]
        rows[#rows + 1] = {
            kind = "row", col = 1, h = PD.ROW_H,
            it = { c.id }, qItem = c.id,
            text = PD.ItemName(c.id),
            sub = CRATE_TIERS[c.tier] or "?",
            right = bests[i] and RA.MoneyStr(bests[i]) or "",
            rightOwn = owns[i] and RA.MoneyStr(owns[i]) or "",
            rightOwnColor = C_TEXT,
            cur = (c.id == sel),
            act = function()
                if PD.crateSel ~= c.id then PD.crateSel = c.id; PD.RequestRender() end
            end,
        }
    end
    local sc
    for _, c in ipairs(list) do if c.id == sel then sc = c break end end
    if not sc then return end
    PD.secPadL = 0
    local secH = #rows + 1
    rows[#rows + 1] = {
        kind = "head", col = 2, h = 28, fs = 16,
        it = { sc.id },
        text = PD.ItemName(sc.id),
    }
    local favTxt = sc.favor and format(L["青睐 +%d"], sc.favor) or L["青睐未验证"]
    PushText(rows, favTxt .. format(L[" · 需等级 %d"], sc.level or 0), 12, C_GREY, 2)
    MarkSec(rows, secH, #rows, 1)
    PushGap(rows, PD.SEC_GAP + 2 * PD.SEC_PAD - 2, 2)
    local secO = #rows + 1
    PushHead(rows, L["凑法（任满其一）"], 2)
    local opts, cheapest, cheapestOpt = {}, nil, nil
    for _, o in ipairs(sc.opts or {}) do opts[#opts + 1] = o end
    for _, o in ipairs(opts) do
        local v = CrateOptCost(o[1], o[2])
        if v and (not cheapest or v < cheapest) then cheapest, cheapestOpt = v, o end
    end
    table.sort(opts, function(a, b)
        local ca, cb = CrateOptCost(a[1], a[2]), CrateOptCost(b[1], b[2])
        if ca and cb then return ca < cb end
        if ca or cb then return ca ~= nil end
        return a[1] < b[1]
    end)
    for _, o in ipairs(opts) do
        local v = CrateOptCost(o[1], o[2])
        local isBest = cheapestOpt and o[1] == cheapestOpt[1] and o[2] == cheapestOpt[2]
        rows[#rows + 1] = {
            kind = "row", col = 2, h = PD.ROW_H1, fs = 14,
            it = { o[1] }, qItem = o[1],
            text = PD.ItemName(o[1]) .. " ×" .. (o[2] or 1),
            tag = isBest and { text = L["最省"], color = CRATE_GREEN } or nil,
            right = v and RA.MoneyStr(v) or "—",
            rightColor = isBest and CRATE_GREEN or (v and C_TEXT or C_GREY),
            tipExtra = function() return PD.PriceTipLines(o[1]) end,
        }
    end
    MarkSec(rows, secO, #rows, 2)
    local own = RA.AHPriceOf and RA.AHPriceOf(sc.id) or nil
    if not cheapestOpt and opts[1] then cheapestOpt = opts[1] end
    PushGap(rows, PD.SEC_GAP + 2 * PD.SEC_PAD - 2, 2)
    local secS = #rows + 1
    PushHead(rows, L["总结"], 2)
    CrateMetaRow(rows, L["自身成本"], own, own, 14)
    rows[#rows + 1] = {
        kind = "row", col = 2, h = PD.ROW_H1, fs = 14,
        text = cheapestOpt and format(L["购买 %s"],
                 PD.MatIconTex(cheapestOpt[1], 14) .. " " .. PD.ItemName(cheapestOpt[1])
                 .. " ×" .. (cheapestOpt[2] or 1)) or "—",
        right = cheapest and RA.MoneyStr(cheapest) or "—",
        rightColor = cheapest and CRATE_GREEN or C_GREY,
        tipExtra = cheapestOpt and function() return PD.PriceTipLines(cheapestOpt[1]) end or nil,
    }
    local total = (own and cheapest) and (own + cheapest) or nil
    CrateMetaRow(rows, L["合计"], total, total, 14)
    if total and (sc.favor or 0) > 0 then
        CrateMetaRow(rows, L["每点青睐的最低成本"], total / sc.favor, true, 14)
    end
    MarkSec(rows, secS, #rows, 3)
    PD.hasSecs = true
    PD.secCount = 3
    PushText(rows, CrateSnapText(), 11, C_GREY, 2)
end

local function CraftAllMap()
    if PD.craftAll and next(PD.craftAll) then return PD.craftAll end
    if not R then RGet(nil) end
    local map = {}
    for slug, d in pairs(R or {}) do
        if type(d) == "table" and type(d.rows) == "table" then
            for _, rec in ipairs(d.rows) do
                local resolved = PD.RecipeData(rec, "rows", slug)
                local iid = resolved.item
                if not resolved.clientUnavailable and type(iid) == "number" and resolved.count and type(resolved.mats) == "table" and #resolved.mats > 0
                   and not map[iid] then
                    local live={}; for k,v in pairs(rec) do live[k]=v end
                    live[2],live[3],live[12]=iid,resolved.count,resolved.mats
                    map[iid] = { rec = live, slug = slug }
                end
            end
        end
    end
    if next(map) then PD.craftAll = map end
    return map
end

local function WritBadge(cinfo, learned)
    if not cinfo then return nil end
    if RA.SpellKnown and RA.SpellKnown(cinfo.rec[1]) then
        return { text = L["已学"], color = { 1, 0.82, 0 } }
    end
    if learned[cinfo.slug] then
        return { text = L["本专业"] }
    end
    local p = D.pro and D.pro[cinfo.slug]
    return { text = p and p.name or cinfo.slug, color = { 0.55, 0.57, 0.62 } }
end

function PD.WritRows(rows)
    PD.secPadL = 0
    local list = CD.writs or {}
    local order, owns, priced, craftT, pcts = {}, {}, {}, {}, {}
    local craftMap = CraftAllMap()
    for i = 1, #list do
        order[i] = i
        local wid = list[i].item or list[i].target
        local own = RA.AHPriceOf and RA.AHPriceOf(wid) or nil
        local mu = RA.AHPriceOf and RA.AHPriceOf(list[i].target) or nil
        owns[i] = own
        priced[i] = (own and mu) and (own + mu * (list[i].qty or 1)) or nil
        local ci = craftMap[list[i].target]
        local csum, ok
        if ci and ci.rec then
            csum, ok = 0, true
            for _, m in ipairs(ci.rec[12]) do
                local p = RA.AHPriceOf and RA.AHPriceOf(m[1]) or nil
                if p then csum = csum + p * (m[2] or 1) else ok = false end
            end
        end
        craftT[i] = (own and ok) and math.floor(own + csum * (list[i].qty or 1) / (ci.rec[3] or 1) + 0.5) or nil
        if craftT[i] and priced[i] and priced[i] > 0 then
            local d = math.floor((craftT[i] - priced[i]) / priced[i] * 100 + 0.5)
            if d > 0 then
                pcts[i] = { text = format("+%d%%", d), color = TIP_RED }
            elseif d < 0 then
                pcts[i] = { text = format("%d%%", d), color = { 0.42, 0.94, 0.62 } }
            else
                pcts[i] = { text = "0%", color = C_GREY }
            end
        end
    end
    local learned = PD.ProfLearned()
    local mode = PD.writSort
    table.sort(order, function(a, b)
        local wa, wb = list[a], list[b]
        if mode then
            local key = priced
            if mode == "own" then key = owns elseif mode == "craft" then key = craftT end
            local ca, cb = key[a], key[b]
            if ca and cb then return ca < cb end
            if ca or cb then return ca ~= nil end
            return (wa.target or 0) < (wb.target or 0)
        end
        if (wa.rep or 0) ~= (wb.rep or 0) then return (wa.rep or 0) > (wb.rep or 0) end
        local ca, cb = priced[a], priced[b]
        if ca and cb then return ca < cb end
        if ca or cb then return ca ~= nil end
        return (wa.target or 0) < (wb.target or 0)
    end)
    if not PD.writSel and list[order[1]] then
        PD.writSel = list[order[1]].quest or list[order[1]].target
    end
    local sel = PD.writSel
    rows[#rows + 1] = { kind = "colhead", col = 1, h = PD.ROW_H,
                        text = L["工匠文书"], right = L["拍卖总价"], craftRight = L["制造总价"],
                        ownRight = L["自身价格"],
                        sortOn = (mode == "total"), craftOn = (mode == "craft"), ownOn = (mode == "own"),
                        act = function()
                            PD.writSort = (mode ~= "total") and "total" or nil
                            PD.RequestRender()
                        end,
                        craftAct = function()
                            PD.writSort = (mode ~= "craft") and "craft" or nil
                            PD.RequestRender()
                        end,
                        ownAct = function()
                            PD.writSort = (mode ~= "own") and "own" or nil
                            PD.RequestRender()
                        end }
    for _, i in ipairs(order) do
        local w = list[i]
        local wid = w.item or w.target
        local craft = craftMap[w.target]
        local tag = craft and WritBadge(craft, learned) or nil
        rows[#rows + 1] = {
            kind = "row", col = 1, h = PD.ROW_H,
            it = { wid }, qItem = wid,
            text = PD.ItemName(wid),
            sub = format(L["声望 +%d"], w.rep or 0),
            tag = tag,
            right = priced[i] and RA.MoneyStr(priced[i]) or "",
            right2 = craftT[i] and RA.MoneyStr(craftT[i]) or "",
            right2Color = C_GOLD,
            pct = pcts[i],
            rightOwn = owns[i] and RA.MoneyStr(owns[i]) or "",
            rightOwnColor = C_TEXT,
            cur = ((w.quest or w.target) == sel),
            act = function()
                local key = w.quest or w.target
                if sel ~= key then PD.writSel = key; PD.RequestRender() end
            end,
        }
    end
    local sw
    for _, i in ipairs(order) do
        local w = list[i]
        if (w.quest or w.target) == sel then sw = w break end
    end
    if not sw then return end
    local wid = sw.item or sw.target
    local wu = RA.AHPriceOf and RA.AHPriceOf(wid) or nil
    local u = RA.AHPriceOf and RA.AHPriceOf(sw.target) or nil
    local buyAll = u and u * (sw.qty or 1) or nil
    local cinfo = craftMap[sw.target]
    local craft = cinfo and cinfo.rec or nil
    local craftSum, allPriced, craftCost
    if craft then
        craftSum, allPriced = 0, true
        for _, m in ipairs(craft[12]) do
            local p = RA.AHPriceOf and RA.AHPriceOf(m[1]) or nil
            if p then craftSum = craftSum + p * (m[2] or 1) else allPriced = false end
        end
        craftCost = allPriced and math.floor(craftSum * math.ceil((sw.qty or 1) / (craft[3] or 1)) + 0.5) or nil
    end
    local secH = #rows + 1
    rows[#rows + 1] = {
        kind = "head", col = 2, h = 28, fs = 16,
        it = { wid },
        text = PD.ItemName(wid),
        tag = cinfo and WritBadge(cinfo, learned) or nil,
    }
    PushText(rows, format(L["声望 +%d · 需等级 %d"], sw.rep or 0, sw.level or 0), 12, C_GREY, 2)
    MarkSec(rows, secH, #rows, 1)
    PushGap(rows, PD.SEC_GAP + 2, 2)
    local cards = {
        { lab = L["直接买齐"], it = sw.target, priceOk = buyAll and true or false,
          name = format(L["%s ×%d"], PD.ItemName(sw.target), sw.qty or 1),
          price = buyAll and RA.MoneyStr(buyAll) or "—",
          tipExtra = function() return PD.PriceTipLines(sw.target) end },
        nil,
    }
    if craft then
        local yn = craft[3] or 1
        cards[2] = {
            lab = L["自己制造"], it = craft[2], priceOk = craftCost and true or false,
            name = yn > 1 and format(L["%s ×%d"], PD.ItemName(craft[2]), yn) or PD.ItemName(craft[2]),
            price = craftCost and RA.MoneyStr(craftCost) or "—",
            tipExtra = function() return PD.PriceTipLines(craft[2]) end,
        }
    else
        cards[2] = { lab = L["自己制造"], name = L["未登记配方"], dim = true }
    end
    if craftCost and buyAll then
        if craftCost < buyAll then
            cards[2].win = true
        elseif craftCost > buyAll then
            cards[1].win = true
        end
    end
    rows[#rows + 1] = { kind = "vs", col = 2, h = 52, vw = PD.splitRW, cards = cards }
    if craft and #craft[12] > 0 then
        PushGap(rows, PD.SEC_GAP + 2, 2)
        local secA = #rows + 1
        rows[#rows + 1] = { kind = "head", col = 2,
                            text = L["自己制造材料明细"], right = L["制造一次"] }
        for _, m in ipairs(craft[12]) do
            local p = RA.AHPriceOf and RA.AHPriceOf(m[1]) or nil
            rows[#rows + 1] = {
                kind = "row", col = 2, h = PD.ROW_H1, fs = 14,
                it = { m[1] }, qItem = m[1],
                text = PD.ItemName(m[1]) .. " ×" .. (m[2] or 1),
                right = p and RA.MoneyStr(p * (m[2] or 1)) or "",
                rightColor = p and C_TEXT or C_GREY,
                tipExtra = function() return PD.PriceTipLines(m[1]) end,
            }
        end
        CrateMetaRow(rows, L["制造一次的成本"], craftSum, allPriced, 14)
        local batches = math.ceil((sw.qty or 1) / (craft[3] or 1))
        CrateMetaRow(rows, L["制造上交所需物的成本"],
                     allPriced and math.floor(craftSum * batches + 0.5) or nil, allPriced, 14)
        MarkSec(rows, secA, #rows, 2)
    end
    local buyTotal = (wu and u) and (wu + u * (sw.qty or 1)) or nil
    local craftTotal = (wu and craftCost) and (wu + craftCost) or nil
    local lowest
    if buyTotal and craftTotal then
        lowest = math.min(buyTotal, craftTotal)
    else
        lowest = buyTotal or craftTotal
    end
    local cheapest = (buyTotal and craftTotal and craftTotal < buyTotal) and "craft"
                    or (buyTotal and craftTotal and buyTotal < craftTotal) and "buy" or nil
    local repUnit = (lowest and (sw.rep or 0) > 0) and (lowest / sw.rep) or nil
    PushGap(rows, PD.SEC_GAP + 2 * PD.SEC_PAD - 2, 2)
    local secB = #rows + 1
    PushHead(rows, L["成本汇总"], 2)
    CrateMetaRow(rows, L["文书自身成本"], wu, wu, 14)
    rows[#rows + 1] = {
        kind = "row", col = 2, h = PD.ROW_H1, fs = 14,
        text = L["直接买齐总成本"],
        right = buyTotal and RA.MoneyStr(buyTotal) or "—",
        rightColor = buyTotal and (cheapest == "buy" and { 0.42, 0.94, 0.62 } or C_TEXT) or C_GREY,
    }
    rows[#rows + 1] = {
        kind = "row", col = 2, h = PD.ROW_H1, fs = 14,
        text = L["自己制造总成本"],
        right = craftTotal and RA.MoneyStr(craftTotal) or "—",
        rightColor = craftTotal and (cheapest == "craft" and { 0.42, 0.94, 0.62 } or C_TEXT) or C_GREY,
    }
    MarkSec(rows, secB, #rows, 3)
    PushGap(rows, PD.SEC_GAP + 2 * PD.SEC_PAD - 2, 2)
    local secC = #rows + 1
    PushHead(rows, L["总结"], 2)
    if cheapest == "buy" then
        rows[#rows + 1] = {
            kind = "row", col = 2, h = PD.ROW_H1, fs = 14,
            text = L["直接买便宜"],
            right = RA.MoneyStr(craftTotal - buyTotal),
            rightColor = { 0.42, 0.94, 0.62 },
        }
    elseif cheapest == "craft" then
        rows[#rows + 1] = {
            kind = "row", col = 2, h = PD.ROW_H1, fs = 14,
            text = L["自己造省"],
            right = RA.MoneyStr(buyTotal - craftTotal),
            rightColor = { 0.42, 0.94, 0.62 },
        }
    end
    CrateMetaRow(rows, L["每点声望最低成本"], repUnit, repUnit, 14)
    MarkSec(rows, secC, #rows, 4)
    PD.hasSecs = true
    PD.secCount = 4
    PushGap(rows, 6, 2)
    PushText(rows, CrateSnapText(), 11, C_GREY, 2)
end

function PD.PlunderRows(rows)
    local list = (ns.PlunderData and ns.PlunderData.goods) or {}
    if not PD.plunderSel and list[1] then PD.plunderSel = list[1].id end
    local sel = PD.plunderSel
    local costs = {}
    for i, g in ipairs(list) do
        local sum, ok = 0, true
        for _, m in ipairs(g.mats or {}) do
            local p = RA.AHPriceOf and RA.AHPriceOf(m[1]) or nil
            if p then sum = sum + p * (m[2] or 1) else ok = false end
        end
        costs[i] = ok and sum or nil
    end
    local mode = PD.plunderSort
    local order = {}
    for i = 1, #list do order[i] = i end
    if mode then
        table.sort(order, function(a, b)
            local ca, cb = costs[a], costs[b]
            if ca and cb then return ca < cb end
            if ca or cb then return ca ~= nil end
            return (list[a].id or 0) < (list[b].id or 0)
        end)
    end
    rows[#rows + 1] = { kind = "colhead", col = 1, h = PD.TEXT_H,
                        text = L["名称"], right = L["装填成本"],
                        sortOn = (mode == "cost"),
                        act = function()
                            PD.plunderSort = (mode ~= "cost") and "cost" or nil
                            PD.RequestRender()
                        end }
    for _, i in ipairs(order) do
        local g = list[i]
        rows[#rows + 1] = {
            kind = "row", col = 1, h = PD.ROW_H,
            it = { g.id }, qItem = g.id,
            text = PD.ItemName(g.id),
            sub = PLUNDER_CATS[g.cat] or g.cat or "",
            right = costs[i] and RA.MoneyStr(costs[i]) or "",
            cur = (g.id == sel),
            act = function()
                if PD.plunderSel ~= g.id then PD.plunderSel = g.id; PD.RequestRender() end
            end,
        }
    end
    local sg
    for _, g in ipairs(list) do if g.id == sel then sg = g break end end
    if not sg then return end
    PushHead(rows, PD.ItemName(sg.id), 2, 16)
    local meta = PLUNDER_CATS[sg.cat] or sg.cat or "—"
    meta = meta .. " · " .. format(L["物品等级 %d"], sg.band or 0)
    PushText(rows, meta, 12, C_GREY, 2)
    PushGap(rows, 6, 2)
    PushHead(rows, L["装填材料"], 2)
    local sum, ok = 0, true
    for _, m in ipairs(sg.mats or {}) do
        local p = RA.AHPriceOf and RA.AHPriceOf(m[1]) or nil
        if p then sum = sum + p * (m[2] or 1) else ok = false end
        rows[#rows + 1] = {
            kind = "row", col = 2, h = PD.ROW_H1,
            it = { m[1] }, qItem = m[1],
            text = PD.ItemName(m[1]) .. " ×" .. (m[2] or 1),
            right = p and RA.MoneyStr(p * (m[2] or 1)) or "—",
            rightColor = p and C_TEXT or C_GREY,
            tipExtra = function() return PD.PriceTipLines(m[1]) end,
        }
    end
    PushGap(rows, 6, 2)
    CrateMetaRow(rows, L["装填成本"], ok and sum or nil, ok)
    PushText(rows, CrateSnapText(), 11, C_GREY, 2)
end

function PD.RowsCrates(rows)
    if not CD then
        PushText(rows, L["暂时没有客户端数据"], 12, C_GREY)
        return
    end
    PD.lvSplit = true
    PD.splitLW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.OV_GUT) * PD.CRATE_SPLIT)
    PD.splitRW = PD.RIGHT_W - 2 * PD.LIST_PAD - PD.OV_GUT - PD.splitLW
    if PD.tab == "writ" then
        PD.WritRows(rows)
    elseif PD.tab == "plunder" then
        PD.PlunderRows(rows)
    else
        PD.CrateRows(rows)
    end
end

function PD.Render()
    if not (PD.built and PD.page) or not PD.cur then return end
    -- ★ 每次渲染清空物品名记忆表（同一次渲染内名字不会变；到货后的重扫会再清）
    PD.ResetItemNameMemo()
    PD.lvRouteHead = nil   -- 工具行路线标题：仅 RowsLeveling 自动路线分支回填（跨页残留清零）
    PD.PickNav()
    PD.PickTabs()
    RememberLast()   -- 2026-10-10：当前显示状态即「上次离开页」，落库供下次还原

    local rows = {}
    local tool, handler = {}, nil
    PD.lvSplit = false
    PD.gridSplit = false
    PD.wantIndexGrid = false
    PD.wantBonusTable = false
    PD.wantTrainerBoard = false
    PD.hasSecs = false
    PD.secPadL = nil
    PD.splitLW, PD.splitRW = nil, nil
    PD.hideDivider = false
    PD.secCount = 0
    -- ★ 上一轮排下、还没建的行必须丢掉（玩家已经点到别的专业 / 别的子页签了），
    --   否则它们会在新页面上冒出来。
    PD.__pendRows = {}
    -- ★★ 第二道闸（2026-10-09）：切页/切专业时把**整池行 + 两个卡池**全收起来。
    --   行池是跨页共用的：上一页画过的行不会自己消失，原先只靠 PaintRows 末尾那句
    --   「藏掉超出本页的行」兜底，而那句用 `#PD.rows` 取上界 —— Lua 的 `#` 遇到
    --   空洞会**提前截断**（建帧失败 / pcall 兜住的行会让 PD.rows[i] 留 nil），
    --   尾部那些上一页还在显示中的行就永远藏不掉 ⇒ 「购物清单的材料残留在路线页」。
    --   这里用 pairs 扫（空洞安全），且**只在页面身份变化时**做：同页重渲
    --   （到货重扫 / 工具点击）零额外开销。
    do
        local pk = tostring(PD.cur) .. "|" .. tostring(PD.tab) .. "|"
                   .. tostring(PD.autoPage) .. "|" .. tostring(PD.setOpen) .. "|" .. tostring(PD.exclusionsOpen)
                   .. "|" .. tostring(PD.partnerPicker) .. "|" .. tostring(PD.partnerUIRevision)
                   .. "|" .. tostring(PD.engineeringUIRevision)
        if pk ~= PD.__pageKey then
            PD.__pageKey = pk
            -- ★ 不只是 Hide：连**内容**一起抹掉（见 PD.WipeRow 的长注释）。
            for _, rr in pairs(PD.rows) do PD.WipeRow(rr) end
            if PD.secCards then
                for i = 1, #PD.secCards do PD.secCards[i]:Hide() end
                for i = 1, #PD.secGoldCards do PD.secGoldCards[i]:Hide() end
            end
        end
    end

    if PD.setOpen then
        PD.RowsSettings(rows)
    elseif PD.tab == "overview" then
        PD.lvSplit = false
        PD.wantIndexGrid = (PD.cur == "__index")
        PD.hasSecs = true
        PD.hideDivider = true
        if PD.cur == "camping" then
            PD.campView = "bonus"
            PD.wantBonusTable = true
        end
        PD.RowsOverview(rows)
    elseif PD.tab == "trainer" then
        PD.wantTrainerBoard = true
    elseif PD.tab == "recipe" then
        tool, handler = PD.RecipeTool(RGet(PD.cur))
        PD.RowsRecipe(rows)
    elseif PD.tab == "crate" or PD.tab == "plunder" or PD.tab == "writ" then
        PD.RowsCrates(rows)
    elseif PD.tab == "gather" then
        PD.gridSplit = (PD.cur == "fishing")
        PD.RowsGather(rows)
    elseif PD.tab == "leveling" then
        if PD.IsGatherRoute() then
            PD.lvSplit = false
            PD.gridSplit = false
            PD.autoPage = nil   -- 制造页购物清单子页残留清掉
            PD.RowsGatherRoute(rows)
        else
        tool, handler = PD.LevelTool()
        -- 路线子页单栏（2026-10-09 v2：旧右栏退役，材料/图纸全收进购物清单子页）。
        -- 购物清单子页（2026-10-09 三轮定稿 B 版）：经典两栏 —— 左列材料+图纸主表，
        -- 右列金币卡（金色底 + 20px 金字 + 三行分类合计）+ 半成品 + 商人直卖（HUD 直售徽标）。
        if PD.autoPage == "shop" or PD.autoPage == "supplement" then
            PD.lvSplit = true
            PD.splitLW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.OV_GUT) * PD.SHOP_SPLIT)
            PD.splitRW = PD.RIGHT_W - 2 * PD.LIST_PAD - PD.OV_GUT - PD.splitLW
        else
            PD.lvSplit = false
        end
        PD.RowsLeveling(rows)
        end
    else
        PD.RowsOverview(rows)
    end

    -- 2026-10-11 用户：路线标题（自动路线头行）移到工具行「重新计算」右侧同行渲染；
    -- RowsLeveling 自动路线分支暂存 PD.lvRouteHead，这里追加成 plain 工具项。
    if tool and PD.lvRouteHead then
        tool[#tool + 1] = { key = "route_head", plain = true,
                            text = PD.lvRouteHead.text, warn = PD.lvRouteHead.warn }
    end

    local toolH
    if PD.tab == "leveling" and not PD.setOpen then
        toolH = PD.PaintLvTiles() + PD.PaintTool(tool, handler, PD.LV_TILE_H + 8)
    else
        -- 其它签也要走一次 PaintLvTiles：内部会按 tab 隐藏信息卡（否则残留在其它签）
        toolH = PD.PaintLvTiles() + PD.PaintTool(tool, handler)
    end
    PD.Layout(toolH)

    -- 配方搜索框：仅配方页显示（工具行右端，红框位置）
    if PD.searchBox then
        if PD.tab == "recipe" and not PD.setOpen then
            PD.searchBox:ClearAllPoints()
            PD.searchBox:SetPoint("TOPRIGHT", PD.page, "TOPRIGHT",
                                  -(PD.CARD_INSET + PD.LIST_PAD), -(PD.BODY_TOP))
            PD.searchBox:Show()
        else
            PD.searchBox:Hide()
        end
    end

    PD.specs = rows
    PD.curRows, PD.visMode = nil, false   -- 内容整体重排，作废旧视口（CullRows 空转）
    PD.scroll:SetVerticalScroll(0)
    PD.truncated = PD.PaintRows(rows)
    ns.OpenPerf.Mark("首屏")
    PD.PlaceSettingsToggles(rows)
    PD.scroll:Show()
    PD.RequestRows(rows)
    PD.WarmNames()
    if PD.UpdateVScroll then PD.UpdateVScroll() end   -- 滚动条：Render 尾兜底刷新（分帧行随后到再由绘制钩子刷）
    -- ★★ 第十一刀（rev17）：收尾挂一次**空闲预热** —— 在当前专业上把物品名
    --   先喂进持久记忆表。用户切到 overview / leveling 的那几百毫秒里，
    --   配方页那 300 个名字就已经备好了 ⇒ 点开配方页那一帧不再向引擎要名字。
end

-- ★★ 第十一刀（rev17）：**空闲预热** —— 把「点开配方页那一帧本该付的取名钱」
--   提前到空闲帧付掉。
--   一页 300 条配方，PD.ScanRecipe 必须为**列宽**取全部 300 个物品名（数据文件
--   只存 ID，名字只能问客户端），实机 428 次 GetItemInfo / 4.7ms 全压在「点开
--   那一瞬间」；而名字一旦到货就不会再变（记忆表已改成跨渲染持久）⇒ 完全可以
--   在空闲帧先喂一遍：用户点开配方页时 PD.ItemName 全是命中，那一帧的引擎调用归零。
--   ★ 只在分帧器空闲（not DG.stepping）时才喂 —— 建行永远优先；每帧只一小口。
--   ★ 跟当前专业走（PD.cur 变了就换目标）；覆盖范围与 PD.RequestRows 一致
--     （min(#d.rows, ROW_CAP) 行）⇒ 只是把本该付的钱挪到前面，不产生额外请求。
--   ★ pcall 包住 —— 预热永不许影响正事；出错就静静停下。
local _warmTok = 0
local PD_WARM_PER_FRAME = 96
function PD.WarmId(id)
    if not id then return end
    local _, got = PD.ItemName(id)
    if got then return end
    if C_Item and C_Item.RequestLoadItemDataByID then
        pcall(C_Item.RequestLoadItemDataByID, id)
    end
    local gi = GetItemInfo or (C_Item and C_Item.GetItemInfo)
    if type(gi) == "function" then pcall(gi, id) end
end
function PD.WarmNames()
    local d = RGet(PD.cur)
    local all = d and d.rows
    if type(all) ~= "table" or #all == 0 then return end
    if not (C_Timer and C_Timer.After) then return end
    _warmTok = _warmTok + 1
    local tok = _warmTok
    local i, n = 0, math.min(#all, PD.ROW_CAP)
    local function feed()
        if tok ~= _warmTok then return end
        if DG.stepping then C_Timer.After(0, feed) return end
        local ok = pcall(function()
            local budget = PD_WARM_PER_FRAME
            while i < n and budget > 0 do
                i = i + 1
                local r = all[i]
                if r then
                    PD.WarmId(r[2])
                    local ms = r[12]
                    if ms then
                        for k = 1, #ms do PD.WarmId(ms[k] and ms[k][1]) end
                    end
                end
                budget = budget - 1
            end
        end)
        if not ok then return end
        if i < n then C_Timer.After(0, feed) end
    end
    C_Timer.After(0, feed)
end

function PD.RequestRows(rows)
    if not DG.ItemName then return end
    local wait = {}
    -- ★ 按 id 去重（2026-10-09 第二轮）：一页几百条配方，同一种材料跨配方反复出现
    --   （实测 511 条 => 1349 次请求，去重后只剩唯一 id）。DG.RequestItem 本来就
    --   靠 DG.__asked 幂等，wait 只被 SweepNames 用来判「有没有任一未到货」⇒
    --   去重不改变语义，纯省掉重复的函数调用。
    local seen = {}
    local function want(id)
        if not id or seen[id] then return end
        seen[id] = true
        local hasName = select(2, PD.ItemName(id))
        if hasName then return end
        -- ★★ 轻量请求（2026-10-09 第四轮；实机 /dfprofperf 实测）：
        --   原先这里调 DG.RequestItem(id) —— 那是为**掉落页**写的：每次都往一个
        --   隐藏 GameTooltip 上 SetItemByID 预热（构建整条 tooltip），再
        --   Item:CreateFromItemID + ContinueOnItemLoad 注册回调。
        --   实测点开配方页签 392 次 = 282.7ms，占整次 363.3ms 的 79%。
        --   配方页只需要**物品名** ⇒ 只请求载入 + 查一次，不建 tooltip、不建 Item 对象。
        --   名字到货后由 PD.SweepNames（0.5/1.5/4/9s 定时）触发重渲，链路不变。
        if C_Item and C_Item.RequestLoadItemDataByID then
            pcall(C_Item.RequestLoadItemDataByID, id)
        end
        local gi = GetItemInfo or (C_Item and C_Item.GetItemInfo)
        if type(gi) == "function" then pcall(gi, id) end
        -- 名字已到货的**不再请求** ⇒ 天然去重；客户端驱逐缓存后名字退回占位，
        -- 那时 hasName 又为假 ⇒ 自动重请一次（与 DG.RequestItem 的 force 语义一致）。
        wait[#wait + 1] = id
    end
    local n = math.min(#rows, PD.ROW_CAP)
    for i = 1, n do
        local spec = rows[i]
        if spec.it then want(spec.it[1]) end
        for _, m in ipairs(spec._mats or {}) do want(m[1]) end
    end
    PD.notReady = (#wait > 0) and wait or nil
    if PD.notReady and not PD.sweeping then PD.ScheduleSweep() end
end

function PD.Show(slug)
    ns.OpenPerf.Begin("专业·" .. tostring(slug))
    PD.HideVendorPick()   -- 行池复用 + 内容重排：弹窗锚会失主，换专业先收
    if slug ~= PD.cur then
        PD.cur = slug
        PD.toolKey = nil
        PD.campView = "a"
        PD.tab = "overview"
        PD.setOpen = false
        PD.searchQ = nil
        if PD.searchBox then PD.searchBox.eb:SetText("") end
    end
    if not PD.built then
        PD.wantOpen = true
    end
    PD.RequestRender()
end

function PD.SetTab(key)
    PD.setOpen = false
    if not (PD.avail and PD.avail[key]) then return end
    PD.tab = key
    PD.RequestRender()
end

-- 2026-10-10 用户：进专业页默认 = 已学的主要专业（kind=="primary"，与左列按钮同数据源
--   PD.ProfLearned）；没学任何专业则退到首个导航项。上次去的（专业, 子页签）由
--   RememberLast 落 DungeonsForeverDB.prof，跨 /reload 记忆，优先级高于默认。
function PD.DefaultSlug()
    local learned = PD.ProfLearned()
    local fallback
    for _, slug in ipairs(PD.navOrder or {}) do
        local p = D.pro[slug]
        if p and not fallback then fallback = slug end
        if learned[slug] and p and p.kind == "primary" then return slug end
    end
    for _, slug in ipairs(PD.navOrder or {}) do
        if learned[slug] then return slug end
    end
    return fallback
end

function PD.EnsureCur()
    if PD.cur and PD.cur ~= "__index" then return end
    local db = ProfDB()
    local slug = db.lastSlug
    if not (slug and D.pro[slug]) then slug = PD.DefaultSlug() end
    if slug then
        PD.cur = slug
        PD.toolKey = nil
        PD.tab = (type(db.lastTab) == "string") and db.lastTab or "overview"
        PD.setOpen = false
    end
end

function PD.RequestRender()
    if not PD.built then
        PD.wantOpen = true
        return
    end
    if not (ns.PaintJob and ns.IdleJobs) then
        PD.Render()
        return
    end
    if ns.PaintJob.Active("Profession") then
        PD.__pend = true
        return
    end
    ns.PaintJob.Run("Profession", function() PD.Render() end, function()
        if PD.__pend then
            PD.__pend = false
            PD.RequestRender()
        end
    end)
end

function PD.Open()
    if not PD.built then
        PD.wantOpen = true
        return
    end
    PD.EnsureCur()
    PD.RequestRender()
end

function PD.Refresh()
    if not PD.built then
        PD.wantOpen = true
        return
    end
    PD.EnsureCur()
    PD.RequestRender()
end

-- ══ 进度条自检 / 演示（/dfprofgate） ═══════════════════════════════════
--   ★ 为什么需要这个命令：行池只增不减 —— 同一个专业第二次打开就是复用已经建好的
--     行帧（真·瞬时，本就不该亮条）。只有「第一次把池子撑大的那个专业」看得见它，
--     好机器上几乎一闪而过 ⇒ 留一条能随时复现的入口（与 /dfgate 同款）。
--   ★ 演示做法：把三道闸临时放宽到「必定触发」（多小都亮 / 一律分帧 / 每帧只建 2 行），
--     再清空行池重新渲染一次 ⇒ 当前专业就把进度条走完一遍。
--     收工由 PD.EndGateDemo 统一还原（队列抽干是唯一可靠的「活干完了」信号）。
PD.DEMO_SAVE = nil

function PD.StartGateDemo()
    if PD.DEMO_SAVE then PD.EndGateDemo() end
    PD.DEMO_SAVE = {
        syncMax  = PD.ROW_SYNC_MAX,
        minSteps = DG.Gate.minSteps,
        rowCap   = DG.LOOT_ROW_FRAME_CAP,
    }
    PD.ROW_SYNC_MAX       = 0     -- 一律走分帧（正式值 20）
    DG.Gate.minSteps      = 0     -- 多小都亮（正式值 24）
    DG.LOOT_ROW_FRAME_CAP = 2     -- 每帧只建 2 行 ⇒ 才看得清（正式值 16）
    -- 清空行池：池子只增不减，不清的话「复用已有行帧」会让待建表为空 ⇒ 进度条照旧不亮
    for i = #PD.rows, 1, -1 do PD.rows[i]:Hide() end
    PD.rows = {}
    PD.RequestRender()
end

function PD.EndGateDemo()
    local s = PD.DEMO_SAVE
    PD.DEMO_SAVE = nil
    if not s then return end
    PD.ROW_SYNC_MAX       = s.syncMax
    DG.Gate.minSteps      = s.minSteps
    DG.LOOT_ROW_FRAME_CAP = s.rowCap
end

if type(SlashCmdList) == "table" then
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

-- ══ 点开耗时打印（/dfprofperf） ═══════════════════════════════════════════
--   ★★ 为什么必须在游戏里量：离线桩（lupa）把 GetStringWidth / CreateFrame /
--      GetItemInfo / 发包全换成了纯 Lua 查表 ⇒ 离线量到的整帧 4.7ms 与实机手感
--      根本不是一回事。真实卡顿只落在「真实 API」上 —— 字体测量走引擎 C 调用、
--      建帧走引擎内存分配、物品名要查客户端缓存、发包要走网络层。
--   ★ 做法：全部在**运行期包函数**，不往 PD.Render 函数体里插一行
--      （并行会话正在改这个文件，动函数体最容易撞车）。
--      一次点击 = 9 段计时 + 6 项调用计数：
--        次数大 ⇒ 该减少调用（省）；单次贵 ⇒ 该换做法（改）。
--   ★ 默认**关**（2026-10-09 用户：性能打印直接关掉；要复盘 /dfprofperf 一条命令再开）。
--      只打「慢过 PD.PERF_MIN」的那一次（正常点不刷屏）。
--      /dfprofperf        开/关
--      /dfprofperf all    连很快的也打
--      /dfprofperf scan   把所有专业挨个走一遍配方页，最后给排序表
--      /dfprofperf bench  微基准：量每个 setter 的实机单价（µs/次）
--      /dfprofperf off    直接关
--   ★ 每条报告会附两行分解：
--      └ 细分（已含在数据里）：扫描 / 建spec / 列宽材料 / 材料串 / 单条spec
--      └ setter 调用：SetText / SetTextColor 的**次数**（单价由 bench 给）
PD.PERF     = false
PD.PERF_MIN = 6

local pfUnpack = unpack
if not pfUnpack and type(table) == "table" then pfUnpack = table.unpack end
if not pfUnpack then pfUnpack = function(t) return t[1] end end

local PF_DEPTH, PF_MS, PF_N, PF_WHERE = 0, nil, nil, ""
local PF_TAIL = nil
local PF_SCAN = nil
local PF_SUB, PF_SET = nil, nil   -- 细分计时 / setter 计数（每次入口重置）
local PF_SKIN0 = nil              -- ★ 第七刀：皮按钮「圆角边框帧重建」的入口快照
local PF_TB0 = nil                -- ★ 第八刀：TryBuild 调用次数的入口快照
local PF_STR0 = nil               -- ★ 第九刀：像素条复算的入口快照（次数/耗时/扫描条数）
local PF_STRM0 = nil
local PF_STRS0 = nil
-- ★★ 只放「Render 顶层」调用的段！ScanRecipe / FitRecipeCols 是在 RowsRecipe
--    内部被调的 ⇒ 它们的时间**已经在「数据」里**，再单列一次就是重复计数
--    （第一版就踩了：实机打出「数据 40.7 + 扫描 10.8 + 列宽 21.7」其实前一项已含后两项）。
local PF_ORDER = { "导航", "数据", "工具P", "工具R", "工具L", "信息卡",
                   "布局", "铺行", "开关", "请求" }
-- 「量宽」= ns.hui.TextW（真·引擎字体测量，记忆化**命中不算**）；
-- 「量宽调用」= PD.TextW（含记忆化命中）⇒ 两个一起看能算出缓存命中率。
-- 「完整预热」= DG.RequestItem（掉落页那套：建 tooltip + CreateFromItemID）；
-- 「发包」= C_Item.RequestLoadItemDataByID（只请求载入）。
local PF_KIND  = { "量宽", "量宽调用", "取名", "取名(引擎)", "发包", "完整预热", "建行", "上数据" }

local function pfNow()
    if type(debugprofilestop) == "function" then return debugprofilestop() end
    if type(GetTime) == "function" then return GetTime() * 1000 end
    return 0
end

local function pfOut(s) print("|cff46bf72[DF性能]|r " .. s) end

-- ★★ 第八刀（rev14）：工具行闸门内部切刀用的记号器。
--   PD.PaintTool 在**热路径**上 ⇒ 探针关（不在入口里）时 __pfT0 返回 nil，
--   闸门里一次 pfNow 都不调。起止都用 pfNow()（桩安全），不用 GetTime()。
--   ★ 必须**运行期动态取**：第七刀把 DG.ItemName 在加载期抓成局部，探针
--     运行期替换就再也不生效（审计全红），这里不能重犯。
function PD.__pfT0()
    if not PF_SUB then return nil end
    return pfNow()
end

function PD.__pfMark(tag, t0)
    if not PF_SUB or not t0 then return end
    local dt = pfNow() - t0
    local e = PF_SUB[tag]
    if e then e[1] = e[1] + 1; e[2] = e[2] + dt
    else PF_SUB[tag] = { 1, dt } end
end

-- ★★ 第九刀（rev15）：只记次数、不计时的记号器（闸门里判「已显 / 未显」用）。
--   与 __pfMark 同源 ⇒ 同样必须**运行期动态取**。
function PD.__pfAdd(tag, n)
    if not PF_SUB or not n then return end
    local e = PF_SUB[tag]
    if e then e[1] = e[1] + n else PF_SUB[tag] = { n, 0 } end
end

local function pfBegin(where)
    PF_DEPTH = PF_DEPTH + 1
    if PF_DEPTH == 1 then
        PF_MS, PF_N = {}, {}
        PF_SUB, PF_SET = {}, {}
        PF_SKIN0 = (ns.hui and ns.hui.__skinBuilds) or 0
        PF_TB0 = (ns.hui and ns.hui.__tryBuilds) or 0
        local _st = ns.hui and ns.hui.__stripStat
        if _st then
            local a, b, c = _st()
            PF_STR0, PF_STRM0, PF_STRS0 = a or 0, b or 0, c or 0
        else
            PF_STR0, PF_STRM0, PF_STRS0 = 0, 0, 0
        end
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
    -- ★ 细分：这几项**已经在「数据」里**（RowsRecipe 内部调用），只作分解展示，
    --   **不相加**。「setter」是引擎 setter 的真实**调用次数**，单价另用
    --   /dfprofperf bench 量（离线桩是空表，只能实机量）。
    local sub = {}
    for _, k in ipairs({ "扫描", "建spec", "列宽材料", "材料串", "单条spec",
                        "工具尺寸", "搜索预留" }) do
        local e = PF_SUB and PF_SUB[k]
        if e then sub[#sub + 1] = string.format("%s %d次/%.1f", k, e[1], e[2]) end
    end
    if #sub > 0 then pfOut("  └ 细分（已含在上面某一段里，不相加）：" .. table.concat(sub, " · ")) end
    local st = {}
    for _, k in ipairs({ "SetText", "SetTextColor", "SetPoint", "SetSize",
                        "SetShown", "Show", "Hide" }) do
        local e = PF_SET and PF_SET[k]
        if e then st[#st + 1] = string.format("%s %d次", k, e[1]) end
    end
    if #st > 0 then pfOut("  └ setter 调用：" .. table.concat(st, " · ")) end
    -- ★★ 第八刀（rev14）：**无条件**打印 + 版本号。
    --   第七刀把这一行写成「sk>0 才打」⇒ 实机看不到它时**无法区分**
    --   「这一版没加载」与「加载了但一副边框帧都没建」。现在恒打：
    --   读到 N=0 就是「本版在跑，且这一入口没建帧」这个硬事实。
    local sk = ((ns.hui and ns.hui.__skinBuilds) or 0) - (PF_SKIN0 or 0)
    local tb = ((ns.hui and ns.hui.__tryBuilds) or 0) - (PF_TB0 or 0)
    pfOut(string.format("  └ 皮按钮帧：建 %d 次 · TryBuild 调用 %d 次（rev14）", sk, tb))
    -- ★★ 第八刀（rev14）：工具行闸门内部拆解。这四项**已含在「工具P」里**，
    --   只作分解展示，**不相加**。
    local zg = PF_SUB and PF_SUB["闸-合计"]
    if zg then
        local seg, hit = {}, 0
        for _, kv in ipairs({ { "闸-尺寸", "尺寸" }, { "闸-锚点", "锚点" },
                              { "闸-文本", "文本" }, { "闸-显示", "显示" } }) do
            local e = PF_SUB[kv[1]]
            if e then
                seg[#seg + 1] = string.format("%s %.1f", kv[2], e[2])
                hit = e[1]
            end
        end
        pfOut(string.format("  └ 工具闸门（已含在「工具P」里）：%d 开 / %.1fms = %s（其中已显 %d）",
                            hit, zg[2], table.concat(seg, " + "),
                            (PF_SUB["闸-已显"] and PF_SUB["闸-已显"][1]) or 0))
    end
    -- ★★ 第九刀（rev15）：**无条件**打印像素条复算（Hui 侧计数器）。
    --   实机「点页签 recipe」时工具行 16 颗按钮 Hide→Show，每一步都触发子帧
    --   OnShow 的 ReapplyStripPixels —— 这条数字直接说明它是不是那 24.5ms：
    --   改对了应当是「16 次 / ~0.0ms / 共扫 ~64 条」（16 × 4）。
    local stn, stms, stscan = 0, 0, 0
    if ns.hui and ns.hui.__stripStat then stn, stms, stscan = ns.hui.__stripStat() end
    pfOut(string.format("  └ 皮条纹复算：%d 次 / %.1fms / 共扫 %d 条（rev15）",
                        stn - (PF_STR0 or 0), stms - (PF_STRM0 or 0), stscan - (PF_STRS0 or 0)))
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

-- ④b 细分：这几项**已经在「数据」里**（RowsRecipe 内部调用），只作分解展示，
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
-- 工具行内部（都在 工具P 那一段里）：量大头是不是 ToolSize 的字体测量。
pfSub(PD, "ToolSize",      "工具尺寸")
pfSub(PD, "SearchReserve", "搜索预留")

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
    -- ★ 2026-10-09 第六轮：bench 单价告诉我们 setter 便宜（0.2~0.6µs），
    --   但「便宜 × 多少次」才是耗时 ⇒ 这些也得计数。都是没有
    --   hooksecurefunc 挂在实例上的方法，覆盖实例字段不影响 HUI 的钩子。
    pfWrapSetter(f, "SetPoint")
    pfWrapSetter(f, "SetSize")
    pfWrapSetter(f, "SetShown")
    pfWrapSetter(f, "Show")
    pfWrapSetter(f, "Hide")
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
do
    local raw = PD.Render
    PD.Render = function(...)
        if not PD.PERF then return raw(...) end
        -- ★ 每一层都补包（2026-10-09 第六轮修）：入口层（SetTab / Show）会**先**把
        --   PF_DEPTH 置 1 再调 Render ⇒ 只看 PF_DEPTH == 0 的话第一次点击永远
        --   装不上计数器（实机第一版 setter 行一次都没出现过）。
        --   pfWrapSetter 自带 __dfw<meth> 幂等标记，重复包无害。
        pfWrapAll()
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
-- ★ 三拆（2026-10-09 第六轮）：实机「工具行 28.3ms」是三项之和，得先知道是谁。
pfTime(PD, "PaintTool",    "工具P")
pfTime(PD, "RecipeTool",   "工具R")
pfTime(PD, "LevelTool",    "工具L")
pfTime(PD, "Layout",      "布局")
pfTime(PD, "PaintRows",   "铺行")
pfTime(PD, "PlaceSettingsToggles", "开关")
pfTime(PD, "RequestRows", "请求")

-- ④ 计数：真实引擎调用（这几项离线桩全是假的，正是实机与离线的差）
pfCount(ns.hui, "TextW",   "量宽")       -- 引擎字体测量（记忆化命中不算）
pfCount(PD, "TextW",       "量宽调用")   -- 含记忆化命中 ⇒ 两项相除 = 命中率
pfCount(PD, "ItemName",    "取名")       -- 总调用（含记忆化命中）
-- ★ 必须包 DG.ItemInfo 而不是 DG.ItemName：PD.ItemName 内部调的是**加载期捕获**
--   的局部 _origItemName，包 DG.ItemName 收不到数（恒 0 = 白测）。
--   ItemInfo 才是真正落到 GetItemInfo(id) 的那一层 ⇒ 两项相除就是命中率。
pfCount(DG, "ItemInfo",    "取名(引擎)")
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
        if msg == "rep" then
            -- ★★ 冷 / 热自测（2026-10-09 第六轮）：连渲同一页 3 次。
            --   第 1 次含「一次性建帧」，第 2/3 次是热路径。两者差多大，
            --   就知道某一段值不值得挪进分帧段 / 做预建。
            if not (PD.built and PD.page) then
                pfOut("先打开专业页（/df zy）再 rep。")
                return
            end
            local save, saveMin = PD.PERF, PD.PERF_MIN
            PD.PERF, PD.PERF_MIN = "all", 0
            for i = 1, 3 do
                pfOut("  ---- 第 " .. i .. " 次 ----")
                PD.Render()
            end
            PD.PERF, PD.PERF_MIN = save, saveMin
            pfOut("rep 完成（第 1 次含建帧，后两次是热路径）。")
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
                local r = RGet(slug)
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
        if msg == "bench" then
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
            pfOut("已关闭。")
        else
            PD.PERF = true
            pfOut(string.format("已开启：只打慢过 %dms 的。点几下配方页即可；"
                                .. "/dfprofperf all 连快的也打，scan 挨个专业跑一遍。",
                                PD.PERF_MIN or 6))
        end
    end
end

-- ══ 行池取证（/dfprofrows） ═══════════════════════════════════════════════════
--   ★ 为什么要它：离线 harness（lupa 桩）把「隐藏」记在**帧自己**的 __shown 上，
--     而真机里「父帧隐藏 ⇒ 整棵子树不渲染」。凡是**真机看得见、离线判干净**的
--     残留，只剩两种形态：
--       ① 孤儿帧 —— 帧挂在 PD.child 下，但**根本不在行池 PD.rows 里** ⇒
--          「藏掉池里多余的行」那条永远碰不到它（`PD.rows = {}` 清池、
--          皮肤重建、第三方插件重挂父级都能造出来）；显示的还是上一页内容。
--       ② 越界行 —— 在池里、也还显示着，但 `i > #PD.specs`（本页没有它的
--          位置）⇒ 它身上挂的就是上一页的规格。
--     这个命令把这两类一次查清，并把它**看起来像什么**打出来（三列文本 +
--     材料块数 + 分段链 / 商人半段的显示状态）。
--   ★ 只读：不改任何字段、不渲染、不发包。
--   ★ 用法：/dfprofrows        当前页：只报「异常项」+ 汇总
--           /dfprofrows all    连**合法**的可见行也逐行打（肉眼比对用）
function PD.AuditRows(all)
    if not (PD.built and PD.page) then
        pfOut("先打开专业页（/df zy）再 /dfprofrows。")
        return
    end
    -- 全量输出进 buf 并落到 DungeonsForeverDB.profAudit（/reload 后写盘）——
    -- 聊天框复制长文本不可靠（rev17：用户实机复制失败），游戏外直接读文件。
    local buf = {}
    local function out(s) buf[#buf + 1] = s; pfOut(s) end
    local function sink(s) buf[#buf + 1] = s end   -- 只进文件，不刷聊天框
    local specN = #(PD.specs or {})
    local idxOf, idxs = {}, {}
    local nPool, nShown = 0, 0
    for i, rr in pairs(PD.rows or {}) do
        idxOf[rr] = i
        idxs[#idxs + 1] = i
        nPool = nPool + 1
        if rr.IsShown and rr:IsShown() then nShown = nShown + 1 end
    end
    table.sort(idxs)
    out(string.format("页面 cur=%s tab=%s 子页=%s 设置页=%s",
                        tostring(PD.cur), tostring(PD.tab),
                        tostring(PD.autoPage), tostring(PD.setOpen)))
    out(string.format("行池 %d 帧 / 显示中 %d / 本页 spec %d",
                        nPool, nShown, specN))
    -- 骨架池可见性：段落卡 / 金卡 / 设置开关 —— 漏藏在这里直接现形
    local nSec, nSecG = 0, 0
    if PD.secCards then
        for _, c in ipairs(PD.secCards) do if c.IsShown and c:IsShown() then nSec = nSec + 1 end end
    end
    if PD.secGoldCards then
        for _, c in ipairs(PD.secGoldCards) do if c.IsShown and c:IsShown() then nSecG = nSecG + 1 end end
    end
    out(string.format("段落卡 可见 %d / 金卡 可见 %d", nSec, nSecG))
    -- 已知骨架帧集合：杂帧扫描要跳过它们（段落卡按 hasSecs 显示是正常的）
    local known = {}
    if PD.secCards then for _, c in ipairs(PD.secCards) do known[c] = true end end
    if PD.secGoldCards then for _, c in ipairs(PD.secGoldCards) do known[c] = true end end
    if PD.setToggles then for _, c in ipairs(PD.setToggles) do known[c] = true end end
    if PD.setHelps then for _, c in ipairs(PD.setHelps) do known[c] = true end end

    local function texts(r)
        local t = {}
        for _, k in ipairs({ "e", "a", "b", "c", "d", "f", "dv" }) do
            local fs = r[k]
            if fs and fs.GetText then
                local ok, v = pcall(fs.GetText, fs)
                if ok and v and v ~= "" then
                    t[#t + 1] = k .. "=" .. tostring(v)
                end
            end
        end
        return table.concat(t, " | ")
    end
    local function shown(f)
        return (f and f.IsShown and f:IsShown()) and true or false
    end
    local function shape(r)
        local nblk = 0
        for j = 1, #(r.blk or {}) do
            local b = r.blk[j]
            if b.ic and shown(b.ic) then nblk = nblk + 1 end
        end
        local nmn, nmz = 0, 0
        for j, mfs in pairs(r.mn or {}) do if shown(mfs) then nmn = nmn + 1 end end
        for j = 1, #(r.mz or {}) do if shown(r.mz[j]) then nmz = nmz + 1 end end
        return string.format("材料块=%d 分段字串=%d 分段热区=%d %s",
                             nblk, nmn, nmz, shown(r.dv) and "商人半段○" or "商人半段-")
    end

    -- ① 越界行：在池里、显示着，但本页没有对应 spec
    local bad = 0
    for _, i in ipairs(idxs) do
        local r = PD.rows[i]
        if shown(r) and not (PD.specs and PD.specs[i]) then
            bad = bad + 1
            out(string.format("  [越界行] idx=%d (%s) %s", i, shape(r), texts(r)))
        end
    end

    -- ② 孤儿帧：PD.child / PD.page 下「行样」的可见帧，却不在行池里
    local function isRowLike(f)
        return (f.a or f.mn or f.blk) and true or false
    end
    local nOrphan = 0
    local function scan(f, where)
        if not (f and type(f.GetChildren) == "function") then return end
        local ok, kids = pcall(function() return { f:GetChildren() } end)
        if not ok or type(kids) ~= "table" then return end
        for _, ch in ipairs(kids) do
            if ch ~= f and type(ch) == "table" and shown(ch)
               and isRowLike(ch) and not idxOf[ch] and not known[ch] then
                nOrphan = nOrphan + 1
                out(string.format("  [孤儿帧] %s @%s %sx%s %s", tostring(where),
                                    tostring(rawget(ch, "__name")),
                                    tostring(ch.GetWidth and ch:GetWidth()),
                                    tostring(ch.GetHeight and ch:GetHeight()),
                                    texts(ch)))
            end
        end
    end
    scan(PD.child, "child")
    scan(PD.page, "page")

    -- ③ 杂帧：PD.child / PD.page 下可见、却不在行池里的**任何**子帧（不限行样）。
    --    ②只认「行样」帧——段落卡、信息卡、或任何漏藏的骨架帧在这里现形。
    --    残留若不是行池的，答案就在这段输出里。
    --    ★ 只扫 PD.child（列表内容层）。PD.page 上常驻着左导航 / 顶部页签 / 信息卡
    --      等骨架帧（rev16 实测误报 31 个），页面骨架可见不是残留。
    local nMisc = 0
    local function geom(f)
        local l, b = -1, -1
        pcall(function() l = math.floor((f:GetLeft() or 0) + 0.5) end)
        pcall(function() b = math.floor((f:GetBottom() or 0) + 0.5) end)
        return l, b
    end
    local function scanMisc(f, where)
        if not (f and type(f.GetChildren) == "function") then return end
        local ok, kids = pcall(function() return { f:GetChildren() } end)
        if not ok or type(kids) ~= "table" then return end
        for _, ch in ipairs(kids) do
            if ch ~= f and type(ch) == "table" and shown(ch)
               and not idxOf[ch] and not known[ch] then
                nMisc = nMisc + 1
                if nMisc <= 20 then
                    local l, b = geom(ch)
                    out(string.format("  [杂帧] %s @%s x=%d y=%d %s %s",
                                        tostring(where),
                                        tostring(rawget(ch, "__name")),
                                        l, b, shape(ch), texts(ch)))
                end
            end
        end
    end
    scanMisc(PD.child, "child")

    if all then
        for _, i in ipairs(idxs) do
            local r = PD.rows[i]
            local sp = PD.specs and PD.specs[i]
            if shown(r) then
                -- spec 应有内容并排打出：行上实际文本与 spec 对不上 =
                -- 「同索引内容残留」（审计①查不出——idx 没越界但内容是上一页的）
                -- ★ 只进文件不刷聊天框（rev17）：聊天框复制长文本不可靠
                local stxt = ""
                if sp then
                    stxt = tostring(sp.text or sp.sub or "")
                    if #stxt > 26 then stxt = stxt:sub(1, 26) .. "…" end
                end
                local l = geom(r)
                sink(string.format("  行 idx=%d kind=%s spec[%s] x=%d %s || %s", i,
                                   tostring(sp and sp.kind), stxt, l,
                                   shape(r), texts(r)))
            end
        end
    end
    out(string.format("结论：越界行 %d / 孤儿帧 %d / 杂帧 %d ⇒ %s", bad, nOrphan, nMisc,
                      (bad + nOrphan + nMisc == 0) and "干净" or "★ 有残留，见上面几行"))
    out("全量已存档（profAudit），/reload 后游戏外直接读文件，无需复制。")
    -- 落盘：全量输出（含聊天框没刷的逐行转储）存进 SavedVariables，
    -- /reload 或退角色后写盘，游戏外直接读 WTF 文件，不用复制聊天框。
    if type(DungeonsForeverDB) == "table" then
        DungeonsForeverDB.profAudit = {
            t = date("%Y-%m-%d %H:%M:%S"),
            page = tostring(PD.cur) .. "/" .. tostring(PD.tab) .. "/" .. tostring(PD.autoPage),
            n = #buf,
            lines = buf,
        }
    end
end

-- ★ 全文本普查（rev19）：递归 PD.page 整棵树（不限层级、不跳行池内部），
--   把所有「实际可见且带非空文本」的 FontString 全部点名：父链路径 + 屏幕坐标 + 文本。
--   四道行审计（越界/孤儿/杂帧/内容比对）都干净而屏幕仍有残留时，残留在更深的层级——
--   这一普查无论它挂在哪个孙帧/曾孙帧上都会现形。结果照旧落 profAudit。
function PD.CensusText()
    if not (PD.built and PD.page) then
        pfOut("先打开专业页再普查。")
        return
    end
    local buf = {}
    local function sink(s) buf[#buf + 1] = s end
    local idxOf = {}
    for i, rr in pairs(PD.rows or {}) do idxOf[rr] = i end
    local n = 0
    local function coords(f)
        local l, b = -1, -1
        pcall(function() l = math.floor((f:GetLeft() or 0) + 0.5) end)
        pcall(function() b = math.floor((f:GetBottom() or 0) + 0.5) end)
        return l, b
    end
    -- 行内字段指纹：报出这条字串到底挂在行的哪个槽位上（f/mn/blk.nm/…）
    local function fieldOf(r, fs)
        if fs == r.f then return "f" end
        if fs == r.dv then return "dv" end
        for _, k in ipairs({ "a", "b", "c", "d", "e" }) do
            if fs == r[k] then return k end
        end
        if fs == r.tagFs then return "tag" end
        for j, mfs in pairs(r.mn or {}) do
            if fs == mfs then return "mn[" .. j .. "]" end
        end
        for j = 1, #(r.blk or {}) do
            local b = r.blk[j]
            if fs == b.nm then return "blk[" .. j .. "].nm" end
            if fs == b.ct then return "blk[" .. j .. "].ct" end
        end
        return "?"
    end
    -- 行池行专项：逐字段点名可见且带字的字串（不递归——行内没有子帧容器）
    local function auditRow(r, idx)
        local rs = "行#" .. idx .. "(" .. (r.IsShown and r:IsShown() and "显示" or "自身隐藏") .. ")"
        local ok, regions = pcall(function() return { r:GetRegions() } end)
        if not (ok and type(regions) == "table") then return end
        for _, fs in ipairs(regions) do
            if type(fs) == "table" and fs.GetText and fs.IsVisible and fs:IsVisible() then
                local ok2, t = pcall(fs.GetText, fs)
                if ok2 and t and t ~= "" then
                    n = n + 1
                    if n <= 4000 then
                        local l, b = coords(fs)
                        sink(string.format("  [字串] %s.%s x=%d y=%d %s", rs,
                                           fieldOf(r, fs), l, b,
                                           (tostring(t):gsub("|", "¦"))))
                    end
                end
            end
        end
    end
    local function walk(f, path, depth)
        if depth > 8 then return end
        local ok, regions = pcall(function() return { f:GetRegions() } end)
        if ok and type(regions) == "table" then
            for _, r in ipairs(regions) do
                if type(r) == "table" and r.GetText and r.IsVisible and r:IsVisible() then
                    local ok2, t = pcall(r.GetText, r)
                    if ok2 and t and t ~= "" then
                        n = n + 1
                        if n <= 4000 then
                            local l, b = coords(r)
                            sink(string.format("  [字串] %s x=%d y=%d %s", path, l, b,
                                               (tostring(t):gsub("|", "¦"))))
                        end
                    end
                end
            end
        end
        local okk, kids = pcall(function() return { f:GetChildren() } end)
        if okk and type(kids) == "table" then
            for _, ch in ipairs(kids) do
                if type(ch) == "table" and ch.IsVisible and ch:IsVisible() then
                    if idxOf[ch] then
                        auditRow(ch, idxOf[ch])
                    else
                        walk(ch, path .. ">" .. tostring(rawget(ch, "__name") or "?"), depth + 1)
                    end
                end
            end
        end
    end
    walk(PD.page, "page", 0)
    sink(string.format("普查：实际可见的非空字串 %d 条", n))
    if type(DungeonsForeverDB) == "table" then
        DungeonsForeverDB.profAudit = {
            t = date("%Y-%m-%d %H:%M:%S"),
            page = tostring(PD.cur) .. "/" .. tostring(PD.tab) .. "/" .. tostring(PD.autoPage),
            n = #buf,
            lines = buf,
        }
    end
    pfOut(string.format("全文本普查完成：%d 条可见字串，已存档（/reload 后游戏外读）。", n))
end

if type(SlashCmdList) == "table" then
    SLASH_DUNGEONSFOREVERPROFROWS1 = "/dfprofrows"
    SlashCmdList["DUNGEONSFOREVERPROFROWS"] = function(msg)
        local m = string.lower(tostring(msg or "")):gsub("^%s+", ""):gsub("%s+$", "")
        -- ★ hide / show（rev18）：一锤定音测试——把整个专业面板藏起来。
        --   残留还在 ⇒ 它根本不在专业面板的帧树里（别的悬浮窗叠着）；
        --   残留跟着消失 ⇒ 它就在面板里，是审计覆盖不到的层（再上全文本普查）。
        if m == "hide" then
            if PD.page and PD.page.Hide then
                PD.page:Hide()
                pfOut("专业面板已整体隐藏（画面别动）。残留还在 ⇒ 不在面板里；"
                      .. "跟着消失 ⇒ 在面板里。/dfprofrows show 恢复。")
            end
            return
        end
        if m == "show" then
            if PD.page and PD.page.Show then
                PD.page:Show()
                pfOut("专业面板已恢复。")
            end
            return
        end
        -- ★ text（rev19）：全文本普查。残留在屏时刻跑，然后 /reload 落盘。
        if m == "text" then
            PD.CensusText()
            return
        end
        PD.AuditRows(m == "all")
    end
end

if RA and RA.OnPlanChanged then
    RA.OnPlanChanged(function(slug, plan)
        PD.craftAll=nil
        if type(slug) == "table" then plan = slug; slug = plan.slug end
        if slug == PD.cur and plan then PD.autoSnapshot = plan; PD.autoSnapshotSlug = slug end
        if PD.built and ns.PageVisible(PD.page)
           and (slug == nil or slug == PD.cur) then PD.RequestRender() end
    end)
end
if RA and RA.OnPricesChanged then
    RA.OnPricesChanged(function()
        if PD.built and ns.PageVisible(PD.page) then
            PD.RequestRender()
        end
    end)
end

if ns.ProfExecution and ns.ProfExecution.OnChanged then
    ns.ProfExecution.OnChanged(function(slug)
        if slug==PD.cur and PD.built and PD.tab=="leveling" and ns.PageVisible(PD.page) then
            PD.RequestRender()
        end
    end)
end
