# -*- coding: utf-8 -*-
"""探索页 · 第 4 步：生成 Core/Data/Data_Explore.lua。

输入：_fc/data/explore_resolved.json（explore_parse.py + explore_resolve.py 的产物）
输出：Core/Data/Data_Explore.lua（幂等：重跑字节不变）

口径：
- 书名 / 图标 / 品质 / 区域名一律不落盘，只存 itemID + AreaTable ID，
  显示时由客户端给中文（GetItemInfo / C_Map.GetAreaInfo）—— 与专业页同一条口径。
- 「位置细节」是攻略文案，客户端查不到 → 人工翻成中文，写在本脚本的 NOTE_ZH
  （键 = 书的英文名）。漏登记时回落英文原文并打警告。
- 表结构：ns.ExploreBooks[i] = { itemID, areaID, x, y, 细节, side, alt }
  side = "A"|"H"|nil（阵营限定）；alt = { {areaID,x,y,细节}, ... }（同名书多位置）。
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '_fc', 'data')
DF = os.path.dirname(HERE)
DST = os.path.join(DF, 'Core', 'Data', 'Data_Explore.lua')

SRC = os.path.join(DATA, 'explore_resolved.json')

# ── 位置细节 · 人工中文（键 = 书的英文名，与指南/游戏物品名一致）
#    2026-09-25 用户定：细节文案不出现英文物件注（Library Book / Scrolls / Manual
#    等括注一律不显示），只留中文位置描述。──
NOTE_ZH = {
    "Archmage Theocritus's Research Journal":
        '阿祖拉之塔半途楼梯口的桌上（不在顶层）',
    'Archmage Antonidas: The Unabridged Autobiography':
        '探险者大厅中央的圆桌上',
    "The Lessons of Ta'zo":
        "精神谷塔佐石壁画上，旅店招牌旁的大石板",
    "The Apothecary's Metaphysical Primer":
        '布瑞尔炼金店的货架上，药剂师旁边',
    'Ataeric: On Arcane Curiosities':
        '银松森林墓穴内的桌上，塞巴斯蒂安·米洛奇旁边（不在影牙城堡：阿鲁高身后那本是无关的黑色圣典）',
    'The Dalaran Digest, Vol. 23':
        '安伯米尔主厅东北角的书架上',
    "Nar'thalas Almanac, Vol. 74":
        '玛塞斯特拉废墟内，下楼梯后第三层平台上的卷轴堆',
    'Rumi of Gnomeregan: The Collected Works':
        '塞尔萨玛旅店二楼桌上（部落角色可能拿不到这本，建议改拿哨兵岭那本）；哨兵岭旅店 52.7,53.8 另有一本，同一本书只算一次，拿过一处另一处失效',
    'Runes of the Sorcerer-Kings':
        '莫格罗什要塞东北角最里面的食人魔洞穴：进门抱左，第一个左转房间，3 个食人魔法师身后右侧',
    'Bewitchments and Glamours':
        '月溪镇入口左侧第一间屋内的书架上',
    'Arcanic Systems Manual':
        '淤泥沼泽钻井平台顶，控制室的椅子上',
    'Baxtan: On Destructive Magics':
        '棘齿城工程楼内，加兹鲁维旁边的箱子上',
    'Secrets of the Dreamers':
        '甜水绿洲（46.0,36.5）进洞，靠哀嚎洞穴副本入口的迷雾洞穴里（洞穴地图 52.8,54.7；书在副本外，不用进本）',
    'Fury of the Land':
        '恐怖图腾岗哨帐篷内的木桶上',
    'Crimes Against Anatomy':
        '从渡鸦岭墓穴进入的黎明森林地下墓穴，尽头木桌上',
    'Goaz Scrolls':
        '维尔加挖掘场最低层的陶瓮里',
    'Geomancy: The Stone-Cold Truth':
        '黑云峰顶最大的棚屋里（上山路径入口 31.0,36.0）',
    'Defensive Magics 101':
        '绞刑场食人魔要塞第一座塔内的书本（斯通布拉德或塔伦米尔侧上山）',
    'A Web of Lies: Debunking Myths and Legends':
        '枯木村小屋旁的帐篷外，卷轴堆上',
    'Demons and You':
        '雷斧堡垒大屋内靠墙的长凳上',
    'Basilisks: Should Petrification be Feared?':
        '水晶矿洞入口右侧的木平台上，不用进矿坑',
    'Mummies: A Guide to the Unsavory Undead':
        '孤丘南侧的墓穴里（路径起点 56.0, 45.0）',
    'RwlRwlRwlRwl!':
        '女巫岭鱼人营地东缘的地上（湿透的书）',
    "A Ludite's Guide to Caring for Your Demonic Pet":
        '法尔圣所的笼子里（隔着笼子直接点击取书，无需钥匙；若点不到，杀周围的失落者拿锈蚀的笼子钥匙再开）',
    'Sanguine Sorcery':
        '沉没的神庙顶层，进团队副本入口前的房间里（站上神庙后自身坐标约 56.3,76.2）',
    'The Liminal and the Arcane':
        '本服已换位置，尚未有人找到新位置：旧位（50.6,15.7 翡翠湖以南湖畔）已失效',
    'Legends of the Tidesages':
        '海盗营地中间房子的书架上',
    'Venomous Journeys':
        '沙德拉·阿洛尔，最东侧神庙旁的棕色墙后',
    'A Mind of Metal':
        '帐篷下的桌上',
    "Conjurer's Codex":
        '诅咒之地目标点地面上',
    'Everyday Etiquette':
        '赫达瑞营地小屋旁的箱子上',
    'Northern Kalimdor - A Comprehensive Guide':
        '木喉要塞内，声望商人上方桥边',
    'Magma or Lava?':
        '黑石深渊入口外侧的台地上（不要进副本）',
    'Necromancy 101':
        '通灵学院城堡顶的桌上（无需进本；旧坐标 52.7,26.3 有误，2026-09-29 更正为 69.4,72.8）',
    'Undead Potatoes':
        '费尔斯通农场，农舍二楼屋内',
    'Stonewrought Design':
        '黑石山中央宝库的大平台上（无需进本；旧位铁穹堡祭坛已移位）',
    'A Study of the Light':
        '圣光之愿礼拜堂内后排左侧（本服从 81.7,57.8 旧位移到这里）',
    'Scourge: Undead Menace or Misunderstood?':
        '去斯坦索姆入口的桥前，右侧桌上（本服从探索赛季旧位 31.3,21.0 移到这里；旁边有两个固定的墓穴行者，单人取书要小心）',
    'The Knight and the Lady':
        '东瘟疫之地（本服从中央小湖边的旧位 54.5,50.8 移到这里）',
    'Ka-Boom!':
        '永望镇炼金屋内，炼金供应商身后的货架上',
}
NOTE_ZH_ALT = {
    'Rumi of Gnomeregan: The Collected Works':
        '哨兵岭旅店老板身后的桌上（与塞尔萨玛那本同一本书，二选一）',
}

# ── 推荐清单（2026-09-26 核对口径）：两站（foreverchanges + zockify）都确认可拾取的
#    19 种书 = 界面名称右侧打「推荐」标；其余 21 种打「待确认」标（UNVER）。
#    ★ 阿拉塔瑞克 210177：2026-09-26 因本服换位归入待确认；2026-10-13 站点更新已
#      确认可在原位置拾取 → 归入已找到（不打待确认，暂不打推荐）。
SITE_REC = {
    "Archmage Theocritus's Research Journal",
    'Archmage Antonidas: The Unabridged Autobiography',
    "The Lessons of Ta'zo",
    "The Apothecary's Metaphysical Primer",
    'The Dalaran Digest, Vol. 23',
    "Nar'thalas Almanac, Vol. 74",
    'Rumi of Gnomeregan: The Collected Works',
    'Runes of the Sorcerer-Kings',
    'Bewitchments and Glamours',
    'Arcanic Systems Manual',
    'Baxtan: On Destructive Magics',
    'Secrets of the Dreamers',
    'Fury of the Land',
    'Crimes Against Anatomy',
    'Goaz Scrolls',
    'Geomancy: The Stone-Cold Truth',
    'Defensive Magics 101',
    'Basilisks: Should Petrification be Feared?',
    'RwlRwlRwlRwl!',
}

# ── 站点实收清单（2026-09-29 三方核对口径）：推荐 19 种 + 双站新确认的 19 种
#    = 38 种有确切位置；待确认只剩 2 本（阿拉塔瑞克 / The Liminal and the Arcane，
#    两站都标「本服换位后至今无人找到」）。保留变量名兼容下方生成逻辑。
SITE_FOUND = SITE_REC | {
    'Ataeric: On Arcane Curiosities',
    'A Web of Lies: Debunking Myths and Legends',
    'Demons and You',
    'Mummies: A Guide to the Unsavory Undead',
    "A Ludite's Guide to Caring for Your Demonic Pet",
    'Sanguine Sorcery',
    'Legends of the Tidesages',
    'Everyday Etiquette',
    'Stonewrought Design',
    'Venomous Journeys',
    'A Mind of Metal',
    "Conjurer's Codex",
    'Undead Potatoes',
    'Magma or Lava?',
    'Northern Kalimdor - A Comprehensive Guide',
    'A Study of the Light',
    'Ka-Boom!',
    'The Knight and the Lady',
    'Scourge: Undead Menace or Misunderstood?',
    'Necromancy 101',
}

# ── 地图等级区间（2026-09-25 用户定：行名右侧标「所在地图」等级区间，如 5~10级）。
#    14 个已核实 = foreverchanges 站点区块头（2026-09-24 更新）；主城标「主城」；
#    其余按经典练级通行区间（阿拉希 30-40 / 荒芜 35-45 / 悲伤 35-45 / 凄凉 30-40 /
#    菲拉斯·塔纳利斯·辛特兰 40-50 / 灼热 43-50 / 诅咒·艾萨拉 45-55 / 费伍德 48-55 /
#    黑石山 50-60 / 西瘟 51-58 / 东瘟 53-60 / 冬泉 55-60）。
ZONE_LV = {
    12: '5~10', 40: '9~18', 10: '19~30', 38: '10~18', 11: '20~30',
    130: '10~20', 85: '5~12', 148: '11~19', 17: '10~25', 33: '30~44',
    400: '24~35', 36: '27~39', 15: '36~43', 406: '15~25',
    45: '30~40', 405: '30~40', 3: '35~45', 8: '35~45',
    357: '40~50', 440: '40~50', 47: '40~50', 51: '43~50',
    4: '45~55', 16: '45~55', 361: '48~55', 25: '50~60',
    28: '51~58', 139: '53~60', 618: '55~60',
    # 主城键 = AreaTable 区域 ID（铁炉堡 1537 / 奥格瑞玛 1637）。
    # ⚠️ 1455/1454 是这俩主城的 **uiMap ID**，只许在 AREA_MAP（ExploreUI）里做映射，
    #    勿混进本表的 areaID 键空间（2026-09-25 实机：错键导致行尾露「1455」无地图名）。
    1537: '主城', 1637: '主城',
}

# ── 坐标/区域修正（2026-09-25 站点核实口径）：站点位置经玩家确认（2026-09-22）。
SITE_XY = {
    "Archmage Theocritus's Research Journal": (65.4, 70.1),
    'Archmage Antonidas: The Unabridged Autobiography': (75.7, 10.5),
    "The Lessons of Ta'zo": (38.7, 78.4),
    "The Apothecary's Metaphysical Primer": (59.4, 52.3),
    'The Dalaran Digest, Vol. 23': (63.5, 63.1),
    "Nar'thalas Almanac, Vol. 74": (59.6, 22.2),
    'Rumi of Gnomeregan: The Collected Works': (35.6, 48.9),
    'Runes of the Sorcerer-Kings': (77.4, 14.0),
    'Bewitchments and Glamours': (45.4, 70.4),
    'Arcanic Systems Manual': (56.3, 8.8),
    'Baxtan: On Destructive Magics': (62.7, 36.3),
    'Secrets of the Dreamers': (52.8, 54.7),
    'Fury of the Land': (74.4, 85.7),
    'Crimes Against Anatomy': (16.6, 28.5),
    'Goaz Scrolls': (33.6, 47.9),
    'Geomancy: The Stone-Cold Truth': (34.4, 40.1),
    'Defensive Magics 101': (48.4, 57.6),
    'Basilisks: Should Petrification be Feared?': (41.4, 50.9),
    'RwlRwlRwlRwl!': (57.2, 20.8),
    # ── 2026-09-26 二次核对（foreverchanges + zockify 交叉）：本服已移位 / 坐标精修 ──
    'The Knight and the Lady': (47.3, 42.3),
    'A Study of the Light': (71.8, 48.2),
    'Stonewrought Design': (48.6, 64.2),
    'Magma or Lava?': (48.4, 63.6),
    'Undead Potatoes': (38.3, 54.6),
    'Everyday Etiquette': (20.7, 62.0),
    'A Mind of Metal': (37.8, 49.6),
    'Legends of the Tidesages': (72.6, 47.8),
    'Ka-Boom!': (60.7, 37.7),
    # ── 2026-09-29 三方核对：两处坐标修正（zockify 标注本服移位 / 旧坐标有误）──
    'Scourge: Undead Menace or Misunderstood?': (26.5, 15.0),
    'Necromancy 101': (69.4, 72.8),
    'Venomous Journeys': (36.0, 72.7),
    'Sanguine Sorcery': (70.0, 51.0),
    "Conjurer's Codex": (55.3, 32.2),
    'Mummies: A Guide to the Unsavory Undead': (57.0, 39.0),
    "A Ludite's Guide to Caring for Your Demonic Pet": (61.0, 22.0),
    'Demons and You': (55.0, 28.0),
    'Northern Kalimdor - A Comprehensive Guide': (65.2, 3.2),
    'A Web of Lies: Debunking Myths and Legends': (73.0, 65.0),
}
# 区域核实：铁炉堡探险者大厅（站点区块=铁炉堡）。2026-09-25 更正：解析原值 1537 就是
# 铁炉堡的 AreaTable 区域 ID（暴风城=1519，旧注释「1537=暴风城」系笔误）；此前改写成
# 的 1455 是 uiMap ID，混入 areaID 字段导致区域名/航点双失效。落库一律 1537。
SITE_AREA = {
    'Archmage Antonidas: The Unabridged Autobiography': 1537,
    'A Web of Lies: Debunking Myths and Legends': 45,
}

# ── 路线书（2026-09-29 用户定）：一页要先后经过两个点的书，右上角画「区名 x,y → x,y」
#    坐标链，每段可点击落图。键 = 书的英文名，值 = 按先后顺序的步骤链
#    [(areaID, x, y), ...]（末步 = 书的实际位置，与主 x/y 一致）。
SITE_ROUTE = {
    'Secrets of the Dreamers': [(17, 46.0, 36.5), (17, 52.8, 54.7)],
    'Geomancy: The Stone-Cold Truth': [(400, 31.0, 36.0), (400, 34.4, 40.1)],
    'Mummies: A Guide to the Unsavory Undead': [(3, 56.0, 45.0), (3, 57.0, 39.0)],
}

# ── 上交任务 ID（键 = 书的英文名；来源 MageBookTracker 插件硬编码表，2026-09-24 交叉验证）──
# 用途：自动识别「已找到」（C_QuestLog.IsQuestFlaggedCompleted）。只存 ID，符合落盘纪律。
# ⚠️ 无限服与 SoD 共用同一批物品 ID（203755+），任务 ID 按同源口径沿用；
#   客户端没有 C_QuestLog 时界面侧静默跳过（ExploreUI.ScanAuto 有守卫）。
QUEST_MAP = {
    "Archmage Theocritus's Research Journal": 79092,
    'Archmage Antonidas: The Unabridged Autobiography': 79091,
    'Rumi of Gnomeregan: The Collected Works': 79093,
    "The Lessons of Ta'zo": 79094,
    "The Apothecary's Metaphysical Primer": 79095,
    'Ataeric: On Arcane Curiosities': 79096,
    'Arcanic Systems Manual': 78145,
    'Fury of the Land': 78149,
    'Secrets of the Dreamers': 78143,
    'The Dalaran Digest, Vol. 23': 78127,
    'Baxtan: On Destructive Magics': 79097,
    'Bewitchments and Glamours': 78142,
    'Goaz Scrolls': 78146,
    'Runes of the Sorcerer-Kings': 78148,
    "Nar'thalas Almanac, Vol. 74": 78124,
    'Crimes Against Anatomy': 78147,
    'Defensive Magics 101': 79948,
    'A Web of Lies: Debunking Myths and Legends': 79949,
    'Mummies: A Guide to the Unsavory Undead': 79951,
    'Basilisks: Should Petrification be Feared?': 79535,
    "A Ludite's Guide to Caring for Your Demonic Pet": 79953,
    'Demons and You': 79950,
    'RwlRwlRwlRwl!': 79952,
    'Geomancy: The Stone-Cold Truth': 79947,
    'A Mind of Metal': 81955,
    'Venomous Journeys': 81954,
    'Stonewrought Design': 81953,
    "Conjurer's Codex": 81956,
    'Sanguine Sorcery': 81947,
    'The Liminal and the Arcane': 81951,
    'Legends of the Tidesages': 81949,
    'Everyday Etiquette': 81952,
    'Undead Potatoes': 84395,
    'Necromancy 101': 84402,
    'Magma or Lava?': 84396,
    'The Knight and the Lady': 84400,
    'Scourge: Undead Menace or Misunderstood?': 84401,
    'A Study of the Light': 84398,
    'Northern Kalimdor - A Comprehensive Guide': 84397,
    'Ka-Boom!': 84399,
}

# 上交任务组（图书馆之友任务链按等级分 4 组：1 / 35 / 45 / 60，键 = 书英文名）。
# 来源为游戏内事实分组；路线规划按组接力（低组在前）。阿拉塔瑞克归组1、利姆纳尔归组45
# （两者未在分组页出现，按区域等级与物品 ID 序列归组，游戏内待核）。
BOOK_SET = {
    "Archmage Theocritus's Research Journal": 1,
    'Archmage Antonidas: The Unabridged Autobiography': 1,
    'Bewitchments and Glamours': 1,
    'Rumi of Gnomeregan: The Collected Works': 1,
    'Crimes Against Anatomy': 1,
    'Runes of the Sorcerer-Kings': 1,
    'Goaz Scrolls': 1,
    'The Dalaran Digest, Vol. 23': 1,
    "The Apothecary's Metaphysical Primer": 1,
    "Nar'thalas Almanac, Vol. 74": 1,
    'Arcanic Systems Manual': 1,
    'Baxtan: On Destructive Magics': 1,
    'Secrets of the Dreamers': 1,
    'Fury of the Land': 1,
    "The Lessons of Ta'zo": 1,
    'Ataeric: On Arcane Curiosities': 1,
    'Basilisks: Should Petrification be Feared?': 35,
    'Geomancy: The Stone-Cold Truth': 35,
    'Defensive Magics 101': 35,
    'RwlRwlRwlRwl!': 35,
    'A Web of Lies: Debunking Myths and Legends': 35,
    'Demons and You': 35,
    'Mummies: A Guide to the Unsavory Undead': 35,
    "A Ludite's Guide to Caring for Your Demonic Pet": 35,
    'Sanguine Sorcery': 45,
    'Legends of the Tidesages': 45,
    'Everyday Etiquette': 45,
    'Stonewrought Design': 45,
    'Venomous Journeys': 45,
    'A Mind of Metal': 45,
    "Conjurer's Codex": 45,
    'The Liminal and the Arcane': 45,
    'Magma or Lava?': 60,
    'Northern Kalimdor - A Comprehensive Guide': 60,
    'Undead Potatoes': 60,
    'The Knight and the Lady': 60,
    'Scourge: Undead Menace or Misunderstood?': 60,
    'A Study of the Light': 60,
    'Ka-Boom!': 60,
    'Necromancy 101': 60,
}

HEAD = '''local _, ns = ...
ns.ExploreBooks = {'''

FOOT = '''}

ns.ExploreBookQuests = {
%s
}

ns.ExploreBookSet = {
%s
}

ns.ExploreZoneLv = {
%s
}

-- 推荐清单（已核实 19 种 + 阿拉塔瑞克 1 种 = 20 种）：键 = itemID。UI 打「推荐」标。
ns.ExploreRecIDs = {
%s
}

-- 待确认清单（获取位置未能核实）：键 = itemID。
-- 已核实的不管它；未核实的 → 名称右侧「待确认」三字。
ns.ExploreUnverIDs = {
%s
}

ns.ExploreBookMeta = {
    updated = "2026-10-13",
    quest10 = "图书馆之友",
    quest20 = "图书馆的挚友",
    quest25 = "图书馆的挚友",
}

ns.ExploreBookRewards = {
    [1] = { at = 10, req = 1, questID = 78150, quest = "图书馆之友",
            items = { A = 277203, H = 277204 } },
    [2] = { at = 20, req = 20, questID = 79536, quest = "图书馆的挚友",
            items = { A = 281634, H = 281635 } },
    [3] = { at = 25, req = 30, questID = 82208, quest = "图书馆的挚友",
            choices = { 277254, 277258, 277260 } },
}

-- 奖励页「如何获得奖励」说明卡。
-- 口径：不出现英文人名（交书 NPC 无中文名 → 只给主城区域 + 坐标）；坐标用主城地图。
ns.ExploreHowTo = {
    title = "如何获得奖励",
    intro = "这条任务线所有职业都能接，没有等级要求。身上要先带着一本书，图书馆员才会给你任务；三档奖励按累计本数解锁，交满 25 本即可全部领完。",
    detail = "有个重要细节：每本书都有独立的任务，找到哪本就可以交哪本，不用攒够 10 本。",
    steps = {
        { t = "搜索书籍", d = "书不是怪物掉落：每本都从固定的物件拾取——书架、卷轴堆、桌上的书等。" },
        { t = "交给你的图书馆员",
          d = "每交一本可得一个理解魔符。联盟：暴风城·法师区 37.6, 80.8；部落：幽暗城·魔法区 73.4, 33.0。" },
        { t = "在 10 本、20 本和 25 本时领奖",
          d = "交出第十本解锁项链奖励，第二十本解锁戒指奖励，第二十五本解锁三选一奖励（求真者之弓 / 阐明徽记 / 研究员的小夜灯 任选其一）。三档任务的接取等级依次为 1 级、20 级、30 级。" },
    },
}

-- 法师专属奖励：首次交书后解锁专业「研究」，技能「学习」6 级起可施放、施法 6 秒、
--   消耗轻羽毛制作一捆卷轴，1 小时冷却，需在图书馆内使用。prof / ability 保留英文
--   原值（守门断言按此校验）。当前测试服重登后该专业会消失（已知问题，修复中）。
ns.ExploreMageBonus = {
    prof = "Research",
    ability = "Study",
    reagent = 17056,
    title = "法师限定 · 研究",
    desc = {
        "首次交书后，法师额外学会新专业「研究」，并解锁技能「学习」。",
        "「学习」6 级起可施放：施法 6 秒，消耗轻羽毛，冷却 1 小时，产出「一捆卷轴」。",
        "需在合适的图书馆内使用；卷轴可开出次级烈焰注入、寒冰小刀注入等法师卷轴。",
        "注：当前测试服重登后该专业可能消失，官方修复中。",
    },
}
'''


def die(msg):
    sys.stderr.write('explore_gen: %s\n' % msg)
    sys.exit(1)


def lua_str(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def norm_key(s):
    """书名键归一化：站点排版引号/破折号 → 游戏内字符。"""
    s = (s or '').replace('\u2019', "'").replace('\u2018', "'")
    s = s.replace('\u2013', '-').replace('\u2014', '-')
    return re.sub(r'\s+', ' ', s).strip()


NOTE_ZH = {norm_key(k): v for k, v in NOTE_ZH.items()}
NOTE_ZH_ALT = {norm_key(k): v for k, v in NOTE_ZH_ALT.items()}


def main():
    books = json.load(open(SRC, encoding='utf-8'))
    if len(books) != 40:
        die('期望 40 本，拿到 %d 本 —— 先核对 explore_resolved.json' % len(books))

    lines = []
    warn = []
    quests = []
    sets = []
    rec_ids = []
    unver_ids = []
    for i, b in enumerate(books, 1):
        name = norm_key(b['name'])
        note = NOTE_ZH.get(name)
        if note is None:
            note = b['note']
            warn.append(name)
        qid = QUEST_MAP.get(name)
        if qid is None:
            die('书「%s」没有登记上交任务 ID（QUEST_MAP）' % name)
        bset = BOOK_SET.get(name)
        if bset is None:
            die('书「%s」没有登记任务组（BOOK_SET）' % name)
        # 站点核实覆盖（2026-09-25）：坐标 / 区域（经玩家确认的站点口径优先）
        if name in SITE_XY:
            b['x'], b['y'] = SITE_XY[name]
        if name in SITE_AREA:
            b['area_id'] = SITE_AREA[name]
        if name in SITE_REC:
            rec_ids.append(b['item_id'])
        elif name not in SITE_FOUND:
            unver_ids.append(b['item_id'])
        quests.append('    [%d] = %d,' % (b['item_id'], qid))
        sets.append('    [%d] = %d,' % (b['item_id'], bset))
        cells = [str(b['item_id']), str(b['area_id']),
                 '%.1f' % b['x'], '%.1f' % b['y'], lua_str(note)]
        if b.get('side'):
            cells.append(lua_str(b['side']))
        alt = b.get('alt') or []
        if alt:
            parts = []
            for a in alt:
                an = NOTE_ZH_ALT.get(name, a.get('note') or '')
                parts.append('{%s, %.1f, %.1f, %s}'
                             % (a['area_id'], a['x'], a['y'], lua_str(an)))
            while len(cells) < 6:
                cells.append('nil')
            cells.append('{ ' + ', '.join(parts) + ' }')
        route = SITE_ROUTE.get(name)
        if route:
            parts = ['{%d, %.1f, %.1f}' % (s[0], s[1], s[2]) for s in route]
            while len(cells) < 7:
                cells.append('nil')
            cells.append('{ ' + ', '.join(parts) + ' }')
        lines.append('    [%d] = { %s },' % (i, ', '.join(cells)))

    if warn:
        print('  [警告] 以下书的中文细节未登记，回落英文原文：%s' % '、'.join(warn))

    zone_lv_lines = []
    for aid in sorted(ZONE_LV):
        zone_lv_lines.append('    [%d] = %s,' % (aid, lua_str(ZONE_LV[aid])))
    rec_lines = []
    for iid in sorted(rec_ids):
        rec_lines.append('    [%d] = true,' % iid)
    unver_lines = []
    for iid in sorted(unver_ids):
        unver_lines.append('    [%d] = true,' % iid)

    body = HEAD + '\n'.join(lines) + '\n\n' + (FOOT % (
        '\n'.join(quests), '\n'.join(sets), '\n'.join(zone_lv_lines), '\n'.join(rec_lines),
        '\n'.join(unver_lines)))
    old = open(DST, 'rb').read().decode('utf-8') if os.path.exists(DST) else None
    with open(DST, 'w', encoding='utf-8', newline='\n') as f:
        f.write(body)
    print('写入 %s（%d 行，%d 字节）%s'
          % (os.path.relpath(DST, DF), body.count('\n'), len(body.encode('utf-8')),
             '（与上次一致）' if old == body else '（有变化）'))
    if old is not None and old != body:
        import difflib
        diff = [l for l in difflib.unified_diff(old.splitlines(), body.splitlines(), lineterm='')
                if l.startswith(('+', '-')) and not l.startswith(('+++', '---'))]
        print('  差异 %d 行' % len(diff))
    return 0


if __name__ == '__main__':
    sys.exit(main())
