# -*- coding: utf-8 -*-
# 2026-10-04 手工入口钉（怒焰 59.1,16.9 / 哀嚎 41.2,60.6 / 死矿 31.3,22.8）落地后，
# 7 处计数/口径断言跟着换：怒焰 4→5、死矿 floor1 4→5、ExtraPinsFor 抽查加死矿入口。
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

# ① ExtraPinsFor 领主大厅：怒焰不再是 nil，改查「1 条入口钉」
s = rep1(s, '''      ck("★★ 图钉扩展：ExtraPinsFor 领主大厅 3 条（1 入口 + 2 任务；floor=nil 不分层 / floor=1 全出 / floor=2 不出）",
         #(_MM.ExtraPinsFor("hall_of_thanes", nil) or {}) == 3
         and #(_MM.ExtraPinsFor("hall_of_thanes", 1) or {}) == 3
         and _MM.ExtraPinsFor("hall_of_thanes", 2) == nil
         and _MM.ExtraPinsFor("ragefire_chasm", nil) == nil
         and _MM.ExtraPinsFor(nil, nil) == nil)''',
    '''      ck("★★ 图钉扩展：ExtraPinsFor 领主大厅 3 条（1 入口 + 2 任务）/ 怒焰 1 条手工入口 / floor=2 不出 / nil 不炸",
         #(_MM.ExtraPinsFor("hall_of_thanes", nil) or {}) == 3
         and #(_MM.ExtraPinsFor("hall_of_thanes", 1) or {}) == 3
         and _MM.ExtraPinsFor("hall_of_thanes", 2) == nil
         and #(_MM.ExtraPinsFor("ragefire_chasm", nil) or {}) == 1
         and (_MM.ExtraPinsFor("ragefire_chasm", nil) or {})[1].kind == "entrance"
         and _MM.ExtraPinsFor(nil, nil) == nil)''', 'extrapins halls')

# ② 数据抽查：死矿 0 → 1 手工入口
s = rep1(s, '''         and #(_MM.ExtraPinsFor("the_deadmines", nil) or {}) == 0''',
    '''         and #(_MM.ExtraPinsFor("the_deadmines", nil) or {}) == 1
         and (_MM.ExtraPinsFor("the_deadmines", nil) or {})[1].left == 31.3''', 'deadmines 1')

# ③ 怒焰 4 → 5（4 boss + 1 手工入口）
s = rep1(s, '''      ck("★★ 有坐标副本（怒焰裂谷）→ 钉点层显示 / 4 颗亮 / 第 5 颗起隐藏",
         _fr.pins.__shown == true and _pn == 4 and _fr.pinBtns[5].__shown == false, _pn)''',
    '''      ck("★★ 有坐标副本（怒焰裂谷）→ 钉点层显示 / 5 颗亮（4 boss + 1 手工入口）/ 第 6 颗起隐藏",
         _fr.pins.__shown == true and _pn == 5 and _fr.pinBtns[6].__shown == false, _pn)''', 'ragefire 5')

# ④ 死矿 floor1 4 → 5
s = rep1(s, '''      ck("★★ 多层有坐标副本（死亡矿井 2 层）第 1 层画 4 颗钉点（4 boss；稀有「矿工约翰森」已并入 BossPos 不再重复，2026-10-04）",
         _fr2.bar.__shown == true and _pins(_fr2) == 4, _pins(_fr2))''',
    '''      ck("★★ 多层有坐标副本（死亡矿井 2 层）第 1 层画 5 颗钉点（4 boss + 1 手工入口(31.3,22.8)；稀有已并入 BossPos，2026-10-04）",
         _fr2.bar.__shown == true and _pins(_fr2) == 5, _pins(_fr2))''', 'sfk? no deadmines f1')

# ⑤ 切回第 1 层原样回来 4 → 5
s = rep1(s, '''      ck("★★ 切回第 1 层 → 钉点原样回来", _pins(_fr2) == 4)''',
    '''      ck("★★ 切回第 1 层 → 钉点原样回来（4 boss + 1 入口）", _pins(_fr2) == 5)''', 'back f1')

# ⑥ 缺省态 4 → 5
s = rep1(s, '''        ck("★ 缺省态：文案「隐藏图钉」+ 描边未点亮 + 钉点照常 4 颗（2026-10-04：开关藏全部钉点；稀有去重后死矿 1 层 = 4 boss）",
           tostring(_bb.__text) == TF_NS.L["隐藏图钉"] and not _outlineOn(_bb) and _n0 == 4,''',
    '''        ck("★ 缺省态：文案「隐藏图钉」+ 描边未点亮 + 钉点照常 5 颗（死矿 1 层 = 4 boss + 1 手工入口）",
           tostring(_bb.__text) == TF_NS.L["隐藏图钉"] and not _outlineOn(_bb) and _n0 == 5,''', 'default 5')

# ⑦ 恢复 4 → 5
s = rep1(s, '''        ck("★★ 再点开关 → 钉点原样回来（4 颗）+ 文案回「隐藏图钉」",
           _pins(U.dungeonMapFrame) == 4''',
    '''        ck("★★ 再点开关 → 钉点原样回来（5 颗）+ 文案回「隐藏图钉」",
           _pins(U.dungeonMapFrame) == 5''', 'restore 5')

wr(p, s)
print('7 处断言更新完成')
