# -*- coding: utf-8 -*-
# 修 fc_pins.py 的 head 模板：object 格式加层号、去 rare 行、补稀有钉不登记说明
import io

P = 'fc_pins.py'
s = io.open(P, encoding='utf-8', newline='').read()

old1 = '-- 无限副本手册 · 副本内地图钉点（入口 / 任务 / 物品 / 稀有）\n'
new1 = '-- 无限副本手册 · 副本内地图钉点（入口 / 任务 / 任务物品）\n'
assert s.count(old1) == 1, s.count(old1)
s = s.replace(old1, new1, 1)

old2 = ("--   object   = { { x%, y%, itemID }, … },    -- 任务物品拾取点（图标/名字运行期问客户端）\n"
        "--   rare     = { { x%, y%, npcID, 名 }, … }, -- 稀有怪（npcID=0 表示自定义怪、无官方 ID）\n")
new2 = "--   object   = { { x%, y%, itemID, 层号 }, … }, -- 任务物品拾取点（图标/名字运行期问客户端）\n"
assert s.count(old2) == 1, s.count(old2)
s = s.replace(old2, new2, 1)

old3 = '--   · 坐标 = 地图画布百分比（与 ns.BossPos 同口径）；省略层号 = 只对第 1 层有效。\n'
new3 = ('--   · 坐标 = 地图画布百分比（与 ns.BossPos 同口径）；层号省略 = 只对第 1 层有效。\n'
        '--   · 稀有怪不在此登记：fc 的稀有钉已全部由 ns.BossPos 以首领钉覆盖（防重复、楼层以\n'
        '--     BossPos 为准）；渲染端 rare 分支保留给将来 BossPos 没有的稀有怪。\n')
assert s.count(old3) == 1, s.count(old3)
s = s.replace(old3, new3, 1)

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('fc_pins.py head 模板已更新')
