# -*- coding: utf-8 -*-
"""BIS 双卷探针：列出各卷的部位键、附魔槽位名，并与 BisUI 的映射表对比。"""
import os
import re

import lupa.lua51 as lua51

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
rt = lua51.LuaRuntime()
rt.globals()['SRC'] = open(os.path.join(DF, 'Core', 'Data', 'Data_BIS.lua'),
                           'rb').read().decode('utf-8')
out = rt.execute(r'''
local f = assert(loadstring(SRC))
local ns = {}
f(nil, ns)
local B = ns.BIS
local res = {}
res.default = tostring(B.default)
for _, lv in ipairs({20, 30}) do
  local v = B.levels[lv]
  if not v then res['lv'..lv] = 'MISSING' else
    local slots, ench, nspec, ncls = {}, {}, 0, 0
    local order = {}
    for _, c in ipairs(v.classes) do
      ncls = ncls + 1
      for _, sp in ipairs(c.specs) do
        nspec = nspec + 1
        for k in pairs(sp.slots or {}) do
          if not slots[k] then slots[k] = true order[#order+1] = k end
        end
        for _, e in ipairs(sp.enchs or {}) do
          if not ench[e.slot] then ench[e.slot] = true end
        end
      end
    end
    table.sort(order)
    local eo = {}
    for k in pairs(ench) do eo[#eo+1] = k end
    table.sort(eo)
    res['lv'..lv] = string.format('classes=%d specs=%d slots=[%s] enchs=[%s]',
      ncls, nspec, table.concat(order, ','), table.concat(eo, '|'))
  end
end
return res
''')
for lv in ('default', 'lv20', 'lv30'):
    print('%-8s %s' % (lv, out[lv]))

# BisUI 的两张映射表
ui = open(os.path.join(DF, 'Core', 'BisUI.lua'), encoding='utf-8').read()
sn = re.search(r'local SLOT_NAMES = \{(.*?)\n\}', ui, re.S).group(1)
slot_names = set(re.findall(r'(\w[\w-]*)\s*=', sn))
es = re.search(r'local ENCH_SLOTS = \{(.*?)\n\}', ui, re.S).group(1)
ench_names = set(re.findall(r'ns\.DL\("([^"]+)"\)', es))
print()
print('SLOT_NAMES 已映射:', sorted(slot_names))
print('ENCH_SLOTS 已映射:', sorted(ench_names))
for lv in ('lv20', 'lv30'):
    s = re.search(r'slots=\[([^\]]*)\]', out[lv]).group(1).split(',')
    miss = [x for x in s if x and x not in slot_names]
    e = re.search(r'enchs=\[([^\]]*)\]', out[lv]).group(1).split('|')
    emiss = [x for x in e if x and x not in ench_names]
    print('%s 未映射部位: %s | 未映射附魔槽: %s' % (lv, miss, emiss))
