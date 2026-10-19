# -*- coding: utf-8 -*-
"""打包行 A/B 内存实测：10 槽行 vs {id,name,pack,icon} 4 槽行（lupa 真值）"""
import os
from lupa import lua51

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'Core/Data/Data_Gear.lua')

L = lua51.LuaRuntime(unpack_returned_tuples=True)
t = L.table()
L.globals()['NSG'] = t
code = open(SRC, 'rb').read().decode('utf-8')
f = L.eval("function(src) local f,err=loadstring(src,'DG') if not f then error(err) end return f end")(code)
f('addon', t)
L.execute("collectgarbage('collect'); collectgarbage('collect')")
base = L.eval("collectgarbage('count')")
t.EnsureGearData()
L.execute("collectgarbage('collect'); collectgarbage('collect')")
after = L.eval("collectgarbage('count')")
G = t.GearData
items = G['items']
n = len(items)
print('rows =', n)
print('EnsureGearData total delta = %.2fMB' % ((after - base) / 1024))

qmin, qmax = 99, -1
lvmin, lvmax = 999, -1
rmin, rmax = 999, -1
umax = -1
slots = {}
icons = {}
sts = {}
cs = {}
for row in items.values():
    q = int(row[3]); ilv = int(row[4]); rq = int(row[5]); s = str(row[6]); c = int(row[7]); u = int(row[8]); st = str(row[10])
    qmin = min(qmin, q); qmax = max(qmax, q)
    lvmin = min(lvmin, ilv); lvmax = max(lvmax, ilv)
    rmin = min(rmin, rq); rmax = max(rmax, rq)
    umax = max(umax, u)
    slots[s] = slots.get(s, 0) + 1
    icons[str(row[9])] = icons.get(str(row[9]), 0) + 1
    sts[st] = sts.get(st, 0) + 1
    cs[c] = cs.get(c, 0) + 1
print('q', qmin, qmax, '| ilvl', lvmin, lvmax, '| req', rmin, rmax, '| umax', umax, '| c', cs)
print('slots =', len(slots), '| icons =', len(icons), '| st =', sts)

slotnames = L.table(*sorted(slots.keys()))

build = L.eval(r'''
function(items, slotnames)
    local slotidx = {}
    for i, s in ipairs(slotnames) do slotidx[s] = i - 1 end
    local out = {}
    for i = 1, #items do
        local it = items[i]
        local sidx = slotidx[it[6]]
        if not sidx then error("unknown slot: " .. tostring(it[6])) end
        local pack = it[3] % 8
            + it[4] * 8
            + it[5] * 2048
            + it[8] * 524288
            + (it[7] == 4 and 16777216 or 0)
            + (it[10] == "new" and 33554432 or 0)
            + sidx * 67108864
        if pack >= 4294967296 then error("pack overflow: " .. pack) end
        out[i] = {it[1], it[2], pack, it[9]}
    end
    return out
end
''')
L.globals()['_C'] = L.table
L.execute("collectgarbage('collect'); collectgarbage('collect')")
p0 = L.eval("collectgarbage('count')")

old_rows = L.eval(r'''
function(items)
    local out = {}
    for i = 1, #items do
        local it = items[i]
        out[i] = {it[1], it[2], it[3], it[4], it[5], it[6], it[7], it[8], it[9], it[10]}
    end
    return out
end
''')
packed_rows = build(items, slotnames)
L.execute("collectgarbage('collect'); collectgarbage('collect')")
p1 = L.eval("collectgarbage('count')")
print('packed 4-slot rows delta = %.2fMB (%d rows)' % ((p1 - p0) / 1024, n))

old = old_rows(items)
L.execute("collectgarbage('collect'); collectgarbage('collect')")
p2 = L.eval("collectgarbage('count')")
print('old 10-slot rows delta = %.2fMB' % ((p2 - p1) / 1024))
