# -*- coding: utf-8 -*-
"""一次性：把 14 条漂移锚点按当前代码字节修进 df_mut_check.py（2026-10-07）。

每条修完立即用 to_file_style 在真实文件上断言「恰好命中 1 次」，
任何一条不唯一就整体失败退出，不落盘。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import df_mut_check as M

ROOT = r'D:\workspace\DungeonsForever'
C = lambda s: s.encode('utf-8')

# name -> (new_old, new_new)（Lua 源码文本，\r\n 由 C() 统一给）
FIXES = {
    '地图：点地图渲染成掉落页（分派串线）': (
        '    elseif isMap then\r\n'
        '        DG.EnsureMapPage()\r\n'
        '        if ns.MapModule then ns.MapModule.Paint(U.dungeonDetailCur) end\r\n',
        '    elseif isMap then\r\n'
        '        DG.EnsureMapPage()\r\n'
        '        U:RenderDungeonLoot() -- MUT: map tab renders loot\r\n',
    ),
    '钉点：SyncPins 不按当前层取（各层钉点全画在当前层）': (
        '    if M.curId and floor then\r\n'
        '        list = M.PinsFor(M.curId, floor)\r\n',
        '    if M.curId and floor then\r\n'
        '        list = M.PinsFor(M.curId) -- MUT: every floor\'s pins on this layer\r\n',
    ),
    '钉点：身份色被抹白（颜色即身份失效，分不清谁是谁）': (
        '            if kind == "boss" then\r\n'
        '                nm = p.zh or p.en or ""\r\n'
        '                cr, cg, cb = M.BossColor(M.curId, p.en)\r\n',
        '            if kind == "boss" then\r\n'
        '                nm = p.zh or p.en or ""\r\n'
        '                cr, cg, cb = 1, 1, 1 -- MUT: identity colors wiped\r\n',
    ),
    '钉点：钉点同步里又新建帧（破「渲染路径零新建帧」）': (
        '    for i = n + 1, M.MAX_PINS do\r\n'
        '        frame.pinBtns[i]:Hide()\r\n',
        '    CreateFrame("Frame", nil, frame) -- MUT: frame built while syncing pins\r\n'
        '    for i = n + 1, M.MAX_PINS do\r\n'
        '        frame.pinBtns[i]:Hide()\r\n',
    ),
    '详情：行池每次强制新建行帧': (
        '        local r = rows[nR]\r\n'
        '        if not r then\r\n',
        '        local r = nil\r\n'
        '        if not r then\r\n',
    ),
    '提示框：预热空转（不请求任何物品）': (
        '    local function warmChunk()\r\n'
        '        local stop = i + DG.ITEM_WARM_CHUNK - 1\r\n',
        '    local function warmChunk()\r\n'
        '        if true then return end -- MUT: prewarm does nothing\r\n'
        '        local stop = i + DG.ITEM_WARM_CHUNK - 1\r\n',
    ),
    '名字可见：重扫不再跳过已到货的卡（每轮白刷）': (
        '            local c = pool[i]\r\n'
        '            local it = c and c.__it\r\n'
        '            if it and not c.__named then\r\n'
        '                -- ★ O(1) 画这张卡；失效只针对这一件（末尾统一 ApplyAll 一次）\r\n'
        '                DG.PaintItemRow(c, it[1])\r\n',
        '            local c = pool[i]\r\n'
        '            local it = c and c.__it\r\n'
        '            if it then -- MUT: sweep rescans named cards\r\n'
        '                -- ★ O(1) 画这张卡；失效只针对这一件（末尾统一 ApplyAll 一次）\r\n'
        '                DG.PaintItemRow(c, it[1])\r\n',
    ),
    '滚轮：掉落卡片不转发（压在卡上滚不动）': (
        '            c.hit:EnableMouseWheel(true)\r\n'
        '            c.hit:SetScript("OnMouseWheel", function(self, delta)\r\n'
        '                DG.WheelScroll(U.dungeonDetailScroll, U.dungeonDetailChild, delta)\r\n',
        '            -- MUT: loot card eats the wheel\r\n'
        '            c.hit:SetScript("OnMouseWheel", function(self, delta)\r\n'
        '                DG.WheelScroll(U.dungeonDetailScroll, U.dungeonDetailChild, delta)\r\n',
    ),
    '卡片墙：摘掉每轮底色复位（悬停态会残留）': (
        '                    if LF and LF.Apply then LF.Apply(r) end\r\n'
        '                    r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)\r\n'
        '                    r:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)\r\n'
        '                    r:ClearAllPoints()\r\n',
        '                    if LF and LF.Apply then LF.Apply(r) end\r\n'
        '                    -- MUT: backdrop reset skipped\r\n'
        '                    r:ClearAllPoints()\r\n',
    ),
    '卡片墙：视图分派断掉（卡片视图永远渲染成列表）': (
        '    if (U.lootView or "list") == "card" then\r\n'
        '        U:RenderDungeonLootCards(groups, filter, takeRow, makeRow)\r\n',
        '    if (U.lootView or "list") == "neveralways" then\r\n'
        '        U:RenderDungeonLootCards(groups, filter, takeRow, makeRow)\r\n',
    ),
    '胶囊：SwitchSub 又把 key 丢掉（永远只显示 5人本）': (
        '    local k = "Dungeons"\r\n'
        '    if key == "Raids" then\r\n'
        '        k = "Raids"\r\n'
        '    elseif key == "Professions" and ns.LoadForeverPages then\r\n'
        '        k = "Professions"\r\n'
        '    elseif key == "Explore" and ns.LoadForeverPages then\r\n'
        '        k = "Explore"\r\n'
        '    elseif key == "Collections" and ns.LoadForeverPages then\r\n'
        '        k = "Collections"\r\n'
        '    elseif key == "Bis" and ns.LoadForeverPages then\r\n'
        '        k = "Bis"\r\n'
        '    elseif key == "Tier" and ns.LoadForeverPages then\r\n'
        '        k = "Tier"\r\n'
        '    end\r\n',
        '    local k = "Dungeons" -- MUT: switch key ignored (always 5-man)\r\n',
    ),
    'Shift 点击：卡片退回 Frame（实机不支持 OnClick）': (
        '    local function makeRow()\r\n'
        '        r = CreateFrame("Button", nil, child, "BackdropTemplate")\r\n'
        '        r:SetSize(cw, DG.LOOT_CARD_H)\r\n',
        '    local function makeRow()\r\n'
        '        r = CreateFrame("Frame", nil, child, "BackdropTemplate") -- MUT: frame cannot click\r\n'
        '        r:SetSize(cw, DG.LOOT_CARD_H)\r\n',
    ),
}

EXTRA = {
    # 绑定 __named（2829 列表路）：前面带列表路特有的 nbudget（cw - tx）行，
    # 与 2983 卡片路（rowW - ix）区分
    '名字可见：绑定时不记 __named（复用的卡会被漏掉）': (
        '                    local nbudget = it[3] and (cw - tx - DG.LOOT_TAG_W) or (cw - tx - DG.LOOT_TEXT_R)\r\n'
        '                    r.name:SetText(DG.FitText(nm, DG.LOOT_FS_NAME, nbudget))\r\n'
        '                    if hasName then\r\n'
        '                        r.name:SetTextColor(DG.QColor(DG.QualOf(it[1])))\r\n'
        '                    else\r\n'
        '                        r.name:SetTextColor(Unpack(C_GREY))\r\n'
        '                    end\r\n'
        '                    r.__named = hasName\r\n',
        '                    local nbudget = it[3] and (cw - tx - DG.LOOT_TAG_W) or (cw - tx - DG.LOOT_TEXT_R)\r\n'
        '                    r.name:SetText(DG.FitText(nm, DG.LOOT_FS_NAME, nbudget))\r\n'
        '                    if hasName then\r\n'
        '                        r.name:SetTextColor(DG.QColor(DG.QualOf(it[1])))\r\n'
        '                    else\r\n'
        '                        r.name:SetTextColor(Unpack(C_GREY))\r\n'
        '                    end\r\n'
        '                    -- MUT: no __named mark on bind\r\n',
    ),
    # 宠物组标题（另有玩具组同形 SetPoint）
    '小动物：导航组标题多抬 11px（-11 → -22，压回上一个按钮）': (
        '        glab:SetPoint("TOPLEFT", page, "TOPLEFT", EG.NAV_X + 2, -(EG.NAV_TOP + navY - 11))\r\n'
        '        glab:SetText(L["宠物"])\r\n',
        '        glab:SetPoint("TOPLEFT", page, "TOPLEFT", EG.NAV_X + 2, -(EG.NAV_TOP + navY - 22))\r\n'
        '        glab:SetText(L["宠物"])\r\n',
    ),
}
FIXES.update(EXTRA)

cache = {}
def raw_of(fname):
    if fname not in cache:
        cache[fname] = open(os.path.join(ROOT, *fname.split('/')), 'rb').read()
    return cache[fname]

new_mutations = []
applied = 0
for name, spec in M.MUTATIONS:
    fname, old, new = M.split_spec(spec)
    if name in FIXES:
        no, nn = C(FIXES[name][0]), C(FIXES[name][1])
        raw = raw_of(fname)
        o = M.to_file_style(no, raw)
        c = raw.count(o)
        if c != 1:
            print('FAIL [%s] new anchor hits=%d' % (name, c))
            sys.exit(1)
        new_mutations.append((name, (fname, no, nn)))
        applied += 1
    else:
        new_mutations.append((name, spec))

if applied != len(FIXES):
    print('FAIL: applied %d / %d（名字没对上的：检查拼写）' % (applied, len(FIXES)))
    sys.exit(1)

out = []
out.append('# -*- coding: utf-8 -*-')
out.append('# ★ 2026-10-07 从 __pycache__/df_mut_check.cpython-313.pyc（Oct 3 版，343 条手修锚点）反构建恢复，')
out.append('#   并按当日代码把 14 条漂移锚点修到当前字节（_apply_anchor_fixes.py）。')
out.append('#   起因：重跑 mk_df_mut.py 会把手修锚点全冲掉（生成链相对手修已陈旧）。')
out.append('#   此后本文件回到「手维护」模式：改锚点直接改这里（与此前实际做法一致）。')
out.append('#   check_mut_anchors.py / df_check_new_muts.py / _mut_isolate.py 均从本模块取符号。')
out.append('')
out.append('import os')
out.append('import sys')
out.append('')
out.append("HERE = os.path.dirname(os.path.abspath(__file__))")
out.append("DF = os.path.dirname(HERE)")
out.append("BETA = r'D:\\Game\\World of Warcraft\\_classic_beta_\\Interface\\AddOns\\DungeonsForever'")
out.append("TITAN = r'D:\\Game\\World of Warcraft\\_classic_titan_\\Interface\\AddOns\\DungeonsForever'")
out.append('')
out.append('def file_is_crlf(data):')
out.append("    cr = data.count(b'\\r\\n')")
out.append("    return cr > 0 and data.count(b'\\n') == cr")
out.append('')
out.append('def to_file_style(anchor, data):')
out.append('    if file_is_crlf(data):')
out.append("        return anchor.replace(b'\\r\\n', b'\\n').replace(b'\\n', b'\\r\\n')")
out.append("    return anchor.replace(b'\\r\\n', b'\\n')")
out.append('')
out.append('def split_spec(spec):')
out.append('    if len(spec) == 3 and isinstance(spec[0], str):')
out.append('        return (spec[0], spec[1], spec[2])')
out.append('    if len(spec) == 2 and isinstance(spec[0], str):')
out.append('        return (spec[0], spec[1][0], spec[1][1])')
out.append("    assert len(spec) == 2, '变异必须是 2 元组 (old, new)，当前 %d 元' % len(spec)")
out.append("    return ('Core/DungeonUI.lua', spec[0], spec[1])")
out.append('')
out.append('MUTATIONS = [')
for name, spec in new_mutations:
    out.append('    (%r, %r),' % (name, spec))
out.append(']')
out.append('')
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'df_mut_check.py'),
     'w', encoding='utf-8', newline='\n').write('\n'.join(out))
print('OK: %d mutations, %d anchors updated' % (len(new_mutations), applied))
