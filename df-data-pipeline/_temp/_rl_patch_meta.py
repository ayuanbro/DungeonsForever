# -*- coding: utf-8 -*-
"""攻略页收尾：DungeonUI 拼接串、toc 加载清单、enUS 界面文案表。"""
import io
import sys

def patch(path, pairs):
    raw = io.open(path, 'rb').read().decode('utf-8')
    crlf = '\r\n' in raw
    src = raw.replace('\r\n', '\n') if crlf else raw
    for tag, old, new in pairs:
        n = src.count(old)
        if n != 1:
            print('!! [%s/%s] 命中 %d 次' % (path, tag, n))
            sys.exit(1)
        src = src.replace(old, new)
        print('OK  [%s / %s]' % (path, tag))
    out = src.replace('\n', '\r\n') if crlf else src
    io.open(path, 'wb').write(out.encode('utf-8'))

# ── 1. DungeonUI：阵营前缀改为整串键（enUS 下冒号也要跟着变）──
patch('Core/DungeonUI.lua', [
    ('部落前缀',
     '''putT(L["部落"] .. "：" .. g.entrance.H, C_TEXT, 4, 6)''',
     '''putT(L["部落："] .. g.entrance.H, C_TEXT, 4, 6)'''),
    ('联盟前缀',
     '''putT(L["联盟"] .. "：", C_TEXT, 4, 2)''',
     '''putT(L["联盟："], C_TEXT, 4, 2)'''),
])

# ── 2. toc：三语言各加一份攻略数据 + 描述补「攻略」──
patch('DungeonsForever.toc', [
    ('zhCN 数据',
     'Core\\Data\\Data_DungeonQuests.lua\nCore\\Data\\Data_NPCLoc.lua',
     'Core\\Data\\Data_DungeonQuests.lua\nCore\\Data\\Data_DungeonGuide.lua\nCore\\Data\\Data_NPCLoc.lua'),
    ('zhTW 覆盖层',
     'Core\\Data\\zhTW\\Data_DungeonQuests.lua\nCore\\Data\\zhTW\\Data_NPCLoc.lua',
     'Core\\Data\\zhTW\\Data_DungeonQuests.lua\nCore\\Data\\zhTW\\Data_DungeonGuide.lua\nCore\\Data\\zhTW\\Data_NPCLoc.lua'),
    ('enUS 覆盖层',
     'Core\\Data\\enUS\\Data_DungeonQuests.lua\nCore\\Data\\enUS\\Data_NPCLoc.lua',
     'Core\\Data\\enUS\\Data_DungeonQuests.lua\nCore\\Data\\enUS\\Data_DungeonGuide.lua\nCore\\Data\\enUS\\Data_NPCLoc.lua'),
    ('Notes-zhCN',
     '## Notes-zhCN: 无限 副本手册：副本列表 / 详情 / 掉落 / 任务（无限服另含专业页）',
     '## Notes-zhCN: 无限 副本手册：副本列表 / 详情 / 掉落 / 任务 / 攻略（无限服另含专业页）'),
    ('Notes-zhTW',
     '## Notes-zhTW: 無限 副本手冊：副本列表 / 詳情 / 掉落 / 任務（無限服另含專業頁）',
     '## Notes-zhTW: 無限 副本手冊：副本列表 / 詳情 / 掉落 / 任務 / 攻略（無限服另含專業頁）'),
    ('Notes-enUS',
     '## Notes-enUS: Dungeon handbook: dungeon list / details / loot / quests (profession page on Forever server only)',
     '## Notes-enUS: Dungeon handbook: dungeon list / details / loot / quests / guides (profession page on Forever server only)'),
])

# ── 3. gen_enus.py：EN 表补界面文案 ──
patch('_temp/gen_enus.py', [
    ('EN 表',
     """    '说明': 'Guide', '注释': 'Notes', '要点': 'Key points', '简介': 'Overview',""",
     """    '说明': 'Guide', '注释': 'Notes', '要点': 'Key points', '简介': 'Overview',
    '攻略': 'Guide', '副本须知': 'Things to know', '怎么进本': 'How to get there',
    'BOSS 打法': 'Boss strategies', '小怪应对': 'Trash mobs',
    '部落：': 'Horde: ', '联盟：': 'Alliance: ',
    '这个副本还没有攻略，数据补上后会自动出现。':
        'No guide for this dungeon yet — it will appear once the data is added.',"""),
])

print('\n全部完成')
