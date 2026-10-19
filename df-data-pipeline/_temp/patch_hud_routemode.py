# -*- coding: utf-8 -*-
"""HUD 路线模式补丁：专业升级 HUD 的数据随专业页「固定路线 / 自动计算」模式切换（2026-10-11）。

改动面（全部落在 Core/ProfFollow.lua，LF，一次执行内完成）：
  ① 顶部取 ns.ProfRouteAuto + 文件头注释补路线模式口径；
  ② 新增 routeFor / routeTarget / routeKey（口径与 ProfessionUI.RowsLeveling 逐项一致）；
  ③ derivedStep / shopList / Sync / Toggle / Prev / Skip / OnMouseWheel / Paint 全部改走 routeFor；
  ④ recMap 并入 rinfo；素材/产物取数走 recMats / recItem / recBreaks（兼容 rinfo 命名字段）；
  ⑤ Paint 段标加「自动计算 / 固定路线」前缀（复用既有 L 键，不新增文案）。
"""
import io

P = "Core/ProfFollow.lua"
s = io.open(P, encoding="utf-8", newline="").read()
assert "\r\n" not in s, "ProfFollow 期望 LF"
orig = len(s)


def rep(old, new, n=1):
    global s
    c = s.count(old)
    assert c == n, "anchor hit %d (expect %d): %r" % (c, n, old[:80])
    s = s.replace(old, new)


# ---- ① 顶部：取自动路线模块 + 头注释补口径 ----
rep("""local LV = ns.ProfLeveling
""",
    """local LV = ns.ProfLeveling
local RA = ns.ProfRouteAuto   -- 自动路线计算（Core/ProfRouteAuto.lua，先于本文件加载）
""")

rep("""--   数据只读 ns.ProfLeveling（升级路线）与 ns.ProfRecipes（材料 / 图标 / 来源），
--   一个字段都不写死；物品名 / 图标一律由客户端给（DG.ItemName / DG.ItemIcon）。
""",
    """--   数据只读 ns.ProfLeveling（升级路线）与 ns.ProfRecipes（材料 / 图标 / 来源），
--   一个字段都不写死；物品名 / 图标一律由客户端给（DG.ItemName / DG.ItemIcon）。
--   ★ 路线模式（2026-10-11）：数据源随专业页「固定路线 / 自动计算」模式切换 ——
--     自动模式下段落 / 购物清单全走 ns.ProfRouteAuto（按拍卖行价格算），口径与专业页逐项一致；
--     不满足（未开 / 没装 Auctionator / 无价格数据）即回落固定路线。
""")

# ---- ② routeFor / routeTarget / routeKey + derivedStep 改走 routeFor ----
rep("""-- 技能推导段落：第一段「上限 > 技能」的；全过则 #steps + 1
local function derivedStep(slug, skill)
    local lv = LV[slug]
    if not (lv and lv.steps) then return nil end
    for i, s in ipairs(lv.steps) do
        if skill < s[2] then return i end
    end
    return #lv.steps + 1
end
""",
    """-- -------------------------------------------------------------------------
-- 路线模式（固定 / 自动）：HUD 数据随专业页「固定路线 / 自动计算」切换（2026-10-11）
--   · 自动 = 设置「自动计算路线」开 + Auctionator 可用 + 算得出结果且已有价格数据；
--     任一不满足 → 回落固定路线（不回退成空页）。
--   · opts 与 ProfessionUI.RowsLeveling 逐项一致（起点 / 三个过滤 / 目标），
--     同一模式下两边算出的路线相同。
--   · 目标等级按 slug 取（HUD 跟随的专业未必是专业页当前专业）。
-- -------------------------------------------------------------------------
local function routeTarget(slug)
    local PD = ns.ProfModule
    local v
    if PD and PD.cur == slug and PD.LvTarget then
        v = PD.LvTarget()
    else
        local db = dbProf()
        v = tonumber(db.lvTarget and db.lvTarget[slug])
    end
    if not v then return 300 end
    return math.max(1, math.min(300, math.floor(v)))
end

-- 返回 mode("auto"/"fixed") + 段落表；自动不可用时回落固定路线
local function routeFor(slug, skill)
    local PD = ns.ProfModule
    if PD and PD.Setting and PD.Setting("autoRoute") and RA and RA.Available() then
        local opts = {
            start = (PD.Setting("autoFromCurrent") and skill) and math.max(1, skill) or 1,
            onlyAH = PD.Setting("autoOnlyAH"),
            noFormula = PD.Setting("autoNoFormula"),
            learnedOnly = PD.Setting("autoLearnedOnly"),
            target = routeTarget(slug),
        }
        local res = RA.Get(slug, opts)
        if res and res.priced then return "auto", res.steps end
    end
    local lv = LV[slug]
    return "fixed", (lv and lv.steps) or nil
end

-- 路线指纹：模式 + 段数 + 首末段（自动路线随价格 / 设置重算时用它决定要不要重推指针）
local function routeKey(mode, steps)
    if not steps then return tostring(mode) .. ":0" end
    local a, b = steps[1], steps[#steps]
    return format("%s:%d:%s:%s:%s", tostring(mode), #steps,
                  tostring(a and a[1]), tostring(a and a[3]), tostring(b and b[2]))
end

-- 技能推导段落：第一段「上限 > 技能」的；全过则 #steps + 1
local function derivedStep(slug, skill)
    local _, steps = routeFor(slug, skill)
    if not steps then return nil end
    for i, s in ipairs(steps) do
        if skill < s[2] then return i end
    end
    return #steps + 1
end
""")

# ---- ③ recMap 并入 rinfo + 取数助手 ----
rep("""-- spellID → 配方行（rec[2] = 产出物 ID / rec[12] = 材料 / rec[13]+rec[14] = 来源）
local recCache = {}
local function recMap(slug)
    local c = recCache[slug]
    if not c then
        c = {}
        local rr = R[slug]
        if rr and rr.rows then
            for _, r in ipairs(rr.rows) do c[r[1]] = r end
        end
        recCache[slug] = c
    end
    return c
end
""",
    """-- spellID → 配方行（rec[2] = 产出物 ID / rec[12] = 材料 / rec[13]+rec[14] = 来源）
-- rinfo 行（升级路线里配方表没有的法术：附魔配方 / 魔棒）用命名字段 makes / mats / learn…grey
local function recMats(rec) return rec and (rec[12] or rec.mats) or nil end
local function recItem(rec) return rec and (rec[2] or rec.makes) or nil end
local function recBreaks(rec)
    if not rec then return nil end
    return rec[7] or rec.learn, rec[8] or rec.yellow, rec[9] or rec.green, rec[10] or rec.grey
end

local recCache = {}
local function recMap(slug)
    local c = recCache[slug]
    if not c then
        c = {}
        local rr = R[slug]
        if rr and rr.rows then
            for _, r in ipairs(rr.rows) do c[r[1]] = r end
        end
        -- 自动 / 固定路线都可能引用 rinfo 里的法术（附魔配方游离在 enchants 之外、魔棒两头都不在）
        local lv = LV[slug]
        if lv and type(lv.rinfo) == "table" then
            for spell, ri in pairs(lv.rinfo) do
                if not c[spell] then c[spell] = ri end
            end
        end
        recCache[slug] = c
    end
    return c
end
""")

# ---- ④ Sync：路线模式 / 内容变化时重推指针 ----
rep("""    local d = derivedStep(s.slug, s.skill or 0)
    if d and d > (s.step or 1) then s.step = d end
end
""",
    """    -- 路线模式 / 路线内容变了（自动路线随价格、设置重算）：段落表整块换掉，指针按技能重推
    local mode, steps = routeFor(s.slug, s.skill or 0)
    local key = routeKey(mode, steps)
    if key ~= s.rkey then
        s.rkey = key
        s.step = derivedStep(s.slug, s.skill or 0) or 1
        PF.view = 0
    end
    local d = derivedStep(s.slug, s.skill or 0)
    if d and d > (s.step or 1) then s.step = d end
end
""")

# ---- ⑤ Toggle：初始化路线指纹 ----
rep("""        local cur = skillOf(slug) or 0
        s = { slug = slug, skill = cur, step = derivedStep(slug, cur) or 1, t0 = time() }
        p.follow[k] = s
""",
    """        local cur = skillOf(slug) or 0
        s = { slug = slug, skill = cur, step = derivedStep(slug, cur) or 1, t0 = time() }
        local _mode, _steps = routeFor(slug, cur)
        s.rkey = routeKey(_mode, _steps)
        p.follow[k] = s
""")

# ---- ⑥ Prev / Skip 改走 routeFor ----
rep("""function PF.Prev()
    local s = st()
    local lv = s and LV[s.slug]
    if not (lv and lv.steps) then return end
    PF.view = math.max(-((s.step or 1) - 1), (PF.view or 0) - 1)
    PF.Paint()
end
""",
    """function PF.Prev()
    local s = st()
    if not (s and s.slug) then return end
    local _, steps = routeFor(s.slug, s.skill)
    if not steps then return end
    PF.view = math.max(-((s.step or 1) - 1), (PF.view or 0) - 1)
    PF.Paint()
end
""")

rep("""function PF.Skip()
    local s = st()
    local lv = s and LV[s.slug]
    if not (lv and lv.steps) then return end
    PF.view = math.min(#lv.steps - (s.step or 1) + 1, (PF.view or 0) + 1)
    PF.Paint()
end
""",
    """function PF.Skip()
    local s = st()
    if not (s and s.slug) then return end
    local _, steps = routeFor(s.slug, s.skill)
    if not steps then return end
    PF.view = math.min(#steps - (s.step or 1) + 1, (PF.view or 0) + 1)
    PF.Paint()
end
""")

# ---- ⑦ craftsLeft 走 recBreaks（兼容 rinfo 命名字段）----
rep("""    local from = math.max(skill or 0, seg[1])
    if from >= seg[2] then return 0 end
    if rec and rec[8] and rec[9] and rec[10] and rec[9] > rec[8] and rec[10] > rec[9] then
        local total = 0
        for sk = from, seg[2] - 1 do
            local e = expPerPoint(sk, rec[7], rec[8], rec[9], rec[10])
            if not e then break end
            total = total + e
        end
        -- 循环没被灰色打断才采用概率口径（打断说明中途已灰，退回线性口径）
        if expPerPoint(seg[2] - 1, rec[7], rec[8], rec[9], rec[10]) then return total end
    end
""",
    """    local from = math.max(skill or 0, seg[1])
    if from >= seg[2] then return 0 end
    local learn, y, g, gr = recBreaks(rec)
    if y and g and gr and g > y and gr > g then
        local total = 0
        for sk = from, seg[2] - 1 do
            local e = expPerPoint(sk, learn, y, g, gr)
            if not e then break end
            total = total + e
        end
        -- 循环没被灰色打断才采用概率口径（打断说明中途已灰，退回线性口径）
        if expPerPoint(seg[2] - 1, learn, y, g, gr) then return total end
    end
""")

# ---- ⑧ shopList 改走 routeFor + recMats ----
rep("""local function shopList(s)
    local lv = LV[s.slug]
    local rm = recMap(s.slug)
    local totals, order = {}, {}
    for i = (s.step or 1), #lv.steps do
        local seg = lv.steps[i]
        local rec = rm[seg[3]]
        local crafts = seg[4] or 0
        if i == s.step then
            crafts = math.ceil(craftsLeft(seg, s.skill, rec))
        end
        if rec and rec[12] and crafts > 0 then
            for _, m in ipairs(rec[12]) do
                local e = totals[m[1]]
""",
    """local function shopList(s)
    local _, steps = routeFor(s.slug, s.skill)
    if not steps then return {} end
    local rm = recMap(s.slug)
    local totals, order = {}, {}
    for i = (s.step or 1), #steps do
        local seg = steps[i]
        local rec = rm[seg[3]]
        local mats = recMats(rec)
        local crafts = seg[4] or 0
        if i == s.step then
            crafts = math.ceil(craftsLeft(seg, s.skill, rec))
        end
        if mats and crafts > 0 then
            for _, m in ipairs(mats) do
                local e = totals[m[1]]
""")

# ---- ⑨ OnMouseWheel 改走 routeFor ----
rep("""        local s = st()
        local lv = s and LV[s.slug]
        if not (lv and lv.steps) then return end
        PF.view = math.max(-(s.step - 1), math.min(#lv.steps - s.step + 1, (PF.view or 0) - delta))
""",
    """        local s = st()
        if not (s and s.slug) then return end
        local _, steps = routeFor(s.slug, s.skill)
        if not steps then return end
        PF.view = math.max(-(s.step - 1), math.min(#steps - s.step + 1, (PF.view or 0) - delta))
""")

# ---- ⑩ paintMats 走 recMats ----
rep("""local function paintMats(seg, rm, sold, w, remaining)
    local rec = rm[seg[3]]
    local n = 0
    local pending = false
    local canCraft
    if rec and rec[12] and #rec[12] > 0 then
""",
    """local function paintMats(seg, rm, sold, w, remaining)
    local rec = rm[seg[3]]
    local mats = recMats(rec)
    local n = 0
    local pending = false
    local canCraft
    if mats and #mats > 0 then
""")

rep("""        for _, m in ipairs(rec[12]) do
            local per = (m[2] or 1)
""",
    """        for _, m in ipairs(mats) do
            local per = (m[2] or 1)
""")

rep("""        for i, m in ipairs(rec[12]) do
            if i > MAT_MAX then break end
""",
    """        for i, m in ipairs(mats) do
            if i > MAT_MAX then break end
""")

rep("""        if #rec[12] > MAT_MAX then
""",
    """        if #mats > MAT_MAX then
""")

rep("""            more:SetText(format(L["…共 %d 种材料，进购物清单看合计"], #rec[12]))
""",
    """            more:SetText(format(L["…共 %d 种材料，进购物清单看合计"], #mats))
""")

# ---- ⑪ Paint：段落表走 routeFor + 段标加模式前缀 ----
rep("""    local s = st()
    if not (s and s.slug) then f:Hide() return end
    local slug = s.slug
    local lv = LV[slug]
    if not (lv and lv.steps) then f:Hide() return end
    local steps = lv.steps
""",
    """    local s = st()
    if not (s and s.slug) then f:Hide() return end
    local slug = s.slug
    local mode, steps = routeFor(slug, s.skill)
    if not steps then f:Hide() return end
""")

rep("""    f.seg:SetText(format(L["段落 %d / %d"], vi, #steps))
""",
    """    f.seg:SetText(((mode == "auto") and L["自动计算"] or L["固定路线"]) .. " · "
                  .. format(L["段落 %d / %d"], vi, #steps))
""")

# ---- ⑫ Paint：产物图标走 recItem ----
rep("""        if rec and rec[2] then
            card.icon:SetTexture(DG.ItemIcon(rec[2]))
        else
            card.icon:SetTexture(Host.FALLBACK_ICON)
        end
""",
    """        local prodItem = recItem(rec)
        if prodItem then
            card.icon:SetTexture(DG.ItemIcon(prodItem))
        else
            card.icon:SetTexture(Host.FALLBACK_ICON)
        end
""")

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("patched OK, len %d -> %d" % (orig, len(s)))
assert "\r\n" not in s
