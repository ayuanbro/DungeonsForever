# -*- coding: utf-8 -*-
# 2026-10-10 二轮：B1 信息卡/输入框倒圆角 + secGoldCards 残留修复
import sys

P = 'Core/ProfessionUI.lua'

EDITS = []

# ---- 1) lvTiles 四张信息卡：SetBackdrop -> BuildRoundedBG（border 存帧上供动态改色）
EDITS.append(('tiles-build', '''        tf:SetBackdrop({\r
            bgFile = "Interface\\\\Buttons\\\\WHITE8x8",\r
            edgeFile = "Interface\\\\Buttons\\\\WHITE8x8",\r
            edgeSize = 1,\r
        })\r
        tf:SetBackdropColor(0, 0, 0, 0.35)\r
        tf:SetBackdropBorderColor(0.45, 0.45, 0.45, 0.6)\r
        tf:Hide()\r
        tf.label = MakeFS(tf, 11, C_GREY, "LEFT")'''.replace('\r\n', '\r\n'),
'''        -- 倒圆角（2026-10-10）：走 HUI 圆角原语；border 片段存帧上供 PaintLvTiles 动态改色\r
        local _, bord = ns.hui.BuildRoundedBG(tf, 6, { 0, 0, 0, 0.35 }, "both", true, 1)\r
        tf.__border = bord or {}\r
        tf:Hide()\r
        tf.label = MakeFS(tf, 11, C_GREY, "LEFT")'''))

# ---- 2) lvTiles 循环后追加 PD.PaintTileBorder 帮手（build 与 PaintLvTiles 两处共用）
EDITS.append(('tile-border-helper', '''        PD.lvTiles[td.key] = tf\r
    end\r
    PD.lvTiles.mode:SetScript("OnClick", function()''',
'''        PD.lvTiles[td.key] = tf\r
    end\r
    -- 圆角边框动态改色（模式卡琥珀提醒 / 输入框金色描边共用）\r
    function PD.PaintTileBorder(f, c)\r
        for _, tex in ipairs(f.__border or {}) do\r
            if tex.__huiBorderStrip then\r
                tex:SetColorTexture(c[1], c[2], c[3], 1)\r
                tex:SetAlpha(c[4] or 1)\r
            else\r
                tex:SetVertexColor(c[1], c[2], c[3])\r
                tex:SetAlpha(c[4] or 1)\r
            end\r
        end\r
    end\r
    PD.lvTiles.mode:SetScript("OnClick", function()'''))

# ---- 3) 模式卡动态边框：SetBackdropBorderColor -> PaintTileBorder
EDITS.append(('mode-border', '''    if warnAuto then\r
        tiles.mode:SetBackdropBorderColor(0.95, 0.75, 0.4, 0.9)\r
    else\r
        tiles.mode:SetBackdropBorderColor(0.45, 0.45, 0.45, 0.6)\r
    end''',
'''    if warnAuto then\r
        PD.PaintTileBorder(tiles.mode, { 0.95, 0.75, 0.4, 0.9 })\r
    else\r
        PD.PaintTileBorder(tiles.mode, { 0.45, 0.45, 0.45, 0.6 })\r
    end'''))

# ---- 4) 目标等级 EditBox：倒圆角（金色描边走 PaintTileBorder）
EDITS.append(('target-eb', '''        local eb = CreateFrame("EditBox", nil, tf, "BackdropTemplate")\r
        eb:SetBackdrop({\r
            bgFile = "Interface\\\\Buttons\\\\WHITE8x8",\r
            edgeFile = "Interface\\\\Buttons\\\\WHITE8x8",\r
            edgeSize = 1,\r
        })\r
        eb:SetBackdropColor(0, 0, 0, 0.55)\r
        eb:SetBackdropBorderColor(1, 0.82, 0, 0.9)''',
'''        local eb = CreateFrame("EditBox", nil, tf, "BackdropTemplate")\r
        local _, ebBord = ns.hui.BuildRoundedBG(eb, 6, { 0, 0, 0, 0.55 }, "both", true, 1)\r
        eb.__border = ebBord or {}\r
        PD.PaintTileBorder(eb, { 1, 0.82, 0, 0.9 })'''))

# ---- 5) 配方搜索 EditBox：倒圆角
EDITS.append(('search-eb', '''    local seb = CreateFrame("EditBox", nil, sb, "BackdropTemplate")\r
    seb:SetBackdrop({\r
        bgFile = "Interface\\\\Buttons\\\\WHITE8x8",\r
        edgeFile = "Interface\\\\Buttons\\\\WHITE8x8",\r
        edgeSize = 1,\r
    })\r
    seb:SetBackdropColor(0, 0, 0, 0.55)\r
    seb:SetBackdropBorderColor(1, 1, 1, 0.25)''',
'''    local seb = CreateFrame("EditBox", nil, sb, "BackdropTemplate")\r
    local _, sebBord = ns.hui.BuildRoundedBG(seb, 6, { 0, 0, 0, 0.55 }, "both", true, 1)\r
    seb.__border = sebBord or {}\r
    PD.PaintTileBorder(seb, { 1, 1, 1, 0.25 })'''))

# ---- 6) 残留修复：secGoldCards 两条清理路径补隐藏
EDITS.append(('gold-cards-hide', '''        for i = ci + 1, #PD.secCards do PD.secCards[i]:Hide() end\r
    elseif PD.secCards then\r
        for i = 1, #PD.secCards do PD.secCards[i]:Hide() end\r
    end''',
'''        for i = ci + 1, #PD.secCards do PD.secCards[i]:Hide() end\r
        for i = ci + 1, #PD.secGoldCards do PD.secGoldCards[i]:Hide() end\r
    elseif PD.secCards then\r
        for i = 1, #PD.secCards do PD.secCards[i]:Hide() end\r
        for i = 1, #PD.secGoldCards do PD.secGoldCards[i]:Hide() end\r
    end'''))


def check():
    data = open(P, 'rb').read()
    ok = True
    for name, old, new in EDITS:
        c = data.count(old.encode('utf-8'))
        if c != 1:
            print('MISS anchor %-18s count=%d' % (name, c))
            ok = False
        else:
            print('ok   anchor', name)
    return ok


def apply():
    if not check():
        sys.exit('anchor check failed, abort')
    data = open(P, 'rb').read()
    for name, old, new in EDITS:
        data = data.replace(old.encode('utf-8'), new.encode('utf-8'), 1)
    open(P, 'wb').write(data)
    print('applied', len(EDITS), 'edits')


if __name__ == '__main__':
    if '--check' in sys.argv:
        check()
    else:
        apply()
