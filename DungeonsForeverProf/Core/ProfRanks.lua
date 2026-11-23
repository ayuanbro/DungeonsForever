local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end
local gns = _G.DF_NS

local R = {}
ns.ProfRanks = R
if type(gns) == "table" and gns ~= ns then
    gns.ProfRanks = R
end

local function getDS()
    return ns.ProfDataStore or (type(gns) == "table" and gns.ProfDataStore) or nil
end

local function getCond()
    return ns.ProfConditions or (type(gns) == "table" and gns.ProfConditions) or nil
end

local function getAPI()
    return ns.ProfAPI or (type(gns) == "table" and gns.ProfAPI) or nil
end

local function getSolverCfg()
    return ns.SolverConfig or (type(gns) == "table" and gns.SolverConfig) or nil
end

local function getLocale()
    local DS = getDS()
    if DS and type(DS.GetLocale) == "function" then return DS.GetLocale() end
    if type(_G.DF_Locale) == "function" then
        local ok, loc = pcall(_G.DF_Locale)
        if ok and type(loc) == "string" and loc ~= "" then return loc end
    end
    if type(_G.GetLocale) == "function" then
        local ok, loc = pcall(_G.GetLocale)
        if ok and type(loc) == "string" and loc ~= "" then return loc end
    end
    return "enUS"
end

local function tr(zh, tw, en)
    local loc = getLocale()
    if loc == "zhCN" then return zh end
    if loc == "zhTW" then return tw end
    return en
end

local function number(value, minimum)
    value = tonumber(value)
    if value and value == value and value < math.huge and value >= (minimum or 0) then return value end
    return nil
end

local function safe(fn, ...)
    if type(fn) ~= "function" then return false end
    return pcall(fn, ...)
end

local function normalizeFaction(raw)
    if raw == "A" or raw == "Alliance" then return "A" end
    if raw == "H" or raw == "Horde" then return "H" end
    if raw == "N" or raw == "Neutral" or raw == "B" or raw == "Both" then return "N" end
    return nil
end

local RANK_LABELS = {
    apprentice = { zhCN = "初级", zhTW = "初級", enUS = "Apprentice" },
    journeyman = { zhCN = "中级", zhTW = "中級", enUS = "Journeyman" },
    expert = { zhCN = "高级", zhTW = "高級", enUS = "Expert" },
    artisan = { zhCN = "大师级", zhTW = "大師級", enUS = "Artisan" },
}

local function rankLabel(rankKey)
    local row = type(rankKey) == "string" and RANK_LABELS[rankKey] or nil
    if not row then return nil end
    return tr(row.zhCN, row.zhTW, row.enUS)
end

function R.Status(slug, opts)
    opts = opts or {}
    local state = { known = false }
    local API = getAPI()
    local loginOK, loggedIn = safe(_G.IsLoggedIn)
    if not loginOK or loggedIn ~= false then
        local ok, a, b, c, d, e, f = safe(_G.GetProfessions)
        if ok and type(_G.GetProfessionInfo) == "function" then
            local slots, valid, found = { a, b, c, d, e, f }, true, false
            local bestCur, bestMax
            for i = 1, 6 do
                if slots[i] then
                    local success, name, _, cur, cap, _, _, skillID = safe(_G.GetProfessionInfo, slots[i])
                    local slotSlug = success and API and type(API.SkillLineToSlug) == "function" and API.SkillLineToSlug(skillID) or nil
                    if not success or not name or not slotSlug then valid = false end
                    if success and slotSlug == slug then
                        found = true
                        local cVal = number(cur)
                        local mVal = number(cap, 1)
                        if cVal ~= nil and (bestCur == nil or cVal > bestCur) then bestCur = cVal end
                        if mVal ~= nil and (bestMax == nil or mVal > bestMax) then bestMax = mVal end
                    end
                end
            end
            if found then
                state.skill = bestCur
                state.maxSkill = bestMax
                state.learned = true
                state.known = state.skill ~= nil and state.maxSkill ~= nil
            elseif valid then
                state.known = true
                state.learned = false
                state.skill = 0
                state.maxSkill = 0
            end
        elseif API and type(API.PlayerProfSet) == "function" then
            local set = API.PlayerProfSet()
            if type(set) == "table" and not set.__unknown then
                if set[slug] ~= nil then
                    state.learned = true
                    state.skill = number(API.ProfLevel and API.ProfLevel(slug) or set[slug])
                    if type(API.ProfLearned) == "function" then
                        local learned = API.ProfLearned()
                        state.maxSkill = type(learned[slug]) == "table" and number(learned[slug].max, 1) or nil
                    end
                    state.known = state.skill ~= nil and state.maxSkill ~= nil
                else
                    state.known = true
                    state.learned = false
                    state.skill = 0
                    state.maxSkill = 0
                end
            end
        end
    end
    local okLvl, level = safe(_G.UnitLevel, "player")
    if okLvl then state.level = number(level, 1) end
    local okFac, faction = safe(_G.UnitFactionGroup, "player")
    if okFac then state.faction = normalizeFaction(faction) end
    if opts.skill ~= nil then state.skill = number(opts.skill) end
    if opts.maxSkill ~= nil then state.maxSkill = number(opts.maxSkill) end
    if opts.skill ~= nil or opts.maxSkill ~= nil then
        state.known = state.skill ~= nil and state.maxSkill ~= nil
        state.learned = state.maxSkill and state.maxSkill > 0 or false
    end
    if opts.level ~= nil then state.level = number(opts.level, 1) end
    if opts.faction ~= nil then
        state.faction = normalizeFaction(opts.faction) or opts.faction
    end
    return state
end

local function buildCondContext(slug, state, opts)
    local Cond = getCond()
    local ctx = (Cond and type(Cond.LiveContext) == "function" and Cond.LiveContext()) or {}
    if state.level ~= nil then ctx.level = state.level end
    if state.faction ~= nil then ctx.faction = state.faction end
    if state.known and state.skill ~= nil then
        ctx.skills = ctx.skills or {}
        ctx.skills[slug] = state.skill
    end
    if type(opts) == "table" then
        if type(opts.quests) == "table" or type(opts.completedQuests) == "table" then
            ctx.quests = opts.quests or opts.completedQuests
        end
        if type(opts.items) == "table" or type(opts.ownedSourceItems) == "table" then
            ctx.items = opts.items or opts.ownedSourceItems
        end
        if type(opts.reputations) == "table" then ctx.reputations = opts.reputations end
        if type(opts.abilities) == "table" then ctx.abilities = opts.abilities end
        if opts.classID ~= nil then ctx.classID = opts.classID end
        if opts.raceID ~= nil then ctx.raceID = opts.raceID end
        if opts.strict ~= nil then ctx.strict = opts.strict == true end
    end
    return ctx
end

local function copyConditions(list)
    if type(list) ~= "table" then return nil end
    local out = {}
    for i = 1, #list do out[i] = list[i] end
    return out
end

local function resolveSources(raw, state, condCtx)
    local DS = getDS()
    local Cond = getCond()
    local out = {}
    local candidates = {}
    local hadCandidates = false
    if type(raw.trainers) == "table" and #raw.trainers > 0 then
        hadCandidates = true
        for i = 1, #raw.trainers do
            candidates[#candidates + 1] = raw.trainers[i]
        end
    elseif raw.method == "book" and type(raw.bookItemID) == "number" and DS and type(DS.VendorOffers) == "function" then
        local vo = DS.VendorOffers(raw.bookItemID)
        if type(vo) == "table" and type(vo.offers) == "table" and #vo.offers > 0 then
            for i = 1, #vo.offers do
                local offer = vo.offers[i]
                if type(offer) == "table" then
                    hadCandidates = true
                    if offer.maxStock ~= 0 then
                        candidates[#candidates + 1] = { npcID = offer.npcID, conditions = offer.conditions }
                    end
                end
            end
        end
    end
    local kind = (raw.method == "book" and "vendor") or raw.method or "trainer"
    for i = 1, #candidates do
        local t = candidates[i]
        local npcID = type(t) == "table" and t.npcID or nil
        if type(npcID) == "number" and npcID > 0 then
            local npc = DS and type(DS.Npc) == "function" and DS.Npc(npcID) or nil
            local npcFaction = npc and normalizeFaction(npc.faction) or nil
            local factionOK = not state.faction or not npcFaction or npcFaction == "N" or npcFaction == state.faction
            local edgeState = true
            if Cond and type(Cond.EvaluateAll) == "function" and type(t.conditions) == "table" and #t.conditions > 0 then
                edgeState = Cond.EvaluateAll(t.conditions, condCtx)
            end
            if factionOK and edgeState ~= false then
                local spawn = type(npc) == "table" and type(npc.spawns) == "table" and npc.spawns[1] or nil
                local areaID = type(spawn) == "table" and spawn.areaID or nil
                local zone = areaID and DS and type(DS.Zone) == "function" and DS.Zone(areaID) or nil
                local uiMapID = (type(spawn) == "table" and spawn.uiMapID) or (type(zone) == "table" and zone.uiMapID) or nil
                out[#out + 1] = {
                    kind = kind,
                    npcID = npcID,
                    name = DS and type(DS.RawText) == "function" and DS.RawText("npc", npcID) or nil,
                    faction = npcFaction,
                    areaID = areaID,
                    map = uiMapID,
                    uiMapID = uiMapID,
                    zone = areaID and DS and type(DS.RawText) == "function" and DS.RawText("zone", areaID) or nil,
                    x = type(spawn) == "table" and spawn.x or nil,
                    y = type(spawn) == "table" and spawn.y or nil,
                    itemID = raw.bookItemID,
                    itemName = raw.bookItemID and DS and type(DS.RawText) == "function" and DS.RawText("item", raw.bookItemID) or nil,
                    questID = raw.questID,
                    questName = raw.questID and DS and type(DS.RawText) == "function" and DS.RawText("quest", raw.questID) or nil,
                    conditions = copyConditions(t.conditions),
                    edgeState = edgeState,
                }
            end
        end
    end
    return out, hadCandidates
end

function R.RouteSteps(slug, target, opts)
    local DS = getDS()
    local Cond = getCond()
    local rawRanks = DS and type(DS.Ranks) == "function" and DS.Ranks(slug) or nil
    if type(rawRanks) ~= "table" or #rawRanks == 0 then return {} end

    local sorted = {}
    for i = 1, #rawRanks do
        if type(rawRanks[i]) == "table" then
            sorted[#sorted + 1] = rawRanks[i]
        end
    end
    table.sort(sorted, function(a, b)
        return (a.rankIndex or 0) < (b.rankIndex or 0)
    end)

    local state = R.Status(slug, opts)
    local condCtx = buildCondContext(slug, state, opts)
    local solverCfg = getSolverCfg()
    target = number(target) or (type(solverCfg) == "table" and solverCfg.DEFAULT_TARGET) or 300

    local out = {}
    local priorCap = 0
    for i = 1, #sorted do
        local raw = sorted[i]
        local cap = number(raw.skillCap, 1)
        local reqSkill = number(raw.reqSkill) or 0
        local reqLevel = number(raw.reqLevel) or 0
        local reminder = number(raw.routeReminderSkill) or reqSkill or priorCap
        if reminder <= target then
            local sources, hadCandidates = resolveSources(raw, state, condCtx)
            local condState = true
            if Cond and type(Cond.EvaluateAll) == "function" then
                condState = Cond.EvaluateAll(raw.conditions, condCtx)
            end
            local factsKnown = (type(cap) == "number") and (type(reqSkill) == "number") and (type(reqLevel) == "number") and (condState ~= nil)
            local qualificationAllowed = condState ~= false
            local complete = state.known and type(cap) == "number" and state.maxSkill >= cap or false

            if #sources > 0 and not complete then
                local anyAvailable, anyUnknown = false, false
                for j = 1, #sources do
                    local src = sources[j]
                    local npcState = true
                    if src.npcID and Cond and type(Cond.NpcAccessState) == "function" then
                        npcState = Cond.NpcAccessState(src.npcID, condCtx)
                    end
                    local edgeState = src.edgeState
                    if npcState == false or edgeState == false then
                        src.accessible = false
                    elseif npcState == true and edgeState == true then
                        src.accessible = true
                        anyAvailable = true
                    else
                        anyUnknown = true
                    end
                    src.edgeState = nil
                end
                if not anyAvailable then
                    qualificationAllowed = false
                    if anyUnknown then factsKnown = false end
                end
            else
                if not complete and hadCandidates then
                    qualificationAllowed = false
                end
                for j = 1, #sources do
                    sources[j].edgeState = nil
                end
            end

            local available = not complete and factsKnown and qualificationAllowed and state.known
                and type(state.skill) == "number" and state.skill >= reqSkill
                and (reqLevel == 0 or (type(state.level) == "number" and state.level >= reqLevel)) or false
            local due = not complete and type(state.skill) == "number" and state.skill >= reminder or false

            local status
            if complete then
                status = "complete"
            elseif available then
                status = "available"
            elseif not state.known then
                status = "unknown"
            elseif type(reqLevel) == "number" and type(state.level) == "number" and state.level < reqLevel then
                status = "level_locked"
            elseif type(reqSkill) == "number" and type(state.skill) == "number" and state.skill < reqSkill then
                status = "skill_locked"
            elseif not qualificationAllowed and factsKnown then
                status = "requirements_locked"
            elseif not factsKnown or (reqLevel > 0 and state.level == nil) then
                status = "unknown"
            elseif not qualificationAllowed then
                status = "requirements_locked"
            else
                status = "available"
            end

            out[#out + 1] = {
                id = "rank:" .. slug .. ":" .. tostring(raw.rankIndex or i),
                rank = raw.rankIndex or i,
                rankIndex = raw.rankIndex or i,
                rankKey = raw.rankKey,
                cap = cap,
                skillCap = cap,
                skillRequired = reqSkill,
                reqSkill = reqSkill,
                levelRequired = reqLevel,
                reqLevel = reqLevel,
                method = raw.method or "unknown",
                bookItemID = raw.bookItemID,
                questID = raw.questID,
                profession = slug,
                professionName = DS and type(DS.ProfessionName) == "function" and DS.ProfessionName(slug) or slug,
                name = rankLabel(raw.rankKey) or tostring(raw.rankIndex or i),
                reminderSkill = reminder,
                state = state,
                sources = sources,
                complete = complete,
                available = available,
                due = due,
                status = status,
            }
        end
        if type(cap) == "number" then priorCap = cap end
    end
    return out
end

function R.NextStep(slug, target, opts)
    local steps = R.RouteSteps(slug, target, opts)
    local state = steps[1] and steps[1].state
    local solverCfg = getSolverCfg()
    local target0 = number(target) or (type(solverCfg) == "table" and solverCfg.DEFAULT_TARGET) or 300
    if state and state.known and type(state.maxSkill) == "number" and target0 <= state.maxSkill then
        return nil
    end
    for _, step in ipairs(steps) do
        if not step.complete then return step end
    end
    return nil
end

function R.Title(step)
    return string.format(tr("%s · %s（上限 %s）", "%s · %s（上限 %s）", "%s · %s (cap %s)"),
        tostring(step.professionName or step.profession or ""),
        tostring(step.name or step.rank or ""),
        tostring(step.cap or "?"))
end

function R.Lines(step, maxSources)
    local DS = getDS()
    local out = {}
    if step.complete then
        out[#out + 1] = tr("已学习：当前技能上限已达到此阶。", "已學習：目前技能上限已達到此階。", "Learned: the current skill cap confirms this rank.")
    elseif step.status == "unknown" then
        out[#out + 1] = tr("晋级资料或角色资格尚未确认；请在游戏中核对。", "晉級資料或角色資格尚未確認；請在遊戲中核對。", "Rank facts or character eligibility are unknown; check in game.")
    elseif step.available then
        out[#out + 1] = tr("已达到参考条件；提升技能上限后继续路线。", "已達到參考條件；提升技能上限後繼續路線。", "Reference requirements met; raise the skill cap to continue.")
    else
        out[#out + 1] = tr("尚未达到学习条件。", "尚未達到學習條件。", "Learning requirements are not yet met.")
    end
    if type(step.levelRequired) == "number" and step.levelRequired > 0 then
        out[#out + 1] = string.format(tr("需要技能 %d · 角色等级 %d", "需要技能 %d · 角色等級 %d", "Requires skill %d · character level %d"),
            step.skillRequired or 0, step.levelRequired)
    elseif step.skillRequired ~= nil then
        out[#out + 1] = string.format(tr("需要技能 %d", "需要技能 %d", "Requires skill %d"), step.skillRequired or 0)
    end
    if type(step.reminderSkill) == "number" and step.reminderSkill < (step.skillRequired or 0) then
        out[#out + 1] = string.format(tr("%d 点开始准备；达到 %d 点后办理任务晋级。", "%d 點開始準備；達到 %d 點後辦理任務晉級。", "Prepare at skill %d; complete the rank quest at skill %d."),
            step.reminderSkill, step.skillRequired or 0)
    end
    if step.method == "trainer" then
        out[#out + 1] = tr("向对应阶级的专业训练师学习。", "向對應階級的專業訓練師學習。", "Learn from a trainer for this rank.")
    elseif step.method == "book" then
        out[#out + 1] = tr("购买并阅读教材。", "購買並閱讀教材。", "Buy and read the skill book.")
    elseif step.method == "quest" then
        out[#out + 1] = tr("完成专业晋级任务。", "完成專業晉級任務。", "Complete the profession rank quest.")
    end
    if type(step.note) == "string" and step.note ~= "" then out[#out + 1] = step.note end
    if step.bookItemID then
        local bookName = DS and type(DS.ItemName) == "function" and DS.ItemName(step.bookItemID) or ("#" .. tostring(step.bookItemID))
        out[#out + 1] = tr("教材：", "教材：", "Book: ") .. bookName
    end
    for index, source in ipairs(step.sources or {}) do
        if maxSources and index > maxSources then break end
        local prefix = source.faction == "A" and tr("联盟 · ", "聯盟 · ", "Alliance · ")
            or (source.faction == "H" and tr("部落 · ", "部落 · ", "Horde · ") or "")
        local npcText = source.name or (source.npcID and DS and type(DS.NpcName) == "function" and DS.NpcName(source.npcID)) or (source.npcID and ("NPC " .. source.npcID)) or ""
        local text = prefix .. npcText
        local zoneText = source.zone or (source.areaID and DS and type(DS.ZoneName) == "function" and DS.ZoneName(source.areaID))
        if type(zoneText) == "string" and zoneText ~= "" then
            text = text .. " · " .. zoneText
        end
        if number(source.x) and number(source.y) then
            text = text .. string.format(" (%.1f, %.1f)", source.x, source.y)
        end
        if text ~= "" then out[#out + 1] = text end
        if source.itemName or source.itemID then
            local iName = source.itemName or (DS and type(DS.ItemName) == "function" and DS.ItemName(source.itemID)) or ("#" .. tostring(source.itemID))
            out[#out + 1] = tr("教材：", "教材：", "Book: ") .. iName
        end
        if source.questName or source.questID then
            local qName = source.questName or (DS and type(DS.QuestName) == "function" and DS.QuestName(source.questID)) or ("#" .. tostring(source.questID))
            out[#out + 1] = tr("任务：", "任務：", "Quest: ") .. qName
        end
    end
    return out
end
