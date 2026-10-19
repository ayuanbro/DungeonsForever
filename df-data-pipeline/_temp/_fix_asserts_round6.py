# -*- coding: utf-8 -*-
# boss 钉图标身份色（第三轮口径）：3 处旧「恒定金骷髅」断言换新
import io


def rd(p):
    return io.open(p, encoding='utf-8', newline='').read()


def wr(p, s):
    io.open(p, 'w', encoding='utf-8', newline='').write(s)


def rep1(src, old, new, tag):
    n = src.count(old)
    assert n == 1, '%s: hit %d' % (tag, n)
    return src.replace(old, new, 1)


p = 'df_dungeon_check.py'
s = rd(p)

# 1) 未选中：dot 与名字同色（身份色）
s = rep1(s, """      ck("★ 未选中 boss 钉 = 金骷髅（BossSkull 统一外观 1,0.82,0；2026-10-04 钉点分类型后钉体不再按 boss 染色）"
         .. " + 名字仍是身份色（色板按首领序号取色）",
         _c1r ~= nil
         and _fr.pinBtns[1].dot.__vc ~= nil
         and math.abs(_fr.pinBtns[1].dot.__vc[1] - 1) < 1e-6
         and math.abs(_fr.pinBtns[1].dot.__vc[2] - 0.82) < 1e-6
         and _fr.pinBtns[1].nm.__textColor ~= nil
         and math.abs(_fr.pinBtns[1].nm.__textColor[1] - _c1r) < 1e-6
         and math.abs(_fr.pinBtns[1].nm.__textColor[2] - _c1g) < 1e-6,
         tostring(_c1r) .. "/" .. tostring(_fr.pinBtns[1].dot.__vc and _fr.pinBtns[1].dot.__vc[1]))""",
"""      ck("★ 未选中 boss 钉 = 身份色骷髅（dot 与名字同走 BossColor，2026-10-04 用户定：图标与文字同色）",
         _c1r ~= nil
         and _fr.pinBtns[1].dot.__vc ~= nil
         and _fr.pinBtns[1].nm.__textColor ~= nil
         and math.abs(_fr.pinBtns[1].dot.__vc[1] - _fr.pinBtns[1].nm.__textColor[1]) < 1e-6
         and math.abs(_fr.pinBtns[1].dot.__vc[2] - _fr.pinBtns[1].nm.__textColor[2]) < 1e-6
         and math.abs(_fr.pinBtns[1].nm.__textColor[1] - _c1r) < 1e-6
         and math.abs(_fr.pinBtns[1].nm.__textColor[2] - _c1g) < 1e-6,
         tostring(_c1r) .. "/" .. tostring(_fr.pinBtns[1].dot.__vc and _fr.pinBtns[1].dot.__vc[1]))""", 'unsel')

# 2) 选中：放大 + 颜色仍身份色
s = rep1(s, """      ck("★ 选中后该钉点放大、仍金骷髅（颜色即身份只活在名字上，钉体外观恒定）",
         math.abs(_fr.pinBtns[1].dot.__vc[1] - 1) < 1e-6
         and math.abs(_fr.pinBtns[1].dot.__vc[2] - 0.82) < 1e-6
         and _fr.pinBtns[1].dot.__w == _M.PIN_SIZE
         and _fr.pinBtns[1].dot.__h == _M.PIN_SIZE)""",
"""      ck("★ 选中后该钉点放大、颜色仍是身份色（dot 与名字同色，2026-10-04 用户定）",
         math.abs(_fr.pinBtns[1].dot.__vc[1] - _fr.pinBtns[1].nm.__textColor[1]) < 1e-6
         and math.abs(_fr.pinBtns[1].dot.__vc[2] - _fr.pinBtns[1].nm.__textColor[2]) < 1e-6
         and _fr.pinBtns[1].dot.__w == _M.PIN_SIZE
         and _fr.pinBtns[1].dot.__h == _M.PIN_SIZE)""", 'sel')

# 3) 静态贴图分派：稀有银染已走名字块变量
s = rep1(s, """   and 'bt.dot:SetTexture(DG.ItemIcon(p.id))' in _mui3_src
   and 'bt.dot:SetVertexColor(0.72, 0.76, 0.85)' in _mui3_src)""",
"""   and 'bt.dot:SetTexture(DG.ItemIcon(p.id))' in _mui3_src
   and 'cr, cg, cb = 0.72, 0.76, 0.85' in _mui3_src
   and 'bt.dot:SetVertexColor(cr, cg, cb)' in _mui3_src)""", 'static tex')
wr(p, s)
print('三处断言已换新口径')
