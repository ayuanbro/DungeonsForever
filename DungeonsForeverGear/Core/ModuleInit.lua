local ns = _G.DF_NS or {}

local P = ns.ModulePaint("Gear")
if P then
    ns.GearIdle = P.Idle
    ns.GearPaint = P.Paint
    ns.GearStep = P.Step
    ns.GearPhased = P.Phased
end

ns.GearDB = ns.ModuleDB("DungeonsForeverGearDB", { "gear", "bis", "wishlist" })
