# -*- coding: utf-8 -*-
"""gen_enus_data.py 加 Data_MapPins 的稀有怪名精确表。"""
src = open('_temp/gen_enus_data.py', encoding='utf-8').read()
a = "FILE_SPECIFIC = {\n    'Data_DungeonQuests.lua': dict(DQ1.FILE_EXACT),\n    'Data_ClassTier.lua': dict(DT.TIER),\n}"
assert a in src, '锚点'
src = src.replace(a, (
    "FILE_SPECIFIC = {\n"
    "    'Data_DungeonQuests.lua': dict(DQ1.FILE_EXACT),\n"
    "    'Data_ClassTier.lua': dict(DT.TIER),\n"
    "    # Data_MapPins 稀有怪名（wowhead 官方英文名；Bruegal Ironknuckle 本就是 ASCII 直过）\n"
    "    'Data_MapPins.lua': {\n"
    "        '黑铁大使': 'Dark Iron Ambassador',\n"
    "        '死亡之誓': 'Deathsworn Captain',\n"
    "        '矿工约翰森': 'Miner Johnson',\n"
    "    },\n"
    "}"))
open('_temp/gen_enus_data.py', 'w', encoding='utf-8', newline='\n').write(src)
print('已加 FILE_SPECIFIC 条目')
