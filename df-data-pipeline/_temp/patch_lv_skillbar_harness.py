# -*- coding: utf-8 -*-
"""重锚「升级分段行」断言（来源行 → 四档色阶条 + 名字右侧来源卡片），并补两条新覆盖。

df_dungeon_check.py（成品）与 mk_df_check.py（生成器）里同一段文本双份同步。
"""
import sys

ROOT = r'D:\workspace\DungeonsForever'

OLD = '''    # ★★★ 五轮（用户 2026-09-24）：「这个配方是向训练师学习，还是通过购买图纸之类的，
    #   是没有展示出来的」→ 分段行从「一行四样」改成**两行表格**：
    #   上行 区间 | [配方图标] 配方名 | ~N 次制作；下行 来源；右侧材料块（图标 + 名 + ×N）。
    #   ★ 配方名与来源**共用同一个左缘**（PD.LV_NAME_X）—— 两行文字不在一个左缘上整行就散了。
    ck('★★ 升级分段行是**两行表格**（上行 配方名 / 下行 来源，两行共用左缘 PD.LV_NAME_X）',
       '~%s 次制作' in profui
       and 'r.a:SetText(spec.rng or "")' in profui
       and 'r.e:SetText(spec.text or "")' in profui
       and 'r.b:SetText(spec.src or "")' in profui
       and 'r.c:SetText(spec.cnt or "")' in profui
       # ⚠️ 这两句要连 8 空格缩进查：通用那一支也有 SetPoint("LEFT"...) 同形句，短串会恒真白测。
       and '        r.e:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X, PD.TBL_NAME_DY)\\n' in profui
       and '        r.b:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X, PD.TBL_SRC_DY)\\n' in profui)
'''

NEW = '''    # ★★★ 五轮（用户 2026-09-24）：「这个配方是向训练师学习，还是通过购买图纸之类的，
    #   是没有展示出来的」→ 分段行从「一行四样」改成**两行表格**。
    #   ★★★ 十轮（用户 2026-10-09）：「专业升级路线页面，我现在每行还是要显示这个配方的
    #   几级变绿、几级变黄」→ 名字下一行（原来源行）改放**四档技能色阶条**
    #   （学 / 黄 / 绿 / 灰 + 当前档落点竖线），来源压成名字右侧的小卡片。
    #   ★ 统一左缘不变：配方名行与色阶条都锚 PD.LV_NAME_X。
    ck('★★ 升级分段行：名字下一行是四档技能色阶条，来源压成名字右侧卡片（左缘仍 PD.LV_NAME_X）',
       '~%s 次制作' in profui
       and 'r.a:SetText(spec.rng or "")' in profui
       and 'r.e:SetText(spec.text or "")' in profui
       and 'r.c:SetText(spec.cnt or "")' in profui
       # 来源不再写进 r.b：新写法在位、旧写法必须彻底消失（两套并存 = 改了一半）
       and '        r.b:SetText("")\\n' in profui
       and 'r.b:SetText(spec.src or "")' not in profui
       and 'function PD.LvTier(skill, learn, yellow, green, grey)' in profui
       and 'function PD.PaintSkillBar(r, vals, tier, dim)' in profui
       and 'function PD.HideSkillBar(r)' in profui
       and 'function PD.PaintCard(r, card)' in profui
       and 'function PD.CardOf(rec, ri)' in profui
       # 两条新通道真的接上了 + 卡片宽度确实进了材料区预算
       and '            PD.PaintSkillBar(r, spec.sbVals, spec.sbTier, spec.passed)\\n' in profui
       and '        PD.PaintCard(r, spec.card)\\n' in profui
       and '    PD.LV_CARD_W = math.ceil(cardNeed)\\n' in profui
       # ⚠️ 这两句要连 8 空格缩进查：通用那一支也有 SetPoint("LEFT"...) 同形句，短串会恒真白测。
       and '        r.e:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X, PD.TBL_NAME_DY)\\n' in profui
       and '        bg:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X + (k - 1) * seg, PD.SB_DY)\\n' in profui)
    # ★★ 十轮：四档**等分**而不是按等级跨度 —— 数据里 learn == yellow 极常见
    #   （如 150/150/162/175），按真实跨度画「必升」那档宽度就是 0，会缺一块。
    ck('★★ 色阶条四档等分（learn == yellow 时「必升」档不许消失）+ 落点竖线',
       'PD.SB_COL = {' in profui
       and 'PD.SB_DY = -8' in profui
       and '    local seg = PD.LV_NAME_W / 4\\n' in profui
       and 'if grey and skill >= grey then return 4 end' in profui
       and 'if yellow and skill >= yellow then return 2 end' in profui
       and '        r.__sbPin:SetPoint("CENTER", r, "LEFT", PD.LV_NAME_X + (tier - 0.5) * seg, PD.SB_DY)\\n' in profui)
    # ★★ 十轮：来源卡片三分色 + 悬停 / 点击两条通道。
    ck('★★ 来源卡片三分色（训练师 / 图纸·掉落 / 图纸·商人）+ 悬停 __tipLines / 点击 __act',
       'PD.CARD_COL = {' in profui
       and 'trainer = { 0.29, 0.33, 0.40 }' in profui
       and 'kind = hasDrop and "drop" or (hasVendor and "vendor" or "drop")' in profui
       and '    z.__tipLines = card.lines\\n' in profui
       and '    z.__act = card.act\\n' in profui
       and '    z.__it = card.fid and { card.fid } or nil\\n' in profui)
'''

for name in ('df_dungeon_check.py', 'mk_df_check.py'):
    p = ROOT + '\\_temp\\' + name
    src = open(p, 'rb').read().decode('utf-8')
    s = src.replace('\r\n', '\n')
    n = s.count(OLD)
    if n != 1:
        print('!! [%s] 锚点命中 %d 次' % (name, n))
        sys.exit(1)
    s = s.replace(OLD, NEW)
    out = s.replace('\n', '\r\n') if src.count('\r\n') else s
    open(p, 'wb').write(out.encode('utf-8'))
    print('OK [%s] 重锚完成（+%d 字节）' % (name, len(out.encode('utf-8')) - len(src.encode('utf-8'))))

print('done')
