local ns = _G.DF_NS or {}

if (type(DF_Locale) ~= "function") or DF_Locale() ~= "enUS" then return end

ns.BisPreset = {
    { slug = "warrior", specs = {
        { key = "arms", label = "Arms", presets = {
            { id = "pre", level = 60, items = { head = {12640}, neck = {22659}, shoulder = {272105}, back = {20068}, chest = {21997}, wrist = {21184}, hands = {272095}, waist = {272403}, legs = {22651}, feet = {21995}, finger = {275976}, finger2 = {19325}, trinket = {21181}, trinket2 = {260824}, main = {19169}, ranged = {22347} }, missingSlots = {}, incomplete = false },
        } },
        { key = "fury", label = "Fury", presets = {
            { id = "pre", level = 60, items = { head = {12640}, neck = {18404}, shoulder = {272105}, back = {20073}, chest = {21997}, wrist = {19578}, hands = {272095}, waist = {272403}, legs = {279265}, feet = {21995}, finger = {272408}, finger2 = {19325}, trinket = {272437}, trinket2 = {270226}, main = {279259}, off = {19104}, ranged = {19107} }, missingSlots = {}, incomplete = false },
        } },
        { key = "prot", label = "Protection", presets = {
            { id = "pre", level = 60, items = { head = {12640}, neck = {19159}, shoulder = {22001}, back = {18511}, chest = {12618}, wrist = {21996}, hands = {250552}, waist = {21994}, legs = {22000}, feet = {21995}, finger = {19325}, finger2 = {272408}, trinket = {272437}, trinket2 = {19024}, main = {250618}, off = {281637}, ranged = {22347} }, missingSlots = {}, incomplete = false },
        } },
    } },
    { slug = "paladin", specs = {
        { key = "holy", label = "Holy", presets = {
            { id = "pre", level = 60, items = { head = {12633}, neck = {20685}, shoulder = {12625}, back = {18510}, chest = {250601}, wrist = {250584}, hands = {250554}, waist = {250574}, legs = {250600}, feet = {250564}, trinket = {272439}, trinket2 = {19288}, main = {22383}, off = {279262}, ranged = {279248} }, missingSlots = {"finger","finger2"}, incomplete = false },
        } },
        { key = "prot", label = "Protection", presets = {
            { id = "pre", tab = "Defensive", level = 60, items = { head = {250597}, neck = {275736}, shoulder = {14552}, back = {18495}, chest = {226992}, wrist = {226985}, hands = {226990}, waist = {14620}, legs = {226988}, feet = {14621}, finger = {272409}, finger2 = {10795}, trinket = {14557}, trinket2 = {272440}, main = {22383}, off = {19321}, ranged = {23203} }, missingSlots = {}, incomplete = false },
            { id = "alt1", label = "Balanced", tab = "Balanced", level = 60, items = { head = {250599}, neck = {19426}, shoulder = {226969}, back = {272411}, chest = {226992}, wrist = {226985}, hands = {226990}, waist = {272404}, legs = {226988}, feet = {226974}, finger = {272409}, finger2 = {22339}, trinket = {14557}, trinket2 = {272437}, main = {2243}, off = {19321}, ranged = {23203} }, missingSlots = {} },
            { id = "alt2", label = "Offensive", tab = "Offensive", level = 60, items = { head = {250599}, neck = {19426}, shoulder = {226969}, back = {272411}, chest = {226973}, wrist = {226970}, hands = {226975}, waist = {226971}, legs = {22753}, feet = {226974}, finger = {22433}, finger2 = {19325}, trinket = {20512}, trinket2 = {272437}, main = {871}, off = {1169}, ranged = {23203} }, missingSlots = {} },
            { id = "alt3", label = "Budget", tab = "Budget", level = 60, items = { head = {276071}, neck = {275736}, shoulder = {14552}, back = {18495}, chest = {14624}, wrist = {250583}, hands = {14622}, waist = {14620}, legs = {14623}, feet = {14621}, finger = {272409}, finger2 = {10795}, trinket = {20071}, trinket2 = {272440}, main = {22332}, off = {12602}, ranged = {272435} }, missingSlots = {} },
        } },
        { key = "ret", label = "Retribution", presets = {} },
    } },
    { slug = "hunter", specs = {
        { key = "bm", label = "Beast Mastery", presets = {
            { id = "pre", level = 60, items = { head = {252605}, neck = {15411}, shoulder = {271956}, back = {13340}, chest = {252483}, wrist = {22011}, hands = {15063}, waist = {22232}, legs = {15062}, feet = {226881}, finger = {272408}, finger2 = {18500}, trinket = {13965}, trinket2 = {19120}, main = {250619}, ranged = {19107} }, missingSlots = {}, incomplete = false },
        } },
        { key = "mm", label = "Marksmanship", presets = {
            { id = "pre", level = 60, items = { head = {252605}, neck = {15411}, shoulder = {271956}, back = {13340}, chest = {252483}, wrist = {22011}, hands = {15063}, waist = {272397}, legs = {15062}, feet = {13967}, finger = {272408}, finger2 = {18500}, trinket = {13965}, trinket2 = {270275}, main = {250619}, ranged = {19107} }, missingSlots = {}, incomplete = false },
        } },
        { key = "surv", label = "Survival", presets = {
            { id = "pre", tab = "Melee weaving", level = 60, items = { head = {252605}, neck = {15411}, shoulder = {272106}, back = {13340}, chest = {252483}, wrist = {22011}, hands = {272099}, waist = {272397}, legs = {12903}, feet = {13967}, finger = {272408}, finger2 = {18500}, trinket = {22321}, trinket2 = {19120}, main = {13285}, ranged = {280020} }, missingSlots = {}, incomplete = false },
            { id = "alt1", label = "Full melee", tab = "Full melee", level = 60, items = { head = {252605}, neck = {15411}, shoulder = {272106}, back = {13340}, chest = {252483}, wrist = {18375}, hands = {15063}, waist = {272397}, legs = {15062}, feet = {22061}, finger = {272408}, finger2 = {13098}, trinket = {22321}, trinket2 = {19289}, main = {1728}, off = {18392}, ranged = {18323} }, missingSlots = {} },
        } },
    } },
    { slug = "rogue", specs = {
        { key = "assa", label = "Assassination", presets = {
            { id = "pre", level = 60, items = { head = {22005}, neck = {22150}, shoulder = {272105}, back = {21187}, chest = {22009}, shirt = {11840}, wrist = {22004}, hands = {21278}, waist = {272395}, legs = {22007}, feet = {18506}, finger = {19325}, finger2 = {21189}, trinket = {272437}, trinket2 = {19289}, main = {19324}, off = {19166}, ranged = {22347}, tabard = {22999} }, missingSlots = {}, incomplete = false },
        } },
        { key = "combat", label = "Combat", presets = {
            { id = "pre", level = 60, items = { head = {22005}, neck = {22150}, shoulder = {272105}, back = {21187}, chest = {22009}, shirt = {11840}, wrist = {22004}, hands = {21278}, waist = {272395}, legs = {22007}, feet = {18506}, finger = {19325}, finger2 = {21189}, trinket = {272437}, trinket2 = {19289}, main = {19324}, off = {22384}, ranged = {22347}, tabard = {22999} }, missingSlots = {}, incomplete = false },
        } },
        { key = "sub", label = "Subtlety", presets = {
            { id = "pre", level = 60, items = { head = {22005}, neck = {22150}, shoulder = {272105}, back = {21187}, chest = {22009}, shirt = {11840}, wrist = {22004}, hands = {21278}, waist = {272395}, legs = {22007}, feet = {18506}, finger = {19325}, finger2 = {21189}, trinket = {272437}, trinket2 = {19289}, main = {22384}, off = {19166}, ranged = {22347}, tabard = {22999} }, missingSlots = {}, incomplete = false },
        } },
    } },
    { slug = "priest", specs = {
        { key = "disc", label = "Discipline", presets = {} },
        { key = "holy", label = "Holy", presets = {
            { id = "pre", level = 60, items = { head = {260212}, neck = {1443}, shoulder = {14139}, back = {18510}, chest = {14154}, wrist = {13958}, hands = {12554}, waist = {19047}, legs = {18386}, feet = {13282}, finger = {16058}, finger2 = {22334}, trinket = {272439}, trinket2 = {18469}, main = {13360}, off = {15805}, ranged = {22254} }, missingSlots = {}, incomplete = false },
        } },
        { key = "shadow", label = "Shadow", presets = {
            { id = "pre", level = 60, items = { head = {22267}, neck = {22403}, shoulder = {226955}, back = {272411}, chest = {14136}, wrist = {13409}, hands = {14146}, waist = {18405}, legs = {10252}, feet = {10247}, finger = {12543}, finger2 = {22339}, trinket = {272438}, trinket2 = {13968}, main = {18372}, off = {18316}, ranged = {13396} }, missingSlots = {}, incomplete = false },
        } },
    } },
    { slug = "shaman", specs = {
        { key = "ele", label = "Elemental", presets = {
            { id = "pre", level = 60, items = { head = {227002}, neck = {22403}, shoulder = {227003}, back = {272411}, chest = {280057}, wrist = {227001}, hands = {227006}, waist = {227008}, legs = {252486}, feet = {227007}, finger = {22339}, finger2 = {272406}, trinket = {272438}, trinket2 = {13968}, main = {20070}, off = {19315}, ranged = {23199} }, missingSlots = {}, incomplete = false },
        } },
        { key = "enh", label = "Enhancement", presets = {
            { id = "pre", level = 60, items = { head = {227002}, neck = {15411}, shoulder = {227003}, back = {272411}, chest = {227024}, wrist = {227017}, hands = {227022}, waist = {227018}, legs = {252606}, feet = {14616}, finger = {19325}, finger2 = {272406}, trinket = {272437}, trinket2 = {13965}, main = {19323}, ranged = {23199} }, missingSlots = {}, incomplete = false },
        } },
        { key = "resto", label = "Restoration", presets = {
            { id = "pre", level = 60, items = { head = {260212}, neck = {18723}, shoulder = {14139}, back = {18510}, chest = {13346}, shirt = {11840}, wrist = {13969}, hands = {12554}, waist = {14553}, legs = {18386}, feet = {13282}, finger = {22334}, finger2 = {16058}, trinket = {272439}, trinket2 = {11819}, main = {13360}, off = {15805}, ranged = {249398}, tabard = {22999} }, missingSlots = {}, incomplete = false },
        } },
    } },
    { slug = "mage", specs = {
        { key = "arcane", label = "Arcane", presets = {
            { id = "pre", level = 60, items = { head = {226935}, neck = {22403}, shoulder = {226936}, back = {272411}, chest = {14152}, wrist = {226929}, hands = {226930}, waist = {18405}, legs = {226933}, feet = {226931}, finger = {272406}, finger2 = {12543}, trinket = {13968}, trinket2 = {22268}, main = {22383}, off = {19315}, ranged = {13938} }, missingSlots = {}, incomplete = false },
        } },
        { key = "fire", label = "Fire", presets = {
            { id = "pre", level = 60, items = { head = {226935}, neck = {22403}, shoulder = {226936}, back = {272411}, chest = {14152}, wrist = {226929}, hands = {226930}, waist = {11662}, legs = {226933}, feet = {226931}, finger = {272406}, finger2 = {22339}, trinket = {272438}, trinket2 = {13968}, main = {944}, ranged = {13938} }, missingSlots = {}, incomplete = false },
        } },
        { key = "frost", label = "Frost", presets = {
            { id = "pre", level = 60, items = { head = {226935}, neck = {22403}, shoulder = {226936}, back = {272411}, chest = {14152}, wrist = {226929}, hands = {226930}, waist = {18405}, legs = {226933}, feet = {226931}, finger = {272406}, finger2 = {12543}, trinket = {13968}, trinket2 = {22268}, main = {944}, ranged = {19108} }, missingSlots = {}, incomplete = false },
        } },
    } },
    { slug = "warlock", specs = {
        { key = "affli", label = "Affliction", presets = {
            { id = "pre", tab = "Realistic best", level = 60, items = { head = {22267}, neck = {18691}, shoulder = {14112}, back = {272411}, chest = {14136}, wrist = {13409}, hands = {18407}, waist = {10255}, legs = {22342}, feet = {10247}, finger = {22339}, finger2 = {12545}, trinket = {272438}, trinket2 = {18467}, main = {18534}, ranged = {13396} }, missingSlots = {}, incomplete = false },
            { id = "alt1", label = "Theoretical best", tab = "Theoretical best", level = 60, items = { head = {22267}, neck = {18691}, shoulder = {19050}, back = {272411}, chest = {14153}, wrist = {19595}, hands = {18407}, waist = {18405}, legs = {22342}, feet = {10247}, finger = {22339}, finger2 = {12545}, trinket = {272438}, trinket2 = {18467}, main = {20220}, ranged = {13396} }, missingSlots = {} },
        } },
        { key = "demo", label = "Demonology", presets = {} },
        { key = "destro", label = "Destruction", presets = {
            { id = "pre", tab = "Realistic best", level = 60, items = { head = {22267}, neck = {22403}, shoulder = {18681}, back = {272411}, chest = {280057}, wrist = {18497}, hands = {13253}, waist = {11662}, legs = {13170}, feet = {11822}, finger = {22339}, finger2 = {272406}, trinket = {272438}, trinket2 = {18467}, main = {18534}, ranged = {13938} }, missingSlots = {}, incomplete = false },
            { id = "alt1", label = "Theoretical best", tab = "Theoretical best", level = 60, items = { head = {22267}, neck = {19426}, shoulder = {19050}, back = {272411}, chest = {14153}, wrist = {19595}, hands = {14146}, waist = {18405}, legs = {22747}, feet = {11822}, finger = {22339}, finger2 = {272406}, trinket = {272438}, trinket2 = {18467}, main = {20220}, ranged = {13938} }, missingSlots = {} },
        } },
    } },
    { slug = "druid", specs = {
        { key = "balance", label = "Balance", presets = {
            { id = "pre", level = 60, items = { head = {22267}, neck = {19426}, shoulder = {226778}, back = {272411}, chest = {280057}, wrist = {13409}, hands = {13258}, waist = {18405}, legs = {252486}, feet = {226774}, finger = {272406}, finger2 = {12543}, trinket = {272438}, trinket2 = {13968}, main = {20070}, off = {19315}, ranged = {272430} }, missingSlots = {}, incomplete = false },
        } },
        { key = "cat", label = "Feral (Cat)", presets = {
            { id = "pre", level = 60, items = { head = {12587}, neck = {19491}, shoulder = {15058}, back = {13340}, chest = {252484}, wrist = {270124}, hands = {21278}, waist = {272396}, legs = {15057}, feet = {12553}, finger = {272408}, finger2 = {19325}, trinket = {13965}, trinket2 = {280065}, main = {19323}, ranged = {220606} }, missingSlots = {}, incomplete = false },
        } },
        { key = "bear", label = "Feral (Bear)", presets = {
            { id = "pre", level = 60, items = { head = {226801}, neck = {275736}, shoulder = {226798}, back = {272415}, chest = {226804}, wrist = {226796}, hands = {13258}, waist = {287040}, legs = {226799}, feet = {226803}, finger = {260216}, finger2 = {15855}, trinket = {272437}, trinket2 = {20071}, main = {18531}, ranged = {23198} }, missingSlots = {}, incomplete = false },
        } },
        { key = "resto", label = "Restoration", presets = {
            { id = "pre", tab = "Best choice", level = 60, items = { head = {252561}, neck = {18723}, shoulder = {14139}, back = {18510}, chest = {12462}, wrist = {13208}, hands = {226784}, waist = {14553}, legs = {16694}, feet = {226781}, finger = {272407}, finger2 = {16058}, trinket = {272439}, trinket2 = {18470}, main = {812}, ranged = {272429} }, missingSlots = {}, incomplete = false },
            { id = "alt1", label = "Easy", tab = "Easy", level = 60, items = { head = {260212}, neck = {18723}, shoulder = {14139}, back = {272413}, chest = {13346}, wrist = {13208}, hands = {12554}, waist = {19047}, legs = {16694}, feet = {18507}, finger = {272407}, finger2 = {16058}, trinket = {272439}, trinket2 = {18470}, main = {13360}, off = {15805}, ranged = {272429} }, missingSlots = {} },
        } },
    } },
}

ns.BisSrcFix = {
    [18316] = "Boss drop|Dire Maul: East · Pusillin",
    [18873] = "Vendor|PvP quartermaster",
    [23053] = "Boss drop|Naxxramas · Kel'Thuzad",
    [220606] = "Enchanting (320)|Crafted",
    [260212] = "Quest reward|Azshara",
    [260216] = "Quest reward|Blackmaw Hold",
    [270124] = "Quest reward|Dire Maul",
    [270226] = "Quest reward|Stranglethorn Vale",
    [275976] = "Vendor|Wardens",
    [280020] = "Boss drop|Shaper's Terrace · Thunderhoof",
    [280057] = "Boss drop|Blackmaw Hold · Impaan the Imprisoner",
    [280065] = "Boss drop|Blackmaw Hold · Blackmaw Behemoth",
    [281637] = "Quest reward",
}

-- 团本前 BIS 方案的专精标签（定义在 Data_BIS.lua）/ pre-raid BIS spec labels (defined in Data_BIS.lua)
do
    local EN = {
        ["元素"] = "Elemental", ["兽王"] = "Beast Mastery", ["冰霜"] = "Frost", ["增强"] = "Enhancement",
        ["奇袭"] = "Assassination", ["奥术"] = "Arcane", ["守护"] = "Guardian", ["射击"] = "Marksmanship",
        ["平衡"] = "Balance", ["恢复"] = "Restoration", ["恶魔"] = "Demonology", ["惩戒"] = "Retribution",
        ["戒律"] = "Discipline", ["战斗"] = "Combat", ["敏锐"] = "Subtlety", ["暗影"] = "Shadow",
        ["武器"] = "Arms", ["毁灭"] = "Destruction", ["火焰"] = "Fire", ["狂怒"] = "Fury",
        ["生存"] = "Survival", ["痛苦"] = "Affliction", ["神圣"] = "Holy", ["野性"] = "Feral",
        ["防护"] = "Protection",
    }
    local d = ns.BisPre
    for _, c in ipairs((type(d) == "table" and d.classes) or {}) do
        for _, sp in ipairs(c.specs or {}) do
            if type(sp) == "table" and sp.label then sp.label = EN[sp.label] or sp.label end
        end
    end
end

return nil
