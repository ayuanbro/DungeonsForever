# -*- coding: utf-8 -*-
"""升级路线行「两根竖线」—— 双 harness 断言同步（2026-10-09 十一轮）。

背景：本轮产品侧把「一根当前档位竖线」换成「两根本行技能区间竖线」
（新增 PD.SBValPos，PaintSkillBar 签名 tier → lvLo/lvHi）。两份 harness 里
描述旧口径的断言必须同步，否则 harness 会红在描述上（断言过时 = 假红）。

改两处：
  · df_dungeon_check.py —— 把「升级分段行是**两行表格**」那条（并发会话重写后
    退回旧版）换成新口径断言；色阶条 / 卡片部分这版缺，一并补上。
  · mk_df_check.py —— 我上轮加的大 ck 里引用了旧签名 `(r, vals, tier, dim)` /
    `spec.sbTier` / 单根 `r.__sbPin:SetPoint`，逐条换成新口径。

★ 两文件都是纯 LF，profui 已 replace('\r\n','\n') ⇒ 断言里的换行写 '\n'。
★ 插入型 + 替换型混合 ⇒ 幂等靠**哨兵串**判。

用法：python _temp/patch_lv_dual_pin_harness.py [--check]
"""
import sys

DF = '_temp/df_dungeon_check.py'
MK = '_temp/mk_df_check.py'

# ── 新口径断言（放在 df 里，替换那条「两行表格」）─────────────────────────────
NEW_DF_CK = (
    "    # ★★★ 五轮（2026-09-24）→ 十轮（2026-10-09 用户）：「我现在每行还是要显示这个\n"
    "    #   配方的几级变绿、几级变黄」→ 名字下一行（原来源行）改放**四档技能色阶条**\n"
    "    #   （学 / 黄 / 绿 / 灰），来源压成名字右侧的小卡片。\n"
    "    #   ★★★ 十一轮（2026-10-09 用户）：「这个竖线，我希望显示两根，显示的位置是\n"
    "    #   左边这个等级的位置。例如：第一根显示在 36 的位置；第二根显示在 45 的位置。」\n"
    "    #   → 一根「当前档位」线 → **两根本行技能区间线**（左 = st[1] / 右 = st[2]）。\n"
    "    #   ★ 统一左缘不变：配方名行与色阶条都锚 PD.LV_NAME_X。\n"
    "    ck('★★ 升级分段行：名字下一行是四档技能色阶条，来源压成名字右侧卡片（左缘仍 PD.LV_NAME_X）',\n"
    "       '~%s 次制作' in profui\n"
    "       and 'r.a:SetText(spec.rng or \"\")' in profui\n"
    "       and 'r.e:SetText(spec.text or \"\")' in profui\n"
    "       and 'r.c:SetText(spec.cnt or \"\")' in profui\n"
    "       # 来源不再写进 r.b：新写法在位、旧写法必须彻底消失（两套并存 = 改了一半）\n"
    "       and '        r.b:SetText(\"\")' in profui\n"
    "       and 'r.b:SetText(spec.src or \"\")' not in profui\n"
    "       and 'function PD.LvTier(skill, learn, yellow, green, grey)' in profui\n"
    "       and 'function PD.SBValPos(skill, learn, yellow, green, grey)' in profui\n"
    "       and 'function PD.PaintSkillBar(r, vals, lvLo, lvHi, dim)' in profui\n"
    "       and 'function PD.HideSkillBar(r)' in profui\n"
    "       and 'function PD.PaintCard(r, card)' in profui\n"
    "       and 'function PD.CardOf(rec, ri)' in profui\n"
    "       # 两条新通道真的接上了 + 卡片宽度确实进了材料区预算\n"
    "       and 'PD.PaintSkillBar(r, spec.sbVals, spec.sbLo, spec.sbHi, spec.passed)' in profui\n"
    "       and 'PD.PaintCard(r, spec.card)' in profui\n"
    "       and 'PD.LV_CARD_W = math.ceil(cardNeed)' in profui\n"
    "       and '        r.e:SetPoint(\"LEFT\", r, \"LEFT\", PD.LV_NAME_X, PD.TBL_NAME_DY)' in profui\n"
    "       and 'bg:SetPoint(\"LEFT\", r, \"LEFT\", PD.LV_NAME_X + (k - 1) * seg, PD.SB_DY)' in profui)\n"
    "    # ★★ 十一轮：两根竖线 = **本行技能区间两端**（左 = st[1] / 右 = st[2]）。\n"
    "    #   落位口径 PD.SBValPos：四段等分、**阈值锚在该段正中央**（=(k-0.5)/4），\n"
    "    #   相邻两档按该档跨度线性细分 ⇒ 任何等级线正好落在它自己那个数字底下\n"
    "    #   （例：阈值 1/30/45/60 时 36 → 0.475、45 → 0.625 = 「45」的正中）。\n"
    "    ck('★★ 色阶条四档等分 + 两根竖线 = 本行技能区间两端（PD.SBValPos 锚在段心）',\n"
    "       'PD.SB_COL = {' in profui\n"
    "       and 'PD.SB_DY = -8' in profui\n"
    "       and 'PD.SB_VAL = 11' in profui\n"
    "       and '    local seg = PD.LV_NAME_W / 4' in profui\n"
    "       and 'if grey and skill >= grey then return 4 end' in profui\n"
    "       and 'if yellow and skill >= yellow then return 2 end' in profui\n"
    "       and '    local span = (type(hi) == \"number\" and hi > lo) and (hi - lo) or PD.SB_VAL' in profui\n"
    "       and '    local lvs = { lvLo, lvHi }' in profui\n"
    "       and 'p:SetPoint(\"CENTER\", r, \"LEFT\", PD.LV_NAME_X + x * PD.LV_NAME_W, PD.SB_DY)' in profui\n"
    "       and 'for k = 1, 2 do r.__sbPin[k]:Hide() end' in profui)\n"
    "    # ★★ 旧口径必须**彻底退役**（两套并存 = 改了一半，实机看不出哪根生效）。\n"
    "    #   一根线 / 按档心摆 / spec.sbTier 三样都不许再出现在产品源码里。\n"
    "    ck('★★ 旧「一根当前档位竖线」彻底退役（不许与两根新线并存）',\n"
    "       'r.__sbPin:SetPoint' not in profui\n"
    "       and 'r.__sbPin:Hide()' not in profui\n"
    "       and 'r.__sbPin = r:CreateTexture' not in profui\n"
    "       and 'spec.sbTier' not in profui\n"
    "       and 'PaintSkillBar(r, vals, tier, dim)' not in profui)\n"
    "    # ★★ 来源卡片三分色 + 悬停 / 点击两条通道。\n"
    "    ck('★★ 来源卡片三分色（训练师 / 图纸·掉落 / 图纸·商人）+ 悬停 __tipLines / 点击 __act',\n"
    "       'PD.CARD_COL = {' in profui\n"
    "       and 'trainer = { 0.29, 0.33, 0.40 }' in profui\n"
    "       and 'kind = hasDrop and \"drop\" or (hasVendor and \"vendor\" or \"drop\")' in profui\n"
    "       and 'z.__tipLines = card.lines' in profui\n"
    "       and 'z.__act = card.act' in profui\n"
    "       and 'z.__it = card.fid and { card.fid } or nil' in profui)\n"
)

NEW_DF_TAIL = None

# mk 里那条「色阶条四档等分」ck 的收尾行（引用旧单根 pin）
MK_OLD_PIN = ("       and 'if yellow and skill >= yellow then return 2 end' in profui\n"
              "       and '        r.__sbPin:SetPoint(\"CENTER\", r, \"LEFT\", PD.LV_NAME_X + "
              "(tier - 0.5) * seg, PD.SB_DY)\\n' in profui)\n")

MK_NEW_PIN = ("       and 'if yellow and skill >= yellow then return 2 end' in profui\n"
              "       and 'function PD.SBValPos(skill, learn, yellow, green, grey)' in profui\n"
              "       and 'PD.SB_VAL = 11' in profui)\n"
              "    # ★★ 十一轮：两根竖线 = 本行技能区间两端（左 = st[1] / 右 = st[2]）。\n"
              "    ck('★★ 两根竖线 = 本行技能区间两端（用户：36 一根、45 一根）',\n"
              "       '    r.__sbPin = {}\\n' in profui\n"
              "       and '                sbLo = segLo, sbHi = segHi,\\n' in profui\n"
              "       and '    local lvs = { lvLo, lvHi }\\n' in profui\n"
              "       and 'PD.PaintSkillBar(r, spec.sbVals, spec.sbLo, spec.sbHi, spec.passed)' in profui\n"
              "       and 'p:SetPoint(\"CENTER\", r, \"LEFT\", PD.LV_NAME_X + x * PD.LV_NAME_W, "
              "PD.SB_DY)' in profui\n"
              "       and 'r.__sbPin:SetPoint' not in profui\n"
              "       and 'spec.sbTier' not in profui)\n")


def patch_df(src):
    start_mark = "    ck('★★ 升级分段行是**两行表格**"
    i = src.find(start_mark)
    if i < 0:
        if 'PD.SBValPos(skill, learn, yellow, green, grey)' in src:
            return None, 'SKIP 已应用'
        return None, 'BAD 找不到「两行表格」ck，且未应用过'
    j = src.find('in profui)', i)
    if j < 0:
        return None, 'BAD 找不到该 ck 的收尾'
    j += len('in profui)')
    old = src[i:j]
    if 'PD.TBL_SRC_DY' not in old:
        return None, 'BAD 命中的块不像「两行表格」ck'
    return src[:i] + NEW_DF_CK.rstrip('\n') + src[j:], 'OK 替换（%d 字符 → %d 字符）' % (len(old), len(NEW_DF_CK.rstrip('\n')))


def patch_mk(src):
    if 'PD.SBValPos(skill, learn, yellow, green, grey)' in src and '两根竖线 = 本行技能区间两端' in src:
        return None, 'SKIP 已应用'
    bad = []
    reps = [
        ("and 'function PD.PaintSkillBar(r, vals, tier, dim)' in profui",
         "and 'function PD.PaintSkillBar(r, vals, lvLo, lvHi, dim)' in profui"),
        ("and '            PD.PaintSkillBar(r, spec.sbVals, spec.sbTier, spec.passed)\\n' in profui",
         "and '            PD.PaintSkillBar(r, spec.sbVals, spec.sbLo, spec.sbHi, spec.passed)\\n' in profui"),
        (MK_OLD_PIN, MK_NEW_PIN),
    ]
    out = src
    for old, new in reps:
        c = out.count(old)
        if c != 1:
            bad.append('锚点 %d 次：%r' % (c, old[:90]))
            continue
        out = out.replace(old, new, 1)
    if bad:
        return None, 'BAD ' + ' / '.join(bad)
    return out, 'OK 3 处替换'


FILES = [(DF, patch_df), (MK, patch_mk)]


def main():
    check = '--check' in sys.argv
    plans = {}
    bad = 0
    for path, fn in FILES:
        raw = open(path, 'rb').read()
        src = raw.decode('utf-8')
        assert src.count('\r\n') == 0, '%s 应是纯 LF' % path
        new, msg = fn(src)
        print('  [%s] %-26s %s' % ('OK ' if new else ('SKIP' if msg.startswith('SKIP') else 'BAD '),
                                   path.split('/')[-1], msg))
        if new is None:
            if not msg.startswith('SKIP'):
                bad += 1
            continue
        plans[path] = (raw, new)
    if bad:
        print('✗ %d 个文件未通过，未落盘' % bad)
        return 1
    if check:
        print('[OK ] 预检通过（未落盘）')
        return 0
    for path, (raw, new) in plans.items():
        assert new.count('\n') == new.count('\n')
        open(path, 'wb').write(new.encode('utf-8'))
        back = open(path, 'rb').read()
        assert back == new.encode('utf-8'), '回读不一致 %s' % path
        print('  [OK ] 已写入 %s（%d → %d 字节）' % (path, len(raw), len(back)))
    # 语法自检
    import ast
    for path in plans:
        ast.parse(open(path, encoding='utf-8').read())
    print('[OK ] 两份 harness Python 语法自检通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
