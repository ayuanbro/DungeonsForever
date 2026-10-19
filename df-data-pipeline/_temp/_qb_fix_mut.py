# -*- coding: utf-8 -*-
"""把 df_mut_check.py 里新加的 4 条变异从 b'中文' 改成 '中文'.encode('utf-8')（bytes 字面量不许非 ASCII）。"""
import io

P = r'D:\workspace\DungeonsForever\_temp\df_mut_check.py'

MARK = '    # ㊱ 快捷按钮栏（2026-09-30 用户'

FIXED = """    # ㊱ 快捷按钮栏（2026-09-30 用户：宽 100、A 方案常驻第二槽、推荐有什么显示什么）
    #   锚点都在「纯代码行」上（行尾注释会被 _strip_cmt 剥掉，锚点就烂了）；
    #   字符串一律 '...'.encode('utf-8') —— b'...' 装不下中文。
    ('快捷栏：面板挪回设置槽（+8）—— 两栏叠在一起、把设置弹窗压死',
     ('Core/QuickBar.lua', (
         '    f:SetPoint("TOPLEFT", host, "TOPRIGHT", self.SLOT2, 0)'.encode('utf-8'),
         '    f:SetPoint("TOPLEFT", host, "TOPRIGHT", 8, 0) -- MUT: slot clash\\n'.encode('utf-8')))),
    ('快捷栏：不再监听升级事件（推荐五人本停在打开界面那一眼的等级）',
     ('Core/QuickBar.lua', (
         '    ev:RegisterEvent("PLAYER_LEVEL_UP")'.encode('utf-8'),
         '    ev:RegisterEvent("PLAYER_INVENTORY_CHANGED") -- MUT: lost level up\\n'.encode('utf-8')))),
    ('快捷栏：副本分组的开关被绕过（关掉也照样铺条目）',
     ('Core/QuickBar.lua', (
         ('    if cfg.groups.dungeon then\\n'
          '        out[#out + 1] = { grp = L["推荐五人本"] }').encode('utf-8'),
         ('    if true then\\n'
          '        out[#out + 1] = { grp = L["推荐五人本"] }').encode('utf-8')))),
    ('快捷栏：专业口径默认变成「全部」（新用户第一次打开就铺 13 个专业）',
     ('Core/Core.lua', (
         '    if q.profMode ~= "all" then q.profMode = "learned" end'.encode('utf-8'),
         '    q.profMode = "all" -- MUT: all professions by default\\n'.encode('utf-8')))),
"""

with io.open(P, 'r', encoding='utf-8', newline='') as f:
    s = f.read()

start = s.index(MARK)
stop = s.index('\n]\n', start)
old = s[start:stop]
print('替换段落行数 = %d' % old.count('\n'))
s = s[:start] + FIXED.rstrip('\n') + s[stop:]

with io.open(P, 'w', encoding='utf-8', newline='') as f:
    f.write(s)

import ast
ast.parse(open(P, encoding='utf-8').read())
b = open(P, 'rb').read()
print('AST OK / CRLF=%d bareLF=%d' % (b.count(b'\r\n'), b.count(b'\n') - b.count(b'\r\n')))
