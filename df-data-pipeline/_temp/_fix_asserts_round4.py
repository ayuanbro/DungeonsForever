# -*- coding: utf-8 -*-
# 乌尔之书/乔丹铁锤 最终对位轮：书 6283@floor1(37.3,53.8)、锤 6895@floor6(47.2,79.3)、
# BossPos 删乔丹 boss 条目 → 影牙 floor1 = 3 boss + 1 书钉 = 4
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

# ① 动态数据抽查
s = rep1(s,
    '''      ck("★★ 图钉扩展数据抽查：影牙只余乌尔之书（6895，第 6 层；floor1/2 不出）"
         .. " / 监狱 / 死矿 / 侏儒 = 0（稀有钉已并入 ns.BossPos，2026-10-04 去重）/ 洛丹伦废墟 2（1 入口 + 1 任务）",
         #(_MM.ExtraPinsFor("shadowfang_keep", nil) or {}) == 1
         and (_MM.ExtraPinsFor("shadowfang_keep", nil) or {})[1].id == 6895
         and #(_MM.ExtraPinsFor("shadowfang_keep", 6) or {}) == 1
         and #(_MM.ExtraPinsFor("shadowfang_keep", 1) or {}) == 0
         and #(_MM.ExtraPinsFor("shadowfang_keep", 2) or {}) == 0
         and #(_MM.ExtraPinsFor("the_stockade", nil) or {}) == 0
         and #(_MM.ExtraPinsFor("the_deadmines", nil) or {}) == 0
         and #(_MM.ExtraPinsFor("gnomeregan", nil) or {}) == 0
         and #(_MM.ExtraPinsFor("ruins_of_lordaeron", nil) or {}) == 2)''',
    '''      ck("★★ 图钉扩展数据抽查：影牙 2 物品钉 = 乌尔之书 6283@第1层(37.3,53.8) + 乔丹铁锤 6895@第6层(47.2,79.3)"
         .. "（fc slug 与坐标交叉，实机两轮标位核准）/ 监狱 / 死矿 / 侏儒 = 0（稀有已并入 BossPos）/ 洛丹伦 2",
         #(_MM.ExtraPinsFor("shadowfang_keep", nil) or {}) == 2
         and (_MM.ExtraPinsFor("shadowfang_keep", 1) or {})[1].id == 6283
         and (_MM.ExtraPinsFor("shadowfang_keep", 6) or {})[1].id == 6895
         and #(_MM.ExtraPinsFor("shadowfang_keep", 2) or {}) == 0
         and #(_MM.ExtraPinsFor("the_stockade", nil) or {}) == 0
         and #(_MM.ExtraPinsFor("the_deadmines", nil) or {}) == 0
         and #(_MM.ExtraPinsFor("gnomeregan", nil) or {}) == 0
         and #(_MM.ExtraPinsFor("ruins_of_lordaeron", nil) or {}) == 2)''',
    'dyn data')

# ② 影牙 floor1：4 boss → 3 boss + 乌尔之书（数量仍 4，构成变了）
s = rep1(s,
    '''        ck("★★ 影牙第 1 层（庭院）只画本层钉点：4 点 = 4 boss（雷希戈尔/影马/斯普林瓦尔/铁匠锤）"
           .. " —— extras 不再落第 1 层（乌尔之书在第 6 层、稀有已并入 BossPos，2026-10-04），6 层阿鲁高不串场",
           _c1 == 4 and _e1 == "Rethilgore", _c1 .. "/" .. tostring(_e1))''',
    '''        local _book1 = false
        for _i = 1, _M.MAX_PINS do
          if _fs.pinBtns[_i].__shown and _fs.pinBtns[_i].__kind == "object"
             and _fs.pinBtns[_i].__p and _fs.pinBtns[_i].__p.id == 6283 then _book1 = true end
        end
        ck("★★ 影牙第 1 层（庭院）只画本层钉点：4 点 = 3 boss（雷希戈尔/影马/斯普林瓦尔）"
           .. " + 乌尔之书（物品钉 6283@(37.3,53.8)，用户标位）—— 乔丹铁锤非 boss 已从 BossPos 删除（2026-10-04）",
           _c1 == 4 and _e1 == "Rethilgore" and _book1, _c1 .. "/" .. tostring(_e1))''',
    'sfk floor1')

# ③ 影牙 floor6：文字从乌尔之书改为乔丹铁锤（数量/6895 校验不变）
s = rep1(s,
    'ck("★★ 切到第 6 层（阿鲁高的房间）→ 芬鲁斯/狼王南杜斯/大法师阿鲁高 + 乌尔之书（物品钉 6895）4 点，阿鲁高在列",',
    'ck("★★ 切到第 6 层（阿鲁高的房间）→ 芬鲁斯/狼王南杜斯/大法师阿鲁高 + 乔丹铁锤（物品钉 6895，实为该层物件）4 点，阿鲁高在列",',
    'sfk floor6 text')

# ④ 静态 Data_MapPins：ID 集 + 已清列表 + 新行
s = rep1(s,
    """ck('★★ ㊲b Data_MapPins：3 个副本登记 + 关键 ID 抽查（任务 96395/98423/95250、乌尔之书 6895@第6层）'
   ' + 稀有/重复旧 ID 必须已清（6283/6228/3586/3872，2026-10-04 并入 BossPos）',
   all((('["%s"] = {' % k)) in _pins_src for k in
       ('hall_of_thanes', 'ruins_of_lordaeron', 'shadowfang_keep'))
   and all(_pins_src.count(str(_i)) >= 1 for _i in (96395, 98423, 95250, 6895))
   and all(_pins_src.count(str(_i)) == 0 for _i in (6283, 6228, 3586, 3872))
   and '{ 47.2, 79.3, 6895, 6 }' in _pins_src)""",
    """ck('★★ ㊲b Data_MapPins：3 个副本登记 + 关键 ID 抽查（任务 96395/98423/95250、'
   '乌尔之书 6283@第1层、乔丹铁锤 6895@第6层）+ 稀有/假 ID 必须已清（6228/3586/3872）',
   all((('["%s"] = {' % k)) in _pins_src for k in
       ('hall_of_thanes', 'ruins_of_lordaeron', 'shadowfang_keep'))
   and all(_pins_src.count(str(_i)) >= 1 for _i in (96395, 98423, 95250, 6283, 6895))
   and all(_pins_src.count(str(_i)) == 0 for _i in (6228, 3586, 3872))
   and '{ 37.3, 53.8, 6283 }' in _pins_src
   and '{ 47.2, 79.3, 6895, 6 }' in _pins_src)""",
    'static pins data')

wr(P, s)
print('4 处断言已换最终口径')
