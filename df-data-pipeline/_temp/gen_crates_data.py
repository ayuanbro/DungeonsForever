# -*- coding: utf-8 -*-
"""生成 Core/Data/Data_Crates.lua（板条箱 / 工匠文书目录 · 生成物）。

数据 = 本机客户端已装目录插件的 Catalog.lua（只读提取，脚本不进包）。
口径与专业页一致：只存 ID / 数量 / 声望 / 档位序号 / 等级，
名字一律运行期 GetItemInfo 取客户端语言。

用法：python gen_crates_data.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
DST = os.path.join(DF, 'Core', 'Data', 'Data_Crates.lua')
SRC = os.path.join(os.environ.get('WF_DIR', ''), 'Catalog.lua') if os.environ.get('WF_DIR') else None
if not SRC or not os.path.isfile(SRC):
    SRC = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\WaylaidForever\Catalog.lua'
if not os.path.isfile(SRC):
    sys.exit('[gen_crates_data] 找不到目录数据源：%s' % SRC)

TIERS = {'学徒': 1, '熟练': 2, '专家': 3, '工匠': 4}

LUA = r'''
local F = {}
local chunk = assert(loadstring(SRC))
chunk(nil, F)
local crates, writs = {}, {}
for _, c in ipairs(F.catalog.crates) do
    local opts = {}
    for _, o in ipairs(c.options) do
        opts[#opts + 1] = o.itemId .. "," .. o.qty
    end
    crates[#crates + 1] = c.id .. "\t" .. c.tier .. "\t" .. c.level .. "\t" .. tostring(c.favor or "")
                          .. "\t" .. table.concat(opts, ";")
end
for _, w in ipairs(F.catalog.writs) do
    writs[#writs + 1] = w.questId .. "\t" .. w.targetId .. "\t" .. w.qty
                        .. "\t" .. w.rep .. "\t" .. w.level .. "\t" .. w.id
end
return table.concat(crates, "\n") .. "\1" .. table.concat(writs, "\n")
'''

from lupa import lua51

L = lua51.LuaRuntime(encoding=None)
with open(SRC, 'rb') as f:
    src = f.read()
L.globals()[b'SRC'] = src
out = L.execute(LUA)
crates_raw, writs_raw = bytes(out).split(b'\x01')
crates_raw = crates_raw.decode('utf-8')
writs_raw = writs_raw.decode('utf-8')

crates, writs = [], {}
for line in crates_raw.splitlines():
    if not line.strip():
        continue
    pid, tier, level, favor, opts = line.split('\t')
    tier = TIERS.get(tier)
    if not tier:
        sys.exit('[gen_crates_data] 未知档位：%s' % tier)
    olist = []
    for o in opts.split(';'):
        a, b = o.split(',')
        olist.append((int(a), int(b)))
    crates.append((int(pid), tier, int(level), int(favor) if favor else None, olist))
for line in writs_raw.splitlines():
    if not line.strip():
        continue
    quest, target, qty, rep, level, wid = line.split('\t')
    writs[int(quest)] = (int(target), int(qty), int(rep), int(level), int(wid))

crates.sort(key=lambda c: (c[1], c[0]))
wkeys = sorted(writs.keys())


def num(v):
    return str(v)


lines = []
lines.append('')
lines.append('')
lines.append('')
lines.append('local _, ns = ...')
lines.append('')
lines.append('ns.CratesData = {')
lines.append('    crates = {')
for pid, tier, level, favor, opts in crates:
    ostr = ', '.join('{ %d, %d }' % o for o in opts)
    fstr = ('favor = %d, ' % favor) if favor else ''
    lines.append('        { id = %d, tier = %d, level = %d, %sopts = { %s } },'
                 % (pid, tier, level, fstr, ostr))
lines.append('    },')
lines.append('    writs = {')
for q in wkeys:
    target, qty, rep, level, wid = writs[q]
    lines.append('        { quest = %d, target = %d, qty = %d, rep = %d, level = %d, item = %d },'
                 % (q, target, qty, rep, level, wid))
lines.append('    },')
lines.append('}')
lines.append('')

body = '\n'.join(lines)
with open(DST, 'wb') as f:
    f.write(body.encode('utf-8'))

n_opt = sum(len(c[4]) for c in crates)
print('[gen_crates_data] crates=%d (opts=%d) writs=%d -> %s' % (len(crates), n_opt, len(wkeys), DST))
