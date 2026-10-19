# -*- coding: utf-8 -*-
"""恢复 PD.RecipeSpec 里的「来源拆段」（src / dpre / dval）。
并发会话把 RecipeSpec 做了 mats 惰性化重构，顺手把需求二的拆段三字段吞了，
导致 BindRow 里 870-882 行的商人半段与热区恒不生效（spec.dval/src 恒 nil）。

原子操作：读 → 断言锚点唯一 → 写 → 回读校验，一次进程内完成（防并发写覆盖）。
"""
import sys

P = 'Core/ProfessionUI.lua'
raw = open(P, 'rb').read()
t = raw.decode('utf-8')

n_crlf = t.count('\r\n')
n_lf = t.count('\n')
assert n_crlf > 0 and n_lf == n_crlf, 'EOL 异常 CRLF=%d LF=%d' % (n_crlf, n_lf)

A1 = ('function PD.RecipeSpec(r)\r\n'
      '    local hasVendor = r[14] and r[14].vendors and #r[14].vendors > 0\r\n')
A2 = ('        right2 = PD.SourceText(r[14]) or (r[13] and L["需要图纸"] or ""),\r\n')

c1, c2 = t.count(A1), t.count(A2)
assert c1 == 1, 'A1 命中 %d 次（要求 1）' % c1
assert c2 == 1, 'A2 命中 %d 次（要求 1）' % c2
assert 'src = r[14],' not in t, 'src = r[14] 已存在（重复打补丁？）'
assert 'dval = dval,' not in t, 'dval = dval 已存在'

BLOCK = (
    '    -- 2026-10-09：来源拆段 —— 「商人：X」恒为最后一段（PD.SourceParts 的顺序铁律），\r\n'
    '    --   单独搬到 r.dv 并单挂热区（悬停出商人明细 +「点击：在地图上标记该 NPC」）。\r\n'
    '    --   dpre 是它前面的前缀串；两半在 BindRow 里用锚点链相接（不量宽，位置交给引擎）。\r\n'
    '    local dpre, dval\r\n'
    '    do\r\n'
    '        local parts = PD.SourceParts(r[14])\r\n'
    '        local vk\r\n'
    '        for i = 1, #parts do\r\n'
    '            if parts[i].vendor then vk = i break end\r\n'
    '        end\r\n'
    '        if vk then\r\n'
    '            dval = (vk > 1 and " · " or "") .. parts[vk].text\r\n'
    '            local pre = {}\r\n'
    '            for i = 1, vk - 1 do pre[#pre + 1] = parts[i].text end\r\n'
    '            dpre = table.concat(pre, " · ")\r\n'
    '        end\r\n'
    '    end\r\n'
)

NEW2 = (
    '        right2 = dpre or (PD.SourceText(r[14]) or (r[13] and L["需要图纸"] or "")),\r\n'
    '        src = r[14],\r\n'
    '        dpre = dpre,\r\n'
    '        dval = dval,\r\n'
)

t2 = t.replace(A1, A1 + BLOCK, 1)
t2 = t2.replace(A2, NEW2, 1)

assert t2 != t
assert t2.count('src = r[14],') == 1, 'src 落点异常'
assert t2.count('dpre = dpre,') == 1
assert t2.count('dval = dval,') == 1
assert t2.count('local parts = PD.SourceParts(r[14])') == 1
assert t2.count('right2 = dpre or') == 1
assert t2.count('SourceText(r[14])') == 1  # 旧的整串调用已被替换
assert t2.count('\r\n') == t2.count('\n'), 'EOL 被破坏'

out = t2.encode('utf-8')
open(P, 'wb').write(out)

chk = open(P, 'rb').read().decode('utf-8')
assert chk == t2, '回读不一致'
print('OK  bytes %d -> %d  CRLF %d' % (len(raw), len(out), chk.count('\r\n')))
