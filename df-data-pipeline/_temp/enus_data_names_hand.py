# -*- coding: utf-8 -*-
"""人工拍板/覆盖层（enus_fetch 系列解决不了的键，2026-09-25）。

语义：
- 前四条是永恒服定制 NPC（wowhead 主站查不到），按英文直译/官方对应名；
- 其余是 title 路由误映射成任务名的真 NPC 名，此处覆盖回官方 NPC 名；
- 「通缉」是悬停布告的 giver 显示名，无唯一官方任务名。
本表优先级最高（gen_enus_data.py 最后并入 EXACT）。
"""

HAND = {
    # 永恒服定制 NPC（wowhead 404）
    '斯普莱特': 'Sprite Jumpsprocket',          # 暴风城 11026
    '贾斯伯·菲尔': 'Jasper Fel',                # 暴风城 1325
    '未完成的憎恶': 'Unfinished Abomination',   # 通灵学院 97290
    '孤儿监护员奈丁加尔': 'Orphan Matron Nightingale',  # 暴风城 14450
    # title 路由误映射 → 真官方 NPC 名
    '哨兵塞尔瑞德': 'Argent Guard Thaelrid',    # 黑暗深渊 4787
    '法拉尼尔': 'Master Apothecary Faranell',   # 幽暗城 2216
    '科劳莫特·钢尺': 'Klockmort Spannerspan',   # 铁炉堡 6169
    '高图斯': 'Warlord Goretooth',              # 荒芜之地 9077
    '麦克斯韦尔': 'Marshal Maxwell',
    '德莉娜': 'Deliana',                        # 数据侧简写，即 16013
    # 悬赏布告
    '通缉': 'WANTED',
    # ==== 2026-10-08 · 达拉然城 7 条任务补录 ====
    '高阶巫师安多玛斯': 'High Sorcerer Andromath',     # 暴风城 5694
    '莎拉米尔': 'Shylamiir',                           # 暴风城 5502
    '梅里萨拉': 'Melisara',                            # 塔伦米尔 2278
    '马丁·费尔本': 'Doctor Martin Felben',             # 幽暗城 11044
    '大法师沃迪恩·伍德格莱尔': 'Magus Wordeen Voidglare',  # 塔伦米尔 2410
    '雷克西·铜钳': 'Rexxie Copperclutch',              # 达拉然下水道入口（Forever 定制 NPC，wowhead 未收录 ID，名字自译）
    '使者雅克': 'Emissary Jacques',                    # 南海镇 247264（Forever 定制 NPC，wowhead 无中文名，名字自译）
    '大法师塞林德拉': 'Archmage Celindra',             # 紫罗兰城堡（Forever 定制 NPC，名字自译）
    '令人不安的请求': 'An Alarming Request',           # q92432（wowhead 无中文名，自译）
    '血染的街道': 'Blood in the Streets',              # q92434（wowhead 无中文名，自译）
    '肯瑞托': 'Kirin Tor',                             # 声望阵营 2740（达拉然城任务收获字段）
    # giverLoc 半翻残余
    '清洁区': 'Clean Zone',
    # ==== 2026-09-25 晚 · fetch8~19 ID 级核实补录（wowhead quest/npc/object/item 标题） ====
    # 官方任务名（按数据 qid 对齐）
    '菌类孢子': 'Serpentbloom',                            # q962
    '荒芜之地的材料': 'Uldaman Reagent Run',               # q17（前置 2500 = Badlands Reagent Run，顺序吻合）
    '搜寻项链': 'Necklace Recovery, Take 2',              # q2284
    '搜寻项链，再来一次': 'Translating the Journal',       # q2318
    '格杀勿论：黑铁矮人': 'KILL ON SIGHT: High Ranking Dark Iron Officials',  # q4082
    '破碎的陷阱': 'A Broken Trap',                        # q1193
    # giver 物件/显示名
    '诺甘农圆盘': 'The Discs of Norgannon',               # object 131474
    '人类的残骸': 'Human Remains',                        # LBRS q5103 起始骸骨
    '健康的龙鳞': 'Healthy Dragon Scale',                 # q5582
    '弄皱的地图': 'Crumpled Map',                         # q720 起始物品（EN 页 grep 实证）
    '残破的矮人骸骨': 'Battered Dwarf Remains',           # q739 Murdaloc 链前步显示
    '超级清洁器5200型': 'Super Cleaner 5200',             # 诺莫瑞根
    # NPC 官方名
    '比格维兹': 'Bilgewhizzle',                           # npc 7407 首席工程师
    '阿什拉姆·瓦罗菲斯特': 'Ashlam Valorfist',            # npc 10838（西瘟冰风岗，数据侧去「指挥官」）
    '塞娜尼·雷心': 'Senani Thunderheart',                 # npc 12696（wowhead cn 检索实证）
    '罗克图斯·暗契': 'Lokhtos Darkbargainer',             # 瑟银兄弟会军需官（BRD q7604）
    '芬克·恩霍尔': 'Finkle Einhorn',                      # LBRS 兽人厨房
    '维埃兰': 'Vaelan',                                   # npc10299 伪装名 Acride；任务链 EN 页通称 Vaelan(20次) — 从链名
    '黑衣威利': 'Wiley the Black',
    '马迪亚斯·肖尔': 'Mathias Shaw',
    '迪菲亚叛徒': 'The Defias Traitor',
    '巴隆斯·阿历克斯顿': 'Baros Alexston',
    '史学家卡尼克': 'Historian Karnik',
    '莫苏尔': "Mor'zul",                                  # 莫苏尔·召血者 简称（数据侧去姓）
    '埃提耶什，被玷污的传说之杖': 'Atiesh, Greatstaff of the Guardian',  # q9257 无限服专属，wowhead 404
    # giverLoc 残余
    '下层黑石塔': 'Lower Blackrock Spire',
    '上层黑石塔': 'Upper Blackrock Spire',
    '厄运之槌 北': 'Dire Maul: North',
    '黑石山 副本入口地图中的[D]': 'Blackrock Mountain - dungeon entrance map [D]',
    # ==== 2026-09-29 · 洛丹伦废墟：按 NPC ID 反查 wowhead 中文名后的重映射 ====
    # 原表键是英文名直译，已按 ID 对齐客户端中文名；右侧英文取 wowhead 英文页
    '塔比莎·织心': 'Tabitha Heartweaver',          # 银松森林 250686（原「塔比莎·织心者」）
    '莫宾·圣光之灾': 'Morbin Lightbane',           # 幽暗城 266484（原「莫尔宾·光灾」）
    '亡灵卫兵克里斯托弗': 'Deathguard Kristof',     # 布瑞尔 251001（原「死亡守卫克里斯托夫」）
    '图曼上尉': 'Captain Truman',                  # 副本入口 265701（新增起始 NPC）
    # ==== 2026-10-07 · fc 全量核查校准 ====
    '法德林·安威玛尔': 'Faldrim Anvilmar',         # 领主大厅 261306（原「法尔德里姆·安威玛尔」自译名，fc/ForG/BIS 共识名）
    '杜根·挽锤': 'Durgen Dirgehammer',             # 领主大厅 261319（原「杜尔根·挽歌之锤」自译名，同上）
    '大法师莫德拉的影像': 'Image of Archmage Modera',  # 达拉然城 92457 起始 NPC=269127（wowhead 2026-10-07 实锤，EN 名无官方中文）
    '马祖空': "Mazu'kon",                          # 沉没之城 96774 起始 NPC=264074（wowhead 2026-10-07 实锤，Forever 定制 NPC 无官方中文）
}
