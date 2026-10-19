# -*- coding: utf-8 -*-
"""df_dungeon_check.py 补丁：胶囊计数 7→8 + PvP 页静态/运行时双份断言。
锚点命中数断言 + 幂等；mk_df_check.py 同步同型改动（该文件已与产物有历史漂移，只做同向修正）。
"""
import io, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

def load(p):
    return open(os.path.join(HERE, p), 'rb').read().decode('utf-8')

def save(p, s):
    open(os.path.join(HERE, p), 'wb').write(s.encode('utf-8'))

# ── 1. 胶囊计数 7 → 8（静态等宽 + 运行时分端 + 注释） ─────────────────────
FIX_COUNT = [
    ("src.count('width = DG.CAPSULE_W') == 7", "src.count('width = DG.CAPSULE_W') == 8"),
    ("#   只要有一颗用了别的宽就会跳形。", "#   只要有一颗用了别的宽就会跳形。"),
    ("#   只要有一颗用了别的宽就会跳形。", "#   只要有一颗用了别的宽就会跳形。"),
]

# ── 2. 静态断言块（插在「第三颗专业」断言之后） ──────────────────────────
STATIC_ANCHOR = "    ck('★★ 第三颗「专业」在无限服/正式服出现（泰坦端没有对应物品与专业）',\n       'if ns.LoadForeverPages then' in src\n       and 'defs[#defs + 1] = { key = \"Professions\", text = L[\"专业\"], width = DG.CAPSULE_W }' in src)\n"
STATIC_BLOCK = '''
    # ── PvP 页（2026-10-08 新增第 8 颗胶囊，仅无限服）静态断言 ──
    _pv = open(os.path.join(ADDON, 'Core', 'PvPUI.lua'), encoding='utf-8',
               errors='replace').read().replace('\\r\\n', '\\n')
    _pvp_toc = open(TOC, encoding='utf-8', errors='replace').read().replace('\\r\\n', '\\n')
    _pvp_rk = open(os.path.join(ADDON, 'Core', 'Data', 'Data_PvPRanks.lua'), encoding='utf-8',
                   errors='replace').read().replace('\\r\\n', '\\n')
    _pvp_sd = open(os.path.join(ADDON, 'Core', 'Data', 'Data_PvPSets.lua'), encoding='utf-8',
                   errors='replace').read().replace('\\r\\n', '\\n')
    _toc_pvpline = _pvp_toc.find('Core\\\\PvPUI.lua')
    _toc_dunline = _pvp_toc.find('Core\\\\DungeonUI.lua')
    _toc_dataline = _pvp_toc.find('Core\\\\Data\\\\Data_PvPRanks.lua')
    ck('★ PvP 页在 TOC 且排在 DungeonUI 之后（取 ns.ProfHost 依赖）',
       _toc_pvpline > -1 and _toc_dunline > -1 and _toc_pvpline > _toc_dunline)
    ck('★ PvP 数据文件在 TOC 且排在 PvPUI 之前',
       _toc_dataline > -1 and _toc_dataline < _toc_pvpline)
    ck('★ DungeonUI 里 PvP 胶囊挂在 LoadForeverPages 闸内（泰坦端不出现）',
       'defs[#defs + 1] = { key = "PvP", text = L["PvP"], width = DG.CAPSULE_W }' in src)
    ck('★ DungeonUI 里 pvpPage 页面帧 + 存档还原 + SwitchSub/UpdateActiveSub/EnsureBuilt 分派齐备',
       'U.pvpPage = CreateFrame("Frame", nil, panel)' in src
       and 'saved == "PvP" and ns.LoadForeverPages' in src
       and 'if U.pvpPage then U.pvpPage:SetShown(isPvP) end' in src
       and 'elseif key == "PvP" and ns.LoadForeverPages then' in src
       and 'ns.PvPModule.Build(U.pvpPage)' in src
       and 'ns.PvPModule.Open()' in src
       and 'ns.PvPModule.Refresh()' in src)
    ck('★ 物品到货重刷已接 PvP（RefreshItemCards 尾部走 ns.PvPModule.OnItemData）',
       'if PVM and PVM.OnItemData then PVM.OnItemData(itemID) end' in src)
    ck('★ PvPUI 模块导出与池常量（芯片池 40 / 物品卡池 16 / 军衔行 14）',
       'ns.PvPModule = PV' in _pv and 'PV.CHIP_MAX = 40' in _pv
       and 'PV.CARD_MAX = 16' in _pv and 'for i = 1, 14 do' in _pv)
    ck('★ PvPUI 图标裁边口径（5 处创建点全部 0.07, 0.93）',
       _pv.count('SetTexCoord(0.07, 0.93, 0.07, 0.93)') == 5,
       str(_pv.count('SetTexCoord(0.07, 0.93, 0.07, 0.93)')))
    ck('★ PvPUI 零站点回退（名字走 DG.ItemName，客户端没缓存才落 物品 #N）',
       'Host.DG.ItemName' in _pv and 'RequestItem' in _pv)
    ck('★ Data_PvPRanks 数据量：14 军衔 + 10 周上限 + 8 印记 + 4 战场',
       _pvp_rk.count('= { pts =') == 14 and _pvp_rk.count('rank = ') >= 18
       and _pvp_rk.count('{ key = "') == 4,
       '%d/%d' % (_pvp_rk.count('= { pts ='), _pvp_rk.count('{ key = "')))
    ck('★ Data_PvPSets 数据量：15 套 × 2 阵营 × 蓝/紫 + 暗矛两级',
       _pvp_sd.count('class = "') == 15 and _pvp_sd.count('blue = {') == 15
       and _pvp_sd.count('epic = {') == 15
       and 'honored' in _pvp_sd and 'revered' in _pvp_sd)
'''

# ── 3. 运行时断言（插在「两颗胶囊文案」之后） ────────────────────────────
RUNTIME_ANCHOR_COUNT = '      ck("★ 胶囊行颗数分端（无限服 7 / 泰坦 2）",\n         #(U.subTabs or {}) == (IS_FOREVER and 7 or 2), #(U.subTabs or {}))\n'
RUNTIME_COUNT_NEW = ('      ck("★ 胶囊行颗数分端（无限服 8 / 泰坦 2）",\n'
                     '         #(U.subTabs or {}) == (IS_FOREVER and 8 or 2), #(U.subTabs or {}))\n')

RUNTIME_ANCHOR_AFTER = '      ck("★ 两颗胶囊文案 = 5人本 / 团本（用户 2026-09-23 改名）",\n         _t1 ~= nil and _t1.text == "5人本" and _t2 ~= nil and _t2.text == "团本",\n         tostring(_t1 and _t1.text) .. " / " .. tostring(_t2 and _t2.text))\n'
RUNTIME_BLOCK = '''      ck("★ 第 8 颗胶囊 key = PvP（仅无限服；泰坦端上面条数断言已挡）",
         (U.subTabs or {})[8] ~= nil and U.subTabs[8].key == "PvP",
         tostring(U.subTabs[8] and U.subTabs[8].key))
      if IS_FOREVER then
        U:SwitchSub("PvP")
        ck("★ SwitchSub(PvP) 后 pvpPage 显示且已构建",
           U.pvpPage ~= nil and U.pvpPage.__shown == true
           and TF_NS.PvPModule ~= nil and TF_NS.PvPModule.built == true)
        ck("★ PvP 页默认落在军衔子页且行池 14 行、芯片池 40",
           TF_NS.PvPModule.cur == "ranks"
           and #TF_NS.PvPModule.rankRows == 14
           and #TF_NS.PvPModule.chips == 40
           and #TF_NS.PvPModule.cards == 16)
        ck("★ 军衔表首行已渲染（R1 列兵/侦察兵 750/750 第1周）",
           TF_NS.PvPModule.rankRows[1].pts.__text == "750"
           and TF_NS.PvPModule.rankRows[1].cum.__text == "750"
           and TF_NS.PvPModule.rankRows[1].week.__text ~= nil)
        U:SwitchSub("Dungeons")
        ck("★ 切回 5人本后 pvpPage 隐藏（互斥）",
           U.pvpPage.__shown == false)
      end
'''

def patch(path, pairs):
    s = load(path)
    for old, new in pairs:
        n = s.count(old)
        if n != 1:
            print('FAIL %s: anchor hit %d times: %r' % (path, n, old[:60]))
            sys.exit(1)
    if 'PvPUI.lua' in s and '第 8 颗胶囊 key = PvP' in s:
        print('SKIP %s (already patched)' % path)
        return
    for old, new in pairs:
        s = s.replace(old, new, 1)
    save(path, s)
    print('patched', path)

pairs = [
    (FIX_COUNT[0][0], FIX_COUNT[0][1]),
    (STATIC_ANCHOR, STATIC_ANCHOR + STATIC_BLOCK),
    (RUNTIME_ANCHOR_COUNT, RUNTIME_COUNT_NEW),
    (RUNTIME_ANCHOR_AFTER, RUNTIME_ANCHOR_AFTER + RUNTIME_BLOCK),
]
patch('df_dungeon_check.py', pairs)
patch('mk_df_check.py', [
    ("src.count('width = DG.CAPSULE_W') == 7", "src.count('width = DG.CAPSULE_W') == 8"),
    (RUNTIME_ANCHOR_COUNT.replace('无限服 7', '无限服 5') if False else '      ck("★ 胶囊行颗数分端（无限服 5 / 泰坦 2）",\n         #(U.subTabs or {}) == (IS_FOREVER and 5 or 2), #(U.subTabs or {}))\n',
     RUNTIME_COUNT_NEW),
])
import py_compile
py_compile.compile(os.path.join(HERE, 'df_dungeon_check.py'), doraise=True)
py_compile.compile(os.path.join(HERE, 'mk_df_check.py'), doraise=True)
print('py_compile OK')
