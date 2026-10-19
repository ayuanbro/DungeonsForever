import sys

P = 'Core/DungeonUI.lua'
CR = b'\r\n'


def B(s):
    return s.replace('\n', '\r\n').encode('utf-8')


EDITS = [
    # 1. 两卡顶 / 左栏滚动区顶上移贴 hero（SCROLL_Y 184 -> FILTER_Y 152）；掉落页 dscroll 不动
    (B('    qscroll:SetPoint("TOPLEFT", detail, "TOPLEFT", 0, -DG.SCROLL_Y)\n'),
     B('    qscroll:SetPoint("TOPLEFT", detail, "TOPLEFT", 0, -DG.FILTER_Y)\n'), 1),

    (B('                  DG.Q_LIST_W + DG.Q_DET_GAP + DG.Q_PAD, -DG.SCROLL_Y)\n'),
     B('                  DG.Q_LIST_W + DG.Q_DET_GAP + DG.Q_PAD, -DG.FILTER_Y)\n'), 1),

    (B('    plateL:SetPoint("TOPLEFT", detail, "TOPLEFT", 0, -DG.SCROLL_Y)\n'),
     B('    plateL:SetPoint("TOPLEFT", detail, "TOPLEFT", 0, -DG.FILTER_Y)\n'), 1),

    (B('                    DG.Q_LIST_W + DG.Q_DET_GAP, -DG.SCROLL_Y)\n'),
     B('                    DG.Q_LIST_W + DG.Q_DET_GAP, -DG.FILTER_Y)\n'), 1),

    # 2. 左卡顶部统计文字改为不显示（保留 SetText，harness 仍以 __text 为观测点）
    (B('    U.dungeonQuestSum:Show()\n'),
     B('    U.dungeonQuestSum:Hide()\n'), 1),

    # 3. 列表内容起点：统计行高 -> 顶部按钮区高
    (B('    local nH, nR, y = 0, 0, -DG.Q_SUM_H\n'),
     B('    local nH, nR, y = 0, 0, -DG.Q_HEAD_H\n'), 1),

    # 4. 新增顶部按钮区高常量
    (B('DG.Q_SUM_H = 28\n'),
     B('DG.Q_SUM_H = 28\nDG.Q_HEAD_H = DG.Q_PAD + 24 + DG.Q_PAD\n'), 1),

    # 5. 阵营图标：12x12/LEFT4 -> 16x16/LEFT7 + 圆角
    (B('        em:SetSize(12, 12)\n        em:SetPoint("LEFT", bt, "LEFT", 4, 0)\n'),
     B('        em:SetSize(16, 16)\n        em:SetPoint("LEFT", bt, "LEFT", 7, 0)\n'
       '        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(em) end\n'), 1),

    # 6. 新增 PvP 同款阵营图标常量（不动 FactionTex，免影响任务行小阵营标）
    (B('DG.__facTex = {}\n'),
     B('DG.Q_FAC_ICON = {\n'
       '    A = "Interface\\\\AddOns\\\\DungeonsForever\\\\Media\\\\icon\\\\FACTION\\\\FactionIcon_Alliance",\n'
       '    H = "Interface\\\\AddOns\\\\DungeonsForever\\\\Media\\\\icon\\\\FACTION\\\\FactionIcon_Horde",\n'
       '}\n\n'
       'DG.__facTex = {}\n'), 1),

    # 7. 外壳补刷里的图标来源
    (B('                local tex = DG.FactionTex(i == 2 and "A" or "H")\n'),
     B('                local tex = DG.Q_FAC_ICON[(i == 2) and "A" or "H"]\n'), 1),

    # 8. 渲染时的图标来源 + 文字锚 + 未选中阵营色
    (B('            local tex = (i == 2 or i == 3) and DG.FactionTex(i == 2 and "A" or "H") or nil\n'
       '            bt:SetText((tex and "  " or "") .. label .. " " .. n)\n'
       '            bt:SetShown(true)\n'
       '            local sel = (i <= 3 and side == key) or (i == 4 and status == "todo") or (i == 5 and status == "done")\n'
       '            SetOutline(bt, sel, 1, 0.82, 0)\n'
       '            bt:GetFontString():SetTextColor(Unpack(sel and C_GOLD or C_GREY))\n'),
     B('            local tex = (i == 2 or i == 3) and DG.Q_FAC_ICON[(i == 2) and "A" or "H"] or nil\n'
       '            bt:SetText(label .. " " .. n)\n'
       '            local bfs = bt:GetFontString()\n'
       '            if bfs then\n'
       '                bfs:ClearAllPoints()\n'
       '                if tex then\n'
       '                    bfs:SetPoint("TOPLEFT", bt, "TOPLEFT", 26, 0)\n'
       '                    bfs:SetPoint("BOTTOMRIGHT", bt, "BOTTOMRIGHT", -2, 0)\n'
       '                else\n'
       '                    bfs:SetAllPoints(bt)\n'
       '                end\n'
       '                bfs:SetJustifyH("CENTER")\n'
       '            end\n'
       '            bt:SetShown(true)\n'
       '            local sel = (i <= 3 and side == key) or (i == 4 and status == "todo") or (i == 5 and status == "done")\n'
       '            SetOutline(bt, sel, 1, 0.82, 0)\n'
       '            if bfs then\n'
       '                if sel then\n'
       '                    bfs:SetTextColor(Unpack(C_GOLD))\n'
       '                elseif i == 2 then\n'
       '                    bfs:SetTextColor(0.40, 0.62, 1.00, 1)\n'
       '                elseif i == 3 then\n'
       '                    bfs:SetTextColor(1.00, 0.36, 0.26, 1)\n'
       '                else\n'
       '                    bfs:SetTextColor(Unpack(C_GREY))\n'
       '                end\n'
       '            end\n'), 1),

    # 9. 任务页按钮重锚到左卡顶部 + 抬层级；其余页回落 detail 顶
    (B('    for key, bt in pairs(U.dungeonTabBtns or {}) do\n'),
     B('    if isQuest and U.dungeonQPlateL then\n'
       '        local plateL = U.dungeonQPlateL\n'
       '        for i = 1, #(U.dungeonFilterBtns or {}) do\n'
       '            local bt = U.dungeonFilterBtns[i]\n'
       '            if bt then\n'
       '                bt:ClearAllPoints()\n'
       '                bt:SetPoint("TOPLEFT", plateL, "TOPLEFT", DG.Q_PAD + (i - 1) * 100, -DG.Q_PAD)\n'
       '                bt:SetFrameLevel(plateL:GetFrameLevel() + 5)\n'
       '            end\n'
       '        end\n'
       '    elseif U.dungeonDetail then\n'
       '        for i = 1, #(U.dungeonFilterBtns or {}) do\n'
       '            local bt = U.dungeonFilterBtns[i]\n'
       '            if bt then\n'
       '                bt:ClearAllPoints()\n'
       '                bt:SetPoint("TOPLEFT", U.dungeonDetail, "TOPLEFT", DG.GUTTER + (i - 1) * 100, -DG.FILTER_Y)\n'
       '            end\n'
       '        end\n'
       '    end\n'
       '    for key, bt in pairs(U.dungeonTabBtns or {}) do\n'), 1),
]

check_only = '--check' in sys.argv
raw = open(P, 'rb').read()
assert raw.count(CR) > 0, 'expected CRLF file'
print('file CRLF=%d bare_LF=%d' % (raw.count(CR), raw.count(b'\n') - raw.count(CR)))

fails = 0
for i, (old, new, want) in enumerate(EDITS, 1):
    n = raw.count(old)
    if n != want:
        print('  FAIL#%d hits=%d expect=%d : %s' % (i, n, want, old[:70]))
        fails += 1
        continue
    print('  ok  #%d hits=%d : %s' % (i, n, old[:62].replace(b'\r\n', b'|')))
    if not check_only:
        raw = raw.replace(old, new, 1)

if check_only:
    print('check done, fails=%d' % fails)
    sys.exit(1 if fails else 0)

assert fails == 0, 'anchor mismatch'
open(P, 'wb').write(raw)
print('patched OK')
