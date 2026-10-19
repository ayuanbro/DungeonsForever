# -*- coding: utf-8 -*-
"""把 df_dungeon_check.py 里的自制图断言从「1024×1024 方图 + UV 裁 682/1024」切到「663×442 贴图即画面 + UV 取满」。"""
import io

P = 'df_dungeon_check.py'
s = io.open(P, encoding='utf-8').read()

reps = []

reps.append((
'''         and math.abs((select(2, _MM.CustomFor("hall_of_thanes")) or 0) - 682 / 1024) < 1e-9
         and math.abs((select(2, _MM.CustomFor("excavation_wetlands")) or 0) - 682 / 1024) < 1e-9''',
'''         and (select(2, _MM.CustomFor("hall_of_thanes")) or 0) == 1
         and (select(2, _MM.CustomFor("excavation_wetlands")) or 0) == 1
         and _MM.CUSTOM_W == _MM.MAP_W and _MM.CUSTOM_H == _MM.FRAME_H'''))

reps.append((
'''      ck("★★ 按层自制的 UV 口径与整图自制**同一套**（都取顶部 682/1024 ≈ 3:2，别各写一个数）",
         math.abs((select(2, _MM.CustomFloorFor("city_of_dalaran", 1)) or 0) - 682 / 1024) < 1e-9
         and math.abs((select(2, _MM.CustomFor("hall_of_thanes")) or 0) - 682 / 1024) < 1e-9)''',
'''      ck("★★ 按层自制的 UV 口径与整图自制**同一套**（贴图即画面 ⇒ 都取满，恒 1，别各写一个数）",
         (select(2, _MM.CustomFloorFor("city_of_dalaran", 1)) or 0) == 1
         and (select(2, _MM.CustomFor("hall_of_thanes")) or 0) == 1)'''))

reps.append((
"""ck('★★ ㊶ 按层自制与整图自制**共用同一条 UV 口径**（`SetTexCoord(0, 1, 0, cv1)` 全仓只此两处，682/1024 也只写一处）',
   _mui3_src.count('SetTexCoord(0, 1, 0, cv1)') == 2
   and 'M.CUSTOM_VH = 682' in _mui3_src
   and 'M.CUSTOM_CANVAS = 1024' in _mui3_src
   and 'return path, M.CUSTOM_VH / M.CUSTOM_CANVAS' in _mui3_src)""",
"""ck('★★ ㊶ 按层自制与整图自制**共用同一条 UV 口径**（`SetTexCoord(0, 1, 0, cv1)` 全仓只此两处，'
   '且两个入口都恒 `return path, 1` —— 贴图即画面、UV 取满，别再冒出第二个数）',
   _mui3_src.count('SetTexCoord(0, 1, 0, cv1)') == 2
   and _mui3_src.count('    return path, 1' + chr(10)) == 2
   and 'M.CUSTOM_W = 663' in _mui3_src
   and 'M.CUSTOM_H = 442' in _mui3_src)"""))

reps.append((
"""ck('★★ ㊶ Media/Maps/Dalaran.tga / ExcavationSite.tga 存在，且**18 字节头与既有自制图逐字节相同**'
   '（1024×1024 / 24 位 / 类型 10 = RLE / 描述符 0 = 原点左下；差一个字段就是另一条加载路径）',
   len(_dal_hdr) == 18 and _dal_hdr == _hall_hdr and _wet_hdr == _hall_hdr,
   repr(_dal_hdr) + ' | ' + repr(_wet_hdr))
ck('★ ㊶ 自制图体积 <= 2.5MB —— 画面只占顶部 682 行、下方 342 行纯黑被 RLE 压掉'
   '（若整张 1024×1024 都当画面，体积会冲到 3.0MB ⇒ 这条能兜住「贴错位置」）',
   os.path.getsize(_WET_TGA) < 2560 * 1024 and os.path.getsize(_DAL_TGA) < 2560 * 1024,
   os.path.getsize(_WET_TGA))""",
"""ck('★★ ㊶ Media/Maps/Dalaran.tga / ExcavationSite.tga 存在，且**18 字节头与既有自制图逐字节相同**'
   '（**663×442** / 24 位 / 类型 10 = RLE / 描述符 0 = 原点左下；差一个字段就是另一条加载路径）',
   len(_dal_hdr) == 18 and _dal_hdr == _hall_hdr and _wet_hdr == _hall_hdr
   and _hall_hdr[12:16] == bytes((0x97, 0x02, 0xBA, 0x01)),
   repr(_dal_hdr) + ' | ' + repr(_wet_hdr))
ck('★ ㊶ 自制图体积 <= 1.5MB —— 贴图就是画布画面（663×442），没有黑边可省'
   '（若误做成 1024×1024 方图会冲到 2.0MB ⇒ 这条能兜住「拿错规格」）',
   os.path.getsize(_WET_TGA) < 1536 * 1024 and os.path.getsize(_DAL_TGA) < 1536 * 1024,
   os.path.getsize(_WET_TGA))"""))

for old, new in reps:
    c = s.count(old)
    assert c == 1, ('count=%d' % c, old[:60])
    s = s.replace(old, new)

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('df_dungeon_check.py ok (4 处)')
