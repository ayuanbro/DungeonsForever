local _, ns = ...

ns.WeaponTraining = {
    zones = {
        [1497] = 1458,
        [1519] = 1453,
        [1537] = 1455,
        [1637] = 1454,
        [1638] = 1456,
        [1657] = 1457,
    },
    order = { 196, 197, 198, 199, 201, 202, 1180, 15590, 227, 200, 264, 266, 5011, 2567 },
    skills = {
        [196] = {
            classes = { HUNTER = true, PALADIN = true, ROGUE = true, SHAMAN = true, WARRIOR = true },
            level = nil,
            trainers = {
                { npc = 11865, name = "布里维夫·石手", faction = "Alliance", zoneId = 1537, x = 61.2, y = 89.5 },
                { npc = 2704, name = "哈纳什", faction = "Horde", zoneId = 1637, x = 81.5, y = 19.6 },
                { npc = 11868, name = "塞尤克", faction = "Horde", zoneId = 1637, x = 81.7, y = 19.6 },
            },
        },
        [197] = {
            classes = { HUNTER = true, PALADIN = true, SHAMAN = true, WARRIOR = true },
            level = nil,
            trainers = {
                { npc = 11865, name = "布里维夫·石手", faction = "Alliance", zoneId = 1537, x = 61.2, y = 89.5 },
                { npc = 2704, name = "哈纳什", faction = "Horde", zoneId = 1637, x = 81.5, y = 19.6 },
                { npc = 11868, name = "塞尤克", faction = "Horde", zoneId = 1637, x = 81.7, y = 19.6 },
            },
        },
        [198] = {
            classes = { DRUID = true, PALADIN = true, PRIEST = true, ROGUE = true, SHAMAN = true, WARRIOR = true },
            level = nil,
            trainers = {
                { npc = 11865, name = "布里维夫·石手", faction = "Alliance", zoneId = 1537, x = 61.2, y = 89.5 },
                { npc = 11869, name = "安塞瓦", faction = "Horde", zoneId = 1638, x = 40.0, y = 63.1 },
            },
        },
        [199] = {
            classes = { DRUID = true, PALADIN = true, SHAMAN = true, WARRIOR = true },
            level = nil,
            trainers = {
                { npc = 11865, name = "布里维夫·石手", faction = "Alliance", zoneId = 1537, x = 61.2, y = 89.5 },
                { npc = 11869, name = "安塞瓦", faction = "Horde", zoneId = 1638, x = 40.0, y = 63.1 },
            },
        },
        [201] = {
            classes = { HUNTER = true, MAGE = true, PALADIN = true, ROGUE = true, WARLOCK = true, WARRIOR = true },
            level = nil,
            trainers = {
                { npc = 11867, name = "吴平", faction = "Alliance", zoneId = 1519, x = 63.9, y = 69.1 },
                { npc = 11870, name = "阿基巴德", faction = "Horde", zoneId = 1497, x = 57.3, y = 32.8 },
            },
        },
        [202] = {
            classes = { HUNTER = true, PALADIN = true, WARRIOR = true },
            level = nil,
            trainers = {
                { npc = 11867, name = "吴平", faction = "Alliance", zoneId = 1519, x = 63.9, y = 69.1 },
                { npc = 11870, name = "阿基巴德", faction = "Horde", zoneId = 1497, x = 57.3, y = 32.8 },
            },
        },
        [1180] = {
            classes = { DRUID = true, HUNTER = true, MAGE = true, PRIEST = true, ROGUE = true, SHAMAN = true, WARLOCK = true, WARRIOR = true },
            level = nil,
            trainers = {
                { npc = 11867, name = "吴平", faction = "Alliance", zoneId = 1519, x = 63.9, y = 69.1 },
                { npc = 13084, name = "比克斯", faction = "Alliance", zoneId = 1537, x = 62.2, y = 89.6 },
                { npc = 11866, name = "伊琳尼雅·月火", faction = "Alliance", zoneId = 1657, x = 57.7, y = 46.0 },
                { npc = 11868, name = "塞尤克", faction = "Horde", zoneId = 1637, x = 81.7, y = 19.6 },
                { npc = 11870, name = "阿基巴德", faction = "Horde", zoneId = 1497, x = 57.3, y = 32.8 },
            },
        },
        [15590] = {
            classes = { DRUID = true, HUNTER = true, ROGUE = true, SHAMAN = true, WARRIOR = true },
            level = nil,
            trainers = {
                { npc = 11865, name = "布里维夫·石手", faction = "Alliance", zoneId = 1537, x = 61.2, y = 89.5 },
                { npc = 11866, name = "伊琳尼雅·月火", faction = "Alliance", zoneId = 1657, x = 57.7, y = 46.0 },
                { npc = 11868, name = "塞尤克", faction = "Horde", zoneId = 1637, x = 81.7, y = 19.6 },
            },
        },
        [227] = {
            classes = { DRUID = true, HUNTER = true, MAGE = true, PRIEST = true, SHAMAN = true, WARLOCK = true, WARRIOR = true },
            level = nil,
            trainers = {
                { npc = 11867, name = "吴平", faction = "Alliance", zoneId = 1519, x = 63.9, y = 69.1 },
                { npc = 11866, name = "伊琳尼雅·月火", faction = "Alliance", zoneId = 1657, x = 57.7, y = 46.0 },
                { npc = 2704, name = "哈纳什", faction = "Horde", zoneId = 1637, x = 81.5, y = 19.6 },
                { npc = 11868, name = "塞尤克", faction = "Horde", zoneId = 1637, x = 81.7, y = 19.6 },
                { npc = 11869, name = "安塞瓦", faction = "Horde", zoneId = 1638, x = 40.0, y = 63.1 },
            },
        },
        [200] = {
            classes = { DRUID = true, HUNTER = true, PALADIN = true, WARRIOR = true },
            level = 20,
            trainers = {
                { npc = 11867, name = "吴平", faction = "Alliance", zoneId = 1519, x = 63.9, y = 69.1 },
                { npc = 11870, name = "阿基巴德", faction = "Horde", zoneId = 1497, x = 57.3, y = 32.8 },
            },
        },
        [264] = {
            classes = { HUNTER = true, ROGUE = true, WARRIOR = true },
            level = nil,
            trainers = {
                { npc = 11866, name = "伊琳尼雅·月火", faction = "Alliance", zoneId = 1657, x = 57.7, y = 46.0 },
                { npc = 2704, name = "哈纳什", faction = "Horde", zoneId = 1637, x = 81.5, y = 19.6 },
                { npc = 11868, name = "塞尤克", faction = "Horde", zoneId = 1637, x = 81.7, y = 19.6 },
            },
        },
        [266] = {
            classes = { HUNTER = true, ROGUE = true, WARRIOR = true },
            level = nil,
            trainers = {
                { npc = 11865, name = "布里维夫·石手", faction = "Alliance", zoneId = 1537, x = 61.2, y = 89.5 },
                { npc = 11869, name = "安塞瓦", faction = "Horde", zoneId = 1638, x = 40.0, y = 63.1 },
            },
        },
        [5011] = {
            classes = { HUNTER = true, ROGUE = true, WARRIOR = true },
            level = nil,
            trainers = {
                { npc = 11867, name = "吴平", faction = "Alliance", zoneId = 1519, x = 63.9, y = 69.1 },
                { npc = 13084, name = "比克斯", faction = "Alliance", zoneId = 1537, x = 62.2, y = 89.6 },
                { npc = 11870, name = "阿基巴德", faction = "Horde", zoneId = 1497, x = 57.3, y = 32.8 },
            },
        },
        [2567] = {
            classes = { HUNTER = true, ROGUE = true, WARRIOR = true },
            level = nil,
            trainers = {
                { npc = 13084, name = "比克斯", faction = "Alliance", zoneId = 1537, x = 62.2, y = 89.6 },
                { npc = 11866, name = "伊琳尼雅·月火", faction = "Alliance", zoneId = 1657, x = 57.7, y = 46.0 },
                { npc = 2704, name = "哈纳什", faction = "Horde", zoneId = 1637, x = 81.5, y = 19.6 },
                { npc = 11868, name = "塞尤克", faction = "Horde", zoneId = 1637, x = 81.7, y = 19.6 },
            },
        },
    },
}
