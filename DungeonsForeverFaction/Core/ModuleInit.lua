local ns = _G.DF_NS or {}

local P = ns.ModulePaint("Faction")
if P then
    ns.FactionIdle = P.Idle
    ns.FactionPaint = P.Paint
    ns.FactionStep = P.Step
    ns.FactionPhased = P.Phased
end

ns.FactionDB = ns.ModuleDB("DungeonsForeverFactionDB", { "factions" })
