# -*- coding: utf-8 -*-
"""补一处：行也要转发滚轮（鼠标停在条目上时滚不动 = 实机典型症状）。

同时把「三处滚轮转发」钉成静态断言 + 一条变异 + 一条非恒真探针。
"""
import io
import os
import sys

ROOT = r'D:\workspace\DungeonsForever'
QB = os.path.join(ROOT, 'Core', 'QuickBar.lua')
CHK = os.path.join(ROOT, '_temp', 'df_dungeon_check.py')
MUT = os.path.join(ROOT, '_temp', 'df_mut_check.py')
PRB = os.path.join(ROOT, '_temp', '_qb_probe_nonvacuous.py')


def edit(path, pairs):
    with io.open(path, 'r', encoding='utf-8', newline='') as f:
        s = f.read()
    for old, new in pairs:
        n = s.count(old)
        if n != 1:
            print('!! %s 锚点命中 %d 次' % (os.path.basename(path), n))
            return False
        s = s.replace(old, new, 1)
    with io.open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(s)
    print('  已改 %s' % os.path.basename(path))
    return True


ok = True

# 1) 行上补滚轮转发
ok &= edit(QB, [(
    '    r:SetScript("OnClick", function(self) QB:Click(self.spec) end)\n',
    '    r:SetScript("OnClick", function(self) QB:Click(self.spec) end)\n'
    '    -- 条目是 Button：不显式接滚轮，鼠标停在条目上就滚不动（实机典型症状）。\n'
    '    r:EnableMouseWheel(true)\n'
    '    r:SetScript("OnMouseWheel", function(_, delta) QB:Scroll(delta) end)\n',
)])

# 2) 静态断言
ok &= edit(CHK, [(
    "ck('★★ ㊱ 不覆盖主窗（父级挂主窗、只占第二槽；没有盖住主窗的热区）',\n",
    "ck('★★ ㊱ 滚轮转发三处齐备（滚动帧 / 内容帧 / 条目 —— 鼠标停在条目上也要能滚）',\n"
    "   _qb_src.count('QB:Scroll(delta)') == 3\n"
    "   and 'r:EnableMouseWheel(true)' in _qb_src)\n"
    "ck('★★ ㊱ 不覆盖主窗（父级挂主窗、只占第二槽；没有盖住主窗的热区）',\n",
)])

# 3) 变异
ok &= edit(MUT, [(
    "    ('快捷栏：专业口径默认变成「全部」（新用户第一次打开就铺 13 个专业）',\n",
    "    ('快捷栏：内容帧不再转发滚轮（鼠标停在条目上滚不动）',\n"
    "     ('Core/QuickBar.lua', (\n"
    "         '    content:SetScript(\"OnMouseWheel\", function(_, delta) QB:Scroll(delta) end)'\n"
    "         '.encode('utf-8'),\n"
    "         '    content:SetScript(\"OnMouseWheel\", function(_, delta) end)'\n"
    "         ' -- MUT: wheel not forwarded\\n'.encode('utf-8')))),\n"
    "    ('快捷栏：专业口径默认变成「全部」（新用户第一次打开就铺 13 个专业）',\n",
)])

# 4) 非恒真探针
ok &= edit(PRB, [(
    "    ('S4 专业口径默认变「全部」', 'Core/Core.lua',\n",
    "    ('S5 内容帧不转发滚轮', 'Core/QuickBar.lua',\n"
    "     '    content:SetScript(\"OnMouseWheel\", function(_, delta) QB:Scroll(delta) end)',\n"
    "     '    content:SetScript(\"OnMouseWheel\", function(_, delta) end) -- MUT: no wheel\\n',\n"
    "     '滚轮转发三处齐备'),\n"
    "    ('S4 专业口径默认变「全部」', 'Core/Core.lua',\n",
)])

print('结果：%s' % ('OK' if ok else 'FAILED'))
sys.exit(0 if ok else 1)
