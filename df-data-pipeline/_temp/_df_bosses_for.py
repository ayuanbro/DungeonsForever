# -*- coding: utf-8 -*-
"""载入 BossPos + DungeonLoot + DungeonGuide，复算 BossesFor 口径与洛丹伦废墟攻略覆盖。"""
import os

from lupa import lua51

DF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(p):
    return open(os.path.join(DF, p), 'rb').read().decode('utf-8')


lua = lua51.LuaRuntime(unpack_returned_tuples=True)
lua.execute('ns = {}')
run = lua.eval('function(code) local f = loadstring(code); return f("DungeonsForever", ns) end')
for f in ('Core/Data/Data_BossPos.lua', 'Core/Data/Data_DungeonLoot.lua',
          'Core/Data/Data_DungeonGuide.lua', 'Core/Data/Data_Dungeons.lua'):
    run(read(f))

res = lua.execute(r'''
local out = {}
local bp = ns.BossPos or {}
local function hasGuide(id, en)
  local g = ns.DungeonGuide and ns.DungeonGuide[id]
  local bs = g and g.bosses
  if type(bs) ~= "table" then return false end
  for i = 1, #bs do if bs[i] and bs[i].en == en then return true end end
  return false
end
for id, loot in pairs(ns.DungeonLoot or {}) do
  local n, named, pinned, guided = 0, 0, 0, 0
  for i = 1, #loot do
    local s = loot[i]
    local hasPin = (bp[id] and bp[id][s[1]]) and true or false
    local hasGd = hasGuide(id, s[1])
    if (s[4] and s[4] ~= "") or hasPin or hasGd then
      n = n + 1
      if hasPin then pinned = pinned + 1 end
      if hasGd then guided = guided + 1 end
      if s[4] and s[4] ~= "" then named = named + 1 end
    end
  end
  out[#out+1] = { id = id, n = n, named = named, pinned = pinned, guided = guided }
end
local g = ns.DungeonGuide and ns.DungeonGuide["ruins_of_lordaeron"]
local gn = 0
if g and g.bosses then gn = #g.bosses end
return { rows = out, gn = gn }
''')

rows, gn = res['rows'], res['gn']
rows = sorted([(rows[k]['id'], rows[k]['n'], rows[k]['named'], rows[k]['pinned'], rows[k]['guided'])
               for k in rows.keys()])
for r in rows:
    print('%-24s total=%2d named=%2d pinned=%2d guided=%2d' % r)
print('洛丹伦废墟 攻略 boss 数 =', gn)
print('副本总数 =', len(rows))
