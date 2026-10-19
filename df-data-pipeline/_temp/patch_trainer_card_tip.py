# -*- coding: utf-8 -*-
"""给「训练师」来源卡片补悬停明细（与「图纸」卡片同口径：悬停都有内容）。"""
import sys

P = r'D:\workspace\DungeonsForever\Core\ProfessionUI.lua'
raw = open(P, 'rb').read().decode('utf-8')
assert (raw.count('\n') - raw.count('\r\n')) == 0, '混有裸 LF'
t = raw.replace('\r\n', '\n')

OLD = '''function PD.CardOf(rec, ri)
    if not rec then
        return (ri and ri.trainer) and { kind = "trainer", text = L["训练师"] } or nil
    end
    local fid = rec[13] and rec[13][1]
    if not fid then return { kind = "trainer", text = L["训练师"] } end
'''
NEW = '''-- 训练师直教卡片（模块级常量：内容固定，全表共用一张；悬停口径与「图纸」卡片一致）
local TRAINER_CARD = {
    kind = "trainer", text = L["训练师"],
    lines = { { L["向训练师学习"], 0.81, 0.85, 0.89 } },
}

function PD.CardOf(rec, ri)
    if not rec then
        return (ri and ri.trainer) and TRAINER_CARD or nil
    end
    local fid = rec[13] and rec[13][1]
    if not fid then return TRAINER_CARD end
'''
n = t.count(OLD)
if n != 1:
    print('!! 锚点命中 %d 次' % n)
    sys.exit(1)
t = t.replace(OLD, NEW)
assert t.count('local TRAINER_CARD = {') == 1
out = t.replace('\n', '\r\n')
open(P, 'wb').write(out.encode('utf-8'))
assert open(P, 'rb').read().decode('utf-8') == out, '回读不一致'
print('OK 训练师卡片补悬停明细，文件 %d 字节 / CRLF %d'
      % (len(out.encode('utf-8')), out.count('\r\n')))
