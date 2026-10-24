# -*- coding: utf-8 -*-
"""Data_ExploreBanner.lua（探索页 · 血色旗帜）专用英文对照表（2026-10-07）。

键 = Data_ExploreBanner.lua 的 zhCN 原文，值 = 整句人工翻译。
★★ m 子串约束：t 整句的译文必须**包含**它每个 m 标记子串的译文
（PetSplit 在渲染期按译文里的子串切段，缺了 = 可点击段静默消失）。
地图标记译文保留资料页坐标原文（/way 口径）；物品名标记译文用官方英文物品名
（Arathi/Graveyard/Swamp/Theramore Echo + Scarlet Banner）。
2026-10-07 三轮：半身像拆 4 行（①②③④ = 使用序 1/3/4/2，每行附位置序 + 增益名，
删歧义口诀）；备注拆短句；长句改写让回响名收尾。增益名「悼言」按 Elegy 直译。
"""

BANNER = {
    # ── src 短语 ──
    '血色修道院 · 四座坟墓拾回响 → 图书馆四座半身像按序使用':
        'Scarlet Monastery · pick up the echoes from four graves, '
        'then use them on the four Library busts in order',

    # ── 组标题（st.h）──
    '收集回响 · 四座坟墓，顺序不限': 'Collect the echoes · four graves, any order',
    '图书馆 · 按序进行': 'The Library · in order',
    '备注': 'Notes',

    # ── 物品名标记（"item" 形态；译文 = 官方英文物品名，必须含于所在句译文）──
    '阿拉希的回响': 'Arathi Echo',
    '塞拉摩的回响': 'Theramore Echo',
    '沼泽的回响': 'Swamp Echo',
    '墓地的回响': 'Graveyard Echo',
    '血色旗帜': 'Scarlet Banner',

    # ── 收集回响 · 阿拉希 ──
    '阿拉希高地 62.2,54.5 格沙克农场北侧，谷仓正后方的坟墓之间，点击坟墓拾取「阿拉希的回响」':
        'Arathi Highlands 62.2,54.5 north of Go\'Shek Farm, among the graves right behind '
        'the barn; click the grave to loot the "Arathi Echo"',
    '阿拉希高地 62.2,54.5': 'Arathi Highlands 62.2,54.5',

    # ── 收集回响 · 尘泥沼泽 ──
    '尘泥沼泽 63.7,42.4 塞拉摩北边路旁的小墓地（上岛大桥前）；联盟城镇、部落小心卫兵，点击坟墓拾取「塞拉摩的回响」':
        'Dustwallow Marsh 63.7,42.4 the small graveyard by the road north of Theramore '
        '(before the isle bridge); Alliance town, Horde mind the guards — click the grave '
        'to loot the "Theramore Echo"',
    '尘泥沼泽 63.7,42.4': 'Dustwallow Marsh 63.7,42.4',

    # ── 收集回响 · 悲伤沼泽 ──
    '悲伤沼泽 16.8,53.8 断矛路口：刻着圆圈的小木桩紧贴树干，和树皮融为一体，绕树一圈；旁边有蜘蛛，点击木桩拾取「沼泽的回响」':
        'Swamp of Sorrows 16.8,53.8 Splinterspear Junction: the small wooden stick marked '
        'with a circle sits against a tree trunk, blended into the bark — walk round the tree; '
        'a spider stands next to it; click the stick to loot the "Swamp Echo"',
    '悲伤沼泽 16.8,53.8': 'Swamp of Sorrows 16.8,53.8',

    # ── 收集回响 · SM 墓地（无坐标 → 只开图）──
    '血色修道院墓地走到底：左后角「遗忘回廊」里枯树靠着陵墓砖墙，刻人字纹的坟墓是唯一可点击的，点击拾取「墓地的回响」':
        'In the Scarlet Monastery Graveyard go to the far end: in the Forlorn Cloister at the '
        'back left corner a dead tree leans on the mausoleum\'s brick wall — the grave carved '
        'with chevrons is the only clickable one; click it to loot the "Graveyard Echo"',
    '血色修道院墓地': 'the Scarlet Monastery Graveyard',

    # ── 图书馆 · 进馆（无坐标 → 只开图）──
    '修道院图书馆：猎手回廊击败驯犬者洛克希，朝奥法师杜安方向前进，过了常放宝箱的凹室右转进「珍宝陈列室」':
        'Scarlet Monastery Library: kill Houndmaster Loksey in the Huntsman\'s Cloister, '
        'head for Arcanist Doan, then turn right past the alcove that often holds a chest '
        'to enter the "Gallery of Treasures"',
    '修道院图书馆': 'Scarlet Monastery Library',

    # ── 图书馆 · 半身像引导行 ──
    '站到半身像正前方 5 码内，增益会报出它的身份（悼言）；从进来那端（驯犬者洛克希侧）开始数，按下面顺序使用回响，顺序错了要重置副本':
        'Stand right in front of a bust (within 5 yards) and a buff names it (an Elegy); '
        'count the busts from the end you enter — the Houndmaster Loksey side — and use the '
        'echoes in the order below (a wrong order resets the instance)',

    # ── 图书馆 · 半身像 4 行（①②③④ = 使用序；括注 = 从入口数的位置序 + 增益名）──
    '战士像 ← 沼泽的回响（进来后第 1 座，增益「战士的悼言」）':
        'Warrior bust ← Swamp Echo (1st from the entrance; the buff is "Elegy of the Warrior")',
    '法师像 ← 阿拉希的回响（进来后第 3 座，增益「法师的悼言」）':
        'Mage bust ← Arathi Echo (3rd from the entrance; the buff is "Elegy of the Mage")',
    '圣骑像 ← 塞拉摩的回响（进来后第 4 座，增益「圣骑士的悼言」）':
        'Paladin bust ← Theramore Echo (4th from the entrance; the buff is "Elegy of the Paladin")',
    '牧师像 ← 墓地的回响（进来后第 2 座，增益「牧师的悼言」）':
        'Priest bust ← Graveyard Echo (2nd from the entrance; the buff is "Elegy of the Priest")',

    # ── 图书馆 · 拾取 ──
    '四座半身像亮起后，血色旗帜立在陈列室中央，点击拾取；全队只出一面，先商量好给谁':
        'Once all four busts light up the Scarlet Banner stands in the middle of the gallery '
        '— click it to loot; only one player per group gets it, so agree first on who takes it',

    # ── 备注 · 档案管理员彩蛋（拆两短句）──
    '顺序由来：半身像纪念四位档案管理员（Blake Godwyn、Primwell Skye、Janet Kaitway、William Powell），排序就是他们效力修道院的先后':
        'Why this order: the busts honour four archivists of the Monastery (Blake Godwyn, '
        'Primwell Skye, Janet Kaitway and William Powell), arranged by their years of service',
    '每个回响都来自其中一人丧命之地':
        'Each echo comes from the place where one of them died',

    # ── 备注 · 使用规则（拆两短句）──
    '使用需附近有营火、户外且脱离战斗：读条 10 秒、立起 15 分钟、1 小时冷却':
        'Using it requires a campfire nearby, outdoors and out of combat: 10 sec to raise, '
        'stands for 15 min, 1 hour cooldown',
    '纯装饰无属性加成，占用营火位并触发营地物品共冷':
        'Pure decoration with no stat bonus; it takes a campfire slot and starts the '
        'cooldown shared by all camp objects',
}
