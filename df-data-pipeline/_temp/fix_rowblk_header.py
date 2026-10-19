# -*- coding: utf-8 -*-
"""修回被 patch_lv_skillbar_card.py 的 N2 段吞掉的 `function PD.RowBlk(r, j)` 行头。"""
import sys

P = r'D:\workspace\DungeonsForever\Core\ProfessionUI.lua'
raw = open(P, 'rb').read().decode('utf-8')
assert (raw.count('\n') - raw.count('\r\n')) == 0, '混有裸 LF'
t = raw.replace('\r\n', '\n')

OLD = '''        act = hasVendor and PD.VendorAct(src) or nil,
    }
end

    local b = r.blk[j]
'''
NEW = '''        act = hasVendor and PD.VendorAct(src) or nil,
    }
end

function PD.RowBlk(r, j)
    local b = r.blk[j]
'''
n = t.count(OLD)
if n != 1:
    print('!! 锚点命中 %d 次' % n)
    sys.exit(1)
t = t.replace(OLD, NEW)
if t.count('function PD.RowBlk(r, j)') != 1:
    print('!! RowBlk 头数量异常：%d' % t.count('function PD.RowBlk(r, j)'))
    sys.exit(1)

out = t.replace('\n', '\r\n')
open(P, 'wb').write(out.encode('utf-8'))
back = open(P, 'rb').read().decode('utf-8')
assert back == out, '回读不一致'
print('OK 修回 RowBlk 头，文件 %d 字节 / CRLF %d' % (len(out.encode('utf-8')), out.count('\r\n')))
