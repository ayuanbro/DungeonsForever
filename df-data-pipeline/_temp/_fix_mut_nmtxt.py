# -*- coding: utf-8 -*-
# 变异锚点修正：锚点在剥注释源上匹配，行尾中文注释必须去掉。
import io

p = 'df_mut_check.py'
s = io.open(p, encoding='utf-8', newline='').read()
old = "u8('        bt.nm = MakeFS(pinText, 14, C_GOLD, \"CENTER\") -- 挂文字层：图标永远盖得住（跨钉也是）\\n')"
assert s.count(old) == 1, s.count(old)
new = "u8('        bt.nm = MakeFS(pinText, 14, C_GOLD, \"CENTER\")\\n')"
s = s.replace(old, new, 1)
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok')
