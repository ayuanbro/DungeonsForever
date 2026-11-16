local ns = _G.DF_NS or {}
if not ns.LoadForeverPages then return end
local G={DataSchema=2};ns.ProfGatheringRoutes=G
local allowed={mining=true,herbalism=true,skinning=true,fishing=true}
local function text(key)
    return ns.L and ns.L[key] or key
end
local function actualCap(slug,opts)
    local cap=tonumber(opts and opts.maxSkill)
    if cap and cap>0 then return cap end
    local ranks=ns.ProfRanks
    local state=ranks and ranks.Status and ranks.Status(slug)
    if state and state.known and state.maxSkill and state.maxSkill>0 then return state.maxSkill end
    local view=ns.ProfModule
    local professions=view and view.ProfLearned and view.ProfLearned()
    cap=professions and professions[slug] and tonumber(professions[slug].max)
    return cap and cap>0 and cap or nil
end
local function zoneNames(locations)
    local names,seen={},{}
    local dg=ns.ProfHost and ns.ProfHost.DG
    for _,area in ipairs(locations or {}) do
        local id=area.areaID or area.zoneID or area[1]
        if id and not seen[id] then
            seen[id]=true;names[#names+1]=dg and dg.ZoneName and dg.ZoneName(id) or ("#"..id)
        elseif not id and type(area.name)=="string" and not seen[area.name] then
            seen[area.name]=true;names[#names+1]=area.name
        end
    end
    return table.concat(names," / ")
end
function G.HasRoute(slug)
    local data=ns.ProfGathering and ns.ProfGathering[slug]
    if type(data)=="table" and data.schema==2 then return allowed[slug] and #(data.guideSteps or {})>0 or false end
    return allowed[slug] and (slug=="fishing" and ns.ProfFishingRoutes and #(ns.ProfFishingRoutes.fishingSteps or {})>0
        or type(data)=="table" and #data>0) or false
end
function G.Steps(slug,target,opts)
    if not G.HasRoute(slug) then return nil end
    opts=opts or {}
    if slug=="mining" and opts.mode=="smelt" then return nil end
    local cap=actualCap(slug,opts)
    local source=slug=="fishing" and ns.ProfFishingRoutes or ns.ProfGathering and ns.ProfGathering[slug]
    target=tonumber(target) or (ns.ProfModule and ns.ProfModule.LV_DEF) or 300
    if not source or source.schema~=2 then target=math.min(300,target) end
    local out={}
    local function add(lo,hi,locations,items)
        if cap then hi=hi and math.min(hi,cap) or cap end
        if hi then hi=math.min(hi,target) end
        if not hi or hi<=lo then return end
        local name=slug=="mining" and text("实地采矿") or slug=="skinning" and text("实地剥皮")
            or slug=="fishing" and text("钓鱼练习") or text("实地采集")
        out[#out+1]={lo,hi,0,0,kind="gather",profession=slug,reference=true,navigationOnly=true,
            checkpoint=true,name=text("参考").." · "..name,locations=locations,gatheredItems=items,
            detail=zoneNames(locations).."\n"..text("参考采集导航；门槛不代表技能提升范围。")}
    end
    if slug=="fishing" then
        for _,stage in ipairs(ns.ProfFishingRoutes.fishingSteps or {}) do
            if type(stage.from)=="number" and type(stage.to)=="number" then add(stage.from,stage.to,stage.areas or {},stage.fishIDs) end
        end
        return #out>0 and out or nil
    end
    local data=ns.ProfGathering[slug]
    if data.schema==2 then
        for _,stage in ipairs(data.guideSteps or {}) do
            if type(stage.from)=="number" and type(stage.to)=="number" then add(stage.from,stage.to,stage.areas or {},stage.itemIDs) end
        end
        return #out>0 and out or nil
    end
    if slug=="skinning" then
        for _,row in ipairs(data) do
            local range=data.skillBands and data.skillBands[row[1] and row[1][1]]
            if range then add(range[1],range[2],row[3],row[2]) end
        end
    else
        local thresholds,locations,items={},{},{}
        for _,row in ipairs(data) do
            local lo=tonumber(row[2])
            if lo and lo>=1 then
                if not locations[lo] then thresholds[#thresholds+1]=lo;locations[lo]={};items[lo]={} end
                for _,area in ipairs(row[3] or {}) do locations[lo][#locations[lo]+1]=area end
                for _,id in ipairs(row[1] or {}) do items[lo][#items[lo]+1]=id end
            end
        end
        table.sort(thresholds)
        for index,lo in ipairs(thresholds) do add(lo,thresholds[index+1],locations[lo],items[lo]) end
    end
    return #out>0 and out or nil
end
