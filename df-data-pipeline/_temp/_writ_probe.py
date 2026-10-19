# -*- coding: utf-8 -*-
# 临时探针：看 writs 条目字段（含任务名/名字类字段）
from lupa import lua51

L = lua51.LuaRuntime(encoding=None)
src = open(r'D:/Game/World of Warcraft/_classic_beta_/Interface/AddOns/WaylaidForever/Catalog.lua', 'rb').read()
L.globals()[b'SRC'] = src
dbg = '''
local F = {}
assert(loadstring(SRC))(nil, F)
local w = F.catalog.writs
for i = 1, 3 do
  local keys = {}
  for k, v in pairs(w[i]) do keys[#keys+1] = k .. '=' .. tostring(v) end
  print(table.concat(keys, ', '))
end
return #w
'''
print('count:', L.execute(dbg))
