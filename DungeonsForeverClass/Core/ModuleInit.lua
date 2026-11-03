local ns = _G.DF_NS or {}

local P = ns.ModulePaint("Class")
if P then
    ns.ClassIdle = P.Idle
    ns.ClassPaint = P.Paint
    ns.ClassStep = P.Step
    ns.ClassPhased = P.Phased
end

ns.ClassDB = ns.ModuleDB("DungeonsForeverClassDB", { "tier", "talent", "talentSim" })
