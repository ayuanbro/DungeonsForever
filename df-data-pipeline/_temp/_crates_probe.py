# -*- coding: utf-8 -*-
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from lupa import lua51
L = lua51.LuaRuntime(encoding=None)
src = open(r'D:/Game/World of Warcraft/_classic_beta_/Interface/AddOns/WaylaidForever/Catalog.lua', 'rb').read()
L.globals()[b'SRC'] = src
dbg = r'''
local F = {}
assert(loadstring(SRC))(nil, F)
local n = 0
for _, c in ipairs(F.catalog.crates) do
  n = n + 1
  if c.favor == nil or c.tier == nil or c.level == nil or c.id == nil or c.options == nil then
    local ks = {}
    for k in pairs(c) do ks[#ks+1] = tostring(k) end
    print('crate #' .. n .. ' missing fields, has: ' .. table.concat(ks, ','))
  end
end
for _, w in ipairs(F.catalog.writs) do
  if w.questId == nil or w.targetId == nil then
    print('writ missing fields: ' .. tostring(w.id))
  end
end
return n
'''
print('crates ok, count =', L.execute(dbg))
