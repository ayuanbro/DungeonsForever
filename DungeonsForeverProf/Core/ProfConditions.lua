local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end

local gns = _G.DF_NS

local Cond = {}

local function getDataStore()
  return ns.ProfDataStore or (type(gns) == "table" and gns.ProfDataStore) or nil
end

local function normalizeFaction(raw)
  if raw == "A" or raw == "Alliance" then return "A" end
  if raw == "H" or raw == "Horde" then return "H" end
  if raw == "N" or raw == "Neutral" then return "N" end
  return nil
end

local function isCtxStrict(ctx)
  return type(ctx) == "table" and ctx.strict == true
end

local function getSkillLineSlug(sid)
  if type(sid) ~= "number" then return nil end
  local DS = getDataStore()
  if DS and type(DS.SkillLineToSlug) == "function" then
    local slug = DS.SkillLineToSlug(sid)
    if slug then return slug end
  end
  local cfg = ns.ProfessionsConfig or (type(gns) == "table" and gns.ProfessionsConfig)
  if type(cfg) == "table" and type(cfg.SKILL_LINE_TO_SLUG) == "table" then
    return cfg.SKILL_LINE_TO_SLUG[sid]
  end
  return nil
end

local function evalSkill(c, ctx)
  local minSkill = tonumber(c.min)
  if not minSkill then return nil end
  if type(c.profession) ~= "string" and type(c.skillLineID) ~= "number" then
    return nil
  end

  local val
  local hadMatch = false
  local sawSkillLineMatch = false
  if type(ctx) == "table" then
    local allowSlugFallback = c.skillLineID == nil or type(ctx.skillLines) ~= "table"
    if type(c.skillLineID) == "number" and type(ctx.skillLines) == "table" and ctx.skillLines[c.skillLineID] ~= nil then
      val = ctx.skillLines[c.skillLineID]
    elseif allowSlugFallback and type(c.profession) == "string" and type(ctx.skills) == "table" and ctx.skills[c.profession] ~= nil then
      val = ctx.skills[c.profession]
    elseif allowSlugFallback and type(c.profession) == "string" and type(ctx.professions) == "table" and ctx.professions[c.profession] ~= nil then
      val = ctx.professions[c.profession]
    elseif val == nil and c.skillLineID == nil and type(ctx.skillLines) == "table" and type(c.profession) == "string" then
      local best
      for sid, entry in pairs(ctx.skillLines) do
        if getSkillLineSlug(sid) == c.profession then
          sawSkillLineMatch = true
          local r = type(entry) == "table" and (entry.cur or entry.skill) or entry
          local num = tonumber(r)
          if num ~= nil and (best == nil or num > best) then
            best = num
          end
        end
      end
      val = best
    end
    hadMatch = val ~= nil
    if type(val) == "table" then
      val = val.cur or val.skill
    end
    if val ~= nil then
      local num = tonumber(val)
      if num == nil then return nil end
      return num >= minSkill
    end
    if sawSkillLineMatch or hadMatch then
      return nil
    end
    if ctx.skillsComplete == true and (type(ctx.skills) == "table" or type(ctx.skillLines) == "table" or type(ctx.professions) == "table") then
      return false
    end
    if isCtxStrict(ctx) or ctx.skills ~= nil or ctx.skillLines ~= nil or ctx.professions ~= nil then
      return nil
    end
  end

  if type(_G.GetProfessions) == "function" and type(_G.GetProfessionInfo) == "function" then
    local ok, a, b, cSlot, d, e, f = pcall(_G.GetProfessions)
    if ok then
      local slots = { a, b, cSlot, d, e, f }
      local exactVal, bestSlugVal
      for i = 1, 6 do
        local idx = slots[i]
        if idx then
          local oki, _, _, cur, _, _, _, sid = pcall(_G.GetProfessionInfo, idx)
          if oki then
            local rank = tonumber(cur) or 0
            if type(c.skillLineID) == "number" and sid == c.skillLineID then
              if exactVal == nil or rank > exactVal then
                exactVal = rank
              end
            end
            if type(c.profession) == "string" and getSkillLineSlug(sid) == c.profession then
              if bestSlugVal == nil or rank > bestSlugVal then
                bestSlugVal = rank
              end
            end
          end
        end
      end
      if type(c.skillLineID) == "number" then
        if exactVal ~= nil then
          return exactVal >= minSkill
        end
        return false
      end
      if bestSlugVal ~= nil then
        return bestSlugVal >= minSkill
      end
      return false
    end
  end
  return nil
end

local function evalLevel(c, ctx)
  local minLvl = tonumber(c.min)
  if not minLvl then return nil end

  local lvl
  if type(ctx) == "table" then
    if ctx.level ~= nil then
      lvl = tonumber(ctx.level)
      if lvl == nil then return nil end
      return lvl >= minLvl
    end
    if isCtxStrict(ctx) then return nil end
  end

  if type(_G.UnitLevel) == "function" then
    local ok, v = pcall(_G.UnitLevel, "player")
    if ok and type(v) == "number" and v > 0 then
      return v >= minLvl
    end
  end
  return nil
end

local function evalReputation(c, ctx)
  local fid = c.factionID
  local minStanding = tonumber(c.minStanding)
  if type(fid) ~= "number" or not minStanding then return nil end

  local standing
  if type(ctx) == "table" and type(ctx.reputations) == "table" then
    local entry = ctx.reputations[fid]
    if type(entry) == "table" then
      standing = entry.reaction or entry.standingID or entry.rank
    else
      standing = entry
    end
    if type(standing) ~= "number" then return nil end
    return standing >= minStanding
  end
  if isCtxStrict(ctx) then return nil end

  if type(_G.C_Reputation) == "table" and type(_G.C_Reputation.GetFactionDataByID) == "function" then
    local ok, data = pcall(_G.C_Reputation.GetFactionDataByID, fid)
    if ok and type(data) == "table" and type(data.reaction) == "number" then
      return data.reaction >= minStanding
    end
  end
  if type(_G.GetFactionInfoByID) == "function" then
    local ok, _, _, rank = pcall(_G.GetFactionInfoByID, fid)
    if ok and type(rank) == "number" then
      return rank >= minStanding
    end
  end
  return nil
end

local function evalAbility(c, ctx)
  local sid = c.spellID
  if type(sid) ~= "number" then return nil end

  if type(ctx) == "table" and type(ctx.abilities) == "table" then
    local v = ctx.abilities[sid]
    if type(v) == "boolean" then return v end
    return nil
  end
  if isCtxStrict(ctx) then return nil end

  local observedFalse = false
  local apis = {
    { _G.C_SpellBook, "IsSpellKnown" },
    { _G, "IsSpellKnown" },
    { _G, "IsPlayerSpell" },
    { _G.C_Spell, "IsSpellKnown" },
  }
  for i = 1, #apis do
    local parent, key = apis[i][1], apis[i][2]
    local fn = type(parent) == "table" and parent[key]
    if type(fn) == "function" then
      local ok, v = pcall(fn, sid)
      if ok and v == true then return true end
      if ok and v == false then observedFalse = true end
    end
  end
  if observedFalse then return false end
  return nil
end

local function questCompleted(qid, ctx)
  if type(qid) ~= "number" or qid <= 0 then return nil end
  if type(ctx) == "table" then
    local qt = ctx.quests or ctx.completedQuests
    if type(qt) == "table" then
      local v = qt[qid]
      if type(v) == "boolean" then return v end
      return nil
    end
    if isCtxStrict(ctx) then return nil end
  end
  if type(_G.C_QuestLog) == "table" and type(_G.C_QuestLog.IsQuestFlaggedCompleted) == "function" then
    local ok, v = pcall(_G.C_QuestLog.IsQuestFlaggedCompleted, qid)
    if ok and type(v) == "boolean" then return v end
  end
  if type(_G.IsQuestFlaggedCompleted) == "function" then
    local ok, v = pcall(_G.IsQuestFlaggedCompleted, qid)
    if ok and type(v) == "boolean" then return v end
  end
  return nil
end

function Cond.EvaluateQuestGroups(groups, ctx)
  if type(groups) ~= "table" or #groups == 0 then return nil end
  local anyUnknown = false
  for i = 1, #groups do
    local grp = groups[i]
    if type(grp) ~= "table" or #grp == 0 then
      anyUnknown = true
    else
      local failed, unknown = false, false
      for j = 1, #grp do
        local done = questCompleted(grp[j], ctx)
        if done == false then
          failed = true
          break
        elseif done ~= true then
          unknown = true
        end
      end
      if not failed and not unknown then
        return true
      end
      if not failed and unknown then
        anyUnknown = true
      end
    end
  end
  if anyUnknown then return nil end
  return false
end

local function evalHasItem(c, ctx)
  local itemID = c.itemID
  local need = tonumber(c.count) or 1
  if type(itemID) ~= "number" then return nil end

  if type(ctx) == "table" then
    local it = ctx.items or ctx.ownedSourceItems
    if type(it) == "table" then
      local cnt = it[itemID]
      if type(cnt) == "number" then return cnt >= need end
      if type(cnt) == "boolean" then
        if cnt == false then return false end
        if need <= 1 then return true end
        return nil
      end
      return nil
    end
    if isCtxStrict(ctx) then return nil end
  end

  local includeBank = (type(ctx) == "table" and ctx.includeBank == true) or false
  local fn = (type(_G.C_Item) == "table" and _G.C_Item.GetItemCount) or _G.GetItemCount
  if type(fn) == "function" then
    local ok, cnt = pcall(fn, itemID, includeBank)
    if ok and type(cnt) == "number" then
      return cnt >= need
    end
  end
  return nil
end

local function evalFaction(c, ctx)
  local target = normalizeFaction(c.side)
  if not target then return nil end
  if target == "N" then return true end

  local raw
  if type(ctx) == "table" then
    if ctx.faction ~= nil then
      raw = ctx.faction
    elseif isCtxStrict(ctx) then
      return nil
    end
  end
  if raw == nil and type(_G.UnitFactionGroup) == "function" then
    local ok, f = pcall(_G.UnitFactionGroup, "player")
    if ok then raw = f end
  end
  local norm = normalizeFaction(raw)
  if not norm then return nil end
  return norm == target
end

local function evalClass(c, ctx)
  local ids = c.classIDs
  if type(ids) ~= "table" or #ids == 0 then return nil end

  local cid
  if type(ctx) == "table" then
    if ctx.classID ~= nil then
      if type(ctx.classID) ~= "number" then return nil end
      cid = ctx.classID
    elseif isCtxStrict(ctx) then
      return nil
    end
  end
  if cid == nil and type(_G.UnitClass) == "function" then
    local ok, _, _, id = pcall(_G.UnitClass, "player")
    if ok then cid = tonumber(id) end
  end
  if cid == nil then return nil end
  for i = 1, #ids do
    if ids[i] == cid then return true end
  end
  return false
end

local function evalRace(c, ctx)
  local ids = c.raceIDs
  if type(ids) ~= "table" or #ids == 0 then return nil end

  local rid
  if type(ctx) == "table" then
    if ctx.raceID ~= nil then
      if type(ctx.raceID) ~= "number" then return nil end
      rid = ctx.raceID
    elseif isCtxStrict(ctx) then
      return nil
    end
  end
  if rid == nil and type(_G.UnitRace) == "function" then
    local ok, _, _, id = pcall(_G.UnitRace, "player")
    if ok then rid = tonumber(id) end
  end
  if rid == nil then return nil end
  for i = 1, #ids do
    if ids[i] == rid then return true end
  end
  return false
end

function Cond.Evaluate(condition, ctx)
  if type(condition) ~= "table" then return nil end
  local kind = condition.kind
  if kind == "skill" then return evalSkill(condition, ctx) end
  if kind == "level" then return evalLevel(condition, ctx) end
  if kind == "reputation" then return evalReputation(condition, ctx) end
  if kind == "ability" then return evalAbility(condition, ctx) end
  if kind == "questGroup" then return Cond.EvaluateQuestGroups(condition.groups, ctx) end
  if kind == "hasItem" then return evalHasItem(condition, ctx) end
  if kind == "faction" then return evalFaction(condition, ctx) end
  if kind == "class" then return evalClass(condition, ctx) end
  if kind == "race" then return evalRace(condition, ctx) end
  if kind == "unknown" then return nil end
  return nil
end

function Cond.EvaluateAll(conditions, ctx)
  if conditions == nil then return true end
  if type(conditions) ~= "table" then return nil end
  if conditions.kind ~= nil then
    return Cond.Evaluate(conditions, ctx)
  end
  if #conditions == 0 then return true end
  local anyNil = false
  for i = 1, #conditions do
    local res = Cond.Evaluate(conditions[i], ctx)
    if res == false then
      return false
    elseif res ~= true then
      anyNil = true
    end
  end
  if anyNil then return nil end
  return true
end

function Cond.IsMet(conditions, ctx)
  return Cond.EvaluateAll(conditions, ctx) == true
end

function Cond.NpcAccessState(npcOrId, ctx)
  local npc = npcOrId
  if type(npcOrId) == "number" then
    local DS = getDataStore()
    npc = DS and DS.Npc and DS.Npc(npcOrId) or nil
  end
  if type(npc) ~= "table" then return nil end
  return Cond.EvaluateAll(npc.accessConditions, ctx)
end

function Cond.IsNpcAccessible(npcOrId, ctx)
  return Cond.NpcAccessState(npcOrId, ctx) == true
end

function Cond.LiveContext()
  local ctx = {}
  if type(_G.UnitLevel) == "function" then
    local ok, lvl = pcall(_G.UnitLevel, "player")
    if ok and type(lvl) == "number" and lvl > 0 then ctx.level = lvl end
  end
  if type(_G.UnitFactionGroup) == "function" then
    local ok, f = pcall(_G.UnitFactionGroup, "player")
    if ok then ctx.faction = normalizeFaction(f) end
  end
  if type(_G.UnitClass) == "function" then
    local ok, _, _, id = pcall(_G.UnitClass, "player")
    if ok and type(id) == "number" then ctx.classID = id end
  end
  if type(_G.UnitRace) == "function" then
    local ok, _, _, id = pcall(_G.UnitRace, "player")
    if ok and type(id) == "number" then ctx.raceID = id end
  end
  if type(_G.GetProfessions) == "function" and type(_G.GetProfessionInfo) == "function" then
    local ok, a, b, cSlot, d, e, f = pcall(_G.GetProfessions)
    if ok then
      local skills, skillLines = {}, {}
      local slots = { a, b, cSlot, d, e, f }
      for i = 1, 6 do
        local idx = slots[i]
        if idx then
          local oki, _, _, cur, _, _, _, sid = pcall(_G.GetProfessionInfo, idx)
          if oki and type(sid) == "number" then
            local val = tonumber(cur) or 0
            skillLines[sid] = val
            local slug = getSkillLineSlug(sid)
            if slug and (not skills[slug] or val > skills[slug]) then
              skills[slug] = val
            end
          end
        end
      end
      ctx.skills = skills
      ctx.skillLines = skillLines
      ctx.skillsComplete = true
    end
  end
  return ctx
end

ns.ProfConditions = Cond
if type(gns) == "table" and gns ~= ns then
  gns.ProfConditions = Cond
end
