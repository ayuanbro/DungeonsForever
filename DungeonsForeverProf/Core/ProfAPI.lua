local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end

local gns = _G.DF_NS

local API = {}
local delegates = {}
local itemNameMemo = {}

local function getDS()
  return ns.ProfDataStore or (type(gns) == "table" and gns.ProfDataStore) or nil
end

local function getCond()
  return ns.ProfConditions or (type(gns) == "table" and gns.ProfConditions) or nil
end

local function getProfCfg()
  return ns.ProfessionsConfig or (type(gns) == "table" and gns.ProfessionsConfig) or nil
end

local function getHost()
  return ns.ProfHost or (type(gns) == "table" and gns.ProfHost) or nil
end

function API.RegisterDelegate(name, impl)
  if type(name) ~= "string" then return end
  if impl == nil then
    delegates[name] = nil
  elseif type(impl) == "table" then
    delegates[name] = impl
  end
end

function API.GetDelegate(name)
  return type(name) == "string" and delegates[name] or nil
end

function API.SetProviders(tbl)
  if type(tbl) ~= "table" then return end
  for k, v in pairs(tbl) do
    API.RegisterDelegate(k, v)
  end
end

function API.ProfessionList()
  local cfg = getProfCfg()
  local out = {}
  if type(cfg) == "table" and type(cfg.ORDER) == "table" then
    for i = 1, #cfg.ORDER do
      out[i] = cfg.ORDER[i]
    end
    return out
  end
  local DS = getDS()
  if DS then
    for slug in pairs(DS.Professions()) do
      out[#out + 1] = slug
    end
    table.sort(out)
  end
  return out
end

function API.ProfessionInfo(slug)
  if type(slug) ~= "string" then return nil end
  local cfg = getProfCfg()
  local DS = getDS()
  local pcfg = type(cfg) == "table" and type(cfg.BY_SLUG) == "table" and cfg.BY_SLUG[slug] or nil
  local vcfg = type(cfg) == "table" and type(cfg.VIRTUAL_ENTRIES) == "table" and cfg.VIRTUAL_ENTRIES[slug] or nil
  local pdata = DS and DS.Profession(slug) or nil
  if not pcfg and not vcfg and not pdata then return nil end

  local srcCfg = pcfg or vcfg or {}
  local name = DS and DS.RawText("profession", slug) or nil
  if not name and slug == "crates" then
    local L = ns.L or (type(gns) == "table" and gns.L)
    name = (type(L) == "table" and L["补给箱"]) or "Crates"
  end
  name = name or slug

  return {
    slug = slug,
    name = name,
    kind = (pdata and pdata.kind) or srcCfg.kind or srcCfg.navGroup,
    navGroup = srcCfg.navGroup or (pdata and pdata.kind),
    section = srcCfg.section,
    guideKey = srcCfg.guideKey,
    icon = (pdata and pdata.icon ~= "" and pdata.icon) or srcCfg.icon,
    maxSkillCap = pdata and pdata.maxSkillCap or nil,
    categories = pdata and pdata.categories or nil,
    perkKeys = pdata and pdata.perkKeys or nil,
    racialKeys = pdata and pdata.racialKeys or nil,
    order = srcCfg.order,
    inGetProfessions = srcCfg.inGetProfessions == true,
    supportsAutoRoute = srcCfg.supportsAutoRoute == true,
    supportsExecution = srcCfg.supportsExecution == true,
    fixedOnly = srcCfg.fixedOnly == true,
    gatherOnly = srcCfg.gatherOnly == true,
    hasTrainers = srcCfg.hasTrainers == true,
    hasRecipes = srcCfg.hasRecipes == true,
    hasCert = srcCfg.hasCert == true,
    hasEssences = srcCfg.hasEssences == true,
    skipEconomy = srcCfg.skipEconomy == true,
    subRank = srcCfg.subRank,
    tabs = srcCfg.tabs,
  }
end

function API.SkillLineToSlug(skillLineID)
  local DS = getDS()
  if DS then
    local slug = DS.SkillLineToSlug(skillLineID)
    if slug then return slug end
  end
  local cfg = getProfCfg()
  if type(cfg) == "table" and type(cfg.SKILL_LINE_TO_SLUG) == "table" then
    return cfg.SKILL_LINE_TO_SLUG[skillLineID]
  end
  return nil
end

function API.PlayerProfSet()
  local out = {}
  if type(_G.GetProfessions) == "function" and type(_G.GetProfessionInfo) == "function" then
    local ok, a, b, c, d, e, f = pcall(_G.GetProfessions)
    if ok then
      local slots = { a, b, c, d, e, f }
      for i = 1, 6 do
        local idx = slots[i]
        if idx then
          local oki, _, _, cur, _, _, _, sid = pcall(_G.GetProfessionInfo, idx)
          local slug = oki and API.SkillLineToSlug(sid) or nil
          if slug then
            local val = tonumber(cur) or 0
            if not out[slug] or val > out[slug] then
              out[slug] = val
            end
          end
        end
      end
      return out
    end
  end
  out.__unknown = true
  return out
end

function API.HasProf(slug)
  if not slug then return true end
  local set = API.PlayerProfSet()
  if set.__unknown then return true end
  return set[slug] ~= nil
end

function API.ProfLevel(slug)
  if not slug then return 0 end
  local set = API.PlayerProfSet()
  return tonumber(set[slug]) or 0
end

function API.ProfLearned(cached)
  local ui = delegates.ui
  if ui and type(ui.ProfLearned) == "function" then
    return ui.ProfLearned(cached)
  end
  local out = {}
  if type(_G.GetProfessions) == "function" and type(_G.GetProfessionInfo) == "function" then
    local ok, a, b, c, d, e, f = pcall(_G.GetProfessions)
    if ok then
      local slots = { a, b, c, d, e, f }
      for i = 1, 6 do
        local idx = slots[i]
        if idx then
          local oki, _, _, cur, maxRank, _, _, sid = pcall(_G.GetProfessionInfo, idx)
          local slug = oki and API.SkillLineToSlug(sid) or nil
          if slug then
            local curVal = tonumber(cur) or 0
            local maxVal = tonumber(maxRank) or 0
            local prev = out[slug]
            if prev then
              if curVal > prev.cur then
                prev.cur = curVal
                prev.skillLineID = sid
              end
              if maxVal > prev.max then
                prev.max = maxVal
              end
            else
              out[slug] = {
                cur = curVal,
                max = maxVal,
                skillLineID = sid,
              }
            end
          end
        end
      end
    end
  end
  return out
end

function API.EnsureRecipes(slugOrList)
  local DS = getDS()
  if not DS then return false end
  if type(slugOrList) == "string" then
    return DS.EnsureRecipes(slugOrList) ~= nil
  end
  local list = type(slugOrList) == "table" and slugOrList or DS.RecipeProfessions()
  for i = 1, #list do
    DS.EnsureRecipes(list[i])
  end
  return true
end

function API.CraftProfessionOf(itemID)
  local DS = getDS()
  if not DS or type(itemID) ~= "number" then return nil end
  local spells = DS.CraftIndex(itemID)
  if type(spells) == "table" and #spells > 0 then
    return DS.RecipeProfession(spells[1]), spells
  end
  return nil
end

function API.PatternIndex()
  local ui = delegates.ui
  if ui and type(ui.PatternIndex) == "function" then
    return ui.PatternIndex()
  end
  local DS = getDS()
  if not DS then return {} end
  local out = {}
  local slugs = DS.RecipeProfessions()
  for i = 1, #slugs do
    local slug = slugs[i]
    local bucket = DS.EnsureRecipes(slug)
    if type(bucket) == "table" and type(bucket.recipes) == "table" then
      local spellIDs = {}
      for spellID, recipe in pairs(bucket.recipes) do
        if type(spellID) == "number" and type(recipe) == "table" and recipe.availability == "live" then
          spellIDs[#spellIDs + 1] = spellID
        end
      end
      table.sort(spellIDs)
      for j = 1, #spellIDs do
        local spellID = spellIDs[j]
        local recipe = bucket.recipes[spellID]
        local tids = {}
        local lr = type(DS.LearningRoutes) == "function" and DS.LearningRoutes(spellID) or nil
        if type(lr) == "table" and type(lr.routes) == "table" then
          local seenTid = {}
          for k = 1, #lr.routes do
            local route = lr.routes[k]
            if type(route) == "table" and route.kind == "item" and type(route.teachingItemID) == "number" and not seenTid[route.teachingItemID] then
              seenTid[route.teachingItemID] = true
              tids[#tids + 1] = route.teachingItemID
            end
          end
        end
        local tid = tids[1]
        local compatMats = {}
        for k = 1, #(recipe.reagents or {}) do
          local m = recipe.reagents[k]
          if type(m) == "table" and type(m.itemID) == "number" then
            compatMats[#compatMats + 1] = { m.itemID, m.count or 1 }
          end
        end
        local compatR = {
          [1] = spellID,
          [2] = recipe.outputItemID,
          [3] = recipe.outputCountMin or 1,
          [7] = recipe.learnedAt,
          [12] = compatMats,
          [13] = tid,
        }
        local entry = {
          spellID = spellID,
          itemID = recipe.outputItemID,
          outputItemID = recipe.outputItemID,
          profession = slug,
          recipe = recipe,
          teachingItemID = tid,
          teachingItemIDs = tids,
          pid = tid,
          r = compatR,
        }
        for k = 1, #tids do
          local t = tids[k]
          if not out[t] then
            out[t] = entry
          end
        end
        if type(recipe.outputItemID) == "number" and not out[recipe.outputItemID] then
          out[recipe.outputItemID] = entry
        end
        if not out[spellID] then
          out[spellID] = entry
        end
      end
    end
  end
  return out
end

function API.CrateByItem(id)
  local DS = getDS()
  return DS and DS.Crate(id) or nil
end

function API.CratesList()
  local DS = getDS()
  if not DS then return {} end
  local out = {}
  for _, crate in pairs(DS.Crates()) do
    if type(crate) == "table" then
      out[#out + 1] = crate
    end
  end
  table.sort(out, function(a, b)
    return (a.itemID or 0) < (b.itemID or 0)
  end)
  return out
end

function API.CrateOf(id)
  local ui = delegates.ui
  if ui and type(ui.CrateOf) == "function" then
    return ui.CrateOf(id)
  end
  local DS = getDS()
  if not DS or type(id) ~= "number" then return nil end
  local direct = DS.Crate(id)
  if direct then return direct end
  for _, crate in pairs(DS.Crates()) do
    if type(crate) == "table" and type(crate.options) == "table" then
      for i = 1, #crate.options do
        if crate.options[i].itemID == id then
          return crate
        end
      end
    end
  end
  return nil
end

function API.CrateIcon()
  local DS = getDS()
  if not DS then return nil end
  local firstID
  for id in pairs(DS.Crates()) do
    if not firstID or id < firstID then firstID = id end
  end
  if not firstID then return nil end
  local host = getHost()
  if host and type(host.DG) == "table" and type(host.DG.ItemIcon) == "function" then
    local ok, tex = pcall(host.DG.ItemIcon, firstID)
    if ok and tex and tex ~= "" and tex ~= host.FALLBACK_ICON then return tex end
  end
  if type(_G.C_Item) == "table" and type(_G.C_Item.GetItemIconByID) == "function" then
    local ok, tex = pcall(_G.C_Item.GetItemIconByID, firstID)
    if ok and tex and tex ~= "" then return tex end
  end
  local item = DS.Item(firstID)
  if type(item) == "table" and type(item.icon) == "string" and item.icon ~= "" then
    if not item.icon:find("[/\\]") then
      return "Interface\\Icons\\" .. item.icon
    end
    return item.icon
  end
  return nil
end

function API.WritsList()
  local DS = getDS()
  if not DS then return {} end
  local out = {}
  for _, writ in pairs(DS.Writs()) do
    if type(writ) == "table" then
      out[#out + 1] = writ
    end
  end
  table.sort(out, function(a, b)
    return (a.questID or 0) < (b.questID or 0)
  end)
  return out
end

function API.WritOf(itemID)
  local ui = delegates.ui
  if ui and type(ui.WritOf) == "function" then
    return ui.WritOf(itemID)
  end
  local DS = getDS()
  if not DS or type(itemID) ~= "number" then return nil end
  return DS.WritByItem(itemID) or DS.Writ(itemID) or DS.WritByTarget(itemID)
end

function API.WritTurnInZone(targetID)
  local DS = getDS()
  if not DS or type(targetID) ~= "number" then return nil end
  local writ = DS.WritByTarget(targetID) or DS.WritByItem(targetID) or DS.Writ(targetID)
  if not writ or type(writ.questID) ~= "number" then return nil end
  local q = DS.Quest(writ.questID)
  if not q then return nil end
  return q.areaID or q.uiMapID, q.uiMapID
end

function API.WritZoneOf(targetID)
  local ui = delegates.ui
  if ui and type(ui.WritZoneOf) == "function" then
    return ui.WritZoneOf(targetID)
  end
  return API.WritTurnInZone(targetID)
end

local function isTeachingItem(e, id)
  if id == e.pid or id == e.teachingItemID then return true end
  local tids = type(e.teachingItemIDs) == "table" and e.teachingItemIDs or nil
  if tids then
    for i = 1, #tids do
      if tids[i] == id then return true end
    end
  end
  return false
end

function API.WritNeedOf(id, title)
  local ui = delegates.ui
  if ui and type(ui.WritNeedOf) == "function" then
    return ui.WritNeedOf(id, title)
  end
  local DS = getDS()
  if not DS or type(id) ~= "number" then return nil end
  if DS.WritByTarget(id) then
    return id, false
  end
  local byItem = DS.WritByItem(id)
  if byItem then
    return byItem.targetItemID, true
  end
  local idx = API.PatternIndex()
  local e = type(idx) == "table" and idx[id] or nil
  if type(e) == "table" and e.pid then
    if not isTeachingItem(e, id) then
      local pname = API.ItemName(e.pid)
      if not (title == nil or title == "" or title == pname) then
        return nil
      end
    end
    local prod = e.itemID or e.outputItemID or (e.r and e.r[2])
    if type(prod) == "number" and prod ~= id and DS.WritByTarget(prod) then
      return prod, false
    end
  end
  return nil
end

function API.PlunderByItem(id)
  local DS = getDS()
  return DS and DS.Plunder(id) or nil
end

local function normalizeFaction(raw)
  if raw == "A" or raw == "Alliance" then return "A" end
  if raw == "H" or raw == "Horde" then return "H" end
  if raw == "N" or raw == "Neutral" then return "N" end
  return nil
end

local function resolvePlayerFaction(ctx)
  if type(ctx) == "table" then
    if ctx.faction ~= nil then
      return normalizeFaction(ctx.faction)
    end
    if ctx.strict == true then
      return nil
    end
  end
  if type(_G.UnitFactionGroup) == "function" then
    local ok, f = pcall(_G.UnitFactionGroup, "player")
    if ok then return normalizeFaction(f) end
  end
  return nil
end

function API.VendorPrice(itemID, ctx)
  local pricing = delegates.pricing
  if pricing and type(pricing.VendorPrice) == "function" then
    return pricing.VendorPrice(itemID, ctx)
  end
  local DS = getDS()
  local Cond = getCond()
  if not DS or not Cond or type(itemID) ~= "number" then return nil end
  local vo = DS.VendorOffers(itemID)
  if type(vo) ~= "table" or type(vo.offers) ~= "table" then return nil end

  local playerFaction = resolvePlayerFaction(ctx)
  local bestPure, bestMixed
  for i = 1, #vo.offers do
    local offer = vo.offers[i]
    if type(offer) == "table" and offer.maxStock ~= 0 and type(offer.priceCopper) == "number" and offer.priceCopper >= 0 then
      local npc = type(offer.npcID) == "number" and DS.Npc(offer.npcID) or nil
      local npcFaction = npc and normalizeFaction(npc.faction) or nil
      local npcOk = true
      if playerFaction and (npcFaction == "A" or npcFaction == "H") and playerFaction ~= npcFaction then
        npcOk = false
      end
      if npcOk and npc and type(npc.accessConditions) == "table" and #npc.accessConditions > 0 then
        npcOk = Cond.IsMet(npc.accessConditions, ctx)
      end
      local offerOk = true
      if npcOk and type(offer.conditions) == "table" and #offer.conditions > 0 then
        offerOk = Cond.IsMet(offer.conditions, ctx)
      end
      if npcOk and offerOk then
        local bundle = (type(offer.bundleSize) == "number" and offer.bundleSize >= 1) and offer.bundleSize or 1
        local unit = offer.priceCopper / bundle
        local isPure = (type(offer.currencies) ~= "table" or #offer.currencies == 0)
          and (type(offer.costItems) ~= "table" or #offer.costItems == 0)
        local cand = {
          priceCopper = offer.priceCopper,
          unitCopper = unit,
          bundleSize = bundle,
          npcID = offer.npcID,
          optionIndex = offer.optionIndex,
          currencies = offer.currencies,
          costItems = offer.costItems,
          maxStock = offer.maxStock,
          priceVerified = offer.priceVerified == true,
          offer = offer,
        }
        if isPure then
          if not bestPure or cand.unitCopper < bestPure.unitCopper then
            bestPure = cand
          end
        else
          if not bestMixed or cand.unitCopper < bestMixed.unitCopper then
            bestMixed = cand
          end
        end
      end
    end
  end
  return bestPure or bestMixed
end

function API.AHPriceOf(itemID, ctx)
  if type(itemID) ~= "number" then return nil end
  if type(ctx) == "table" and type(ctx.ahPrices) == "table" and type(ctx.ahPrices[itemID]) == "number" then
    return ctx.ahPrices[itemID]
  end
  local pricing = delegates.pricing
  if pricing and type(pricing.AHPriceOf) == "function" then
    return pricing.AHPriceOf(itemID, ctx)
  end
  return nil
end

function API.EffectiveCost(itemID, qtyOrCtx, ctxOrNil)
  if type(itemID) ~= "number" then return nil end
  local qty, ctx
  if type(qtyOrCtx) == "table" and ctxOrNil == nil then
    qty, ctx = 1, qtyOrCtx
  else
    qty = tonumber(qtyOrCtx) or 1
    ctx = ctxOrNil
  end
  if qty <= 0 then return 0 end

  local pricing = delegates.pricing
  if pricing and type(pricing.EffectiveCost) == "function" then
    return pricing.EffectiveCost(itemID, qty, ctx)
  end

  local vp = API.VendorPrice(itemID, ctx)
  local vendorUnit = nil
  if vp then
    local pure = (type(vp.currencies) ~= "table" or #vp.currencies == 0)
      and (type(vp.costItems) ~= "table" or #vp.costItems == 0)
    if pure and type(vp.unitCopper) == "number" then
      vendorUnit = vp.unitCopper
    end
  end
  local ahUnit = API.AHPriceOf(itemID, ctx)
  local bestUnit
  if type(vendorUnit) == "number" and type(ahUnit) == "number" then
    bestUnit = math.min(vendorUnit, ahUnit)
  elseif type(vendorUnit) == "number" then
    bestUnit = vendorUnit
  elseif type(ahUnit) == "number" then
    bestUnit = ahUnit
  end
  if not bestUnit then return nil end
  return bestUnit * qty
end

function API.MatPriceOf(itemID, ctx)
  local pricing = delegates.pricing
  if pricing and type(pricing.MatPriceOf) == "function" then
    return pricing.MatPriceOf(itemID, ctx)
  end
  return API.EffectiveCost(itemID, 1, ctx)
end

function API.NPCSellPriceOf(itemID)
  local pricing = delegates.pricing
  if pricing and type(pricing.NPCSellPriceOf) == "function" then
    return pricing.NPCSellPriceOf(itemID)
  end
  local DS = getDS()
  local item = DS and DS.Item(itemID) or nil
  return item and item.sellPriceCopper or nil
end

function API.InvalidatePricing()
  local pricing = delegates.pricing
  if pricing and type(pricing.Invalidate) == "function" then
    pcall(pricing.Invalidate)
  end
  local solver = delegates.solver
  if solver and type(solver.Invalidate) == "function" then
    pcall(solver.Invalidate)
  end
end

function API.ActiveCooldownAlerts()
  local cdwatch = delegates.cdwatch
  if cdwatch and type(cdwatch.TodoList) == "function" then
    local ok, list = pcall(cdwatch.TodoList)
    if ok and type(list) == "table" then return list end
  end
  return {}
end

function API.RefreshLearningObservations(...)
  local exec = delegates.execution
  if exec and type(exec.RefreshLearningObservations) == "function" then
    return exec.RefreshLearningObservations(...)
  end
  local eco = ns.ProfEconomy or (type(gns) == "table" and gns.ProfEconomy) or nil
  if eco and type(eco.RefreshLearningObservations) == "function" then
    return eco.RefreshLearningObservations(...)
  end
  local learning = delegates.learning
  if learning and type(learning.Refresh) == "function" then
    return learning.Refresh(...)
  end
  return nil
end

function API.ItemName(itemID)
  if type(itemID) ~= "number" then return "", false end
  local memo = itemNameMemo[itemID]
  if memo then return memo[1], memo[2] end

  local DS = getDS()
  local name = DS and DS.RawText("item", itemID) or nil
  if type(name) == "string" and name ~= "" then
    itemNameMemo[itemID] = { name, true }
    return name, true
  end
  if type(_G.C_Item) == "table" and type(_G.C_Item.GetItemNameByID) == "function" then
    local ok, n = pcall(_G.C_Item.GetItemNameByID, itemID)
    if ok and type(n) == "string" and n ~= "" then
      itemNameMemo[itemID] = { n, true }
      return n, true
    end
  end
  if type(_G.GetItemInfo) == "function" then
    local ok, n = pcall(_G.GetItemInfo, itemID)
    if ok and type(n) == "string" and n ~= "" then
      itemNameMemo[itemID] = { n, true }
      return n, true
    end
  end
  return "#" .. tostring(itemID), false
end

function API.ResetItemNameMemo(_hard)
  for k in pairs(itemNameMemo) do
    itemNameMemo[k] = nil
  end
  local ui = delegates.ui
  if ui and type(ui.ResetItemNameMemo) == "function" then
    pcall(ui.ResetItemNameMemo, _hard)
  end
end

function API.ProfKnows(itemID)
  local ui = delegates.ui
  if ui and type(ui.ProfKnows) == "function" then
    return ui.ProfKnows(itemID) == true
  end
  local DS = getDS()
  local Cond = getCond()
  local spells = DS and DS.CraftIndex(itemID) or nil
  if type(spells) == "table" and Cond then
    for i = 1, #spells do
      if Cond.Evaluate({ kind = "ability", spellID = spells[i] }) == true then
        return true
      end
    end
  end
  return false
end

function API.ProductCraftTitle(itemID)
  local ui = delegates.ui
  if ui and type(ui.ProductCraftTitle) == "function" then
    return ui.ProductCraftTitle(itemID)
  end
  local slug = API.CraftProfessionOf(itemID)
  if not slug then return nil end
  local DS = getDS()
  return DS and DS.ProfessionName(slug) or slug
end

function API.PatternTipLines(id, title)
  local ui = delegates.ui
  if ui and type(ui.PatternTipLines) == "function" then
    return ui.PatternTipLines(id, title)
  end
  return nil
end

function API.ProductTipLines(id, title)
  local ui = delegates.ui
  if ui and type(ui.ProductTipLines) == "function" then
    return ui.ProductTipLines(id, title)
  end
  return nil
end

function API.CrateTipLines(id)
  local ui = delegates.ui
  if ui and type(ui.CrateTipLines) == "function" then
    return ui.CrateTipLines(id)
  end
  return nil
end

function API.WritTipLines(id)
  local ui = delegates.ui
  if ui and type(ui.WritTipLines) == "function" then
    return ui.WritTipLines(id)
  end
  return nil
end

function API.CrateNeedLines(id, title)
  local ui = delegates.ui
  if ui and type(ui.CrateNeedLines) == "function" then
    return ui.CrateNeedLines(id, title)
  end
  return nil
end

function API.WritNeedLines(id, title)
  local ui = delegates.ui
  if ui and type(ui.WritNeedLines) == "function" then
    return ui.WritNeedLines(id, title)
  end
  return nil
end

function API.Build(page)
  local ui = delegates.ui
  if ui and type(ui.Build) == "function" then return ui.Build(page) end
end

function API.Open()
  local ui = delegates.ui
  if ui and type(ui.Open) == "function" then return ui.Open() end
end

function API.Refresh()
  local ui = delegates.ui
  if ui and type(ui.Refresh) == "function" then return ui.Refresh() end
end

function API.Show(slug)
  local ui = delegates.ui
  if ui and type(ui.Show) == "function" then return ui.Show(slug) end
end

function API.OnItemData(itemID)
  local ui = delegates.ui
  if ui and type(ui.OnItemData) == "function" then return ui.OnItemData(itemID) end
end

function API.Fit(s, fs, maxw)
  local ui = delegates.ui
  if ui and type(ui.Fit) == "function" then return ui.Fit(s, fs, maxw) end
  return s
end

function API.HoverRow()
  local ui = delegates.ui
  if ui and type(ui.HoverRow) == "function" then return ui.HoverRow() end
  return ui and ui.hoverRow or nil
end

local function EnsureProfAPI()
  return API
end

ns.ProfAPI = API
ns.EnsureProfAPI = EnsureProfAPI
if type(gns) == "table" and gns ~= ns then
  gns.ProfAPI = API
  gns.EnsureProfAPI = EnsureProfAPI
end
