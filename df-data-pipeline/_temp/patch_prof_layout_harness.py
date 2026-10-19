# harness 同步：容器卡版式 + 总览内容删改
#  df_dungeon_check：大卡断言改 MakeCard 口径 + 新增双容器卡/阵营图标断言
#  df_mut_check：BIGCARD_UNPOS 重锚 + 新增 NAVCARD_GONE / FACICON_BACK
import io

def load(p):
    d = open(p, "rb").read().decode("utf-8")
    crlf = d.count("\r\n")
    lf = d.count("\n") - crlf
    return d.replace("\r\n", "\n"), crlf > lf

def save(p, t, crlf):
    if crlf:
        t = t.replace("\n", "\r\n")
    open(p, "wb").write(t.encode("utf-8"))

# ── df_dungeon_check.py ──
P1 = r"D:\workspace\DungeonsForever\_temp\df_dungeon_check.py"
t, crlf = load(P1)

def rep1(old, new, n=1):
    global t
    assert t.count(old) == n, "check anchor x%d (want %d): %s" % (t.count(old), n, old[:70])
    t = t.replace(old, new)

rep1("""    ck('★★ 专业页正文是一张**大卡片**（用户：现在是每一行一个小卡片 → 要整页一张）',
       'PD.listCard = listCard' in _pbuild
       and 'listCard:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)' in _pbuild)
    # ★ 顺序断言：同为 page 的子帧按创建序绘制 —— 大卡必须先于滚动帧建，否则盖住整页列表
    ck('★★ 大卡建在滚动帧**之前**（子帧按创建序绘制，反了就盖住列表）',
       _pbuild.index('PD.listCard = listCard') < _pbuild.index('SetScrollChild(child)'))
""",
"""    ck('★★ 专业页正文是一张**大卡片**（用户：现在是每一行一个小卡片 → 要整页一张）',
       'PD.listCard = PD.MakeCard(page)' in _pbuild
       and 'function PD.MakeCard(f)' in profui
       and 'c:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)' in profui)
    # ★ 顺序断言：同为 page 的子帧按创建序绘制 —— 大卡必须先于滚动帧建，否则盖住整页列表
    ck('★★ 大卡建在滚动帧**之前**（子帧按创建序绘制，反了就盖住列表）',
       _pbuild.index('PD.listCard = PD.MakeCard(page)') < _pbuild.index('SetScrollChild(child)'))
    # ★★ 容器卡版式（用户定）：左导航 + 右正文两张 L1 卡，顶/底对齐等高；子页签收进右卡
    ck('★★ 专业页双容器卡：navCard/listCard 先建垫底 + 等高锚定（窗沿 = PAGE_INSET+GUTTER，卡间 = GUTTER）',
       'PD.CARD_INSET = PAGE_INSET + (DG.GUTTER or 8)' in profui
       and 'PD.navCard = PD.MakeCard(page)' in _pbuild
       and 'PD.navCard:SetPoint("BOTTOMRIGHT", page, "BOTTOMLEFT",' in profui
       and 'PD.RIGHT_X - PD.LIST_PAD, -PD.CARD_INSET)' in profui
       and '-PD.CARD_INSET, PD.CARD_INSET)' in profui
       and _pbuild.index('PD.navCard = PD.MakeCard(page)')
           < _pbuild.index('navEntry("__index"'))
       and _pbuild.index('PD.navCard = PD.MakeCard(page)')
           < _pbuild.index('for _, def in ipairs(DG.PROF_SUBTABS)'))
""")

rep1("""       and 'function PD.RowsCamp' not in profui
       and '对营地系统的贡献' not in profui)
""",
"""       and 'function PD.RowsCamp' not in profui
       and '对营地系统的贡献' not in profui)
    # ⑳ 总览内容删改（用户）：简介状态行/状态标签说明退役；军需官行换阵营图标并入营地位置
    ck('★★ 总览删简介状态行与状态标签说明（p.status 不再上界面）',
       'text = p.status or L["未标注"]' not in profui
       and 'PushHead(rows, L["状态标签说明"])' not in profui)
    ck('★★ 军需官行：阵营图标 + 组织·区域·地点副行（营地行只在无军需官侧兜底）',
       'PD.FAC_ICON = {' in profui
       and 'icon = PD.FAC_ICON[side]' in profui
       and 'icon = vd[4]' not in profui
       and "loc = format(\\"%s · %s · %s\\", tostring(camp[1] or \\"\")," in profui
       and 'elseif camp then' in profui
       and 'L["营地位置 %.1f, %.1f"]' in profui)
""")
save(P1, t, crlf)

# ── df_mut_check.py ──
P2 = r"D:\workspace\DungeonsForever\_temp\df_mut_check.py"
t, crlf = load(P2)

def rep2(old, new, n=1):
    global t
    assert t.count(old) == n, "mut anchor x%d (want %d): %s" % (t.count(old), n, old[:70])
    t = t.replace(old, new)

rep2("""MUT_PROF_BIGCARD_UNPOS = ('Core/ProfessionUI.lua', (
    b'    PD.listCard:ClearAllPoints()\\n    PD.listCard:SetPoint("TOPLEFT", PD.page, "TOPLEFT",\\n                         PD.RIGHT_X - PD.LIST_PAD, -(top - PD.LIST_PAD))\\n    PD.listCard:SetPoint("BOTTOMRIGHT", PD.page, "BOTTOMRIGHT",\\n                         -PAGE_INSET, bot - PD.LIST_PAD)\\n',
    b'    PD.listCard:ClearAllPoints()\\n    -- MUT: big card never positioned\\n'))
""",
"""MUT_PROF_BIGCARD_UNPOS = ('Core/ProfessionUI.lua', (
    b'    PD.listCard:ClearAllPoints()\\n    PD.listCard:SetPoint("TOPLEFT", PD.page, "TOPLEFT",\\n                         PD.RIGHT_X - PD.LIST_PAD, -PD.CARD_INSET)\\n    PD.listCard:SetPoint("BOTTOMRIGHT", PD.page, "BOTTOMRIGHT",\\n                         -PD.CARD_INSET, PD.CARD_INSET)\\n',
    b'    PD.listCard:ClearAllPoints()\\n    -- MUT: big card never positioned\\n'))

MUT_PROF_NAVCARD_GONE = ('Core/ProfessionUI.lua', (
    b'    PD.navCard = PD.MakeCard(page)\\n    PD.navCard:SetPoint("TOPLEFT", page, "TOPLEFT", PD.CARD_INSET, -PD.CARD_INSET)\\n',
    b'    -- MUT: nav card gone\\n'))

MUT_PROF_FACICON_BACK = ('Core/ProfessionUI.lua', (
    b'kind = "row", col = 1, nameColor = fc, icon = PD.FAC_ICON[side],\\n',
    b'kind = "row", col = 1, nameColor = fc, icon = vd[4], -- MUT: faction icon reverted\\n'))
""")

rep2("""    ('专业页：大卡片没定位（等于没有大卡）', MUT_PROF_BIGCARD_UNPOS),
""",
"""    ('专业页：大卡片没定位（等于没有大卡）', MUT_PROF_BIGCARD_UNPOS),
    ('专业页：左导航容器卡被摘', MUT_PROF_NAVCARD_GONE),
    ('专业页：军需官阵营图标回退旧物品图标', MUT_PROF_FACICON_BACK),
""")
save(P2, t, crlf)
print("harness patched OK")
