# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tf_dryrun as T          # noqa: E402
from lupa import lua51         # noqa: E402

ADDON = r'D:\workspace\DungeonsForever'
lua = lua51.LuaRuntime(unpack_returned_tuples=True)
lua.execute(T.STUB)
lua.execute('os = nil')
lua.execute('time = function() return 1 end')
lua.execute('UnitClass = function() return "战士", "WARRIOR", 1 end')
lua.execute('ADDON_ROOT = %r' % ADDON.replace('\\', '/'))
lua.execute('TF_NS = TF_NS or {}')
lua.execute('do local o = GetBuildInfo; GetBuildInfo = function(...) '
            'local a,b,c,d = o(...); return a,b,c,16001,e end end')

files = [l.strip().replace('\\', '/') for l in
         open(os.path.join(ADDON, 'DungeonsForever.toc'), encoding='utf-8',
              errors='replace').read().splitlines()
         if l.strip() and not l.strip().startswith('##')]
lf = lua.eval('function(rel) local c = loadfile(ADDON_ROOT .. "/" .. rel); '
              'if not c then return nil end; '
              'return function() return c("DungeonsForever", TF_NS) end end')
for rel in files:
    if rel.lower().endswith('.xml'):
        continue
    ch = lf(rel)
    if ch is None:
        print('NIL', rel)
        break
    ch()
print('loaded OK')

r = lua.eval(r'''(function()
  local U = TF_NS.DungeonUI
  local out = {}
  local ok, tb = xpcall(function() U:Build() end, function(e)
      return tostring(e) .. " || " .. (debug and debug.traceback and debug.traceback("", 2) or "")
  end)
  out[#out+1] = 'Build ok=' .. tostring(ok) .. ' :: ' .. tb:gsub("[\r\n]+", " | ")
  return table.concat(out, '\n')
end)()''')
print(r)
