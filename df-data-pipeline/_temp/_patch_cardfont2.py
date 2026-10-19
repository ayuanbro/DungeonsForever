# -*- coding: utf-8 -*-
"""一次性补丁：把「副本卡字号」补丁条目从 14/12 升到 16/12，并给 meta 补 1px 阴影细描边。

用户 2026-09-24：「副本名字号改为16」「等级 · BOSS n 加上细描边」。
  · 本插件固定 hui 主题，ns.hui.FontFlags 恒返回 ""（无描边）→ 副行压在场景图上发虚。
  · 细描边 = SetShadowColor(0,0,0,1) + SetShadowOffset(1,-1)，
    与详情页标题 dungeonDetailTitle/Meta 同款（产物 699-700 / 712-713 行的先例）。

受检替换：每处锚点命中不是 1 次就退出（不静默改错）。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, 'port_dungeonsforever.py')
CRLF = '\r\n'
src = io.open(P, 'r', encoding='utf-8', newline='').read()


def rep(old, new, label):
    global src
    n = src.count(old)
    if n != 1:
        sys.exit('锚点「%s」命中 %d 次（应为 1）' % (label, n))
    src = src.replace(old, new)


# ① name 字号 14 → 16（append 块 new 文本里的那处；上游原文是 12，不会误伤）
rep('MakeFS(card, 14, C_WHITE', 'MakeFS(card, 16, C_WHITE', 'name 14→16')

# ② meta 行后补 1px 阴影（锚点 = new 文本里 meta SetPoint 行 + label 行的连续串；
#    old 文本块里同样的 SetPoint 行后面跟的是 new 块开头，不会命中）
rep("       '    card.meta:SetPoint(\"BOTTOMLEFT\", card, \"BOTTOMLEFT\", 8, 5)')," + CRLF +
    "    '副本卡字号 12/10 → 14/12',",
    "       '    card.meta:SetPoint(\"BOTTOMLEFT\", card, \"BOTTOMLEFT\", 8, 5)'," + CRLF +
    "       '    -- hui 主题 FontFlags 恒返回 \"\"（无描边），副行压在场景图上发虚 → 补 1px 阴影当细描边，" + CRLF +
    "       '    --   与详情页标题 dungeonDetailTitle/Meta 的 SetShadowOffset(1, -1) 同款。'," + CRLF +
    "       '    card.meta:SetShadowColor(0, 0, 0, 1)'," + CRLF +
    "       '    card.meta:SetShadowOffset(1, -1)')," + CRLF +
    "    '副本卡字号 12/10 → 16/12 + meta 细描边',",
    'meta shadow')

# ③ 补丁注释头同步（字号与余量数值）
rep('#   12pt / 10pt → 14pt / 12pt：卡 175x58 内两行合计 26px，仍余 32px 空隙；',
    '#   12pt / 10pt → 16pt / 12pt：卡 175x58 内两行合计 28px，仍余 30px 空隙；',
    '注释头字号')

io.open(P, 'w', encoding='utf-8', newline='').write(src)
print('  [OK] 副本卡补丁已升级：name 16pt + meta 12pt 细描边')
