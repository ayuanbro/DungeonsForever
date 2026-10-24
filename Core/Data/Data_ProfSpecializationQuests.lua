local _, ns = ...
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
        questID=3639, questName="工作成果", prerequisiteQuestIDs={3638},
        inputs={{4394,20},{10507,20},{4384,5}},
        npcID=8126, npcName="尼克斯·斯普克斯宾", zone="加基森",
        mapID=1446, x=52.48, y=27.33,
        factions={A=true,H=true},
    },
    gnomish={
        id="engineering:gnomish", choice="gnomish", profession="engineering",
        abilityID=20219, minSkill=200, minLevel=30,
        questName="工作成果", inputs={{10559,6},{4407,1},{4392,2}},
        variants={
            A={questID=3641, prerequisiteQuestIDs={3640}, npcID=7944,
                npcName="工匠大师欧沃斯巴克", zone="铁炉堡", mapID=1455, x=69.55, y=50.33},
            H={questID=3643, prerequisiteQuestIDs={3642}, npcID=7406,
                npcName="奥格索普·奥布诺提斯", zone="藏宝海湾", mapID=1434, x=28.36, y=76.35},
        },
    },
}
