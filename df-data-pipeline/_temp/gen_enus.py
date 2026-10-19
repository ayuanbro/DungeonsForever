# -*- coding: utf-8 -*-
"""生成 DungeonsForever/Locales/enUS.lua（界面层英文覆盖，2026-09-25）。

与 gen_zhtw.py 同纪律：enUS.lua 是生成物，禁手改。校对发现的错译回填本文件的
EN 表（或 EXACT 特例）后重跑。

结构：
- EN：键（简体文案）→ 英文全文，逐键人工级翻译，术语对齐暴雪客户端官方英文。
- 自动校验：格式符（%d/%s/%%）多重集必须与键一致；|cff…|r 颜色码必须原样保留；
  键遗漏 → 列出并退出非 0（宁可失败也不静默漏翻）。
- 「选一系」自对查约束：L["选一"] 的英文必须是 L["二选一"]/L["三选一"] 的子串
  （ExploreUI find(L["选一"]) 依赖），生成前自检。

用法：python gen_enus.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
CORE = os.path.join(DF, 'Core')
DST = os.path.join(DF, 'Locales', 'enUS.lua')

# ── 英文全表（键 = 简体文案；值 = 英文）─────────────────────────────────────
EN = {
    # ── 通用 UI ──
    '全部': 'All', '全部 %d': 'All %d', '其他': 'Other', '其他 %d': 'Other %d',
    '类型：': 'Type: ', 'BOSS：': 'Boss: ', '职业：': 'Class: ',
    '小怪': 'Trash',
    # ── 藏品页 / 宠物页（2026-10-07 并行会话遗留未登记，此处补齐）──
    '坐骑': 'Mounts', '宠物 · 共 %d 只': 'Pets · %d total', '当前 %d 只': 'Showing %d',
    '搜索宠物…': 'Search pets…', '查看获取详情 →': 'How to get →',
    '没有匹配的条目': 'No matching entries',
    # ── 声望页 ──
    '搜索阵营…': 'Search factions…', '筛选': 'Filter',
    '本阵营': 'My faction', '敌对阵营': 'Enemy factions',
    '中立': 'Neutral', '起始': 'Start', '起始声望': 'Starting reputation',
    '军需官位置': 'Quartermaster',
    '联盟首都': 'Alliance Capitals', '部落首都': 'Horde Capitals',
    '战场 · 联盟部队': 'Battlegrounds · Alliance Forces',
    '战场 · 部落军队': 'Battlegrounds · Horde Forces',
    '热砂集团': 'Steamwheedle Cartel', '其他势力': 'Other Factions',
    '专业专精': 'Profession Specializations',
    '仇恨': 'Hated', '敌对': 'Hostile', '冷淡': 'Unfriendly',
    # 2026-10-08 宠物难度新键（并行会话）+ 坐骑来源 NPC 点击行（本会话）
    '商人': 'Vendor', '扒窃': 'Pickpocket',
    '来源：': 'Source: ', '等 %d 处': '+%d more',
    '列表': 'List', '卡片': 'Card', '关闭': 'Close', '删除': 'Delete', '改名': 'Rename',
    '关于': 'About', '复制网址': 'Copy URL', '合计': 'Total', '容量': 'Capacity',
    '状态': 'Status', '状态：': 'Status: ', '等级': 'Level', '级': ' Lv',
    '无': 'None', '无数据': 'No data', '未收录': 'Not indexed', '未标注': 'Unmarked',
    '说明': 'Guide', '注释': 'Notes', '要点': 'Key points', '简介': 'Overview',
    '攻略': 'Guide', '副本须知': 'Things to know', '怎么进本': 'How to get there',
    'BOSS 打法': 'Boss strategies', '小怪应对': 'Trash mobs',
    '首领': 'Bosses', '‹ 全部首领': '‹ All bosses', '攻略待补充': 'Guide pending',
    # 地图页左上角「隐藏 boss」开关（两种文案等宽 ⇒ 按钮宽度切换不跳）
    '隐藏boss': 'Hide bosses', '显示boss': 'Show bosses',
    # 2026-10-04 开关改管全部钉点，改名「隐藏图钉」（两种文案等宽 ⇒ 按钮宽度切换不跳）
    '隐藏图钉': 'Hide pins', '显示图钉': 'Show pins',
    '隐藏首领': 'Hide bosses', '显示首领': 'Show bosses',
    '隐藏任务': 'Hide quests', '显示任务': 'Show quests',
    '图钉显示': 'Pins', '首领图钉': 'Boss pins', '任务图钉': 'Quest pins',
    '隐藏路线': 'Hide route', '显示路线': 'Show route',
    '全部显示': 'Show all', '全部隐藏': 'Hide all',
    '路线显示': 'Route',
    '彩虹渐变': 'Rainbow gradient', '落日渐变': 'Sunset gradient',
    '青柠渐变': 'Lime gradient', '蓝紫渐变': 'Blue-purple gradient',
    '极光渐变': 'Aurora gradient',
    '配色：%s': 'Palette: %s',
    '路线粗细：%s': 'Line: %s', '粗': 'Thick', '细': 'Thin',
    '点击查看任务详情': 'Click to open quest',
    '可接': 'Available', '前置': 'Pre-quest', '未解锁': 'Locked',
    '完成后解锁：%s': 'Unlocks: %s',
    '副本任务': 'Dungeon quest',
    '点击进入[无限副本手册]任务详情': 'Click to open [DungeonsForever] quest details',
    '5秒回蓝': 'Mana per 5 sec',
    '定位·治疗': 'Role · Healer', '定位·法系': 'Role · Caster',
    '定位·物理': 'Role · Physical', '定位·自动': 'Role · Auto',
    '定位：自动': 'Role: Auto',
    '法系输出': 'Caster DPS', '物理输出': 'Physical DPS',
    '自动探测': 'Auto-detect',
    '图钉设置': 'Pin settings',
    '图钉大小': 'Pin size',
    '显示范围': 'Show scope',
    '按等级能接的': 'Available at my level',
    '当前推荐副本': 'Recommended dungeons',
    '可进入的副本': 'Enterable dungeons',
    '任务难度灰色不显示': 'Hide grey-difficulty quests',
    '默认（自动探测）': 'Default (auto-detect)',
    '全部任务': 'All quests',
    '世界地图显示': 'Show on world map',
    '非亡灵': 'Not Forsaken',
    '主属性': 'Main attribute',
    '伤害': 'Damage',
    '几率': 'Chance',
    '命中时': 'On hit',
    '强度': 'Power',
    '抗性': 'Resistance',
    '触发': 'Trigger',
    '方案数量已达上限（最多 5 个）': 'Preset limit reached (max 5)',
    '武器伤害': 'Weapon damage',
    '默认': 'Default',
    '左键应用 · 右键菜单': 'Left-click to apply · Right-click for menu',
    '应用此方案': 'Apply this preset',
    '添加评分方案': 'Add scoring preset',
    '评分权重': 'Scoring weights',
    '请先填写方案名称': 'Enter a preset name first',
    '重命名方案': 'Rename preset',
    '默认只读，添加方案后可编辑': 'Read-only by default; add a preset to edit',
    '躲闪等级': 'Dodge rating',
    '招架等级': 'Parry rating',
    '格挡等级': 'Block rating',
    '防御技能': 'Defense skill',
    '韧性': 'Resilience',
    # 2026-10-14 任务钉三态 + 任务页「地图图钉」开关
    '地图图钉': 'Quest pins',
    '需先完成：%s': 'Requires: %s first',
    '完成本任务后解锁：%s': 'Completing this unlocks: %s',
    '生成 BiS 方案': 'Generate BiS plan', '过滤': 'Filter',
    # 载入闸门（2026-10-03 第五刀：顶部 3px 进度条 + 右下角状态丸 + /dfspeed 速度档位）
    '正在载入…': 'Loading…', '跳过': 'Skip',
    '载入速度': 'Loading speed', '当前': 'Current',
    '省电': 'Power saver', '标准': 'Standard', '激进': 'Aggressive',
    # 探索页 · 地图书钉 + 收集路线（ExploreMap.lua）
    '路线': 'Route', '重算': 'Recalc',
    '路线第%d站': 'Route step %d', '收集 %d/%d': 'Collected %d/%d',
    'Shift+点击打卡': 'Shift-click: mark as found',
    '路线完成': 'Route finished', '另一位置': 'alt spot',
    '剩 %d 站': '%d stops left',
    # 探索地图设置面板（2026-10-04 晚：追踪条齿轮入口）
    '探索地图设置': 'Explore map settings',
    '连接方式': 'Route linking', '就近串联': 'Nearest chain',
    '按区域分堆': 'Group by zone', '数据表顺序': 'Data order',
    '打卡后自动重算': 'Auto re-plan after check-in',
    '包含存疑书籍': 'Include unverified books',
    '开图自动亮路线': 'Auto route on map open',
    '图钉大小': 'Pin size', '图钉编号': 'Pin numbers', '显示连线': 'Show route line', '找书HUD': 'Book HUD',
    '到目标连线': 'Line to target',
    '连线粗细': 'Line width', '细': 'Thin', '中': 'Med', '粗': 'Thick',
    '追踪条': 'Tracker', '显示罗盘': 'Show compass',
    '锁定位置': 'Lock position', '界面缩放': 'HUD scale',
    '进度数据': 'Progress data', '下一站坐标': 'Next stop coords',
    '地图设置': 'Map Settings', '书籍显示': 'Book tracking',
    '手动选书': 'Manual pick', '自动跟随': 'Auto follow route',
    '点击图钉选择书籍': 'Click a map pin to pick a book',
    '点击追踪此书': 'Click to track this book', '暂无目标': 'No target yet',
    '复制坐标': 'Copy coords', '已复制': 'Copied',
    '%d 码': '%d yd', '其他大陆': 'Other continent',
    # /dfgate 自检与演示（进度条只在真有活时才亮 —— 好电脑上平时看不到）
    '进度条': 'Progress bar', '待建行': 'Rows pending', '行池': 'Row pool',
    '已还原。': 'Restored.',
    '先点开一个副本的掉落页，再运行这个命令。':
        'Open a dungeon\'s Loot page first, then run this command.',
    '演示：每帧只建 2 行，进度条会走完一遍。':
        'Demo: 2 rows per frame, so you can watch the bar fill.',
    # /dfprofgate 自检与演示（专业页大列表，同一根进度条）
    '先打开一个专业的配方页，再运行这个命令。':
        'Open a profession\'s Recipe page first, then run this command.',
    '部落：': 'Horde: ', '联盟：': 'Alliance: ',
    '这个副本还没有攻略，数据补上后会自动出现。':
        'No guide for this dungeon yet — it will appear once the data is added.',
    '总览': 'Overview', '功能': 'Features', '角色': 'Character', '作者': 'Author',
    '鸣谢': 'Credits', '圆圆': 'Yuanyuan',
    '黑科研 · 胡里胡涂': 'Heikeyan · Hulihutu', '黑科研研究所': 'Heikeyan Studio',
    'QQ群': 'QQ Group',
    '下一步': 'Next step', '互斥': 'Mutually exclusive', '取代': 'Replaces',
    '待核实': 'Needs verification', '待确认': 'Unverified', '推荐': 'Recommended',
    '推荐 · ': 'Recommended · ', '稀有': 'Rare', '稀有 · ': 'Rare · ',
    '已知内容': 'Known Content', '包含位置来源': 'Incl. Location Sources',
    '新': 'New', ' |cff40d940新|r': ' |cff40d940New|r',
    '仅新增': 'New additions only', '标注新增': 'Marked as new',
    '入口': 'Entrance', '任务': 'Quest', '奖励': 'Rewards', '收集': 'Collect',
    '拾取': 'Pick Up', '击杀': 'Kill', '上交': 'Turn In',
    '所需等级': 'Required level', '等级 %d 起': 'Level %d+',
    '最低 %d 级': 'Min level %d', '最高 %d 级': 'Max level %d',
    '任务路线': 'Quest route', '副本外前置任务': 'Outside pre-quest',
    '黑市': 'Black Market',
    '收获': 'Yields', '采集': 'Gathering', '制造': 'Crafted', '升级': 'Leveling',
    '配方': 'Recipes', '配方规模': 'Recipe counts', '配方 %d 条': '%d recipes',
    '阵营': 'Faction', '阵营：': 'Faction: ', '职业': 'Class', '武器': 'Weapon',
    '玩具': 'Toy', '数据版本': 'Data version', '探索': 'Explore', '探索数据': 'Explore data',
    '作者备注': "Author's notes", '任务注释': 'Quest notes',
    '主城': 'Capital', '5人本': 'Dungeons', '团本': 'Raids', '副本': 'Dungeon',
    'BIS配装': 'BiS Gear', '‹ 副本': '‹ Dungeons', '‹ 团本': '‹ Raids', '副本入口': 'Dungeon entrance',
    '团本数据待补': 'Raid data pending',
    '共 %d 个副本 · 你（%d 级）可进入 %d 个，其中推荐 %d 个':
        '%d dungeons total · you (level %d) can enter %d, %d recommended',
    '按等级排布，一眼看清全部副本分布':
        'Arranged by level — see the whole dungeon spread at a glance',
    '场景图卡片墙：按能否进入分三组，点卡片看详情':
        'Card wall of instance art, grouped into three by entry eligibility — click a card for details',
    '尚未收录这个副本的 boss 名单，数据补上后会自动出现。':
        'No boss list indexed for this dungeon yet — it will appear once the data is added.',
    '本站资料里这个副本还没有任务清单，数据补上后会自动出现。':
        'No quest list for this dungeon in our data yet — it will appear once the data is added.',
    '谁掉什么、掉率多少是经典旧世的数据。标「新」的是无限版新增的掉落；其余物品无限版的属性可能有改动，以正式版为准。':
        'Who drops what, and at what rate, is Classic Era data. Items marked "New" are Forever-edition drops; other items may have altered stats in the Forever edition — the live version is authoritative.',
    '新副本的 boss 名单来自 beta 客户端，标「新」的是无限版新增的物品；没有掉落数据的 boss 只列名字。':
        'Boss lists for new dungeons come from the beta client; items marked "New" are Forever-edition additions. Bosses without drop data are listed by name only.',
    '数值以 60 级为基准、随等级成长 —— 游戏内低等级看到的数字更小属正常缩放。':
        'Values are baselined at level 60 and scale with level — smaller numbers at lower levels in game are normal scaling.',
    '暂无掉落数据': 'No drop data yet',
    '该分类下暂无任务。': 'No quests in this category.',
    '该分类下暂无掉落。': 'No drops in this category.',
    '这个筛选下没有条目': 'Nothing matches this filter',
    '这个筛选下没有条目 —— 40 本都找齐了？': 'Nothing matches this filter — found all 40 books?',
    '列表只画前 %d 条，还有 %d 条没显示 —— 用上方分类缩小范围。':
        'Only the first %d rows are drawn; %d more are hidden — narrow it down with the filters above.',
    '当前分类 %d 条（标注总计 %d 条，其中 %d 条来源不可读）':
        'Current filter: %d entries (%d marked in total, %d with unreadable source)',
    '搜索物品…': 'Search items…',
    '搜索附魔…': 'Search enchants…',
    '点左侧任务查看详情': 'Click a quest on the left for details',
    '点左侧部位查看备选': 'Click a slot on the left for alternatives',
    '点左侧部位查看该部位的附魔': 'Click a slot on the left for its enchants',
    '该部位没有附魔推荐': 'No enchant recommendation for this slot',
    '属性汇总': 'Stat summary',
    '客户端未收录此物品': 'Not in the client database yet',
    '客户端未收录此任务，暂时没有客户端数据': 'Quest not in the client database — no client data yet',
    '点击：在地图上标记该任务': 'Click: mark this quest on the map',
    '点击：在地图上标记': 'Click: mark on the map',
    '点击：查看商人位置（%d 位商人）': 'Click: view vendor locations (%d vendors)',
    '点击：查看稀有怪位置（%d 处刷新）': 'Click: view rare spawn locations (%d spots)',
    '选择要标记的稀有怪刷新点': 'Select a rare spawn to mark',
    '稀有怪': 'Rare creature',
    '点击：打开该副本掉落详情': 'Click: open dungeon loot details',
    '点击：打开%s的地图': 'Click: open the map of %s',
    '点击：打开任务所在地图': 'Click: open the quest zone map',
    '未收录任务 #%d 的地图位置': 'No map location indexed for quest #%d',
    '客户端详细数据加载中，稍后自动刷新': 'Loading detailed client data — will refresh automatically',
    '暂时没有客户端数据': 'No client data yet',
    '位置未知': 'Location unknown', '来源未收录': 'Source not indexed',
    '本表未收录起始信息': 'No start info in this table',
    '未收录该 NPC 的地图位置': 'No map location indexed for this NPC',
    '未收录该位置的地图': 'No map indexed for this location',
    '未收录该位置的地图，无法标记': 'No map indexed for this location, cannot place marker',
    '未收录该副本的入口位置': 'No entrance location indexed for this dungeon',
    'NPC #%d 未收录地图位置': 'NPC #%d has no indexed map location',
    '前置 ID 未收录，查不了状态': 'Pre-quest ID not indexed — cannot track status',
    '自动识别：金格 = 已上交；绿格 = 背包有书未上交':
        'Auto-detect: gold cell = turned in; green cell = book in your bags, not yet turned in',
    '状态来自你自己的任务日志，交完任务这里会自动变。':
        'Status comes from your own quest log and updates here automatically after you turn the quest in.',
    '状态标签说明': 'Status tag legend',
    '地图标记仅无限客户端支持': 'Map markers are supported on the Forever client only',
    '全程无 NPC · 点地面物件触发': 'No NPCs involved · triggered by clicking ground objects',
    '由物件「%s」起始': 'Starts from the object "%s"',
    '「%s」没有独立世界地图，请按位置细节前往':
        '"%s" has no standalone world map — navigate by the location details',
    '点击在地图上定位': 'Click to locate on the map',
    '点击坐标在地图上定位': 'Click the coordinates to locate on the map',
    '点击：在地图上标记副本入口': 'Click: mark the dungeon entrance on the map',
    '点击：在地图上标记此位置': 'Click: mark this location on the map',
    '点击：在地图上标记此点': 'Click: mark this point on the map',
    '点击：在地图上标记该 NPC': 'Click: mark this NPC on the map',
    '点击：在地图上标记军需官位置': 'Click: mark the quartermaster on the map',
    '未收录该阵营的军需官位置': 'No quartermaster location indexed for this faction',
    '数据来源：wowhead': 'Data source: wowhead',
    '点击复制数据来源网址': 'Click to copy the data source URL',
    '无限副本手册': 'DungeonsForever',
    '左键：打开 / 关闭界面': 'Left-click: open / close the window',
    '用法：/df 打开或关闭界面。': 'Usage: /df toggles the window.',
    '/副本手册': '/dungeons',
    '界面大小': 'UI Scale', '放大界面': 'Zoom in', '缩小界面': 'Zoom out',
    '点击复位 100%': 'Click to reset to 100%',
    '范围 60%–140%，停手 0.5 秒生效': 'Range 60%–140%, applies 0.5s after you stop',
    '心愿': 'Wish',
    'NPC #%d 未收录地图位置': 'NPC #%d has no indexed map location',

    # ── 任务 / 状态 ──
    '任务 #%d': 'Quest #%d', '任务 #?': 'Quest #?', '任务奖励': 'Quest rewards',
    '任务已完成': 'Quest complete', '任务未完成': 'Quest incomplete',
    '要求等级 %d': 'Requires level %d',
    '要求%d级': 'Req. level %d',
    '%d 级可用': 'Usable at lv. %d',
    '需要等级 %d': 'Requires level %d',
    '装等%d': 'ilvl %d',
    '任务物品': 'Quest item', '任务目标': 'Quest objective',
    '拾取绑定': 'Binds when picked up', '装备后绑定': 'Binds when equipped',
    '任务等级 Lv%s': 'Quest level %s', ' · 任务等级 Lv%s': ' · Quest level %s',
    '任务线奖励总览': 'Quest chain reward overview', '任务难度': 'Quest difficulty',
    '任务需求': 'Quest requirements', '任务：': 'Quest: ',
    '关联任务（%d 个）': 'Related quests (%d)',
    '点击折叠 / 展开该组': 'Click to collapse / expand this group',
    '前置': 'Pre-quests', '前置：': 'Pre-quests: ', '无前置': 'No pre-quests',
    '可共享': 'Sharable',
    '前置任务': 'Pre-quests', '后续任务': 'Follow-up quests',
    '后续': 'Follow-up', '地下城': 'Dungeon', '（%s 掉落）': ' (drops from %s)',
    # 任务详情「共享：可分享 / 不可共享」（2026-10-03 补：并行会话新加的 L 键，EN 表漏登）
    '共享': 'Share', '可分享': 'Shareable', '不可共享': 'Not shareable',
    '可接等级': 'Min. level', '可接等级：': 'Min. level: ',
    # 缩写口径（2026-09-25 实机反馈）：任务行右列与状态字同排，长句会相撞 → Lv N+
    '%d 级可接': 'Lv %d+',
    '%d 级可接 · 任务等级 Lv%d': 'Lv %d+ · qLv %d',
    '任务等级': 'Quest level',
    '已完成': 'Completed', '已完成 %d / %d': 'Completed %d / %d',
    '显示已完成': 'Show completed',
    '已接取': 'Accepted', '进行中': 'In progress', '未完成': 'Incomplete',
    '任务完成': 'Done', '未接取': 'Not accepted',
    '进本前先去接': 'Pick up the quest before entering',
    '（只看%s阵营任务）': '(%s faction quests only)',
    '（含对方阵营的任务）': "(includes the other faction's quests)",
    '（已按你的阵营筛选）': '(filtered to your faction)',
    '起始：': 'Start: ', '结束：': 'End: ', '交出：%s': 'Turn in: %s', '产出：%s': 'Yields: %s',
    '换得：%s': 'Exchanged for: %s', '换得配方：%s': 'Recipe obtained: %s',
    '分布：%s': 'Found in: %s', '适用：%s': 'Applies to: %s',
    '材料：%s': 'Materials: %s', '改版前材料：%s': 'Pre-revamp materials: %s',
    '所需：技能 %s · 商人青睐 %s': 'Requires: skill %s · vendor prefers %s',
    '地图标记仅无限客户端支持': 'Map markers are supported on the Forever client only',

    # ── 阵营 ──
    '联盟': 'Alliance', '部落': 'Horde', '盟': 'A', '部': 'H',
    '联盟领地': 'Alliance territory', '部落领地': 'Horde territory',
    '争夺中的领地': 'Contested territory',
    '联盟专属': 'Alliance-only', '部落专属': 'Horde-only',
    # 筛选胶囊固定宽 84px（ExploreUI TOOL_W），英文必须 ≤84px@14px 字号，否则截字
    '联盟可用': 'For Alliance', '部落可用': 'For Horde',
    '联盟限定': 'Alliance-only', '部落限定': 'Horde-only',
    '两阵营通用': 'Both factions', '双阵营共有': 'Shared by both factions',
    '种族相关': 'Race-specific',

    # ── 职业 ──
    '战士': 'Warrior', '圣骑士': 'Paladin', '猎人': 'Hunter', '盗贼': 'Rogue',
    '牧师': 'Priest', '萨满': 'Shaman', '萨满祭司': 'Shaman', '法师': 'Mage',
    '术士': 'Warlock', '德鲁伊': 'Druid', '潜行者': 'Rogue',
    '战': 'War', '骑': 'Pal', '猎': 'Hun', '盗': 'Rog', '牧': 'Pri',
    '萨': 'Sha', '法': 'Mag', '术': 'Lock', '德': 'Dru',
    '%s专属': '%s only',

    # ── 属性 / 部位 ──
    '力量': 'Strength', '敏捷': 'Agility', '耐力': 'Stamina', '智力': 'Intellect',
    '精神': 'Spirit', '攻击强度': 'Attack Power', '法术强度': 'Spell Power',
    '暴击等级': 'Critical Strike Rating', '急速等级': 'Haste Rating',
    '护甲': 'Armor', '护甲类型：%s': 'Armor type: %s',
    '头部': 'Head', '颈部': 'Neck', '肩部': 'Shoulders', '背部': 'Back',
    '胸部': 'Chest', '手腕': 'Wrists', '手部': 'Hands', '腰部': 'Waist',
    '腿部': 'Legs', '脚': 'Feet', '戒指': 'Finger', '饰品': 'Trinket',
    '衬衣': 'Shirt', '公会徽章': 'Tabard', '双手武器': 'Two-Hand',
    '主手': 'Main Hand', '副手': 'Off Hand', '副手：盾牌': 'Off Hand: Shield',
    '远程': 'Ranged', '主手、副手': 'Main Hand, Off Hand', '手部、腿部': 'Hands, Legs',
    '被双手武器占用': 'Occupied by a two-handed weapon',
    '项链': 'Neck', '10本 项链': '10 books → Neck', '20本 戒指': '20 books → Finger',
    '25本 三选一': '25 books → Choice of 3',
    '%d本 → 戒指': '%d books → Finger', '%d本 → 项链': '%d books → Neck',
    '%d本 → 三选一': '%d books → Choice of 3',
    '40本书': '40 Books',

    # ── 专业 ──
    '专业': 'Professions', '全部专业': 'All professions', '主专业': 'Primary',
    '次专业': 'Secondary', '炼金': 'Alchemy', '锻造': 'Blacksmithing',
    '裁缝': 'Tailoring', '制皮': 'Leatherworking', '附魔': 'Enchanting',
    '工程学': 'Engineering', '急救': 'First Aid', '烹饪': 'Cooking',
    '钓鱼': 'Fishing',
    '制造专业 —— 每个角色选两个主要专业':
        'Crafting professions — each character picks two primary professions',
    '采集专业 —— 为制造专业提供材料':
        'Gathering professions — they supply materials for crafting',
    '次要专业 —— 每个角色三个都能学':
        'Secondary professions — a character can learn all three',
    '左侧选专业、右侧切子页。子页按数据是否存在自动启用：采集类没有配方与升级路线（但有节点表）。物品名与图标全部由客户端提供，客户端还没加载到的会先显示占位、随后自动补上。':
        'Pick a profession on the left and switch sub-tabs on the right. Sub-tabs enable automatically when data exists: gathering professions have no recipes or leveling routes (but do have node tables). Item names and icons all come from the game client; entries show placeholders until the client loads them.',
    '左侧选专业、右侧切子页。子页按数据是否存在自动启用：采集类没有配方与升级路线（但有节点表），营地系统只有营地和说明。物品名与图标全部由客户端提供，客户端还没加载到的会先显示占位、随后自动补上。':
        'Pick a profession on the left, switch sub-pages on the right. Sub-pages enable based on available data: gathering professions have no recipes or leveling routes (but do have node tables), and the camp system only has Camp and Guide. Item names and icons all come from the client — anything not loaded yet shows a placeholder and fills in automatically.',
    '所需技能': 'Required skill', '技能 %d': 'Skill %d',
    '技能 %d · %d 点': 'Skill %d · %d points', '技能 %d · %s': 'Skill %d · %s',
    '技能 %s': 'Skill %s', '技能加成': 'Skill bonus',
    '技能等级（怎么把上限提上去）': 'Skill levels (how to raise the cap)',
    '技能：学 %s · %s': 'Skill: learn %s · %s', '学 %s': 'Learn: %s',
    '向训练师学习': 'Learn from a trainer', '学会后解锁': 'Unlocks once learned',
    '可制造 %d': 'Craftable: %d', '~%s 次制作': '~%s crafts',
    # 右栏标题（升级页 col 2）：标题长度 = 右栏宽下限（189px@13pt），必须 ≤189px
    '半成品（%d 种）': 'Intermediates (%d)', '%d 种材料': '%d materials',
    '要准备的材料': 'Materials to gather', '还需升级': 'Needs more skill',
    '商人直卖（无需自采）': 'Sold by vendors',
    '商人兑换 %d': 'Vendor exchange %d', '商人青睐 %s': 'Vendor prefers %s',
    '商人：%s': 'Vendor: %s', '需图纸 · 商人出售': 'Requires a pattern · sold by a vendor',
    '商人：%s 等 %d 人': 'Vendor: %s and %d more',
    '选择要标记的商人': 'Pick a vendor to mark',
    '双阵营': 'Both factions',
    '进阶': 'Next rank',
    '角色等级': 'Char level',
    '上限 %d': 'Cap %d',
    '选择要标记的 NPC': 'Pick an NPC to mark',
    '掉落：%s': 'Dropped by: %s',
    '…等 %d 处': '…%d more sources',
    ' · %d%%': ' · %d%%',
    '…等 %d 个商人': '…and %d more vendors', '该商人的位置暂未收录': 'This vendor has not been mapped yet',
    '掉落：%s': 'Drops: %s',
    # 2026-10-08 晚：升级页成本路线（ProfRouteAuto）设置项
    '%d金%02d银': '%dg%02ds', '%d银': '%ds',
    '自动计算路线（按拍卖行价格）': 'Auto route (auction prices)',
    '关闭 = 显示固定路线；开启 = 依据 Auctionator 价格计算最省钱的制作路线': 'Off = fixed route; on = cheapest craft route from Auctionator prices',
    '需要安装 Auctionator 并完成一次拍卖行扫描；不可用时自动回落固定路线。': 'Requires Auctionator with a completed auction scan; falls back to the fixed route when unavailable.',
    '路线与购物清单在「升级」页签顶部的按钮切换。': 'Switch between route and shopping list with the buttons at the top of the Leveling tab.',
    '只使用拍卖行可购材料的配方': 'Only recipes with auction-buyable materials',
    '材料在拍卖行/商人都查不到价格时，该配方不参与计算（商人直售材料不受限）': 'Recipes whose materials have no AH/vendor price are skipped (vendor-sold materials are always priced)',
    '开启：路线更可靠，但可能出现无配方可用的缺口区间。': 'On: more reliable route, but gaps with no usable recipe may appear.',
    '关闭：缺口区间会改用无价材料的配方补位，花费按已知价格估算（行内打 ? 标记）。': 'Off: gaps get filled with unpriced-material recipes; cost is estimated from known prices (marked with ? inline).',
    '排除需要图纸的配方': 'Exclude pattern recipes',
    '跳过掉落图纸类配方；图纸可从商人购买的配方仍会使用': 'Skips recipes whose patterns drop; recipes with vendor-sold patterns are still used',
    '开启：只使用训练师直学与商人图纸配方，开荒最稳。': 'On: trainer-taught and vendor-pattern recipes only — the safest pick.',
    '关闭：掉落图纸配方也会参与，可能更便宜但要自己刷图纸。': 'Off: dropped-pattern recipes join in; cheaper, but you farm the patterns yourself.',
    '仅使用已学习的配方': 'Only learned recipes',
    '只在本角色已学会的配方中挑选': 'Picks only from recipes this character has learned',
    '开启：路线里的每一段都能立刻开做。': 'On: every segment of the route can be crafted right away.',
    '关闭：按「学会全部候选配方」的理想情况计算。': 'Off: computed as if every candidate recipe were learned.',
    '从当前技能开始计算': 'Start from current skill',
    '开启 = 只算当前技能到 300 的路线；关闭 = 从 1 全量重算整条路线（预估全程花费）': 'On = route from current skill to 300; off = full recalc from 1 (estimates total cost)',
    '开启：适合练级中途打开手册直接照着做。': 'On: best for picking the guide up mid-leveling.',
    '关闭：查看从零开始的最优路线与总花费。': 'Off: shows the optimal route and total cost from scratch.',
    '1 → 300 自动路线（按拍卖行价格）': '1 → 300 auto route (auction prices)',
    '~%d 次制作 · %s': '~%d crafts · %s',
    '一键导入购物清单 →': 'Import shopping list →',
    '含无价材料：花费为估算下限（可在设置放宽「只使用拍卖行可购材料」）': 'Includes unpriced materials: cost is a lower-bound estimate (relax "Only recipes with auction-buyable materials" in settings)',
    '段落花费：%s': 'Segment cost: %s',
    '点击切换到购物清单子页，可一键导入 Auctionator': 'Click to open the shopping list sub-tab, one-click import into Auctionator',
    '缺口：%d–%d 无符合筛选的配方（可放宽设置重算）': 'Gap: %d–%d has no recipe matching the filters (relax settings and recompute)',
    # 2026-10-09 缺口回填：无价材料不再误杀配方，缺口段自动按估价回填
    '缺口 %d–%d 已按估价回填（配方含无价材料，花费为下限）': 'Gap %d–%d filled with estimated recipes (they contain unpriced materials; cost is a lower bound)',
    '≈%d 次制作 · 约%s': '≈%d crafts · ~%s',
    '≈%d 次制作 · 价格未知': '≈%d crafts · price unknown',
    '该段材料缺价格数据：花费按已估价材料估算（未知材料按 0 计）': 'Materials in this segment lack price data: cost is estimated from priced materials only (unpriced count as 0)',
    '价格未知（Auctionator 无记录）': 'Price unknown (no Auctionator record)',
    '部分配方材料价格未知：总花费为估算下限': 'Some recipes contain unpriced materials: total cost is a lower-bound estimate',
    # 2026-10-09 v2 布局重排：目标等级输入框 + 购物清单双模式 + 固定路线金币 + 图纸成本
    '目标等级': 'Target level',
    '级（300 = 全程）': ' (300 = full)',
    '1 → %d 分段路线': '1 → %d fixed route',
    '1 → %d 自动路线（按拍卖行价格）': '1 → %d auto route (auction prices)',
    '需要金币 %s': 'Gold needed %s',
    '材料 %d 种 · 其中图纸 %s · 价格快照 %d 分钟前（Auctionator）': '%d materials · formulas %s · price snapshot %d min ago (Auctionator)',
    '配方 %d 种 · %d 次制作 · 商人直售 %s · 图纸 %s · 价格快照 %d 分钟前（Auctionator）': '%d recipes · ~%d crafts · vendor-sold %s · formulas %s · price snapshot %d min ago (Auctionator)',
    '价格数据不可用（安装并扫描 Auctionator 后显示金币）': 'No price data (install Auctionator and run a scan to show gold)',
    '含无价材料 %d 种：花费为估算下限': '%d materials have no price: cost is a lower-bound estimate',
    '含无价材料 %d 种：总花费为估算下限': '%d materials have no price: total cost is a lower-bound estimate',
    '目标 %d 之后的段落已省略，跨目标段的制作数量按比例折算。': 'Segments beyond %d are omitted; counts of segments crossing the target are scaled proportionally.',
    ' · 按目标 %d 折算': ' · scaled to target %d',
    '按目标 %d 折算': 'Scaled to target %d',
    '图纸：%s · %s（一次性，已计入合计）': 'Formula: %s · %s (one-time, included in total)',
    '未知图纸': 'Unknown formula',
    '购物清单（固定路线 1–%d）': 'Shopping list (fixed route 1–%d)',
    '共 %d 种材料 · 合计 %d 件 · 价格快照 %d 分钟前（Auctionator）': '%d materials · %d items total · price snapshot %d min ago (Auctionator)',
    '一键导入 Auctionator →': 'Import into Auctionator →',
    '点击在 Auctionator 生成购物清单；同名清单会被覆盖': 'Creates the shopping list in Auctionator; same-name lists are overwritten',
    '×%d · %s': '×%d · %s',
    '材料（%d 种）': 'Materials (%d)',
    '图纸（一次性）（%d 个）': 'Formulas (one-time) (%d)',
    '配方：%s': 'Recipe: %s',
    ' · 商人可购': ' · vendor-sold',
    '商人可购': 'vendor-sold',
    '图纸只买一次，已计入合计': 'Formulas are bought once and included in the total',
    ' · 价格未知': ' · price unknown',
    '价格未知': 'price unknown',
    '自动路线不可用': 'Auto route unavailable',
    '自动路线需要 Auctionator 的价格数据：请安装 Auctionator 并完成一次拍卖行扫描；当前显示固定路线。': 'Auto route needs Auctionator price data: install Auctionator and run an auction scan; showing the fixed route for now.',
    '购物清单在「购物清单」子页': 'Shopping list is in the "Shopping List" sub-tab',
    '配方 %d 种 · %d 次制作 · 商人直售 %s · 价格快照 %d 分钟前（Auctionator）': '%d recipes · ~%d crafts · vendor-sold %s · price snapshot %d min ago (Auctionator)',
    '预计总花费 %s': 'Estimated total cost %s',
    # 2026-10-09 三轮：购物清单两栏 B 版 —— 右栏金币卡 + 三行分类合计 + HUD 直售徽标
    '总共需要': 'Total needed', '拍卖行购入': 'From auction house',
    '图纸购入': 'From formulas', '商人直售购入': 'From vendors',
    '价格快照 %d 分钟前（Auctionator）': 'price snapshot %d min ago (Auctionator)',
    # 2026-10-11 并行会话在 ProfessionUI 新增的快照年龄其余分支（原先只登记了「分钟前」一条，
    # 生成器卡在缺键上 ⇒ 顺带补齐，否则 enUS.lua 无法重生成）
    '价格快照 %d 小时前（Auctionator）': 'price snapshot %d h ago (Auctionator)',
    '价格快照 %d 天前（Auctionator）': 'price snapshot %d d ago (Auctionator)',
    '价格快照：今天（Auctionator）': 'price snapshot: today (Auctionator)',
    '价格快照：刚刚（Auctionator）': 'price snapshot: just now (Auctionator)',
    '价格快照年龄未知（Auctionator）': 'price snapshot age unknown (Auctionator)',
    '价格快照数据过期，距离上次扫描超过 2 天上限，需要重新扫描': 'price snapshot expired: last scan is beyond the 2-day limit, rescan the auction house',
    '共 %d 种材料 · 合计 %d 件': '%d materials · %d items total',
    # 2026-10-09 配方搜索（并行会话补登记）
    '搜索': 'Search',
    '没有名称或材料匹配「%s」的配方 —— 换个关键词再试试。': 'No recipes match "%s" by name or materials — try another keyword.',
    '配方名 / 材料名': 'Recipe / material name',
    ' · 商人直售': ' · vendor-sold', '%d 件 · %s': '%d items · %s',
    '共 %d 种材料 · 价格快照 %d 分钟前（Auctionator）': '%d materials · price snapshot %d min ago (Auctionator)',
    '商人直售': 'vendor-sold', '固定路线': 'Fixed route', '自动计算': 'Auto route',
    '在 Auctionator 生成购物清单；同名清单会被覆盖': 'Creates the shopping list in Auctionator; same-name lists are overwritten',
    # 2026-10-09 四轮：材料行直售徽标 + 产物收益卡；半成品/商人直卖两段退役
    '产物收益': 'Product revenue',
    '产物丢拍卖行收益': 'Products sold on the AH',
    '直接卖给NPC收益': 'Products sold to vendors',
    '净花费（产物丢拍卖行）': 'Net cost (AH route)',
    '净赚 %s': 'profit %s',
    '部分产物无拍卖行价格：收益为估算下限': 'Some products lack AH prices: revenue is a lower-bound estimate',
    '商人直售（军需官处直购，无需拍卖行）': 'vendor-sold (buy from the vendor directly, no AH needed)',
    # 2026-10-09 四轮补登记：工具行目标输入框 / 汇总条等 v2 期间的存量缺键
    '%d 分钟前 · Auctionator': '%d min ago · Auctionator',
    # 2026-10-11 同上（并行会话的短格式快照年龄分支）
    '%d 小时前 · Auctionator': '%d h ago · Auctionator',
    '%d 天前 · Auctionator': '%d d ago · Auctionator',
    '今天 · Auctionator': 'today · Auctionator',
    '刚刚 · Auctionator': 'just now · Auctionator',
    '快照年龄未知 · Auctionator': 'snapshot age unknown · Auctionator',
    # 2026-10-11 三轮：时间与插件名紧贴（去掉 ·），超 24 小时直接显示 X 天前
    '%d 分钟前Auctionator': 'Auctionator: %d min ago',
    '%d 小时前Auctionator': 'Auctionator: %d h ago',
    '%d 天前Auctionator': 'Auctionator: %d d ago',
    '今天Auctionator': 'Auctionator: today',
    '刚刚Auctionator': 'Auctionator: just now',
    '快照年龄未知Auctionator': 'Auctionator: snapshot age unknown',
    '1 → %d 预计总花费': '1 → %d estimated total cost',
    '价格快照': 'Price snapshot',
    '全程': 'full range',
    '商人直售 %s · 图纸 %s': 'vendor-sold %s · formulas %s',
    '固定路线：按资料整理的分段练法逐段冲技能': 'Fixed route: level up segment by segment following the curated route',
    '安装 Auctionator 并完成一次拍卖行扫描后，这里显示价格快照年龄。': 'After installing Auctionator and running an auction scan, the price snapshot age shows here.',
    '未接入 Auctionator': 'Auctionator not connected',
    '材料 %d 种': '%d materials',
    '模式 · 点击切换': 'Mode · click to switch',
    '模式': 'Mode',
    '每专业独立记忆；300 = 全程。点击修改': 'Remembered per profession; 300 = full range. Click to edit',
    '点击在固定 / 自动之间切换': 'Click to switch between fixed and auto',
    '目标等级 · 点击修改': 'Target level · click to edit',
    '自动计算：依据 Auctionator 价格算最省钱的制作路线': 'Auto route: computes the cheapest leveling route from Auctionator prices',
    '自动计算：按当前路线方案逐点择优（在「路线方案」卡切换）': 'Auto route: picks recipes per skill point by the current scheme (switch on the Scheme card)',
    '最省钱': 'Cheapest',
    '材料成本': 'Material cost',
    '次数最少': 'Fewest crafts',
    '乐观计数': 'Optimistic',
    '路线方案 · 点击切换': 'Scheme · click to switch',
    '最省钱：材料价 + 图纸价按升点概率摊到每一点，选期望花费最低的配方': 'Cheapest: material + formula price spread over each skill point; picks the lowest expected cost',
    '材料成本：只按材料价选配方（不含图纸价）': 'Material cost: picks by material price only (formula price excluded)',
    '次数最少：优先升点率高的配方，同分取便宜': 'Fewest crafts: prefers recipes with higher skill-up chance; ties go to the cheaper one',
    '乐观计数：材料不看市价，一律按卖店价值折算；次数固定按做一次涨一点统计、只是下限；快变黄前 25 点的配方也纳入可选；带冷却的转化配方和资料未收录的材料不进路线': 'Optimistic: materials valued at vendor sell value instead of market prices; each segment counts one craft per skill point as a lower bound; recipes are eligible from 25 points before they turn yellow; cooldown transmutes and recipes with unmapped materials are skipped',
    '钓鱼升级路线（%d 处水域）': 'Fishing route (%d waters)',
    '按技能门槛分档推进：下竿必涨，到下一档门槛就换区域。': 'Progress by skill gates: every cast levels you up; move to the next tier when you reach its gate.',
    '技能 %d 起': 'From skill %d',
    '◆ 推荐当前就练这一档': '◆ This is your current tier',
    '练到 %d 换下一档': 'Move to the next tier at %d',
    '练满为止': 'Stay until maxed',
    '采集升级路线（全程）': 'Gathering route (full run)',
    '当前技能 %d，绿色为推荐段：采到区间上缘再换下一段。': 'Current skill %d; the green band is where you should farm now, up to its upper edge.',
    '未学到该专业，先找训练师学习；学习后这里显示当前位置。': 'You have not learned this profession yet; visit a trainer, then your position will show here.',
    '%d - %d': '%d - %d',
    '当前技能': 'Current skill',
    '未学': 'Not learned',
    '读取角色当前的专业技能值': 'Reads your character\'s current profession skill',
    '路线进度': 'Route progress',
    '列表中绿色高亮行 = 推荐当前采集的区间': 'The green row in the list marks the band to farm now',
    '路线范围': 'Route range',
    '静态推荐路线（全程显示）：按资料整理的采集区间推进，不含价格与概率，无需价格插件': 'Static recommended route (full run): band-by-band from compiled data; no prices or probabilities, no price addon needed',
    '熔炼升级路线（全程）': 'Smelting route (full run)',
    '当前技能 %d，绿色为可练区间：练到下一档再换锭。': 'Current skill %d; the green band is what you can smelt now, switch bars at the next tier.',
    '大多在 %s': 'Mostly in %s',
    '点击切换：采集 ⇄ 熔炼': 'Click to switch: gathering / smelting',
    '列表中绿色高亮行 = 当前技能可练的熔炼区间': 'The green row marks the bar band you can smelt at your current skill',
    '采集': 'Gather',
    '熔炼': 'Smelt',
    '乐观计数：花费按卖店价值粗算，不是拍卖行行情': 'Optimistic: costs are a rough vendor-sell-value estimate, not auction prices',
    '乐观计数 · 不依赖价格插件': 'Optimistic · no price addon needed',
    '配方 %d 种 · %d 次制作': '%d recipes · %d crafts',
    '没有需要准备的材料。': 'Nothing to gather.',
    '约 %s': '~%s', '购物清单（自动路线）': 'Shopping list (auto route)', '重新计算': 'Recompute',
    '需要：%d': 'Need: %d', '首用于 %d–%d 段': 'first used at %d–%d',
    '需要图纸': 'Requires a pattern', '图纸：%s': 'Pattern: %s',
    '图纸': 'Pattern', '训练师': 'Trainer',
    '图纸：%s · 掉落 %d 处': 'Pattern: %s · drops in %d places',
    '公式:': 'Formula: ', '公式: ': 'Formula: ', '公式：': 'Formula: ',
    '1 → 300 分段路线': '1 → 300 segmented route',
    '展开 %d 级文本': 'Expand level %d text', '收起逐级文本': 'Collapse level-by-level text',
    '认证与称号': 'Certification & titles', '认证技能': 'Certified skills',
    '解锁称号：%s': 'Title unlocked: %s',
    '传承': 'Legacy', '传承特权': 'Legacy perks', '里程碑': 'Milestones',
    '里程碑与传承点数': 'Milestones & Legacy points', '%d 点': '%d points',
    '传承特权（13 个专业共用同一批，按 id 引用）':
        'Legacy perks (one shared set across all 13 professions, referenced by id)',
    '刻画塑像': 'Carved figurines', '雕刻塑像': 'Carved figurines',
    '附魔 %d': 'Enchant %d',
    '附魔魔棒（所需技能 → 魔棒）': 'Enchanted wands (required skill → wand)',
    '钓鱼法术': 'Fishing spells', '钓鱼物品': 'Fishing items',
    '钓鱼称号': 'Fishing titles', '钓鱼食物': 'Fishing food', '鱼饵': 'Lure',
    '可作为钓具': 'Usable as fishing gear', '可钓区域（%d 处）': 'Fishable zones (%d)',
    '节点 %d': 'Node %d', '档次 %d': 'Tier %d', '%d 档': '%d tiers',
    '节点表（所需技能 → 产出 → 分布）': 'Node table (required skill → yield → zones)',
    '剥皮档次（等级区间 → 产出 → 分布）': 'Skinning tiers (level range → yield → zones)',
    '数字速览': 'Quick stats', '%d 条 · %d 个分类': '%d entries · %d categories',
    '%s（%d 条）': '%s (%d)', '%d 件': '%d items', '个': '', ' 个': ' ',
    '%d 个': '%d', '个 ': ' ',

    # ── 营地 / 睡袋 / 书 ──
    '营地': 'Camp', '营地 · %s': 'Camp · %s', '营地系统': 'Camp System',
    '营地三档': 'Camp: three tiers', '营地增益': 'Camp buffs',
    '开发备注': 'Dev notes', '暂无备注': 'No notes yet',
    '营地位置 %.1f, %.1f': 'Campsite %.1f, %.1f',
    '营地档位对照表 →「营地系统」': 'Camp tier table → "Camp System"',
    '职业加成': 'Class bonus', '营地档位对照表 →「营地系统 → 职业加成」':
        'Camp tier table → "Camp System → Class Bonus"',
    '三档营地物件（技能 20 / 140 / 300）': 'Three camp-object tiers (skill 20 / 140 / 300)',
    '全部专业的营地物件档位对照': 'Camp-object tier comparison across all professions',
    '营地与军需官坐标（按阵营）': 'Camp & quartermaster coordinates (by faction)',
    '军需官 · %s': 'Quartermaster · %s',
    '营地增益不与同类职业增益叠加、效果略低于职业版（如王者祝福 10% → 营地 8%）。':
        "Camp buffs don't stack with the same class buff and are slightly weaker (e.g. Blessing of Kings 10% → camp 8%).",
    '物件 %d · 职业加成': 'Object %d · Class Bonus',
    '同营地 · 营火': 'Same camp · campfire', '营火': 'Campfire',
    '营火材料': 'Campfire materials', '② 营火材料': '② Campfire materials',
    '营火容量 %s': 'Campfire capacity %s',
    '可选步：用②给的普通木柴 + 燧石和火绒重燃营火，燧石和火绒用完会还给你；链路不需要这步。':
        'Optional step: relight the campfire with the ordinary firewood from step 2 plus Flint and Tinder (both returned to you afterwards); the chain does not require this step.',
    '睡袋': 'Sleeping Bag', '舒适睡袋': 'Cozy Sleeping Bag',
    '信使行囊': "Messenger's Satchel", '散落杂物': 'Scattered Debris',
    '烧焦的残骸': 'Scorched Remains', '土堆': 'Mound',
    '链中必给': 'Guaranteed in the chain', '12 格包': '12-slot bag',
    '12 格包 · ②': '12-slot bag · ②',
    '铺开睡袋躺进去休息：每躺满 1 分钟叠 1 层 +1% 经验，最多 3 层（共 3%），持续 2 小时；铺开需原地站 15 秒，睡袋落地留 20 分钟，使用冷却 1 小时。每 1~2 小时铺一次、躺满 3 分钟即可常驻 3%，队友可同躺。':
        'Deploy the bedroll and rest in it: every full minute lying in it adds one stack of +1% XP, up to 3 stacks (3% total) lasting 2 hours. Deploying requires standing still for 15 sec; the bedroll stays on the ground for 20 min and the item has a 1 hr cooldown. Redeploy every 1–2 hours and lie in it for 3 minutes to keep the 3% up — party members can share it.',
    '旧版的休息经验加成在无限服已移除，当应急干粮就好；吃下去还会附一波「方便零嘴」（0.75 秒 60% 移速）；':
        'The old rested-XP bonus is gone on the Forever realm — treat it as trail rations; every bite now also procs Trail Snack (60% movement speed for 0.75 sec);',
    '：躺满 1 分钟 +1% 经验、最多 3 层、持续 2 小时；铺开需原地站 15 秒、睡袋落地留 20 分钟，冷却 1 小时，队友可同躺':
        ': +1% XP per full minute rested, up to 3 stacks lasting 2 hours; deploying requires standing still for 15 sec, the bedroll stays on the ground for 20 min, 1 hr cooldown, party members can share it',
    '：吃一口立即回 500 血、12 秒内再回 1050，并回复法力 / 50 怒气 / 100 能量，5 分钟冷却、最多叠 30 个；':
        ': eat to instantly restore 500 health and another 1050 over 12 sec, plus mana / 50 Rage / 100 Energy; 5 min cooldown, stacks up to 30;',
    '40本书': '40 Books', '图书馆之友': 'Friend of the Library',
    '三选一': 'Pick one of 3', '二选一': 'Pick one of 2', '选一': 'Pick one',
    '三选一 · 第③步': 'Pick one of 3 · Step 3', '二选一 · 第②步': 'Pick one of 2 · Step 2',
    '三选一 · 魔杖': 'Pick one of 3 · Wand', '③ · 魔杖': '③ · Wand',

    # ── 等级 / 进入条件 ──
    '等级 %d–%d · %s': 'Levels %d–%d · %s', '等级 %s': 'Level %s',
    '等级 %s - %s': 'Levels %s - %s', '需 14 级': 'Requires level 14',
    '满级 %s': 'Max level %s', '当前等级 %d': 'Your level: %d',
    '现在可以进入': 'You can enter now', '等级正合适，优先前往': 'In the ideal range — go first',
    '等级已超出，仍可前往': 'Above the level range — still visitable',
    '等级达到下限后开放': 'Opens once you reach the minimum level',

    # ── BiS / 方案 ──
    '方案': 'Plan', '我的方案 %d': 'My Plan %d', '另存当前': 'Save as…',
    '恢复推荐': 'Use recommended', '战场': 'PvP', '坦克': 'Tank',
    # 分卷（20级 / 30级）：预设方案行与用户方案名都带等级前缀
    '%d级推荐 · %s': 'Lv%d Recommended · %s',
    '%d级 · ': 'Lv%d · ',
    '%d级 · 我的方案 %d': 'Lv%d · My Plan %d',
    '%d级 · %s · 我的方案 %d': 'Lv%d · %s · My Plan %d',
    '附魔': 'Enchant', '附魔 %d': 'Enchant %d', '套装：%s': 'Set: %s',
    '共同变化': 'Shared changes', '%s · 备选': '%s · Alternatives',
    '如何获得奖励': 'How to obtain the rewards', '你可以选择一件：': 'Choose one of:',
    '你还会获得：': 'You will also receive:',
    '职业版对照 / 其他功能': 'Class versions / other features',
    '持续（分钟）': 'Duration (min)', '增益': 'Buff', '增益：%s': 'Buff: %s',
    ' master NPC #%s': ' Trainer NPC #%s', '师傅 NPC #%s': 'Trainer NPC #%s',

    # ── 探索页长文与坐标标签 ──
    '希尔斯布莱德 87.4,49.7': 'Hillsbrad 87.4,49.7',
    '希尔斯布莱德丘陵 · 索拉丁之墙': "Hillsbrad Foothills · Thoradin's Wall",
    '洛克莫丹 49.4,12.9': 'Loch Modan 49.4,12.9',
    '洛克莫丹 · 巨石水坝矮人头像雕刻': 'Loch Modan · dwarf-head carving on the Stonewrought Dam',
    '石爪山脉 39.6,49.9': 'Stonetalon Mountains 39.6,49.9',
    '石爪山脉 40.7,52.4': 'Stonetalon Mountains 40.7,52.4',
    '石爪山脉 · 同营地营火（可选）': 'Stonetalon Mountains · camp campfire (optional)',
    '石爪山脉 · 烈日石居上方废弃营地': 'Stonetalon Mountains · abandoned camp above Sun Rock Retreat',
    '石爪山脉 · 营地正北山丘土堆': 'Stonetalon Mountains · mound on the hill due north of camp',
    '西部荒野 37,50': 'Westfall 37,50', '西部荒野 37.4,50.6': 'Westfall 37.4,50.6',
    '西部荒野 · 阿历克斯顿农场': 'Westfall · Alexston Farmstead',
    '贫瘠之地 46,74': 'The Barrens 46,74', '贫瘠之地 46.4,73.9': 'The Barrens 46.4,73.9',
    '贫瘠之地 · 陶拉祖营地以南烧毁塔楼': 'The Barrens · burnt tower south of Camp Taurajo',
    '全链起点：无 NPC，在阿历克斯顿农场烧毁的田地点「烧焦的残骸」起链，旁边立着一块镶钉木板；两阵营从这里反向出发。':
        'Chain start: no NPC — click "Scorched Remains" in the burnt field at Alexston Farmstead to begin; a studded board stands beside it. Both factions set out from here in opposite directions.',
    '两阵营互交互：在对方大陆的「烧焦的残骸 / 镶钉木板」上交①，再从镶钉木板接取本步；必给里的旧工具箱是 12 格包。':
        'Cross-faction turn-ins: hand in step 1 at the "Scorched Remains / Studded Board" on the opposing continent, then accept this step from the Studded Board; the guaranteed rewards include an old toolbox (a 12-slot bag).',
    '从烈日石居东北 ': 'Northeast of Sun Rock Retreat ',
    ' 的小路离开大路，往西翻过山到废弃营地，点箱子上的「散落杂物」交接；烈日石居是部落据点，联盟会从守卫旁经过。':
        ' take the trail off the road, head west over the ridge to the abandoned camp, and click "Scattered Debris" on the crate to turn in; Sun Rock Retreat is a Horde stronghold — Alliance should skirt past the guards.',
    '）跳上索拉丁之墙，穿过墙内房间点阿拉希一侧的信使行囊（':
        ") climb onto Thoradin's Wall, pass through the chamber inside the wall and click the messenger's satchel on the Arathi side (",
    ' ）跳上索拉丁之墙，穿过墙内房间点阿拉希一侧的信使行囊（':
        " ) climb onto Thoradin's Wall, pass through the chamber inside the wall and click the messenger's satchel on the Arathi side (",
    '）交接、再点下方草草收起的包裹拿睡袋；PVP 服小心。':
        ') to turn in, then click the hastily packed bundle below to get the sleeping bag; be careful on PvP realms.',
    ' ）交接、再点下方草草收起的包裹拿睡袋；PVP 服小心。':
        ' ) to turn in, then click the hastily packed bundle below to get the sleeping bag; be careful on PvP realms.',
    '最大难点：敦霍尔德城堡东南方的推车（': 'Biggest hurdle: the cart southeast of Durnholde Keep (',
    '%d 个专业 · 新增配方 %d 条 · 营地物件 %d 个 · 传承里程碑 %d 点 · 特权 %d 个':
        '%d professions · %d new recipes · %d camp objects · %d legacy milestones · %d perks',
    '副本内': 'In dungeon', '区域 #%d': 'Zone #%d', '区域 %d': 'Zone %d',
    '只看没找到': 'Unfound only', '已找到 %d / %d · 已提交 %d / %d':
        'Found %d / %d · turned in %d / %d',
    '已收藏': 'Collected', '已装备': 'Equipped', '掉落': 'Drops',
    '法术 #%d': 'Spell #%d', '物品 #%d': 'Item #%d', '接取': 'Start', '目标': 'Objective', '需求': 'Requirements',
    '爬上营地北边的山丘，跳到土堆上点它，途中要跳过一道缺口；注意摔落伤害。':
        'Climb the hill north of camp and jump onto the mound to click it; hop over a gap on the way — watch out for fall damage.',
    '沿巨石水坝走出去、面向北方湿地，跳到坝顶下方的矮人头像雕刻上交接；水坝有联盟守卫，部落小心。':
        'Walk out along the Stonewrought Dam facing the Wetlands to the north and jump onto the dwarf-head carving below the dam top to turn in; the dam has Alliance guards — Horde be careful.',
    ' · 掉落 %d': ' · %d drops', ' · 当前：': ' · Current: ',
    ' · BOSS %d': ' · Boss %d', '掉落 %d 处': 'Drops in %d places',
    '副本内领取 / 交付': 'Pick up / turn in inside the dungeon',
    '怎么开始': 'How to start', '怎么读这份手册': 'How to read this handbook',
    '这份手册里有什么': "What's in this handbook",
    '经验': 'XP', ' 经验': ' XP', '%s 经验': '%s XP',
    '金': 'Gold', '银': 'Silver', '铜': 'Copper',
    '进度 %d / %d': 'Progress %d / %d',
    '副本入口': 'Dungeon entrance',
    'build %s · 更新于 %s': 'build %s · updated %s',
    '专业数据 build %s · %s': 'Profession data build %s · %s',
    '仅新增': 'New additions only',

    # ── 战斗法师子页（ExploreUI BM 块；页签/胶囊走缩写适配固定宽控件）──
    '战斗法师': 'Battle Mage',
    '法师专属内容 ——「理解」为法师职业副技能':
        'Mage-only — Comprehension is a mage secondary skill',
    '背包持有 %d / 3': 'In bags %d / 3',
    '冷焰佩剑': 'Saber', '女巫之刃': 'Witchblade', '卷轴图鉴': 'Codex',
    '学习「理解」': 'Learn "Comprehension"',
    '6 级 · 法师训练师': 'Lv 6 · Mage trainer',
    '法师专属副技能 · 破译卷轴升到 300':
        'Mage secondary skill · decipher scrolls to 300',
    '法师训练师从 6 级起教你「理解」，像专业一样：破译未翻译的卷轴一路升到 300。':
        'Mage trainers teach Comprehension from level 6, like a profession: decipher untranslated scrolls all the way to 300.',
    '「学习」每小时一次，耗一根轻羽毛，给一捆卷轴（内含数张）；需要先在暴风城或幽暗城的图书馆交书学会。':
        '"Learn" runs once per hour, costs one Light Feather and yields a bundle of scrolls; you must first turn in books at the libraries of Stormwind or Undercity to unlock it.',
    '四档未翻译卷轴：理解 1 / 15 / 50 / 175 起可破译，30 / 75 / 200 / 300 变灰（变灰后不再涨技能）。':
        'Four tiers of untranslated scrolls: decipherable at Comprehension 1 / 15 / 50 / 175, grey at 30 / 75 / 200 / 300 (grey scrolls no longer grant skill-ups).',
    '破译未翻译的卷轴 · 走运才能拿到':
        'Decipher untranslated scrolls · lucky drop',
    '理解（15）档最可能出': 'Mostly from the Comp 15 tier',
    '理解（175）档最可能出': 'Mostly from the Comp 175 tier',
    '持续破译未翻译的卷轴，佩剑卷轴最可能来自理解（15）档。':
        'Keep deciphering untranslated scrolls — the saber scroll most likely comes from the Comp 15 tier.',
    '未翻译卷轴名字乱码、只有法师能读；很多怪物都会掉落，掉率约 0.2%–4%。':
        'Untranslated scrolls have gibberish names and only mages can read them; most monsters drop them at roughly 0.2%–4%.',
    '破译也可能得到所有职业都能用的卷轴（注入 / 魔宠等，见「卷轴图鉴」页签）。':
        'Deciphering can also yield scrolls any class can use (imbues, pets and more — see the Codex tab).',
    '影牙城堡 · 约 12 次出': 'Shadowfang Keep · ~12 runs',
    '影牙城堡 · 银松森林': 'Shadowfang Keep · Silverpine Forest',
    '反复击杀席瓦莱恩男爵直到掉落': 'Farm Baron Silverlaine until it drops',
    '席瓦莱恩之刃由影牙城堡的席瓦莱恩男爵掉落，约 12 次出。':
        "Silverlaine's Blade drops from Baron Silverlaine in Shadowfang Keep — roughly one in 12 runs.",
    '卷轴和刀刃都是拾取后绑定：破译卷轴的法师也要自己拾取刀刃，记得请队友让给你。':
        'Both scroll and blade are BoP: the mage deciphering the scroll must loot the blade too — ask your group to pass.',
    '20 级就能拾取刀刃并做出佩剑，但两者都需 21 级才能装备（Beta 等级上限 20，暂穿不了）。':
        'You can loot the blade and craft the saber at level 20, but both require level 21 to equip (Beta level cap is 20 — not wearable yet).',
    '冻结近战 +98 火焰伤害': '+98 fire dmg vs frozen targets',
    '主手剑 · 需要等级 21 · 法师专属': 'Main-hand sword · Req. level 21 · Mage-only',
    '对刀刃使用佩剑卷轴即得冷焰佩剑：对冻结目标的近战命中额外造成 98 点火焰伤害（冰霜灼烧）。':
        'Use the saber scroll on the blade to get the Cold Flame Saber: melee hits on frozen targets deal 98 extra fire damage (frostburn).',
    '冻结手段：冰霜新星；霜寒刺骨（冰冷效果最多 15% 几率冻结 5 秒）；寒冰指（会不会触发灼烧未验证）。':
        'Freeze tools: Frost Nova; Frostbite (chill effects up to 15% chance to freeze for 5 s); Fingers of Frost (whether it triggers the burn is unverified).',
    '可搭配火花注入卷轴：受近战命中时火焰冲击冷却有机会重置；寒冰之刃注入是匕首注入，与佩剑不兼容。':
        'Pairs with the Spark imbue scroll: Fire Blast cooldown may reset when you are melee-hit; the Icy Blade imbue is dagger-only and incompatible with the saber.',
    '第二张武器卷轴 · 46 级档': 'Second weapon scroll · Tier 46',
    '持续破译未翻译的卷轴，机智卷轴最可能来自理解（175）档。':
        'Keep deciphering untranslated scrolls — the wit scroll most likely comes from the Comp 175 tier.',
    '第二把刀刃在 Beta 里也拿不到全流程：先攒卷轴，等等级上限提高。':
        "The second blade's full chain isn't reachable on Beta either: stockpile scrolls and wait for the level cap to rise.",
    '通灵学院 · 约 1/8 掉率': 'Scholomance · ~1/8 drop rate',
    '通灵学院 · 西瘟疫之地': 'Scholomance · Western Plaguelands',
    '黑暗院长加丁掉落': 'Dropped by Darkmaster Gandling',
    '女巫之刃由通灵学院的黑暗院长加丁掉落，经典旧世大约每八次击杀掉一次。':
        'The Witchblade drops from Darkmaster Gandling in Scholomance — about one in eight kills in Classic.',
    '单手匕首，需要等级 57 —— 与冷焰佩剑的剑不同，这是法师的第二条武器链。':
        "One-hand dagger, requires level 57 — unlike the saber, this is the mage's second weapon chain.",
    '未知武器': 'Unknown weapon',
    '还不在客户端里': 'Not in the client yet',
    '未实装 · 先攒材料': 'Not implemented · stock up first',
    '机智卷轴对女巫之刃使用后做出的武器还不在 Beta 客户端里：没有名字，也没有属性。':
        "The weapon crafted by using the wit scroll on the Witchblade isn't in the Beta client yet: no name, no stats.",
    '两者都需 57 级：等暴雪把等级上限提高到 30 级之后，这条链才真正可做。':
        'Both require level 57: this chain only becomes doable after Blizzard raises the level cap to 30+.',
    '提升技能': 'Skill-ups',
    '未翻译的卷轴有四种，每一种需要的理解技能等级都更高。一种卷轴变灰之后就不会再提升技能：在技能到达它变灰的等级之前，换成下一种。':
        'There are four untranslated scrolls, each requiring a higher Comprehension skill. A greyed-out scroll no longer grants skill-ups: switch to the next one before your skill reaches its grey level.',
    '未翻译的卷轴': 'Untranslated scrolls',
    '可破译于': 'Decipher at', '变灰于': 'Greys at', '卷轴等级': 'Scroll Lv',
    '理解(%d) · %s': 'Comp %d · %s',
    '需要理解 %d': 'Comp %d required',
    '5 级档': 'Tier 5', '16 级档': 'Tier 16', '25 级档': 'Tier 25', '46 级档': 'Tier 46',
    '「一捆卷轴」开出率（17 捆样本）': '"Bundle of Scrolls" rates (17-bundle sample)',
    '合成': 'Craft', '匕首': 'Dagger', '法杖': 'Staff', '剑': 'Sword',
    '魔宠': 'Pet', '法术': 'Spell', '其它': 'Other',
    '注入法杖 1 小时：火焰伤害最多 +4': 'Staff imbue 1h: up to +4 fire dmg',
    '注入法杖 1 小时：冰霜伤害最多 +8': 'Staff imbue 1h: up to +8 frost dmg',
    '注入法杖 1 小时：法术伤害时偶尔释放奥术飞弹':
        'Staff imbue 1h: spell damage may cast Arcane Missiles',
    '注入法杖 1 小时：目标火焰抗性 -10': 'Staff imbue 1h: target fire res -10',
    '注入匕首 1 小时：击中时偶尔减速敌人': 'Dagger imbue 1h: hits may slow the target',
    '注入匕首 1 小时：击中时偶尔冻结敌人': 'Dagger imbue 1h: hits may freeze the target',
    '注入剑 1 小时：受近战命中时火焰冲击冷却有机会重置':
        'Sword imbue 1h: Fire Blast cooldown may reset when melee-hit',
    '注入匕首 1 小时：击中时偶尔恢复法力值': 'Dagger imbue 1h: hits may restore mana',
    '注入法杖 1 小时：法术命中几率 +3': 'Staff imbue 1h: +3 spell hit',
    '注入法杖 1 小时：法术伤害有几率提高魔杖攻速':
        'Staff imbue 1h: spell damage may raise wand attack speed',
    '注入法杖 1 小时：目标冰霜抗性 -15': 'Staff imbue 1h: target frost res -15',
    '注入法杖 1 小时：火焰伤害最多 +12': 'Staff imbue 1h: up to +12 fire dmg',
    '召唤青蛙魔宠 1 小时：智力 +6': 'Frog pet 1h: +6 Intellect',
    '召唤猫魔宠 1 小时：智力 +12': 'Cat pet 1h: +12 Intellect',
    '召唤老鼠魔宠 1 小时：智力 +2': 'Rat pet 1h: +2 Intellect',
    '蛊惑目标野兽：对你造成的伤害降低 15%':
        'Beguile target beast: its damage to you reduced by 15%',
    '目标元素生物受到你的法术伤害提高 15%':
        'Target elemental takes 15% more spell damage from you',
    '用魔法打开开锁难度 125 或更低的锁':
        'Magically open locks up to lockpicking difficulty 125',
    '对女巫之刃使用，合成第二把武器（未实装）':
        'Use on the Witchblade to craft the second weapon (not implemented)',
    '对 5 码内所有敌人造成 643–867 冰霜伤害（1 分钟冷却）':
        '643–867 frost dmg to all enemies within 5 yd (1 min cooldown)',
    '注入法杖 1 小时：火焰伤害最多 +20': 'Staff imbue 1h: up to +20 fire dmg',
    '注入法杖 1 小时：冰霜伤害最多 +20': 'Staff imbue 1h: up to +20 frost dmg',
    '注入法杖 1 小时：法术爆击几率 +5%': 'Staff imbue 1h: +5% spell crit',
    '对席瓦莱恩之刃使用，合成冷焰佩剑':
        "Use on Silverlaine's Blade to craft the saber",

    # ── 团本页（时间线 / 规则 / 倒计时）──
    '时间线': 'Timeline',
    '后续预告': 'Upcoming',
    '首批开启': 'First wave',
    '同日开启': 'Opens the same day',
    '已开启': 'Open now',
    '未公布': 'TBA',
    '地点未公布': 'Location TBA',
    '未定名团本': 'Unnamed raid',
    '国服待确定': 'To be confirmed for CN',
    '团本规则': 'Raid rules',
    '指令': 'Command',
    '人': ' players',
    '%d 年 %d 月 %d 日': '%d/%d/%d',
    '共 %d 座 · 更新于 %s': '%d raids · updated %s',
    '距首批开放还有 %d 天 %d 小时 %d 分': '%dd %dh %dm until the first wave opens',
    '官方只给了窗口，名称与地点均未公布':
        'Only a window has been announced; neither the name nor the location is revealed.',
    '排期窗口以官方公布为准，未定名的条目仍会变动':
        'Schedule windows follow official announcements; unnamed entries may still change.',
    '首发即开放 10 / 20 / 40 人团本，2027 年的后续梯队已在排期':
        '10 / 20 / 40-player raids open from launch, with later tiers already scheduled for 2027',
    '任务说明': 'Quest description',
    '点击查看详情': 'Click for details',

    # ── 专业页 · 升级页设置 ──
    '升级页设置': 'Leveling page settings',
    '当前段落高亮': 'Highlight current segment',
    '已过段落灰显': 'Dim passed segments',
    '开关窗口': 'Toggle window',
    '这里的开关只作用于「升级」页签里的制作路线（升级路线表），不影响其他页签。':
        'These toggles only apply to the crafting route on the Leveling tab (the leveling table); other tabs are unaffected.',
    '上下限跨着当前技能的段落（如下一个要练的 15~58）加一圈主题色外框':
        'Segments whose range brackets your current skill (such as 15–58 for the next one to train) get a themed outline',
    '上限低于当前技能的段落（如 42 级时的 1~15）整行灰显':
        'Segments whose maximum is below your current skill (such as 1–15 at level 42) are dimmed entirely',
    '开启后：下一个要练的段落四周显示一圈主题绿描边，一眼定位当前制作路线；外框只是描边，不影响行内容与点击。':
        'On: the next segment to train gets a green themed outline so you can spot your current route at a glance. The outline is decorative and does not affect row content or clicks.',
    '关闭后：不显示外框，该段落样式与其他行一致。':
        'Off: no outline is drawn; that segment looks like any other row.',
    '开启后：段名、出处、数量文字变暗，配方与材料图标去饱和，不再作为下一个要关注的制作目标；':
        'On: segment names, sources, and counts dim, and recipe and material icons desaturate, so it no longer reads as the next target to focus on.',
    '关闭后：所有段落恢复常规配色，不做灰显处理。':
        'Off: every segment returns to the standard colors, with no dimming.',

    # ── 帮助行 ──
    '页面': 'Page',
    '配装': 'Gear',
    '直达对应页': 'jumps straight to that page',
    '用法：/df 或 /fbsc 打开或关闭界面。':
        'Usage: /df or /fbsc toggles the window.',
    '该页面仅无限服可用，已为你打开副本页。':
        'That page is only available on the Forever server, so the dungeon list was opened instead.',

    # ── 职业指南页 · 职业排行 ──
    '职业指南': 'Class Guides',
    '指南': 'Guides',
    '职业排行': 'Spec Tiers',
    '输出': 'DPS',
    '坦克': 'Tank',
    '治疗': 'Healer',
    '排名依据': 'Ranking Criteria',
    '本档为空': 'No specs in this tier',
    '你的职业': 'Your class',
    '%s 档': 'Tier %s',
    '补丁 %s · 等级上限 %d · 已更新 %s': 'Patch %s · Level cap %d · Updated %s',

    # ── 团本页 · 套装子页 ──
    '套装': 'Sets',
    '件': ' pc',
    ' 件套': ' pieces',
    '新增': 'new',
    '改动': 'changed',
    '原样': 'unchanged',
    '挪位': 'moved',
    '基线技能': 'baseline skill',
    '%s · %d 套 / %d 职业 · 每套 %d 件 %d 项效果':
        '%s · %d sets / %d classes · %d pieces, %d bonuses each',
    '共 %d 套 · 更新于 %s': '%d sets · Updated %s',
    # 五稿（2026-10-07）：批次筛平铺 + 职业下拉 + 分节标签 + 未揭示占位卡
    '全部职业': 'All classes',
    '专属': 'Exclusive',
    '效果已公开': 'Bonuses revealed',
    '效果未揭示': 'Bonuses hidden',
    '部件编号': 'Item IDs',
    '%s · %d 套 · 效果尚未揭示（部分仅存部件编号）':
        '%s · %d sets · bonuses not yet revealed (some item IDs only)',
    '共 %d 套 · %d 套效果已公开 / %d 套待揭示':
        '%d sets · %d with bonuses revealed / %d still hidden',
    '%s · %d 套 · %d 套效果已公开 / %d 套待揭示':
        '%s · %d sets · %d with bonuses revealed / %d still hidden',
    # 六稿（2026-10-07）：主从布局——批次 × 职业筛空时的空态提示
    '没有匹配的套装': 'No matching sets',

    # ── 掉落过滤面板 ──
    '装备过滤': 'Loot Filter',
    '装备过滤设置': 'Loot Filter Settings',
    '勾选 = 我需要': 'Checked = I need it',
    '勾选全部': 'Check all',
    '取消勾选全部': 'Uncheck all',
    '新建方案': 'New preset',
    '编辑方案': 'Edit preset',
    '删除方案': 'Delete preset',
    '重命名 / 更换图标': 'Rename / change icon',
    '切换到此方案': 'Switch to this preset',
    '方案设置': 'Preset settings',
    '方案数量已达上限（最多 6 个）': 'Preset limit reached (max 6)',
    '未命名方案': 'Unnamed preset',
    '请先选择一个方案': 'Select a preset first',
    '按本职业预设重置': 'Reset to this class preset',
    '关闭过滤': 'Close filter',
    '左键开关过滤 · 右键菜单': 'Left-click to toggle filter · right-click for menu',
    '左移': 'Move left',
    '右移': 'Move right',
    '名称：': 'Name:',
    '图标：': 'Icon:',
    '本职业': 'This class',
    '-通用': '-General',

    # ── 专精指南板块页签 ──
    '专精指南': 'Spec Guides',
    '改动速览': 'Changes',
    '定位评估': 'Viability',
    '优缺点': 'Pros & Cons',
    '新手上手': 'Getting Started',
    '职业系统': 'Class Systems',
    '种族推荐': 'Races',
    '专业推荐': 'Professions',
    '输出循环': 'Rotation',
    '属性优先级': 'Stat Priority',
    '★ %s级 · %s': '★ %s tier · %s',

    # ── 快捷栏 / 专业页 / 探索页（2026-09-30 补齐：EN 表此前落后于代码，这 16 键一直缺英文）──
    '5人本专业探索': 'Dungeon Professions',
    '全部副本': 'All dungeons',
    '推荐五人本': 'Recommended dungeons',
    '当前等级暂无推荐副本': 'No recommended dungeons at your level',
    '专业列表': 'Professions',
    '只看已学': 'Learned only',
    '未学任何专业': 'No professions learned',
    '探索子页': 'Explore sub-pages',
    '未选任何探索子页': 'No explore sub-page selected',
    '奖励总览': 'Reward overview',
    '熟练度 %d/%d': 'Skill %d/%d',
    '等级 %d-%d': 'Level %d-%d',
    '未学习': 'Not learned',
    '快捷按钮栏': 'Quick bar',
    '标签页': 'Tabs',
    '显示快捷按钮栏': 'Show quick bar',
    '显示分组': 'Show groups',

    # ── 地图页（2026-09-30 新增）──
    '地图': 'Map',
    '这个副本没有客户端自带的地图。': 'No client-provided map for this dungeon.',
    '第 %d 层': 'Floor %d',

    # ── 探索页 · 小动物（2026-10-01 新增）──
    '小动物': 'Critters',
    '宠物': 'Pets',
    '宠物获取 · 共 %d 只': 'Pets · %d total',
    '点宠物名 / 区域名 / 坐标可在世界地图标记':
        'Click a pet, zone or coordinate to mark it on the world map',
    '点击在世界地图标记': 'Click to mark on the world map',
    # ★ 无坐标热点（数据侧 false = wowhead 没标坐标）只打开区域地图，提示语要分开。
    '点击打开该区域地图': 'Click to open this zone on the world map',
    '难度·组队': 'Difficulty: Group',
    '难度·单人': 'Difficulty: Solo',
    '难度·简单': 'Difficulty: Easy',
    '区域 #%d': 'Zone #%d',
    # ★ 2026-10-01 补两处历史缺口（MapUI 的 boss技能、ExploreUI 的双阵营）：
    #   这两个键一直在用，但 EN 表没登记 ⇒ gen_enus.py 的 check() 会直接退出。
    'boss技能': 'Boss Skills',
    '双阵营': 'Both factions',

    # ── 探索页 · 玩具（2026-10-04 新增，守夜人火炬）──
    '玩具': 'Toys',
    '守夜人火炬': "Night Watchman's Torch",
    '玩具 · 共 %d 件': 'Toys · %d total',
    '点名称 / 区域名 / 坐标可在世界地图标记':
        'Click a name, zone or coordinate to mark it on the world map',
    '点地名 / 坐标在世界地图标记 · 悬停物品名看提示':
        'Click a place or coordinate to mark it on the world map · hover an item name for its tooltip',
    '任务 #%d': 'Quest #%d',

    # ── 探索页 · 血色旗帜（2026-10-07 新增，独立子页）──
    '血色旗帜': 'Scarlet Banner',
    '血色旗帜 · 隐藏寻宝（已拾取）': 'Scarlet Banner · hidden treasure (looted)',
    '血色旗帜 · 隐藏寻宝（未拾取）': 'Scarlet Banner · hidden treasure (not looted yet)',

    # ── 藏品页 · 坐骑 + 任务详情（2026-10-07 补登记，先前会话遗留缺口）──
    '藏品': 'Collection',
    '坐骑 · 共 %d 匹': 'Mounts · %d total',
    '当前 %d 匹': 'Showing %d',
    '搜索坐骑…': 'Search mounts…',
    '没有匹配的坐骑': 'No mounts match',
    '自动旋转 · 拖动旋转 · 滚轮缩放': 'Auto-rotate · drag to rotate · scroll to zoom',
    '职业任务': 'Class quest',
    '商城': 'Shop',
    '传承轨迹': 'Legacy track',
    '声望': 'Reputation',
    '声望商人': 'Reputation vendor',
    '待补充': 'TBD',
    '点击查看首领详情': 'Click for boss details',

    # ── 通用控件 ──
    '设置': 'Settings',
    '确定': 'OK',
    '返回': 'Back',
    '重置': 'Reset',

    # ── 2026-10-08 补齐存量缺口：PvP 军衔页 + 专业升级 HUD（并行会话遗留未登记）──
    '%d 对 %d': '%d vs %d',
    '%d–%d 级': 'Levels %d–%d',
    '%s升级HUD': '%s Leveling HUD',
    '%s跟随完成 · %s': '%s follow finished · %s',
    '15 对 15 · 30–60 级': '15 vs 15 · Levels 30–60',
    'CP 结算存在 ±10 点的已知浮动 bug，实际结果可能相差一档；起点模拟按 0% 进度、0 荣誉计算，仅供参考':
        'Rank point settlement has a known ±10 point variance bug; actual results may differ by one tier. Simulation starts at 0% progress and 0 honor, for reference only',
    '…共 %d 种材料，进购物清单看合计': '…%d reagents total, see the shopping list',
    '一等军士长': 'First Sergeant',
    '上一步': 'Previous',
    '下士': 'Corporal',
    '不在轮换': 'Not in rotation',
    '中士': 'Sergeant',
    '中将': 'Lieutenant General',
    '传承点数 · PvP 侧共 12 点': 'Legacy points · 12 total from PvP',
    '侦察兵': 'Scout',
    '元帅': 'Marshal',
    '元素': 'Elemental',
    '共 14 级军衔 · 每阵营 15 套 · 更新于 %s': '14 ranks · 15 gear sets per faction · updated %s',
    '军团士兵': 'Legionnaire',
    '军士长': 'Master Sergeant',
    '军衔': 'Rank',
    '军衔 %d · 进度 %.1f%%': 'Rank %d · %.1f%%',
    '军衔 1 及以下无需荣誉：本周 15 次荣誉击杀即可晋级':
        'Ranks of 1 or below need no honor: 15 honorable kills this week are enough to advance',
    '军衔不会衰减：没有任何东西会扣点数，等级是一条只增不减的进度条':
        'Ranks never decay: nothing takes points away — rank is a progress bar that only goes up',
    '军衔点数来自战场与加基森 PvP 任务，荣誉另来自荣誉击杀（上限 25,000）':
        'Rank points come from battlegrounds and Gadgetzan PvP quests; honor also comes from honorable kills (cap 25,000)',
    '冲刺目标': 'Sprint goal',
    '列兵': 'Private',
    '别下水：有鲨鱼': "Don't go in the water: sharks",
    '勇士': 'Champion',
    '印记门槛：手腕 / 腰部 R8 · 脚 R9 · 手 R10 · 腿 / 肩 R12 · 胸 / 头 R13；每套另有非套装的护腕与腰带':
        'Mark requirements: wrists / belt R8 · boots R9 · hands R10 · legs / shoulders R12 · chest / head R13; each set also has non-set bracers and a belt',
    '召唤轮换 %d': 'Summon rotation %d',
    '史诗 · 装等65 · 60 级 + 蓝装 + 对应部位无畏印记':
        'Epic · ilvl 65 · level 60 + blue gear + Marks of Intrepidity for the slot',
    '司令': 'Commander',
    '周': 'Week',
    '周上限 · 按赛季累计点数': 'Weekly cap · points accumulate per season',
    '商人直卖': 'Sold by vendors',
    '四个据点加中立旗帜，先到 2,000 分获胜': 'Four bases plus a neutral flag; first to 2,000 resources wins',
    '回到当前': 'Back to current',
    '在古拉巴什竞技场击杀 25 次': '25 kills in Gurubashi Arena',
    '在四个战场阵营声望达到崇拜（各 1 点，共 4 点）': 'Exalted with all four battleground factions (1 point each, 4 total)',
    '在奥特兰克山谷击杀 200 次': '200 kills in Alterac Valley',
    '在战歌峡谷 / 阿拉希盆地 / 暗矛群岛击杀 25 次': '25 kills in Warsong Gulch / Arathi Basin / Darkspear Isles',
    '增强': 'Enhancement',
    '士官长': 'Chief Sergeant',
    '大元帅': 'Grand Marshal',
    '奥特兰克山谷': 'Alterac Valley',
    '完成 3 场战歌峡谷 / 阿拉希盆地 / 暗矛群岛战斗': 'Complete 3 Warsong Gulch / Arathi Basin / Darkspear Isles matches',
    # 2026-10-11 战场声望页（wuxianwow /factions 口径）
    '战场声望': 'Battlegrounds',
    '友善': 'Friendly',
    '崇拜': 'Exalted',
    '%d 对 %d · %d–%d 级': '%d v %d · Level %d–%d',
    '%s · %d 件': '%s · %d items',
    '阿拉索联军正试图为暴风城夺回阿拉希盆地。':
        'The League of Arathor seeks to reclaim Arathi Basin for Stormwind.',
    '污染者试图为部落夺取阿拉希盆地的重要资源。':
        'The Defilers seek to claim the resources of Arathi Basin for the Horde.',
    '灰谷地区坚定的守卫者，目前正与战歌氏族在战歌峡谷中激烈交战。':
        'Steadfast guardians of Ashenvale, now locked in battle with the Warsong clan in Warsong Gulch.',
    '战歌氏族是最具攻击性的兽人氏族，目前正与暗夜精灵的银翼哨兵部队在战歌峡谷中激烈地交战中。':
        'The most aggressive orc clan, now battling the night elves\' Silverwing Sentinels in Warsong Gulch.',
    '一群在奥特兰克山谷建立了永久居所的矮人，正与霜狼氏族的兽人激烈交战中。':
        'Dwarves who built a permanent outpost in Alterac Valley, locked in fierce combat with the Frostwolf clan.',
    '霜狼氏族正在努力将雷矛探险队赶出奥特兰克山谷。':
        'The Frostwolf clan fights to drive the Stormpike expedition out of Alterac Valley.',
    '达到崇拜解锁成就「战歌峡谷主宰」':
        'Reach Exalted to earn the "Warsong Gulch Master" achievement',
    '达到崇拜解锁成就「奥特兰克山谷主宰」':
        'Reach Exalted to earn the "Alterac Valley Master" achievement',
    '将军': 'General',
    '尊敬': 'Honored',
    '少校': 'Lieutenant Commander',
    '崇敬': 'Revered',
    '已备齐': 'Ready',
    '所有物品已备齐': 'All items stocked',
    '已学习': 'Learned',
    '已达该军衔': 'Rank already reached',
    '已过 %d 段 · %s %d–%d': 'Cleared %d segments · %s %d–%d',
    '平衡': 'Balance',
    '当前军衔：R%d · %.0f%%': 'Current rank: R%d · %.0f%%',
    '总共约%d次制作': 'About %d crafts total',
    '恢复': 'Restoration',
    '惩戒': 'Retribution',
    '战场轮换': 'Battleground rotation',
    '战斗的召唤': 'Call to Battle',
    '战歌峡谷': 'Warsong Gulch',
    '所有专精': 'All specializations',
    '技能 %d / %d': 'Skill %d / %d',
    '护卫骑士': 'Knight-Champion',
    '排队：主城战场军官 / 贫瘠之地北方城堡（传送门直达商旅海岸）· 声望：塞拉摩远征军 / 暗矛突袭者 · 30–39 级 3 枚奖章换 30 点荣誉与声望，崇拜送战袍':
        'Queue: BG officers in capital cities / North Bastion in the Barrens (portal to Merchant Coast) · Reputation: Theramore Expedition / Darkspear Raiders · levels 30–39: 3 badges for 30 honor and reputation, tabard at exalted',
    '无材料': 'No reagents',
    '无畏印记购买门槛（按部位）': 'Mark of Intrepidity purchase requirements (by slot)',
    '暗影': 'Shadow',
    '暗矛群岛': 'Darkspear Isles',
    '暗矛群岛 · 新战场': 'Darkspear Isles · new battleground',
    '最早解锁': 'Earliest unlock',
    '未学过该专业，先找训练师学习': 'Profession not learned yet — visit a trainer first',
    '本周': 'This week',
    '本周先打 %s 荣誉 → 重置后 %s': 'Farm %s honor this week → after reset %s',
    '本周增量': 'Weekly gain',
    '本周荣誉': 'Honor this week',
    '本周荣誉 %s · 荣誉击杀 %d': 'Honor this week %s · honorable kills %d',
    '本周荣誉里程碑（军衔 %d）': 'Weekly honor milestone (rank %d)',
    '材料未收录': 'Reagents not indexed',
    '材料还可制作%d次': 'reagents for %d more crafts',
    '模拟中：从 R%d 0%% 起跑（再点一次取消）': 'Simulating: starting from R%d 0%% (click again to cancel)',
    '步兵': 'Grunt',
    '武器（28 级起，另有 38 / 48 / 58 版本）': 'Weapons (from level 28, also 38 / 48 / 58 versions)',
    '段落 %d / %d': 'Segment %d / %d',
    '每周前三个战场轮流当“战斗的召唤”：暗矛群岛 → 阿拉希盆地 → 战歌峡谷，当周给更多荣誉与等级点数；各战场荣誉已拉平':
        'The first three battlegrounds take turns as the weekly "Call to Battle": Darkspear Isles → Arathi Basin → Warsong Gulch, granting extra honor and rank points that week; battleground honor has been equalized',
    '每周结算模型': 'Weekly settlement model',
    '点数': 'Points',
    '用时 %d 分 %d 秒': 'Time %d min %d sec',
    '百夫长': 'Centurion',
    '直售': 'Vendor',
    '督军': 'Warlord',
    '石头守卫': 'Stone Guard',
    '神圣': 'Holy',
    '神圣和戒律': 'Holy and Discipline',
    '第 %d 周': 'Week %d',
    '等级 4 和 10 永远不是某周的上限；第 7 周一次跳两级（等级 11 与黑色战争坐骑）；上限按赛季累计点数计算，晚开始可直接冲级':
        'Levels 4 and 10 are never a weekly cap; week 7 jumps two levels at once (level 11 and the Black War Steed); caps are based on season-accumulated points, so late starters can rush ranks',
    '累计': 'Total',
    '累计上限': 'Cumulative cap',
    '统帅': 'Lieutenant General',
    '缺%d': 'Need %d',
    '荣誉之地': 'Honor Grounds',
    '荣誉之地 · 每赛季 10 个每周任务（给荣誉与等级点数，已知目标）':
        'Honor Grounds · 10 weekly quests per season (honor and rank points, known objectives)',
    '荣誉之地第 4 / 7 / 10 周任务（各 1 点，共 3 点，跨赛季持续开放）':
        'Honor Grounds week 4 / 7 / 10 quests (1 point each, 3 total, stay open across seasons)',
    '蓝色 · 装等60 · 55 级荣誉直购，不需要军衔': 'Blue · ilvl 60 · buy directly with honor at level 55, no rank required',
    '血卫士': 'Blood Guard',
    '购物清单': 'Shopping list',
    '购物（从当前段累计到 300，含银行）': 'Shopping (accumulated to 300 from the current segment, incl. bank)',
    # 2026-10-11 升级 HUD 购物清单：「仅显示缺失」视图开关（表头右侧，开关左侧带同字标签）
    ' · 共%d种': ' · %d items',
    '仅显示缺失': 'Missing only',
    '开启：购物清单只列出还缺的材料，已备齐的自动隐藏。':
        'On: only list reagents you still need; fully stocked ones are hidden.',
    '赢得 10 场决斗': 'Win 10 duels',
    '赢得一场任意战场战斗': 'Win any battleground match',
    '起点模拟 0%': 'Start simulation 0%',
    '距每周重置 %d 天 %02d 小时': 'Weekly reset in %d days %02d hours',
    '路径卡住：当前进度无法继续推进': 'Path stuck: current progress cannot advance',
    '跳档': 'Tier skip',
    '达到 %s：约 %d 周 · 共 %s 荣誉': 'Reach %s: about %d weeks · %s honor total',
    '达到军衔': 'Reach rank',
    '达到军衔 3 / 7 / 10 / 13 / 14（各 1 点，共 5 点）': 'Reach ranks 3 / 7 / 10 / 13 / 14 (1 point each, 5 total)',
    '达到军衔后，在暴风城的勇士大厅 / 奥格瑞玛的传说大厅购买奖励；点数按赛季累计，升级不消耗':
        "After reaching a rank, buy rewards in the Champion's Hall in Stormwind / Hall of Legends in Orgrimmar; points accumulate per season and are not spent on ranking up",
    '重置后场景（需至少 15 次本周荣誉击杀才结算）': 'Post-reset scenario (settles only with at least 15 honorable kills this week)',
    '野性战斗': 'Feral Combat',
    '阿拉希盆地': 'Arathi Basin',
    '饰品 / 戒指 / 披风': 'Trinkets / rings / cloaks',
    '骑士': 'Knight',
    '骑士中尉': 'Knight-Lieutenant',
    '骑士队长': 'Knight-Captain',
    '高阶军士': 'Sergeant Major',
    '高阶督军': 'High Warlord',

    # ── 2026-10-08 新增：购物清单一键导入 Auctionator（AuctionatorBridge / ProfFollow）──
    '[DF] %s购物清单': '[DF] %s shopping list',
    '已导入 Auctionator：%s（共 %d 种）': 'Imported to Auctionator: %s (%d items)',
    '导入失败：': 'Import failed: ',
    '购物清单为空，没有可导入的物品': 'Shopping list is empty — nothing to import',
    '未检测到 Auctionator，请复制以下导入串': 'Auctionator not detected — copy the import string below',
    '未检测到 Auctionator，请在 Auctionator → 购物清单 → 导入 中粘贴':
        'Auctionator not detected — paste this in Auctionator → Shopping Lists → Import',
    '一键导入购物清单': 'Import shopping list',
    '一键导入': 'Import',
    '大约还需制作%d次': '~%d crafts remaining',
    '一键导入到拍卖行': 'Import to Auctionator',
    '将当前购物清单导入 Auctionator 的购物清单，只导入还缺的数量，同名清单将被覆盖。':
        'Imports the current shopping list into Auctionator (missing quantity only); a list with the same name will be replaced.',
    # ── 2026-10-10 补登记：升级页跳转制造 / 成本列（ProfFollow，此前漏登记致 enUS 拒生成）──
    '~%d 次制作': '~%d crafts',
    '≈%d 次制作': '≈%d crafts',
    '%d 次制作': '%d crafts',
    '制作成本': 'Craft cost',
    '制作次数': 'Crafts',
    '单次花费': 'Cost per craft',
    '总花费': 'Total cost',
    '段落': 'Range',
    '%s级怪物': '%s mobs',
    '%d级可接': 'Requires level %d',
    '总价格': 'Total price',
    '拍卖总价': 'AH total',
    '制造总价': 'Craft total',
    '遭劫货物': 'Plundered Goods',
    '装填成本': 'Fill cost',
    '装填材料': 'Fill materials',
    '物品等级 %d': 'Item level %d',
    '锭与石材': 'Ingots & Stone',
    '草药': 'Herbs',
    '皮革': 'Leather',
    '附魔材料': 'Enchanting mats',
    '药水与药剂': 'Potions & Elixirs',
    '食物': 'Food',
    '绷带': 'Bandages',
    '炸弹与装置': 'Bombs & Devices',
    '武器与护甲': 'Weapons & Armor',
    '数据不一致': 'Mismatched',
    '直接买齐': 'Buy all on AH',
    '自己制造': 'Craft it yourself',
    '制造合计': 'Craft total',
    '每次制作 ×%d': 'Crafts ×%d',
    '自己造省': 'Crafting saves',
    '直接买便宜': 'Buying is cheaper',
    '拍卖单价 %s · 卖店价 %s': 'AH unit %s · Vendor %s',
    '自身价格': 'Own price',
    '本专业': 'This profession',
    '已学': 'Learned',
    '制造成本': 'Crafting cost',
    '成本: %s': 'Cost: %s',
    '卖店: %s': 'Vendor: %s',
    '拍卖': 'Auction',
    '拍卖: %s': 'Auction: %s',
    '差价: %s': 'Diff: %s',
    '差价': 'Diff',
    '材料': 'Materials',
    '难度': 'Difficulty',
    '跳转制造': 'Jump to craft',
    '该配方还未学会，先找训练师学习': 'Recipe not learned yet — learn it from a trainer first',
    # ── 2026-10-11 补登记：板条箱 / 工匠文书页（ProfessionUI）──
    '板条箱': 'Crates',
    '工匠文书': 'Artisan Writs',
    '自身成本': 'Item price',
    '拍卖价从低到高': 'Auction price: low to high',
    '名称': 'Name', '类型': 'Type', '来源': 'Source',
    '最低成本': 'Best cost',
    '交付物': 'Deliverable',
    '总成本': 'Total cost',
    '文书自身 %s': 'Writ price %s',
    '材料明细': 'Materials',
    '自己制造材料明细': 'Craft materials',
    '制造一次': 'One craft',
    '制造一次的成本': 'Cost per craft',
    '制造上交所需物的成本': 'Cost per turn-in',
    '成本汇总': 'Cost summary',
    '文书自身成本': 'Writ cost',
    '直接买齐总成本': 'Buy-all total',
    '自己制造总成本': 'Craft-all total',
    '最省': 'Cheapest',
    '每点声望最低成本': 'Best cost per rep',
    '每点青睐的最低成本': 'Best cost per favor',
    '总结': 'Summary',
    '未登记配方': 'No recipe on record',
    '学徒': 'Apprentice',
    '熟练': 'Journeyman',
    '专家': 'Expert',
    '工匠': 'Artisan',
    '凑法（任满其一）': 'Fill options (any one)',
    '声望 +%d': 'Rep +%d',
    '声望 +%d · 需等级 %d': 'Rep +%d · Req. level %d',
    '声望未验证': 'Reputation unverified',
    '青睐 +%d': 'Favor +%d',
    '青睐未验证': 'Favor unverified',
    '购买 %s': 'Buy %s',
    ' · 需等级 %d': ' · Req. level %d',
    '需求数量': 'Required qty',
    '拍卖单价': 'AH unit price',
    '卖店价': 'Vendor price',
    '配方数据未就绪，稍后再试': 'Recipe data not ready — try again later',
    '材料不足，先按购物清单备齐再制造': 'Not enough materials — restock per the shopping list before crafting',
    '无法自动打开专业面板，请手动打开后重试': 'Could not open the profession panel automatically — open it manually and retry',
    '面板已打开但未能自动定位配方，请在列表中手动选择': 'Panel is open but the recipe could not be located — pick it manually from the list',
    '已选中配方 %s，请在专业面板输入制造数量': 'Recipe %s selected — enter the craft quantity in the profession panel',
    '正在打开专业面板并定位 %s（预填数量 %d）…': 'Opening the profession panel and locating %s (quantity %d)…',
    '已定位配方 %s，预填制造数量 %d —— 在专业面板点一次制造即可': 'Recipe %s located, craft quantity pre-filled (%d) — click Craft once in the profession panel',
    '打开专业面板并自动定位当前段配方、预填制造数量；在面板内点一次制造即可批量完成。':
        'Opens the profession panel, locates the recipe for the current segment and pre-fills the quantity; click Craft once in the panel to batch-craft.',
    '装备库': 'Gear Library', '全部装备': 'All gear', '护甲': 'Armor',
    '饰品与穿戴': 'Accessories & Worn', '武器': 'Weapons',
    '头部': 'Head', '肩部': 'Shoulder', '手腕': 'Wrist', '手部': 'Hands',
    '腰部': 'Waist', '腿部': 'Legs', '脚部': 'Feet', '背部': 'Back',
    '颈部': 'Neck', '手指': 'Finger', '盾牌 · 副手': 'Shield & Off-hand',
    '单手 · 主手': 'One-Hand & Main Hand', '双手': 'Two-Hand', '远程': 'Ranged',
    '稀有程度': 'Quality', '过滤器': 'Filters', '等级范围': 'Level range',
    '只显示可用种类': 'Only usable types', '来源不明': 'Unknown source',
    '来源：商人': 'Source: Vendor', '来源：怪物掉落': 'Source: Mob drop',
    '来源：世界掉落': 'Source: World drop', '来源：5人本掉落': 'Source: Dungeon drop',
    '来源：团本掉落': 'Source: Raid drop', '来源：任务奖励': 'Source: Quest reward',
    '来源：专业制作': 'Source: Crafted', '来源：不明': 'Source: Unknown',
    '★ 专属': '★ Exclusive', '效果尚未揭示': 'Bonuses not yet revealed', '该筛选下暂无套装': 'No sets match the current filter',
    '需要等级': 'Req. level', '物品等级': 'Item level',
    '上一页': 'Prev', '下一页': 'Next',
    '第 %d / %d 页 · 共 %d 件': 'Page %d / %d · %d items', '共 %d 件': '%d items',
    '加入心愿清单': 'Add to wishlist', '移出心愿清单': 'Remove from wishlist',
    '没有匹配的装备': 'No gear matches the filters',
    '传说': 'Legendary', '史诗': 'Epic', '精良': 'Rare', '优秀': 'Uncommon',
    '普通': 'Common', '粗糙': 'Poor',
    '等级 %d': 'Level %d',
    '当前筛选无匹配装备（全库共 %d 件，可点品质标签取消筛选）':
        'No gear matches the current filters (%d items in the library; click the quality chips to clear filters)',
    '装备目录为空': 'Gear library is empty',
    '力量': 'Strength', '敏捷': 'Agility', '智力': 'Intellect', '耐力': 'Stamina',
    '命中等级': 'Hit Rating', '暴击等级': 'Crit Rating', '急速等级': 'Haste Rating',
    '%d 项属性': '%d Stats',
    '未识别': 'Unresolved',
    '未识别物品 #%d': 'Unresolved item #%d',
    '正在向服务器查询物品数据…': 'Fetching item data from server...',
    '披风': 'Cloak', '杂项': 'Miscellaneous', '杂件': 'Odds & Ends', '装饰品': 'Cosmetic',
    '副手物品': 'Held In Off-hand', '单手': 'One-Hand', '圣物': 'Relic',
    '弹药': 'Ammo', '投掷': 'Thrown', '盾牌': 'Shield', '背包': 'Bag', '衬衫': 'Shirt',
    '心愿清单': 'Wishlist', '套装': 'Sets',
    '开放世界': 'Open world', '任务奖励': 'Quest rewards', '商人': 'Vendor',
    '专业制作': 'Crafted', '其他来源': 'Other sources',
    '%s · %d 件': '%s · %d items', '%d 件套': '%d-piece set', '%d 件：%s': '%d pieces: %s',
    '清空': 'Clear', 'Shift+点击确认清空': 'Shift+click to confirm clearing',
    '还没有收藏的装备：在装备列表悬停行星标，点 ☆ 即可加入心愿清单':
        'Nothing collected yet: hover a gear row and click the star to add it to the wishlist',
    '共 %d 套': '%d sets', '第 %d / %d 页 · 共 %d 套': 'Page %d / %d · %d sets',
    # ── 职业指南 · 战斗页（输出循环 / 宏命令，2026-10-16）──
    '文字攻略': 'Written Guide', '宏命令': 'Macros',
    '自上而下 = 优先级，用第一个就绪的': 'Top to bottom = priority; use the first one that is ready',
    '金色 = 以后才解锁': 'Gold = unlocked later',
    '点击拣起放入动作条': 'Click to pick it up for your action bar',
    '已掌握': 'Known', 'Lv %d 解锁': 'Unlocks at Lv %d',
    '暂无输出循环数据': 'No rotation data for this spec yet',
    '已可用': 'Ready now', '稍后': 'Later',
    '点击创建宏': 'Click to create', 'Shift+点击复制': 'Shift+click to copy',
    '还缺技能：%s': 'Missing: %s',
    '暂无宏数据': 'No macro data for this class yet',
    '战斗状态无法创建宏': "Can't create macros in combat",
    '战斗状态无法拣起法术': "Can't pick up a spell in combat",
    '宏已创建：%s · 用 /macro 拖到动作条': 'Macro created: %s · open /macro and drag it to your bar',
    '创建失败：角色宏已达上限': 'Failed: character macro limit reached',
    'Ctrl+C 复制': 'Ctrl+C to copy',
    '还缺技能': 'Missing skills', '单体目标': 'Single target', '多目标': 'Multi-target (AoE)', '暂无 AOE 循环数据': 'No AoE rotation data yet',
    '详解': 'Details', '用途': 'What for', '创建宏': 'Create macro', '复制': 'Copy',
    '宏命令详解': 'Macro explained',
    '%d 级': 'Lv %d', '%d 步': '%d steps',
    '任务链': 'Quest chain', '本链总奖励': 'Chain rewards',
    '技能': 'Ability', '技能 #%d': 'Ability #%d', '第 %d / %d 步': 'Step %d of %d',
    '链内进度': 'In chain', '限定种族': 'Races',
    '暂无职业任务数据': 'No class quest data for this class yet',
    '当前筛选下没有任务': 'No quests match this filter',
    '全部种族': 'All races',
    '种族': 'Race',
    '全部任务': 'All quests',
    '全部阵营': 'All factions',
    '本表未收录这个任务的数据': 'This quest is not in the table yet',
}

# ── 生成 ────────────────────────────────────────────────────────────────────
FMT = re.compile(r'%(?:%|[ds])')

def fmt_tokens(s):
    return sorted(FMT.findall(s))

def check():
    # 收集全部 L 键
    keys = set()
    for name in os.listdir(CORE):
        if name.endswith('.lua'):
            s = open(os.path.join(CORE, name), 'rb').read().decode('utf-8')
            keys.update(re.findall(r'L\["([^"]*[\u4e00-\u9fff][^"]*)"\]', s))
    s = open(os.path.join(DF, 'Locales', 'zhCN.lua'), 'rb').read().decode('utf-8')
    keys.update(re.findall(r'^L\["([^"]+)"\]\s*=', s, re.M))
    missing = sorted(k for k in keys if k not in EN)
    # EN 里的死键（代码已不用的）只提醒不退出
    dead = sorted(k for k in EN if k not in keys)
    if missing:
        print('EN 表缺 %d 键：' % len(missing))
        for k in missing:
            print('  -', k)
        sys.exit(1)
    # 格式符校验
    bad = []
    for k, v in EN.items():
        if k not in keys:
            continue
        if fmt_tokens(k) != fmt_tokens(v):
            bad.append((k, v))
    if bad:
        print('格式符不一致 %d 条：' % len(bad))
        for k, v in bad:
            print('  键[%s] 值[%s]' % (k, v))
        sys.exit(1)
    # 颜色码校验
    for k, v in EN.items():
        if k not in keys:
            continue
        if sorted(re.findall(r'\|cff[0-9a-fA-F]{6}|\|r', k)) != sorted(re.findall(r'\|cff[0-9a-fA-F]{6}|\|r', v)):
            print('颜色码不一致：键[%s] 值[%s]' % (k, v))
            sys.exit(1)
    # 选一系自对查
    if EN['选一'] not in EN['二选一'] or EN['选一'] not in EN['三选一']:
        print('选一系子串约束破坏：%r 必须是 %r / %r 的子串'
              % (EN['选一'], EN['二选一'], EN['三选一']))
        sys.exit(1)
    return keys, dead

def lua_str(s):
    return '"%s"' % s.replace('\\', '\\\\').replace('"', '\\"')

def main():
    keys, dead = check()
    lines = [
        '-- =============================================================================',
        '-- DungeonsForever · English (enUS) overlay',
        '-- Generated by _temp/gen_enus.py — DO NOT hand-edit.',
        '-- Corrections go back into the EN table in that script, then re-run it.',
        '-- =============================================================================',
        '',
        'local _, ns = ...',
        '',
        'if (type(GetLocale) ~= "function") or GetLocale() ~= "enUS" then return end',
        '',
        'local L = ns.L',
        '',
    ]
    for k in sorted(EN):
        if k not in keys:
            continue
        lines.append('L[%s] = %s' % (lua_str(k), lua_str(EN[k])))
    open(DST, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
    print('enUS.lua：%d 条（登记 %d / 键总数 %d）；死键提醒 %d'
          % (sum(1 for k in EN if k in keys), len(EN), len(keys), len(dead)))
    if dead:
        for k in dead:
            print('  死键：', k)

if __name__ == '__main__':
    main()
