-- Manually maintained profession tool goals. Recipe inputs/yields are always
-- read from the current catalogue/client, never copied into this small list.
-- Audited against the shipped Forever 1.60.1.70450 catalogue (2026-10-21).
-- These are Forever learning levels: Alchemist's Stone is 275, not 300.
local _, ns = ...
ns.ProfTools = {
    revision = 1,
    engineering = {
        {spell=7430, item=6219, minSkill=50}, -- Arclight Spanner
    },
    alchemy = {
        {spell=11459, item=9149, minSkill=225, bindOnPickup=true}, -- Philosopher's Stone
        {spell=17632, item=13503, minSkill=275, bindOnPickup=true}, -- Alchemist's Stone
    },
    enchanting = {
        {spell=7421, item=6218, minSkill=5, bindOnPickup=true}, -- Runed Copper Rod
        {spell=7795, item=6339, minSkill=130, bindOnPickup=true}, -- Runed Silver Rod
        {spell=13628, item=11130, minSkill=175, bindOnPickup=true}, -- Runed Golden Rod
        {spell=13702, item=11145, minSkill=220, bindOnPickup=true}, -- Runed Truesilver Rod
        {spell=20051, item=16207, minSkill=290, bindOnPickup=true}, -- Runed Arcanite Rod
    },
}
