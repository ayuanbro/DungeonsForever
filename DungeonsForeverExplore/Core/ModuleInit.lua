local ns = _G.DF_NS or {}

local P = ns.ModulePaint("Explore")
if P then
    ns.ExploreIdle = P.Idle
    ns.ExplorePaint = P.Paint
    ns.ExploreStep = P.Step
    ns.ExplorePhased = P.Phased
end

ns.ExploreDB = ns.ModuleDB("DungeonsForeverExploreDB", {  })
