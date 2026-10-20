-- Additional, traceable formula sources; loaded after locale catalogues.
-- Catalogue omissions are not evidence that a formula is a quest reward.
-- Only explicit Forever quest rewards below are marked quest-only.
local _,ns=...
ns.ProfFormulaMeta=ns.ProfFormulaMeta or {}
local function Quest(item,quest,name)
    ns.ProfFormulaMeta[item]={verifiedAt="2026-10-18",source={questOnly=true,
        quests={{id=quest,name=name}},url="https://www.wowhead.com/forever/quest="..quest}}
end
Quest(4597,429,"Wild Hearts")
Quest(4624,715,"Liquid Stone")
Quest(6735,1618,"Gearing Redridge")
Quest(5083,769,"Kodo Hide Bag")
Quest(7978,2752,"On Iron Pauldrons")
Quest(7979,2751,"Barbaric Battlements")
Quest(7980,2754,"Horns of Frenzy")
Quest(7981,2753,"Trampled Under Foot")
Quest(7982,2755,"Joys of Omosh")

-- NPC 1685, Wowhead Forever Sells shelf, checked 2026-10-18.
-- maxStock describes the refresh cap, never current inventory or a promise
-- of immediate availability. These records contain no purchase prices.
ns.ProfFormulaOffers=ns.ProfFormulaOffers or {}
local function Limited(item,cap)
    ns.ProfFormulaOffers[item]={{itemID=item,npcID=1685,faction="A",quantity=1,
        maxStock=cap,limited=true,unlimited=false,catalogueOnly=true,
        source="wowhead-forever",verifiedAt="2026-10-18",
        url="https://www.wowhead.com/forever/npc=1685"}}
end
Limited(5640,2)
Limited(6053,1)
