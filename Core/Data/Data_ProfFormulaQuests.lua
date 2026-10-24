local _,ns=...
ns.ProfFormulaMeta=ns.ProfFormulaMeta or {}
local function Quest(item,quest,name)
    ns.ProfFormulaMeta[item]={source={questOnly=true,
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
