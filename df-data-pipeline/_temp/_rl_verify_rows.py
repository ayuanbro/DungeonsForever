# -*- coding: utf-8 -*-
"""用真 Lua 5.1 加载 Data_DungeonQuests.lua，逐条核对洛丹伦废墟任务的字段。"""
import io
import os

from lupa import LuaRuntime

HERE = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(HERE, '..', 'Core', 'Data', 'Data_DungeonQuests.lua')
FS = os.path.join(HERE, '..', 'Core', 'Data', 'enUS', 'Data_DungeonQuests.lua')
FZ = os.path.join(HERE, '..', 'Core', 'Data', 'zhTW', 'Data_DungeonQuests.lua')

FIELDS = ['questID', '阵营', '可接等级', '任务等级', '起始NPC', '起始地点', '前置名', '副本内',
          '前置ID', '奖励物品ID', '任务目标', '任务注释', '难度档位', '需要提供物品ID',
          '职业限制', '起始NPCID', '起始NPC名', '收获']


def load(path, locale='zhCN'):
    L = LuaRuntime(unpack_returned_tuples=True)
    src = io.open(path, 'rb').read()
    ns = L.table()
    if locale == 'zhCN':
        L.execute(src, None, ns)
    else:
        # 覆盖层需要 GetLocale 才不秒退
        L.execute(b'function GetLocale() return "%s" end' % locale.encode())
        L.execute(src, None, ns)
    return ns


ns = load(F)
d = ns['DungeonQuests']['ruins_of_lordaeron']
print('== zhCN 洛丹伦废墟任务 %d 条 ==' % len(d))
for i in range(1, len(d) + 1):
    r = d[i]
    print('%6d %s 副本内=%-5s 起始=%-14s 注释=%s'
          % (r[1], r[2] or '-', str(r[8]), str(r[17]), (r[12] or '')[:46]))
    assert r[12], '缺注释: %d' % r[1]
print('全部 %d 条均有注释 ✓' % len(d))
