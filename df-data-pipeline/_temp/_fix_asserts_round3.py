# -*- coding: utf-8 -*-
# 图钉修正轮：稀有钉并入 BossPos / 乌尔之书 6895@floor6 / 断言换新口径（9 处）
import io

def rd(p):
    return io.open(p, encoding='utf-8', newline='').read()

def wr(p, s):
    io.open(p, 'w', encoding='utf-8', newline='').write(s)

def rep1(src, old, new, tag):
    n = src.count(old)
    assert n == 1, '%s: anchor hit %d' % (tag, n)
    return src.replace(old, new, 1)

P = 'df_dungeon_check.py'
s = rd(P)

# ① 动态数据抽查：影牙只剩乌尔之书（floor6）、稀有钉去重
old = '''      ck("★★ 图钉扩展数据抽查：影牙 3（2 任务物品 + 1 稀有「死亡之誓」）/ 监狱 4（Bruegal×4，npcID=0）"
         .. " / 死矿 1 / 侏儒 1 / 洛丹伦废墟 2（1 入口 + 1 任务）",
         #(_MM.ExtraPinsFor("shadowfang_keep", nil) or {}) == 3
         and #(_MM.ExtraPinsFor("the_stockade", nil) or {}) == 4
         and #(_MM.ExtraPinsFor("the_deadmines", nil) or {}) == 1
         and #(_MM.ExtraPinsFor("gnomeregan", nil) or {}) == 1
         and #(_MM.ExtraPinsFor("ruins_of_lordaeron", nil) or {}) == 2
         and (_MM.ExtraPinsFor("shadowfang_keep", nil) or {})[3].name == "死亡之誓"
         and (_MM.ExtraPinsFor("the_stockade", nil) or {})[1].id == 0)'''
new = '''      ck("★★ 图钉扩展数据抽查：影牙只余乌尔之书（6895，第 6 层；floor1/2 不出）"
         .. " / 监狱 / 死矿 / 侏儒 = 0（稀有钉已并入 ns.BossPos，2026-10-04 去重）/ 洛丹伦废墟 2（1 入口 + 1 任务）",
         #(_MM.ExtraPinsFor("shadowfang_keep", nil) or {}) == 1
         and (_MM.ExtraPinsFor("shadowfang_keep", nil) or {})[1].id == 6895
         and #(_MM.ExtraPinsFor("shadowfang_keep", 6) or {}) == 1
         and #(_MM.ExtraPinsFor("shadowfang_keep", 1) or {}) == 0
         and #(_MM.ExtraPinsFor("shadowfang_keep", 2) or {}) == 0
         and #(_MM.ExtraPinsFor("the_stockade", nil) or {}) == 0
         and #(_MM.ExtraPinsFor("the_deadmines", nil) or {}) == 0
         and #(_MM.ExtraPinsFor("gnomeregan", nil) or {}) == 0
         and #(_MM.ExtraPinsFor("ruins_of_lordaeron", nil) or {}) == 2)'''
s = rep1(s, old, new, 'dyn data')

# ② 死亡矿井 floor1：5 → 4（矿工约翰森不再重复）
s = rep1(s,
    'ck("★★ 多层有坐标副本（死亡矿井 2 层）第 1 层画 5 颗钉点（4 boss + 1 稀有「矿工约翰森」，2026-10-04 图钉扩展）",\n'
    '         _fr2.bar.__shown == true and _pins(_fr2) == 5, _pins(_fr2))',
    'ck("★★ 多层有坐标副本（死亡矿井 2 层）第 1 层画 4 颗钉点（4 boss；稀有「矿工约翰森」已并入 BossPos 不再重复，2026-10-04）",\n'
    '         _fr2.bar.__shown == true and _pins(_fr2) == 4, _pins(_fr2))',
    'dm floor1')

# ③ 切回第 1 层 5 → 4
s = rep1(s,
    'ck("★★ 切回第 1 层 → 钉点原样回来", _pins(_fr2) == 5)',
    'ck("★★ 切回第 1 层 → 钉点原样回来", _pins(_fr2) == 4)',
    'dm back')

# ④ 缺省态 5 → 4
s = rep1(s,
    'ck("★ 缺省态：文案「隐藏图钉」+ 描边未点亮 + 钉点照常 5 颗（2026-10-04 改名：开关从藏 boss 扩成藏全部钉点）",\n'
    '           tostring(_bb.__text) == TF_NS.L["隐藏图钉"] and not _outlineOn(_bb) and _n0 == 5,',
    'ck("★ 缺省态：文案「隐藏图钉」+ 描边未点亮 + 钉点照常 4 颗（2026-10-04：开关藏全部钉点；稀有去重后死矿 1 层 = 4 boss）",\n'
    '           tostring(_bb.__text) == TF_NS.L["隐藏图钉"] and not _outlineOn(_bb) and _n0 == 4,',
    'dm default')

# ⑤ 恢复 5 → 4
s = rep1(s,
    'ck("★★ 再点开关 → 钉点原样回来（5 颗）+ 文案回「隐藏图钉」",\n'
    '           _pins(U.dungeonMapFrame) == 5',
    'ck("★★ 再点开关 → 钉点原样回来（4 颗）+ 文案回「隐藏图钉」",\n'
    '           _pins(U.dungeonMapFrame) == 4',
    'dm restore')

# ⑥ 影牙 floor1：7 → 4（纯 boss；extras 不再落第 1 层）
s = rep1(s,
    'ck("★★ 影牙第 1 层（庭院）只画本层钉点：7 点 = 4 boss（雷希戈尔/影马/斯普林瓦尔/铁匠锤，含草稿物件点）"\n'
    '           .. " + 2 任务物品（乌尔之书等）+ 1 稀有（死亡之誓）—— extras 无层号、只落第 1 层，6 层阿鲁高不串场",\n'
    '           _c1 == 7 and _e1 == "Rethilgore", _c1 .. "/" .. tostring(_e1))',
    'ck("★★ 影牙第 1 层（庭院）只画本层钉点：4 点 = 4 boss（雷希戈尔/影马/斯普林瓦尔/铁匠锤）"\n'
    '           .. " —— extras 不再落第 1 层（乌尔之书在第 6 层、稀有已并入 BossPos，2026-10-04），6 层阿鲁高不串场",\n'
    '           _c1 == 4 and _e1 == "Rethilgore", _c1 .. "/" .. tostring(_e1))',
    'sfk floor1')

# ⑦ 影牙 floor6：3 → 4（3 boss + 乌尔之书物品钉）
s = rep1(s,
    '''        local _c6, _has6 = 0, false
        for _i = 1, _M.MAX_PINS do
          if _fs.pinBtns[_i].__shown then
            _c6 = _c6 + 1
            if _fs.pinBtns[_i].__en == "Archmage Arugal" then _has6 = true end
          end
        end
        ck("★★ 切到第 6 层（阿鲁高的房间）→ 芬鲁斯/狼王南杜斯/大法师阿鲁高 3 点，阿鲁高在列",
           _c6 == 3 and _has6, _c6)''',
    '''        local _c6, _has6, _book6 = 0, false, false
        for _i = 1, _M.MAX_PINS do
          if _fs.pinBtns[_i].__shown then
            _c6 = _c6 + 1
            if _fs.pinBtns[_i].__en == "Archmage Arugal" then _has6 = true end
            if _fs.pinBtns[_i].__kind == "object" and _fs.pinBtns[_i].__p
               and _fs.pinBtns[_i].__p.id == 6895 then _book6 = true end
          end
        end
        ck("★★ 切到第 6 层（阿鲁高的房间）→ 芬鲁斯/狼王南杜斯/大法师阿鲁高 + 乌尔之书（物品钉 6895）4 点，阿鲁高在列",
           _c6 == 4 and _has6 and _book6, _c6)''',
    'sfk floor6')

# ⑧ 静态 ExtraPinsFor：层号判据换新
s = rep1(s,
    """ck('★★ ㊲b ExtraPinsFor：四类按 entrance→quest→object→rare 遍历 + 第 1 层口径 + 扁平结构（kind/left/top/id/name）',
   'function M.ExtraPinsFor(id, floor)' in _mui3_src
   and '{ "entrance", "quest", "object", "rare" }' in _mui3_src
   and 'if floor == nil or floor == 1 then' in _mui3_src
   and 'kind = kind, left = p[1], top = p[2], id = p[3],' in _mui3_src
   and '(kind == "rare") and p[4] or nil' in _mui3_src)""",
    """ck('★★ ㊲b ExtraPinsFor：四类按 entrance→quest→object→rare 遍历 + 每钉层号口径（4/5 位缺省 1）+ 扁平结构',
   'function M.ExtraPinsFor(id, floor)' in _mui3_src
   and '{ "entrance", "quest", "object", "rare" }' in _mui3_src
   and 'local pf = p[(kind == "rare") and 5 or 4] or 1' in _mui3_src
   and 'if floor == nil or pf == floor then' in _mui3_src
   and 'kind = kind, left = p[1], top = p[2], id = p[3],' in _mui3_src
   and '(kind == "rare") and p[4] or nil' in _mui3_src)""",
    'static ExtraPinsFor')

# ⑨ 静态 Data_MapPins：3 副本 + 新 ID 集 + 旧重复 ID 必须不在 + 乌尔之书楼层
s = rep1(s,
    """ck('★★ ㊲b Data_MapPins：6 个副本登记齐全 + 关键 ID 抽查（任务 96395/98423/95250、物品 6895/6283、稀有 6228/3586/3872）',
   all((('["%s"] = {' % k)) in _pins_src for k in
       ('gnomeregan', 'hall_of_thanes', 'ruins_of_lordaeron',
        'shadowfang_keep', 'the_deadmines', 'the_stockade'))
   and all(_pins_src.count(str(_i)) >= 1 for _i in
           (96395, 98423, 95250, 6895, 6283, 6228, 3586, 3872)))""",
    """ck('★★ ㊲b Data_MapPins：3 个副本登记 + 关键 ID 抽查（任务 96395/98423/95250、乌尔之书 6895@第6层）'
   .. ' + 稀有/重复旧 ID 必须已清（6283/6228/3586/3872，2026-10-04 并入 BossPos）',
   all((('["%s"] = {' % k)) in _pins_src for k in
       ('hall_of_thanes', 'ruins_of_lordaeron', 'shadowfang_keep'))
   and all(_pins_src.count(str(_i)) >= 1 for _i in (96395, 98423, 95250, 6895))
   and all(_pins_src.count(str(_i)) == 0 for _i in (6283, 6228, 3586, 3872))
   and '{ 47.2, 79.3, 6895, 6 }' in _pins_src)""",
    'static pins data')

wr(P, s)
print('9 处断言已换新口径')
