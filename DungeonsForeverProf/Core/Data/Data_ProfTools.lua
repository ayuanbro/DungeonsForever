local ns = _G.DF_NS or {}
ns.ProfTools = {
    revision = 2,
    engineering = {
        {spell=7430, item=6219, minSkill=50},
    },
    alchemy = {
        {spell=11459, item=9149, minSkill=225, bindOnPickup=true},
        {spell=17632, item=13503, minSkill=275, bindOnPickup=true},
    },
    enchanting = {
        {spell=7421, item=6218, minSkill=5, bindOnPickup=true, tier=1},
        {spell=7795, item=6339, minSkill=130, bindOnPickup=true, tier=2},
        {spell=13628, item=11130, minSkill=175, bindOnPickup=true, tier=3},
        {spell=13702, item=11145, minSkill=220, bindOnPickup=true, tier=4},
        {spell=20051, item=16207, minSkill=290, bindOnPickup=true, tier=5},
    },
}
