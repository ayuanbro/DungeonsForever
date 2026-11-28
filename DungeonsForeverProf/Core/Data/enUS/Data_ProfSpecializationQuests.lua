local ns = _G.DF_NS or {}

if (type(DF_Locale) ~= "function") or DF_Locale() ~= "enUS" then return end
ns.ProfSpecializationQuestMeta = {
    schemaVersion=1, revision=1, sourceBuild="",
    sourceCommit="af56aeef176b2b7534be683907c276c52beabb6d",
    sourceURL="https://github.com/Questie/QuestieDB/blob/af56aeef176b2b7534be683907c276c52beabb6d/data/Forever/foreverQuestDB.lua",
    correctionURL="https://github.com/Questie/QuestieDB/blob/af56aeef176b2b7534be683907c276c52beabb6d/src/corrections/Forever/legacy/classicQuestFixes.lua",
}
ns.ProfSpecializationAbilities = {
    [20219]="engineering", [20222]="engineering",
    [9787]="blacksmithing", [9788]="blacksmithing",
    [17039]="blacksmithing", [17040]="blacksmithing", [17041]="blacksmithing",
    [10656]="leatherworking", [10658]="leatherworking", [10660]="leatherworking",
}
ns.ProfSpecializationQuests = {
    goblin={
        id="engineering:goblin", choice="goblin", profession="engineering",
        abilityID=20222, minSkill=200, minLevel=30,
        questID=3639, questName="Fruits of Labor", prerequisiteQuestIDs={3638},
        inputs={{4394,20},{10507,20},{4384,5}},
        npcID=8126, npcName="Nixx Sprocketspring", zone="Gadgetzan",
        mapID=1446, x=52.48, y=27.33,
        factions={A=true,H=true},
    },
    gnomish={
        id="engineering:gnomish", choice="gnomish", profession="engineering",
        abilityID=20219, minSkill=200, minLevel=30,
        questName="Fruits of Labor", inputs={{10559,6},{4407,1},{4392,2}},
        variants={
            A={questID=3641, prerequisiteQuestIDs={3640}, npcID=7944,
                npcName="Tinkmaster Overspark", zone="Ironforge", mapID=1455, x=69.55, y=50.33},
            H={questID=3643, prerequisiteQuestIDs={3642}, npcID=7406,
                npcName="Oglethorpe Obnoticus", zone="Booty Bay", mapID=1434, x=28.36, y=76.35},
        },
    },
}
