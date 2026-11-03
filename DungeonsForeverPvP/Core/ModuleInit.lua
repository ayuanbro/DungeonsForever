local ns = _G.DF_NS or {}

local P = ns.ModulePaint("PvP")
if P then
    ns.PvPIdle = P.Idle
    ns.PvPPaint = P.Paint
    ns.PvPStep = P.Step
    ns.PvPPhased = P.Phased
end
