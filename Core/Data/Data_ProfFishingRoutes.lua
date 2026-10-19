local _,ns=...
local locale=GetLocale and GetLocale() or "zhCN"
local function text(cn,tw,en) return locale=="enUS" and en or locale=="zhTW" and tw or cn end
local maps={[12]=1429,[14]=1411,[141]=1438,[215]=1412,[1519]=1453,[1537]=1455,[1637]=1454,[1638]=1456,[1657]=1457,
    [267]=1424,[44]=1433,[331]=1440,[406]=1442,[15]=1445,[36]=1416,[33]=1434,[440]=1446,[47]=1425,
    [357]=1444,[361]=1448,[139]=1423,[618]=1452,[38]=1432,[130]=1421,[17]=1413,[40]=1436}
local function area(id,skill,safe,cn,tw,en,rate,faction)
    return {zoneID=id,mapID=ns.AreaMap and ns.AreaMap[id] or maps[id],minSkill=skill,noGetaway=safe,
        name=text(cn,tw,en),catchRate=rate,faction=faction,reference=true}
end
local starters={
    area(12,1,25,"艾尔文森林·内陆池塘","艾爾文森林·內陸池塘","Elwynn Forest: inland ponds",.60,"A"),
    area(215,1,25,"莫高雷·内陆湖泊","莫高雷·內陸湖泊","Mulgore: inland lakes",.60,"H"),
    area(14,1,25,"杜隆塔尔·野猪农场池塘","杜洛塔·野豬農場池塘","Durotar: Jaggedswine Farm pond",.60,"H"),
    area(141,1,25,"泰达希尔·内陆湖泊","泰達希爾·內陸湖泊","Teldrassil: inland lakes",.60,"A")}
local cities={
    area(1519,1,75,"暴风城·运河","暴風城·運河","Stormwind canals",nil,"A"),
    area(1537,1,75,"铁炉堡·荒弃的洞穴","鐵爐堡·荒棄的洞穴","Ironforge: Forlorn Cavern",nil,"A"),
    area(1637,1,75,"奥格瑞玛·荣誉谷","奧格瑪·榮譽谷","Orgrimmar: Valley of Honor",nil,"H"),
    area(1638,1,75,"雷霆崖·池塘","雷霆崖·池塘","Thunder Bluff ponds",nil,"H")}
local catfish={
    area(267,55,150,"希尔斯布莱德丘陵·内陆河流","希爾斯布萊德丘陵·內陸河流","Hillsbrad Foothills: inland rivers",.60),
    area(44,55,150,"赤脊山·止水湖","赤脊山·止水湖","Redridge Mountains: Lake Everstill",.60),
    area(406,55,150,"石爪山脉·中央池塘","石爪山脈·中央池塘","Stonetalon Mountains: central pond",.60)}
local trout={
    area(36,130,225,"奥特兰克山脉·洛丹米尔湖西岸","奧特蘭克山脈·洛丹米爾湖西岸","Alterac Mountains: western Lordamere Lake"),
    area(15,130,225,"尘泥沼泽·内陆水域","塵泥沼澤·內陸水域","Dustwallow Marsh: inland waters"),
    area(33,130,225,"荆棘谷·内陆河流","荊棘谷·內陸河流","Stranglethorn Vale: inland rivers")}
local cod={area(15,130,225,"尘泥沼泽·海岸（联盟可选塞拉摩码头）","塵泥沼澤·海岸（聯盟可選塞拉摩碼頭）","Dustwallow Marsh: coast (Theramore docks for Alliance)"),
    area(33,130,225,"荆棘谷·格罗姆高以南海岸","荊棘谷·格羅姆高以南海岸","Stranglethorn Vale: coast south of Grom'gol")}
local yellowtail={
    area(440,205,300,"塔纳利斯·热砂港海岸","塔納利斯·熱砂港海岸","Tanaris: Steamwheedle Port coast",.40),
    area(47,205,300,"辛特兰·海岸","辛特蘭·海岸","The Hinterlands: coast",.40),
    area(357,205,300,"菲拉斯·海岸","菲拉斯·海岸","Feralas: coast",.40)}
local redgill={area(47,205,300,"辛特兰·隐匿石西侧池塘","辛特蘭·隱匿石西側池塘","The Hinterlands: pond west of Skulk Rock",.40),
    area(361,205,300,"费伍德森林·内陆水域","費伍德森林·內陸水域","Felwood: inland waters",.40)}
local salmon={area(618,330,425,"冬泉谷·多诺瓦附近池塘","冬泉谷·多諾瓦附近池塘","Winterspring: pond near Donova Snowden",.40),
    area(357,330,425,"菲拉斯·加德米尔湖","菲拉斯·加德米爾湖","Feralas: Lake Jademir",.40)}
local conflict=text("指南对白鳞鲑鱼门槛记载不一致；保守按 330/425，并需钓鱼加成。","指南對白鱗鮭魚門檻記載不一致；保守按 330/425，並需釣魚加成。","The guide conflicts on salmon thresholds; conservatively use 330/425 and fishing bonuses.")
for _,a in ipairs(salmon) do a.note=conflict end
local FR={verifiedAt="2026-10-19",version=1,sources={cooking=cook,fishing=fishing},fish={},
    cookingSteps={{from=1,to=50,spell=7751,guideCrafts=52},{from=50,to=100,spell=7753,guideCrafts=55},
        {from=100,to=175,spell=7755,guideCrafts=120},{from=175,to=225,spell=20916,guideCrafts=55},
        {from=225,to=300,spell=18238}},
    recipeSpells={7751,7752,7753,7754,7755,20916,7827,7828,25704,25954,18238,18239,18240,18241,18242,18243,18244,18247}}
ns.ProfFishingRoutes=FR
local function fish(id,areas,extra)
    local f={id=id,areas=areas,reference=true}
    for k,v in pairs(extra or {}) do f[k]=v end
    FR.fish[id]=f
end
fish(6291,starters,{minSkill=1,noGetaway=25,catchRate=.60})
fish(6289,cities,{minSkill=1,noGetaway=75})
fish(6308,catfish,{minSkill=55,noGetaway=150,catchRate=.60})
fish(8365,trout,{minSkill=130,noGetaway=225})
fish(6362,cod,{minSkill=130,noGetaway=225})
fish(4603,yellowtail,{minSkill=205,noGetaway=300,catchRate=.40})
fish(13758,redgill,{minSkill=205,noGetaway=300,catchRate=.40})
fish(13754,yellowtail,{minSkill=205,noGetaway=300,catchRate=.20})
fish(13889,salmon,{minSkill=330,noGetaway=425,catchRate=.40,thresholdConflict=true})
fish(6303,{area(14,1,25,"杜隆塔尔·森金村海岸","杜洛塔·森金村海岸","Durotar: Sen'jin Village coast"),
    area(141,1,25,"泰达希尔·海岸","泰達希爾·海岸","Teldrassil coast")},{minSkill=1,noGetaway=25})
fish(6361,{area(17,1,75,"贫瘠之地·棘齿城海岸","貧瘠之地·棘齒城海岸","The Barrens: Ratchet coast"),
    area(40,1,75,"西部荒野·海岸","西部荒野·海岸","Westfall coast")},{minSkill=1,noGetaway=75})
fish(21071,{area(38,1,75,"洛克莫丹·鼠尾鱼群","洛克莫丹·鼠尾魚群","Loch Modan: Sagefish Schools"),
    area(130,1,75,"银松森林·鼠尾鱼群","銀松森林·鼠尾魚群","Silverpine Forest: Sagefish Schools")},{minSkill=1,noGetaway=75,pools=true})
fish(21153,{trout[1],trout[3]},{minSkill=130,noGetaway=225,pools=true})
fish(13759,redgill,{minSkill=205,noGetaway=300,catchRate=.25,timeRestricted=true})
fish(13760,redgill,{minSkill=205,noGetaway=300,catchRate=.25,timeRestricted=true})
fish(13755,yellowtail,{minSkill=205,noGetaway=300,catchRate=.10,seasonal=true})
fish(13756,yellowtail,{minSkill=205,noGetaway=300,catchRate=.10,seasonal=true})
FR.fishingSteps={
    {from=1,to=25,areas=starters,fishIDs={6291},note=text("先在出生地内陆水域起步，减少脱钩。","先在出生地內陸水域起步，減少脫鉤。","Start in inland starter-zone waters to reduce getaways.")},
    {from=25,to=150,areas=cities,fishIDs={6291,6289,6308},note=text("主城安全便利；幽暗城杂鱼较多，优先其他主城。","主城安全便利；幽暗城雜魚較多，優先其他主城。","Capital cities are safe and convenient; prefer other capitals over Undercity's bycatch.")},
    {from=150,to=225,areas={cod[1],trout[2],trout[1]},fishIDs={6362,8365},note=text("尘泥沼泽：海岸钓鳕鱼，内陆钓冠鳟；换区不是涨点的必要条件。","塵泥沼澤：海岸釣鱈魚，內陸釣冠鱒；換區不是漲點的必要條件。","Dustwallow: cod at the coast, trout inland. Moving zones is optional for skill gains.")},
    {from=225,to=300,areas=yellowtail,fishIDs={4603},note=text("热砂港优先，斑点黄尾鱼全年全天可钓；有效技能不足时可继续低级水域或使用钓鱼加成。","熱砂港優先，斑點黃尾魚全年全天可釣；有效技能不足時可繼續低級水域或使用釣魚加成。","Prefer Steamwheedle Port for year-round yellowtail; stay in lower waters or use fishing bonuses when needed.")}}
local function shelf(npc,faction,rows)
    ns.ProfFormulaOffers=ns.ProfFormulaOffers or {}
    local loc=ns.ProfVendors and ns.ProfVendors[npc]
    for _,row in ipairs(rows) do
        local id=row[1];local offers=ns.ProfFormulaOffers[id] or {};ns.ProfFormulaOffers[id]=offers
        offers[#offers+1]={itemID=id,npcID=npc,faction=faction,price=row[2],quantity=1,bundleSize=1,
            unlimited=true,available=true,reference=true,priceVerified=true,estimated=true,priceBasis="reference",
            areaID=loc and loc[1],mapID=loc and loc[2],x=loc and loc[3],y=loc and loc[4]}
    end
end
shelf(5494,"A",{{6325,42},{6330,1136},{6368,378}})
shelf(5162,"A",{{6326,40},{6328,400},{6369,2200},{17062,2200}})
shelf(3027,"H",{{6328,360},{6330,1080},{21099,450},{21219,4500}})
shelf(3029,"H",{{6325,42},{6330,1263}})
shelf(3333,"H",{{6368,400},{6369,2315},{17062,2315}})
shelf(8137,"N",{{13939,14400},{13942,16000},{13945,20000},{13946,20000}})
