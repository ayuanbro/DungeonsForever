# -*- coding: utf-8 -*-
"""给「详情页地图页签」补 harness 断言与变异（2026-09-30）。

一次改三件（都是 LF 文本，二进制读写）：
  1. df_dungeon_check.py   既有 7 条页签断言跟着四态化 + 新增地图页静态/动态断言块
  2. df_mut_check.py       修正 2 条被改坏的锚点 + 9 条地图页变异（其中 4 条打 Core/MapUI.lua）
  3. df_check_new_muts.py  DEFAULT_WANT 登记这 9 条

★ 变异锚点一律「摘整项 / 换整行」，禁止把表收尾符留在替换区间外（那会变成 Lua 语法错 = 脏抓）。

    python patch_map_assert.py --check
    python patch_map_assert.py
"""
import sys

HERE = r"D:/workspace/DungeonsForever/_temp"
D = HERE + "/df_dungeon_check.py"
M = HERE + "/df_mut_check.py"
W = HERE + "/df_check_new_muts.py"

# ─────────────────────────── 1) df_dungeon_check.py ───────────────────────────

STATIC_BLOCK = '''    # ★★ 详情页「地图」页签（2026-09-30 新增；页面独立成件 Core/MapUI.lua）
    #    图源 = 客户端自带的世界地图瓦片。只登记**副本内图**：
    #    只有区域图的 3 个（旧铁炉堡 / 湿地区域 / 提瑞斯法）+ 完全没图的 5 个一律空态。
    _mapui = open(os.path.join(ADDON, 'Core', 'MapUI.lua'), encoding='utf-8',
                  errors='replace').read()
    _mapbare = '\\n'.join(l.split('--')[0] for l in _mapui.split('\\n'))
    ck('★★ 地图页独立成件且 toc 排在 DungeonUI 之后（ProfHost 在后者末尾才赋值）',
       'Core\\\\MapUI.lua' in _toc_seq
       and _toc_seq.index('Core\\\\DungeonUI.lua') < _toc_seq.index('Core\\\\MapUI.lua'))
    ck('★★ 只登记副本内图 —— 区域图目录一个都不许进表（旧铁炉堡 / 湿地区域 / 提瑞斯法 / 洛丹伦废墟）',
       'OldIronforge' not in _mapbare and 'Wetlands' not in _mapbare
       and 'Tirisfal' not in _mapbare and 'RuinsofLordaeron' not in _mapbare)
    _mcnt = _mapbare.count(r'= "Interface\\\\WorldMap\\\\')
    ck('★★ 图源一律客户端自带瓦片（21 条路径 = 18 条明细 + 3 条共用前缀）',
       _mcnt == 21, _mcnt)
    ck('★ 瓦片几何常量：4 列 × 3 行 / 单块 256 / 有效画面 1002×668（右侧 22 与底部 100 是装饰边）',
       'M.COLS, M.ROWS = 4, 3' in _mapbare and 'M.TILE = 256' in _mapbare
       and 'M.ART_W, M.ART_H = 1002, 668' in _mapbare)
    _mpsplit = _mapbare.split('function M.Paint')
    ck('★★ 帧只在 Build 里建（渲染路径零新建帧：Paint 里不许出现 CreateFrame）',
       len(_mpsplit) == 2 and 'CreateFrame' not in _mpsplit[1])
    ck('★ 无图副本给空态文案（不是留白），有图 / 无图两条路都在',
       'L["这个副本没有客户端自带的地图。"]' in _mapbare
       and 'frame.empty:Show()' in _mapbare)

'''

DYNAMIC_BLOCK = '''
    -- ---------- 详情页「地图」页签（2026-09-30 新增，最左第四颗）----------
    do
      local _MM = TF_NS.MapModule
      ck("★★ 地图模块已装载（ns.MapModule + Paint / Layout）",
         _MM ~= nil and type(_MM.Paint) == "function" and type(_MM.Layout) == "function")
      local _art = (_MM and _MM.ART) or {}
      local _na, _nr = 0, 0
      for _, d in ipairs(data.dungeons) do
        if _art[d.id] then _na = _na + 1 else _nr = _nr + 1 end
      end
      ck("★★ 27 个副本有客户端内地图 / 8 个走空态（与实机 /mapprobe inv 盘点逐条一致）",
         _na == 27 and _nr == 8, _na .. "/" .. _nr)
      ck("★★ 只登记副本内图 —— 三个只有区域图的副本（领主大厅 / 挖掘场湿地 / 洛丹伦废墟）一律空态",
         _MM.PathFor("hall_of_thanes") == nil
         and _MM.PathFor("excavation_wetlands") == nil
         and _MM.PathFor("ruins_of_lordaeron") == nil)
      local _zone = 0
      for _, _p in pairs(_art) do
        local _lp = string.lower(_p)
        if _lp:find("oldironforge", 1, true) or _lp:find("tirisfal", 1, true)
           or _lp:find("wetlands", 1, true) then _zone = _zone + 1 end
      end
      ck("★★ 表里不许混进区域图目录（旧铁炉堡 / 提瑞斯法 / 湿地区域）", _zone == 0, _zone)
      ck("★ 路径前缀（怒焰 / 达拉然抽查）",
         _MM.PathFor("ragefire_chasm") == "Interface\\\\WorldMap\\\\Ragefire\\\\Ragefire1_"
         and _MM.PathFor("city_of_dalaran") == "Interface\\\\WorldMap\\\\Dalaran\\\\Dalaran1_",
         tostring(_MM.PathFor("ragefire_chasm")))
      ck("★★ 四个血色分区共用一套图 / 厄运三区共用一套 / 斯坦索姆两区共用一套",
         _MM.PathFor("sm_graveyard") == _MM.PathFor("sm_cathedral")
         and _MM.PathFor("dire_maul_east") == _MM.PathFor("dire_maul_west")
         and _MM.PathFor("stratholme_main") == _MM.PathFor("stratholme_service"))

      local _w1, _h1, _x1, _y1 = _MM.FitBox(1002, 668)
      ck("★★ 适应几何：正好放得下时 1:1 且不偏移（1002×668 → 1002×668 / 0,0）",
         _w1 == 1002 and _h1 == 668 and _x1 == 0 and _y1 == 0,
         _w1 .. "x" .. _h1 .. " @" .. _x1 .. "," .. _y1)
      local _w2, _h2 = _MM.FitBox(501, 668)
      ck("★★ 适应几何：宽受限时等比缩（501×668 → 501×334）", _w2 == 501 and _h2 == 334,
         _w2 .. "x" .. _h2)
      local _w3, _h3, _x3, _y3 = _MM.FitBox(936, 502)
      ck("★★ 适应几何：详情页可用区 936×502 → 高度吃满、宽不超 936、左右留白对称",
         _h3 == 502 and _w3 > 700 and math.abs(_w3 + _x3 * 2 - 936) <= 1 and _y3 == 0,
         _w3 .. "x" .. _h3 .. " x=" .. _x3)

      local _lay = _MM.Layout(1002, 668)
      ck("★★ 瓦片布局 = 12 块（4 列 × 3 行，行优先）", #_lay == 12, #_lay)
      local _p1, _p9, _p12 = _lay[1], _lay[9], _lay[12]
      ck("★ 第 1 块贴左上、256×256 满幅 UV",
         _p1.x == 0 and _p1.y == 0 and _p1.w == 256 and _p1.h == 256
         and _p1.u0 == 0 and _p1.u1 == 1 and _p1.v0 == 0 and _p1.v1 == 1)
      ck("★★ 第三行按有效画面裁短（高 156 = 668 - 512，UV 只取到 0.609375）",
         _p9.h == 156 and math.abs(_p9.v1 - 0.609375) < 1e-9, _p9.h .. "/" .. tostring(_p9.v1))
      ck("★★ 第四列按有效画面裁窄（宽 234 = 1002 - 768）", _p12.w == 234, _p12.w)
      ck("★★ 12 块拼满有效画面（每行宽和 = 1002 / 每列高和 = 668）",
         _lay[1].w + _lay[2].w + _lay[3].w + _lay[4].w == 1002
         and _lay[1].h + _lay[5].h + _lay[9].h == 668)

      local _rfc, _hall2
      for _, d in ipairs(data.dungeons) do
        if d.id == "ragefire_chasm" then _rfc = d
        elseif d.id == "hall_of_thanes" then _hall2 = d end
      end

      U:ShowDungeonDetail(_rfc)
      U:SetDungeonTab("map")
      ck("★★ 切地图 → curTab = map", U.dungeonTab == "map", tostring(U.dungeonTab))
      ck("★★ 切地图 → 地图容器显示 / 掉落区与攻略区都隐藏",
         U.dungeonMapFrame.__shown == true and U.dungeonDetailScroll.__shown == false
         and U.dungeonGuideScroll.__shown == false)
      ck("★★ 切地图 → 任务列表与任务详情都隐藏",
         U.dungeonQuestScroll.__shown == false and U.dungeonQDet.__shown == false)
      local _fv3 = 0
      for _, b in pairs(U.dungeonFilterBtns or {}) do if b.__shown then _fv3 = _fv3 + 1 end end
      ck("★★ 切地图 → 筛选按钮全隐（地图不分档）", _fv3 == 0, _fv3)

      local _tiles = U.dungeonMapFrame.tiles
      local _show, _path = 0, 0
      for _i = 1, #_tiles do
        if _tiles[_i].__shown then _show = _show + 1 end
        local _tx = tostring(_tiles[_i].__tex or "")
        if _tx:find("Ragefire1_", 1, true) then _path = _path + 1 end
      end
      ck("★★ 有图副本（怒焰裂谷）→ 12 块瓦片全显", _show == 12, _show)
      ck("★★ 12 块都指向该副本的瓦片前缀（不是别的图 / 占位）", _path == 12, _path)
      ck("★ 有图副本不显示空态", U.dungeonMapFrame.empty.__shown == false)

      U:ShowDungeonDetail(_hall2)
      U:SetDungeonTab("map")
      local _s0 = 0
      for _i = 1, #_tiles do if _tiles[_i].__shown then _s0 = _s0 + 1 end end
      ck("★★ 无图副本（领主大厅）→ 12 块全隐 + 空态文案出现（不给区域图顶替）",
         _s0 == 0 and U.dungeonMapFrame.empty.__shown == true, _s0)

      FRAMES = 0
      U:SetDungeonTab("loot")
      U:SetDungeonTab("map")
      U:SetDungeonTab("loot")
      ck("★★ 反复切地图页零新建帧（瓦片池复用）", FRAMES == 0, FRAMES)

      U:ShowDungeonDetail(_rfc)
      U:SetDungeonTab("loot")
      ck("★ 切回掉落 → 地图容器隐藏 / 掉落区显示（互斥不破）",
         U.dungeonMapFrame.__shown == false and U.dungeonDetailScroll.__shown == true)
    end

'''

CHECK_PATCHES = [
    (
        "页签三项 → 四项，「地图」排最左（存在性先短路，防变异时 index 抛异常）",
        """    ck('★★ 详情页签三项且「攻略」排最左（右起排布 ⇒ defs 第三项）',
       '{ key = "loot", text = L["掉落"] }' in _tabs
       and '{ key = "quest", text = L["任务"] }' in _tabs
       and '{ key = "guide", text = L["攻略"] }' in _tabs
       and _tabs.index('key = "guide"') > _tabs.index('key = "quest"')
       > _tabs.index('key = "loot"'))
""",
        """    ck('★★ 详情页签四项且「地图」排最左（右起排布 ⇒ defs 第四项）',
       all(k in _tabs for k in ('key = "loot"', 'key = "quest"',
                                'key = "guide"', 'key = "map"'))
       and _tabs.index('key = "map"') > _tabs.index('key = "guide"')
       > _tabs.index('key = "quest"')
       > _tabs.index('key = "loot"'))
""",
    ),
    (
        "SetDungeonTab 三态 → 四态",
        """    ck('★★ SetDungeonTab 三态（掉落 / 任务 / 攻略；漏一态 ⇒ 点攻略落在掉落页）',
       'if tab == "quest" then t = "quest" elseif tab == "guide" then t = "guide" end' in _rset)
""",
        """    ck('★★ SetDungeonTab 四态（掉落 / 任务 / 攻略 / 地图；漏一态 ⇒ 点该页落回掉落页）',
       'if tab == "quest" then t = "quest" elseif tab == "guide" then t = "guide" elseif tab == "map" then t = "map" end' in _rset)
""",
    ),
    (
        "RenderDungeonTab 分派三分支 → 四分支",
        """    ck('★★ RenderDungeonTab 分派三分支（否则攻略页永远渲染不出来）',
       'if U.dungeonGuideScroll then U.dungeonGuideScroll:SetShown(isGuide) end' in _rtab
       and 'elseif isGuide then' in _rtab and 'U:RenderDungeonGuide()' in _rtab)
""",
        """    ck('★★ RenderDungeonTab 分派四分支（否则攻略 / 地图页永远渲染不出来）',
       'if U.dungeonGuideScroll then U.dungeonGuideScroll:SetShown(isGuide) end' in _rtab
       and 'if U.dungeonMapFrame then U.dungeonMapFrame:SetShown(isMap) end' in _rtab
       and 'elseif isGuide then' in _rtab and 'U:RenderDungeonGuide()' in _rtab
       and 'elseif isMap then' in _rtab and 'ns.MapModule.Paint(U.dungeonDetailCur)' in _rtab)
""",
    ),
    (
        "掉落滚动区让位（加地图态）",
        """    ck('★ 攻略态下掉落滚动区必须让位（不是叠在攻略上）',
       'SetShown(not isQuest and not isGuide)' in _rtab)
""",
        """    ck('★ 攻略 / 地图态下掉落滚动区必须让位（不是叠在上面）',
       'SetShown(not isQuest and not isGuide and not isMap)' in _rtab)
""",
    ),
    (
        "筛选按钮全隐（加地图态）",
        """    ck('★★ 攻略态下筛选按钮全隐（攻略不分档，留着会挂空档位）',
       'if isGuide then' in _rtab and 'U.dungeonFilterBtns[i]:Hide()' in _rtab)
""",
        """    ck('★★ 攻略 / 地图态下筛选按钮全隐（这两页不分档，留着会挂空档位）',
       'if isGuide or isMap then' in _rtab and 'U.dungeonFilterBtns[i]:Hide()' in _rtab)
""",
    ),
    (
        "DB 存档三态 → 四态 + 地图容器建帧 / 复位",
        """    ck('★★ DB 存的页签三态都能还原（漏 guide ⇒ 重开界面点攻略跳掉落）',
       'U.dungeonTab = (dt == "quest" or dt == "guide") and dt or "loot"' in src)
""",
        """    ck('★★ DB 存的页签四态都能还原（漏 map ⇒ 重开界面点地图跳掉落）',
       'U.dungeonTab = (dt == "quest" or dt == "guide" or dt == "map") and dt or "loot"' in src)
    ck('★★ 地图容器在 Build 里一次建好（帧 + 12 块瓦片池都在这条路径上）',
       'U.dungeonMapFrame = ns.MapModule.Build(detail, hero)' in src)
    ck('★ Build 复位清单收进地图容器（防跨页复用旧池）',
       'U.dungeonMapFrame = nil' in src)
""",
    ),
    (
        "动态：详情页签共 3 个 → 4 个",
        """      ck("★★ 详情页签共 3 个（掉落 / 任务 / 攻略）", _ntb == 3 and _tb.guide ~= nil, _ntb)
""",
        """      ck("★★ 详情页签共 4 个（掉落 / 任务 / 攻略 / 地图）",
         _ntb == 4 and _tb.guide ~= nil and _tb.map ~= nil, _ntb)
""",
    ),
    (
        "静态：插入地图页断言块（攻略静态块之后）",
        """    ck('★★ BOSS 中文名从掉落表反查（攻略数据只存英文键 ⇒ 名字单一真源）',
       'function DG.GuideBossName(dungeonID, en)' in src
       and 'if loot[i][1] == en then return loot[i][2] or en end' in src)
""",
        """    ck('★★ BOSS 中文名从掉落表反查（攻略数据只存英文键 ⇒ 名字单一真源）',
       'function DG.GuideBossName(dungeonID, en)' in src
       and 'if loot[i][1] == en then return loot[i][2] or en end' in src)

""" + STATIC_BLOCK,
    ),
    (
        "动态：插入地图页断言块（攻略动态块之后）",
        """      U:SetDungeonTab("loot")
      ck("★ 切回掉落 → 攻略区隐藏 / 掉落区显示（互斥不破）",
         U.dungeonGuideScroll.__shown == false and U.dungeonDetailScroll.__shown == true)
    end
""",
        """      U:SetDungeonTab("loot")
      ck("★ 切回掉落 → 攻略区隐藏 / 掉落区显示（互斥不破）",
         U.dungeonGuideScroll.__shown == false and U.dungeonDetailScroll.__shown == true)
    end
""" + DYNAMIC_BLOCK,
    ),
]

# ─────────────────────────── 2) df_mut_check.py ───────────────────────────

GUIDE_TAB_OLD = """MUT_GUIDE_TAB_GONE = (
    b', { key = "guide", text = L["\\xe6\\x94\\xbb\\xe7\\x95\\xa5"] } }',
    b' }')
"""

GUIDE_TAB_NEW = """MUT_GUIDE_TAB_GONE = (
    # 2026-09-30：页签表长了第四项（地图）⇒ 锚点收成「只摘攻略那一项」，不再连表尾一起吞
    #（吞了表尾 `} }` 就是 Lua 语法错 = 脏抓）。
    ', { key = "guide", text = L["攻略"] }'.encode('utf-8'),
    b'')
"""

GUIDE_SCROLL_OLD = """MUT_GUIDE_KEEP_SCROLL = (
    b'    if U.dungeonDetailScroll then U.dungeonDetailScroll:SetShown(not isQuest and not isGuide) end\\r\\n',
    b'    if U.dungeonDetailScroll then U.dungeonDetailScroll:SetShown(not isQuest) end -- MUT\\r\\n')
"""

GUIDE_SCROLL_NEW = """MUT_GUIDE_KEEP_SCROLL = (
    # 2026-09-30：让位条件长了 `and not isMap` ⇒ 变异改成「把地图那半条件摘掉」。
    b'    if U.dungeonDetailScroll then U.dungeonDetailScroll:SetShown(not isQuest and not isGuide and not isMap) end\\r\\n',
    b'    if U.dungeonDetailScroll then U.dungeonDetailScroll:SetShown(not isQuest and not isGuide) end -- MUT\\r\\n')
"""

MAP_MUTS = '''# ㊷ 详情页「地图」页签（2026-09-30 新增；图源 = 客户端自带世界地图瓦片）
#    四条打 DungeonUI.lua 的挂点，五条打 Core/MapUI.lua 本体（表内容 / 裁剪 / 空态）。
MUT_MAP_TAB_GONE = (
    ', { key = "map", text = L["地图"] }'.encode('utf-8'),
    b'')

MUT_MAP_DISPATCH_LOOT = (
    b'    elseif isMap then\\r\\n'
    b'        if ns.MapModule then ns.MapModule.Paint(U.dungeonDetailCur) end\\r\\n',
    b'    elseif isMap then\\r\\n'
    b'        U:RenderDungeonLoot() -- MUT: map tab renders loot\\r\\n')

MUT_MAP_KEEP_SCROLL = (
    b'    if U.dungeonMapFrame then U.dungeonMapFrame:SetShown(isMap) end\\r\\n',
    b'    if U.dungeonMapFrame then U.dungeonMapFrame:SetShown(true) end -- MUT: map container never hidden\\r\\n')

MUT_MAP_FILTER_KEEP = (
    b'    if isGuide or isMap then\\r\\n',
    b'    if isGuide then -- MUT: map keeps the filter row\\r\\n')

MUT_MAP_RESTORE_DROP = (
    b'        U.dungeonTab = (dt == "quest" or dt == "guide" or dt == "map") and dt or "loot"\\r\\n',
    b'        U.dungeonTab = (dt == "quest" or dt == "guide") and dt or "loot" -- MUT: map restore dropped\\r\\n')

MUT_MAP_ART_DROP = ('Core/MapUI.lua', (
    b'    city_of_dalaran       = "Interface\\\\WorldMap\\\\Dalaran\\\\Dalaran1_",\\n',
    b'    -- MUT: dalaran map row dropped\\n'))

MUT_MAP_ART_ZONE = ('Core/MapUI.lua', (
    b'local ART = {\\n',
    b'local ART = {\\n'
    b'    hall_of_thanes        = "Interface\\\\WorldMap\\\\OldIronforge\\\\OldIronforge",\\n'))

MUT_MAP_CROP_GONE = ('Core/MapUI.lua', (
    b'M.ART_W, M.ART_H = 1002, 668\\n',
    b'M.ART_W, M.ART_H = 1024, 768 -- MUT: decoration edge given up\\n'))

MUT_MAP_EMPTY_GONE = ('Core/MapUI.lua', (
    b'        frame.empty:Show()\\n',
    b'        frame.empty:Hide() -- MUT: empty state never shown\\n'))

'''

MUT_PATCHES = [
    ("修正 MUT_GUIDE_TAB_GONE 锚点", GUIDE_TAB_OLD, GUIDE_TAB_NEW),
    ("修正 MUT_GUIDE_KEEP_SCROLL 锚点", GUIDE_SCROLL_OLD, GUIDE_SCROLL_NEW),
    (
        "插入地图页变异定义（挂在 MUTATIONS 表头之前）",
        "MUTATIONS = [\n    # ㉕ 副本攻略页 卡片式版面（2026-09-29 用户定「4 个卡片、两列、极简描边」）\n",
        MAP_MUTS + "\nMUTATIONS = [\n    # ㉕ 副本攻略页 卡片式版面（2026-09-29 用户定「4 个卡片、两列、极简描边」）\n",
    ),
    (
        "注册地图页变异进 MUTATIONS",
        "    ('攻略：页签「攻略」被摘（入口消失）', MUT_GUIDE_TAB_GONE),\n",
        "    ('攻略：页签「攻略」被摘（入口消失）', MUT_GUIDE_TAB_GONE),\n"
        "    # ㊷ 详情页「地图」页签（2026-09-30 新增）\n"
        "    ('地图：页签「地图」被摘（入口消失）', MUT_MAP_TAB_GONE),\n"
        "    ('地图：点地图渲染成掉落页（分派串线）', MUT_MAP_DISPATCH_LOOT),\n"
        "    ('地图：地图容器不随页签隐藏', MUT_MAP_KEEP_SCROLL),\n"
        "    ('地图：地图态没隐掉筛选行（挂一排空档位）', MUT_MAP_FILTER_KEEP),\n"
        "    ('地图：存档还原丢掉 map（重开界面点地图跳掉落）', MUT_MAP_RESTORE_DROP),\n"
        "    ('地图：有条副本被从地图表里摘掉（该副本变空态）', MUT_MAP_ART_DROP),\n"
        "    ('地图：区域图被塞进表（旧铁炉堡冒充副本内图）', MUT_MAP_ART_ZONE),\n"
        "    ('地图：放弃裁装饰边（1024×768 整幅上屏）', MUT_MAP_CROP_GONE),\n"
        "    ('地图：空态分支被摘（无图副本一片空白）', MUT_MAP_EMPTY_GONE),\n",
    ),
]

WANT_BLOCK = """    # ㊷ 详情页「地图」页签（2026-09-30 新增）
    '地图：页签「地图」被摘（入口消失）',
    '地图：点地图渲染成掉落页（分派串线）',
    '地图：地图容器不随页签隐藏',
    '地图：地图态没隐掉筛选行（挂一排空档位）',
    '地图：存档还原丢掉 map（重开界面点地图跳掉落）',
    '地图：有条副本被从地图表里摘掉（该副本变空态）',
    '地图：区域图被塞进表（旧铁炉堡冒充副本内图）',
    '地图：放弃裁装饰边（1024×768 整幅上屏）',
    '地图：空态分支被摘（无图副本一片空白）',
]
"""

WANT_PATCHES = [
    ("登记地图页变异进 DEFAULT_WANT",
     "    '专业页：iOS 开关不再绑定设置键（点了也写不进 DB）',\n]\n",
     "    '专业页：iOS 开关不再绑定设置键（点了也写不进 DB）',\n" + WANT_BLOCK),
]


def apply(path, patches, check):
    raw = open(path, "rb").read()
    crlf = raw.count(b"\r\n") > 0
    txt = raw.decode("utf-8").replace("\r\n", "\n")
    bad = 0
    for name, old, new in patches:
        n = txt.count(old)
        print("  %s[%d] %s" % ("OK " if n == 1 else "!! ", n, name))
        if n != 1:
            bad += 1
        elif not check:
            txt = txt.replace(old, new, 1)
    if not check and not bad:
        out = txt.replace("\r\n", "\n")
        if crlf:
            out = out.replace("\n", "\r\n")
        open(path, "wb").write(out.encode("utf-8"))
    return bad


def main():
    check = "--check" in sys.argv
    total = 0
    print("① %s" % D)
    total += apply(D, CHECK_PATCHES, check)
    print("② %s" % M)
    total += apply(M, MUT_PATCHES, check)
    print("③ %s" % W)
    total += apply(W, WANT_PATCHES, check)
    if total:
        print("\n锚点异常 %d 条，未写入。" % total)
        return 2
    print("\n%s" % ("全部锚点各命中 1 次（未写入）。" if check else "三份已写入。"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
