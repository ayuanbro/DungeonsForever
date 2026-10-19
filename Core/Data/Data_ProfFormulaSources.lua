local _,ns=...
ns.ProfFormulaMeta=ns.ProfFormulaMeta or {}
local function Quest(item,quest,name)
    ns.ProfFormulaMeta[item]={source={questOnly=true,quests={{id=quest,name=name}}}}
end
Quest(4597,429,"荒野之心")
Quest(4624,715,"卢希恩的药水")
Quest(6735,1618,"赤脊山的补给")
Quest(5083,769,"科多兽皮包")
Quest(7978,2752,"铁肩铠")
Quest(7979,2751,"野人装甲")
Quest(7980,2754,"疯狂之角")
Quest(7981,2753,"踩在脚下")
Quest(7982,2755,"沃姆什的喜悦")

ns.ProfFormulaOffers=ns.ProfFormulaOffers or {}
local function Limited(item,price,cap)
    ns.ProfFormulaOffers[item]={{itemID=item,npcID=1685,faction="A",quantity=1,
        price=price,maxStock=cap,limited=true,unlimited=false,reference=true,
        priceVerified=true,priceBasis="npc-shelf"}}
end
Limited(5640,100,2)
Limited(6053,842,1)
