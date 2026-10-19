# -*- coding: utf-8 -*-
# 追加变异：pinText 层级未钉住（SetFrameLevel 行被删 → 同层 FontString 后画，文字再盖图标）
import io

P = 'df_mut_check.py'
s = io.open(P, encoding='utf-8', newline='').read()

# 找 MUTATIONS 列表结尾（注册表第一个 '\n]'）
i = s.find('\nMUTATIONS = [')
assert i > 0
end = s.find('\n]', i)
assert end > 0

mut = """    ('图钉扩展：pinText 层级没钉住（SetFrameLevel 行被删 → 同层 FontString 后画，文字再盖图标）',
     ('Core/MapUI.lua', (
         u8('    pinText:SetFrameLevel(math.max(pins:GetFrameLevel(), 0))\\n'),
         u8('    -- MUT: text layer level not pinned\\n')))),
"""
s = s[:end] + mut + s[end:]
io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('变异已追加')
