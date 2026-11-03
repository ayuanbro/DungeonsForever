local ns = _G.DF_NS or {}

local P = ns.ModulePaint("Spell")
if P then
    ns.SpellIdle = P.Idle
    ns.SpellPaint = P.Paint
    ns.SpellStep = P.Step
    ns.SpellPhased = P.Phased
end
