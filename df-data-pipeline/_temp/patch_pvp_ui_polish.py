# -*- coding: utf-8 -*-
# 2026-10-08 PvP 页四项 UI 反馈补丁（锚点断言，幂等可重跑）：
#   ①军衔页表头五列对齐 + 当前军衔徽章（规范化 RenderRanks 头块）
#   ②套装职业列表：按钮边框 + 选中金色描边 + 悬停高亮
#   ③冲刺页 目标/起点 按钮：创建期补描边层（渲染期 SetOutline 已在）
#   ④三语键（zhCN 键名即文案）+ harness 静态闸
import re

P = r'D:/workspace/DungeonsForever/Core/PvPUI.lua'
s = open(P, encoding='utf-8').read()


def rep(old, new, tag):
    global s
    n = s.count(old)
    assert n == 1, (tag, n, old[:70])
    s = s.replace(old, new)
    print('OK', tag)


# ---- 0. 采集真实成员名（防显示污染，按文件实际字节定名） ----
m_child = re.search(r'row:SetPoint\("TOPLEFT", PV\.(\w+), "TOPLEFT", 0, -y\)', s)
CHILD = m_child.group(1) if m_child else 'child'
m_bad = re.search(r'PV\.(\w+):SetTexture\(format\("Interface\\\\PvPRankBadges', s)
BADGE = m_bad.group(1) if m_bad else 'rankBadge'
print('CHILD =', CHILD, '| BADGE =', BADGE)

# ---- 1. RenderRanks 头块规范化（表头五列 + 徽章） ----
start = s.index('function PV.RenderRanks()')
tail_re = re.compile(
    r'PV\.facBtn2:SetPoint\("TOPLEFT", PV\.' + CHILD +
    r', "TOPLEFT", PV\.W - 76 - PV\.TAB_STEP, -\(y \+ 1\)\)\n')
m2 = tail_re.search(s, start)
assert m2, 'facBtn2 锚点'
canon = r'''function PV.RenderRanks()
    local y = 0
    -- ★★ 表头五列：x 锚点与行内列完全一致（2026-10-08 反馈：原单串「·」头与
    --   右对齐的 点数 / 累计 / 最早解锁 列错位；奖励列与芯片起点 540 对齐）。
    local rh = PV.rankHead
    rh.lvl:SetPoint("TOPLEFT", PV.@CHILD@, "TOPLEFT", 6, -(y + 6))
    rh.pts:SetPoint("TOPRIGHT", PV.@CHILD@, "TOPLEFT", 366, -(y + 6))
    rh.cum:SetPoint("TOPRIGHT", PV.@CHILD@, "TOPLEFT", 448, -(y + 6))
    rh.week:SetPoint("TOPRIGHT", PV.@CHILD@, "TOPLEFT", 522, -(y + 6))
    rh.rew:SetPoint("TOPLEFT", PV.@CHILD@, "TOPLEFT", 540, -(y + 6))
    for _, fs in pairs(rh) do fs:Show() end
    -- 当前军衔徽章（与冲刺页同一贴图族）：悬停显示实时军衔与进度。
    local lv, lp = LiveState()
    if lv and lv >= 1 then
        PV.@BADGE@:SetTexture(format("Interface\\PvPRankBadges\\PvPRank%02d", lv))
        PV.@BADGE@:SetPoint("TOPRIGHT", PV.@CHILD@, "TOPLEFT",
            PV.W - 76 - PV.TAB_STEP - 32, -(y + 1))
        PV.@BADGE@:Show()
        if SetTip then
            SetTip(PV.@BADGE@, format(L["当前军衔：R%d · %.0f%%"], lv, (lp or 0) * 100))
        end
    end
'''.replace('@CHILD@', CHILD).replace('@BADGE@', BADGE)
canon += m2.group(0)
s = s[:start] + canon + s[m2.end():]
print('OK RenderRanks 头块规范化')

# ---- 2. 套装职业列表：边框 + 悬停（创建期） ----
rep('''        bt.count:SetPoint("TOPRIGHT", bt, "TOPRIGHT", -8, -8)
        bt.__idx = i''',
    '''        bt.count:SetPoint("TOPRIGHT", bt, "TOPRIGHT", -8, -8)
        bt.bg = bt:CreateTexture(nil, "BACKGROUND")
        bt.bg:SetAllPoints(bt)
        bt.bg:SetColorTexture(1, 1, 1, 0.04)
        MakeOutline(bt, 1, 0.82, 0)
        bt.hover = bt:CreateTexture(nil, "OVERLAY")
        bt.hover:SetAllPoints(bt)
        bt.hover:SetColorTexture(1, 1, 1, 0.06)
        bt.hover:Hide()
        bt:SetScript("OnEnter", function(self) self.hover:Show() end)
        bt:SetScript("OnLeave", function(self) self.hover:Hide() end)
        bt.__idx = i''', 'setRows 边框+悬停')

# ---- 3. RenderSets：选中金色描边 ----
rep('''        row.name:SetTextColor(Unpack((PV.selSet == i) and C_GOLD or C_TEXT))
        row:Show()''',
    '''        row.name:SetTextColor(Unpack((PV.selSet == i) and C_GOLD or C_TEXT))
        SetOutline(row, PV.selSet == i, 1, 0.82, 0)
        row:Show()''', 'setRows 选中描边')

# ---- 4. 冲刺页目标/起点按钮：创建期补描边 ----
rep('''        local bt = NewButton(child, format("R%d", i + 1), 34, 22, 11)
        bt.__goal = i + 1''',
    '''        local bt = NewButton(child, format("R%d", i + 1), 34, 22, 11)
        MakeOutline(bt, 1, 0.82, 0)
        bt.__goal = i + 1''', 'goalBtn 描边')
rep('''        local bt = NewButton(child, format("R%d", i), 34, 22, 11)
        bt.__sim = i''',
    '''        local bt = NewButton(child, format("R%d", i), 34, 22, 11)
        MakeOutline(bt, 1, 0.82, 0)
        bt.__sim = i''', 'simBtn 描边')

open(P, 'w', encoding='utf-8', newline='').write(s)
print('PVPUI 写回完成, len =', len(s))

# ---- 5. 三语键（zhCN 键名即文案，只补 zhTW / enUS） ----
key = re.search(r'L\["(当前军衔[^"]*)"\]', s).group(1)
print('KEY =', repr(key))
assert 'R%d' in key and '%.0f%%' in key
for path, val in [
    (r'D:/workspace/DungeonsForever/Locales/zhTW.lua',
     key.replace('当前', '當前').replace('军衔', '軍銜')),
    (r'D:/workspace/DungeonsForever/Locales/enUS.lua',
     'Current rank: R%d · %.0f%%'),
]:
    t = open(path, encoding='utf-8').read()
    if ('L["%s"]' % key) in t:
        print('locale 已有键，跳过:', path)
        continue
    if not t.endswith('\n'):
        t += '\n'
    t += 'L["%s"] = "%s"\n' % (key, val)
    open(path, 'w', encoding='utf-8', newline='').write(t)
    print('locale 追加:', path)

# ---- 6. harness 静态闸 ----
HP = r'D:/workspace/DungeonsForever/_temp/df_dungeon_check.py'
h = open(HP, encoding='utf-8').read()
if '★ PvPUI 军衔页表头五列' in h:
    print('harness 断言已存在，跳过')
else:
    pat = re.compile(r"ck\('★ PvPUI 滚动区必须挂 SetScrollChild.*?_pv\)\n", re.S)
    m3 = pat.search(h)
    assert m3, 'harness SetScrollChild ck 锚点'
    add = (
        "    ck('★ PvPUI 军衔页表头五列 rankHead + 当前军衔徽章 rankBadge（Build 期建池）',\n"
        "       'PV.rankHead' in _pv and 'PV.rankBadge' in _pv)\n"
        "    ck('★ 军衔页徽章走 LiveState 实时军衔 + PvPRankBadges 贴图族',\n"
        "       'PvPRankBadges' in _pv and 'LiveState()' in _pv)\n"
        "    ck('★ 套装职业列表 / 冲刺目标 / 起点模拟按钮全部有描边层（MakeOutline 5 调用点）',\n"
        "       _pv.count('MakeOutline(bt, 1, 0.82, 0)') >= 5)\n"
        "    ck('★ 套装职业列表选中态金色描边 + 悬停高亮纹理',\n"
        "       'SetOutline(row, PV.selSet == i' in _pv and 'self.hover:Show()' in _pv)\n")
    h = h[:m3.end()] + add + h[m3.end():]
    open(HP, 'w', encoding='utf-8', newline='').write(h)
    print('harness 追加 4 条静态闸')
print('ALL DONE')
