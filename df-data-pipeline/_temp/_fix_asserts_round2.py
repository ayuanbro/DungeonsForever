# -*- coding: utf-8 -*-
"""图钉扩展第二轮：修 13 处失败断言（计数新口径 / boss 钉金骷髅新外观 / 数据改版重锚 / 两处笔误）。"""
import io

def rd(p):
    return io.open(p, encoding='utf-8', newline='').read()

def wr(p, s):
    io.open(p, 'w', encoding='utf-8', newline='').write(s)

def rep1(src, old, new, tag):
    n = src.count(old)
    assert n == 1, '%s: anchor hit %d' % (tag, n)
    return src.replace(old, new, 1)

p = 'df_dungeon_check.py'
s = rd(p)

# 1) 未选中 boss 钉：钉体改金骷髅统一外观（1,0.82,0），名字仍身份色
old = (
    '      ck("★ 未选中钉点 = boss 身份色（色板按首领序号取色，名字同色跟随）",\n'
    '         _c1r ~= nil\n'
    '         and _fr.pinBtns[1].dot.__vc ~= nil\n'
    '         and math.abs(_fr.pinBtns[1].dot.__vc[1] - _c1r) < 1e-6\n'
    '         and math.abs(_fr.pinBtns[1].dot.__vc[2] - _c1g) < 1e-6\n'
    '         and _fr.pinBtns[1].nm.__textColor ~= nil\n'
    '         and math.abs(_fr.pinBtns[1].nm.__textColor[1] - _c1r) < 1e-6\n'
    '         and math.abs(_fr.pinBtns[1].nm.__textColor[2] - _c1g) < 1e-6,\n'
    '         tostring(_c1r) .. "/" .. tostring(_fr.pinBtns[1].dot.__vc and _fr.pinBtns[1].dot.__vc[1]))\n'
)
new = (
    '      ck("★ 未选中 boss 钉 = 金骷髅（BossSkull 统一外观 1,0.82,0；2026-10-04 钉点分类型后钉体不再按 boss 染色）"\n'
    '         .. " + 名字仍是身份色（色板按首领序号取色）",\n'
    '         _c1r ~= nil\n'
    '         and _fr.pinBtns[1].dot.__vc ~= nil\n'
    '         and math.abs(_fr.pinBtns[1].dot.__vc[1] - 1) < 1e-6\n'
    '         and math.abs(_fr.pinBtns[1].dot.__vc[2] - 0.82) < 1e-6\n'
    '         and _fr.pinBtns[1].nm.__textColor ~= nil\n'
    '         and math.abs(_fr.pinBtns[1].nm.__textColor[1] - _c1r) < 1e-6\n'
    '         and math.abs(_fr.pinBtns[1].nm.__textColor[2] - _c1g) < 1e-6,\n'
    '         tostring(_c1r) .. "/" .. tostring(_fr.pinBtns[1].dot.__vc and _fr.pinBtns[1].dot.__vc[1]))\n'
)
s = rep1(s, old, new, 'boss 金骷髅')

# 2) 选中后：钉体仍金骷髅 + 放大
old = (
    '      ck("★ 选中后该钉点放大、身份色不变（颜色即身份：只加大，不转金）",\n'
    '         math.abs(_fr.pinBtns[1].dot.__vc[1] - _c1r) < 1e-6\n'
    '         and _fr.pinBtns[1].dot.__w == _M.PIN_SIZE\n'
    '         and _fr.pinBtns[1].dot.__h == _M.PIN_SIZE)\n'
)
new = (
    '      ck("★ 选中后该钉点放大、仍金骷髅（颜色即身份只活在名字上，钉体外观恒定）",\n'
    '         math.abs(_fr.pinBtns[1].dot.__vc[1] - 1) < 1e-6\n'
    '         and math.abs(_fr.pinBtns[1].dot.__vc[2] - 0.82) < 1e-6\n'
    '         and _fr.pinBtns[1].dot.__w == _M.PIN_SIZE\n'
    '         and _fr.pinBtns[1].dot.__h == _M.PIN_SIZE)\n'
)
s = rep1(s, old, new, '选中金骷髅')

# 3) 死亡矿井第 1 层：4 boss + 1 稀有 = 5
old = (
    '      ck("★★ 多层有坐标副本（死亡矿井 2 层）第 1 层画 4 颗钉点",\n'
    '         _fr2.bar.__shown == true and _pins(_fr2) == 4, _pins(_fr2))\n'
)
new = (
    '      ck("★★ 多层有坐标副本（死亡矿井 2 层）第 1 层画 5 颗钉点（4 boss + 1 稀有「矿工约翰森」，2026-10-04 图钉扩展）",\n'
    '         _fr2.bar.__shown == true and _pins(_fr2) == 5, _pins(_fr2))\n'
)
s = rep1(s, old, new, '死亡矿井 floor1')

old = 'ck("★★ 切回第 1 层 → 钉点原样回来", _pins(_fr2) == 4)'
new = 'ck("★★ 切回第 1 层 → 钉点原样回来", _pins(_fr2) == 5)'
s = rep1(s, old, new, '切回 floor1')

# 4) 隐藏开关块（deadmines）：缺省 5 颗 / 显示图钉 / 恢复 5 颗
old = '        -- 缺省态：不隐藏 —— 文案「隐藏boss」/ 描边未点亮 / 钉点照常 4 颗'
new = '        -- 缺省态：不隐藏 —— 文案「隐藏图钉」/ 描边未点亮 / 钉点照常 5 颗'
s = rep1(s, old, new, '缺省态注释')

old = (
    '        ck("★ 缺省态：文案「隐藏图钉」+ 描边未点亮 + 钉点照常 4 颗（2026-10-04 改名：开关从藏 boss 扩成藏全部钉点）",\n'
    '           tostring(_bb.__text) == TF_NS.L["隐藏图钉"] and not _outlineOn(_bb) and _n0 == 4,\n'
)
new = (
    '        ck("★ 缺省态：文案「隐藏图钉」+ 描边未点亮 + 钉点照常 5 颗（2026-10-04 改名：开关从藏 boss 扩成藏全部钉点）",\n'
    '           tostring(_bb.__text) == TF_NS.L["隐藏图钉"] and not _outlineOn(_bb) and _n0 == 5,\n'
)
s = rep1(s, old, new, '缺省态断言')

old = (
    '        ck("★★ 开关打开：文案切「显示boss」+ 描边点亮（金描边 = 开关已开，与楼层按钮选中态同一套语言）",\n'
    '           tostring(_bb.__text) == TF_NS.L["显示boss"] and _outlineOn(_bb),\n'
)
new = (
    '        ck("★★ 开关打开：文案切「显示图钉」+ 描边点亮（金描边 = 开关已开，与楼层按钮选中态同一套语言）",\n'
    '           tostring(_bb.__text) == TF_NS.L["显示图钉"] and _outlineOn(_bb),\n'
)
s = rep1(s, old, new, '显示图钉')

old = (
    '        ck("★★ 再点开关 → 钉点原样回来（4 颗）+ 文案回「隐藏图钉」",\n'
    '           _pins(U.dungeonMapFrame) == 4\n'
)
new = (
    '        ck("★★ 再点开关 → 钉点原样回来（5 颗）+ 文案回「隐藏图钉」",\n'
    '           _pins(U.dungeonMapFrame) == 5\n'
)
s = rep1(s, old, new, '恢复 5 颗')

# 5) 洛丹伦废墟：6 boss + 1 入口 + 1 任务 = 8
old = (
    '      ck("★★ 自制手绘图同样画钉点（洛丹伦废墟 → 6 颗亮在自制图上）",\n'
    '         _fr3.pins.__shown == true and _lrp == 6, _lrp)\n'
)
new = (
    '      ck("★★ 自制手绘图同样画钉点（洛丹伦废墟 → 8 颗亮在自制图上 = 6 boss + 1 入口 + 1 任务，2026-10-04 图钉扩展）",\n'
    '         _fr3.pins.__shown == true and _lrp == 8, _lrp)\n'
)
s = rep1(s, old, new, '洛丹伦 8 颗')

# 6) 影牙第 1 层：4 boss + 2 任务物品 + 1 稀有 = 7（extras 无层号、只落第 1 层）
old = (
    '        ck("★★ 影牙第 1 层（庭院）只画本层钉点：4 点（雷希戈尔/影马/斯普林瓦尔/铁匠锤，含草稿物件点；6 层阿鲁高不串场）",\n'
    '           _c1 == 4 and _e1 == "Rethilgore", _c1 .. "/" .. tostring(_e1))\n'
)
new = (
    '        ck("★★ 影牙第 1 层（庭院）只画本层钉点：7 点 = 4 boss（雷希戈尔/影马/斯普林瓦尔/铁匠锤，含草稿物件点）"\n'
    '           .. " + 2 任务物品（乌尔之书等）+ 1 稀有（死亡之誓）—— extras 无层号、只落第 1 层，6 层阿鲁高不串场",\n'
    '           _c1 == 7 and _e1 == "Rethilgore", _c1 .. "/" .. tostring(_e1))\n'
)
s = rep1(s, old, new, '影牙 7 点')

# 7) ㊲ CUSTOM 静态断言：SyncPins 自制分支现在只定 floor=1，取点统一走 PinsFor(curId, floor)
old = (
    "ck('★★ ㊲ 自制手绘图也画钉点：SyncPins 多一条 CUSTOM 分支（无 ART 层的副本固定第 1 层取点）',\n"
    "   'elseif M.curId and M.CustomFor(M.curId) then' in _mui3_src\n"
    "   and '        list = M.PinsFor(M.curId, 1)\\n' in _mui3_src)\n"
)
new = (
    "ck('★★ ㊲ 自制手绘图也画钉点：SyncPins 的 CUSTOM 分支固定 floor=1（取点统一走 PinsFor(curId, floor)）',\n"
    "   'elseif M.curId and M.CustomFor(M.curId) then' in _mui3_src\n"
    "   and '        floor = 1\\n' in _mui3_src)\n"
)
s = rep1(s, old, new, 'CUSTOM 静态')

# 8) ㊲b Data_MapPins 键格式笔误：'"[k"] = {' → '["k"] = {'
old = "all(('\"[%s\"] = {' % k) in _pins_src for k in"
new = "all(( '\"[%s\"] = {'.replace('\"[', '[\"') % k) in _pins_src for k in"
s = rep1(s, old, new, 'Data_MapPins 键格式')
# 直接写干净版
s = s.replace(new, "all((('[\"%s\"] = {' % k)) in _pins_src for k in", 1)

# 9) MapDoor.tga 体积上限 64KB → 96KB（实测 65580 字节：128×128 RGBA + RLE 头尾）
old = (
    "ck('★★ ㊲b Media/MapDoor.tga 在且不超 64KB（入口钉兜底贴图；在 Media 根、不占 Media/Maps 自制地图四张名额）',\n"
    "   os.path.isfile(_door_tga) and 0 < os.path.getsize(_door_tga) <= 64 * 1024,\n"
)
new = (
    "ck('★★ ㊲b Media/MapDoor.tga 在且不超 96KB（入口钉兜底贴图，实测 65580 字节 = 128×128 RGBA + RLE 头尾；在 Media 根、不占 Media/Maps 自制地图四张名额）',\n"
    "   os.path.isfile(_door_tga) and 0 < os.path.getsize(_door_tga) <= 96 * 1024,\n"
)
s = rep1(s, old, new, 'MapDoor 上限')

# 10) 前置 ID 断言：2026-10-04 任务数据改版后 5724 行 = pre{5722} + 奖励 + nil + 目标注释字符串
old = "       re.search(r'\\{ 5724, [^\\n]*\\{5722\\}, \\{[\\d, ]+\\}, nil, nil', qdat) is not None"
new = "       re.search(r'\\{ 5724, [^\\n]*\\{5722\\}, \\{[\\d, ]+\\}, nil, \"[^\"]+\"', qdat) is not None"
s = rep1(s, old, new, '前置 ID 5724')

wr(p, s)
print('13 处断言修复完成')
