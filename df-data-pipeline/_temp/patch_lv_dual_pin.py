# -*- coding: utf-8 -*-
"""升级路线行色阶条：一根「当前档位」竖线 → 两根「本行技能区间两端」竖线（2026-10-09 十一轮）。

用户口径：「现在这个竖线，我希望显示两根，显示的位置是左边这个等级的位置。
        例如：第一根显示在 36 的位置；第二根显示在 45 的位置。」
（左边就是行首的「36 – 45」区间，也就是 st[1] / st[2]）

落位口径（PD.SBValPos）——**每档阈值锚在该段正中央**：
  条上四段等分，段 k 的中心 = (k-0.5)/4。阈值 T_k 就画在段 k 的中心，
  两个阈值之间按「该档跨度」线性细分 ⇒ 任何一根等级线都**正好落在它自己那个数字底下**，
  肉眼可核对。示例（阈值 1/30/45/60）：36 → 0.475（落在「30」右、「45」左）；
  45 → 0.625（正好在「45」这个数字底下）。

用法：python _temp/patch_lv_dual_pin.py
"""
import os
import sys

DEV = r'D:\workspace\DungeonsForever'
F = 'Core/ProfessionUI.lua'
P = os.path.join(DEV, *F.split('/'))

raw = open(P, 'rb').read()
CRLF = raw.count(b'\r\n') and raw.count(b'\n') == raw.count(b'\r\n')
assert CRLF, 'ProfessionUI.lua 应为纯 CRLF 文件'
text = raw.decode('utf-8')
n0 = len(raw)


T = text


def sub(tag, old, new, count=1):
    """锚点必须在**当前累积文本** T 里唯一；命中数不对就整批失败（不做半截补丁）。

    ⚠️ 必须读写全局 T（累积），不能对固定的 text 反复 replace ——
       否则每个 sub 都从原始文本出发，只有最后一次替换能留下来（本项目踩过）。
    """
    global T
    c = T.count(old)
    if c != count:
        print('!! 锚点异常 [%s]：命中 %d 次（要求 %d）' % (tag, c, count))
        print('   old = %r' % old[:180])
        sys.exit(1)
    T = T.replace(old, new)

# ── ① Row 骨架：一根 pin → 两根 pin（表）───────────────────────────────────────
sub('Row-pin',
        '    r.__sbPin = r:CreateTexture(nil, "OVERLAY")\r\n'
        '    r.__sbPin:SetWidth(2)\r\n'
        '    r.__sbPin:SetColorTexture(1, 1, 1, 0.9)\r\n'
        '    r.__sbPin:Hide()\r\n',
        '    -- 2026-10-09 十一轮（用户）：「这个竖线，我希望显示两根，显示的位置是\r\n'
        '    --   左边这个等级的位置」→ 两根线分别落在**本行技能区间**的两端\r\n'
        '    --   （左 = st[1] / 右 = st[2]），不再只画「当前档位」那一根。\r\n'
        '    --   落位口径见 PD.SBValPos（每档阈值锚在该段正中央）。\r\n'
        '    r.__sbPin = {}\r\n'
        '    for k = 1, 2 do\r\n'
        '        local p = r:CreateTexture(nil, "OVERLAY")\r\n'
        '        p:SetWidth(2)\r\n'
        '        p:SetColorTexture(1, 1, 1, 0.9)\r\n'
        '        p:Hide()\r\n'
        '        r.__sbPin[k] = p\r\n'
        '    end\r\n')

# ── ② 常量：档内跨度兜底值 ────────────────────────────────────────────────────
sub('SB_VAL',
        'PD.SB_FS = 11            -- 段内数字字号\r\n',
        'PD.SB_FS = 11            -- 段内数字字号\r\n'
        'PD.SB_VAL = 11           -- 档内跨度兜底（该档到下一档没有数值跨度时用它，见 PD.SBValPos）\r\n')

# ── ③ 新增 PD.SBValPos（插在 LvTier 之后、PaintSkillBar 注释之前）──────────────
sub('SBValPos',
        '-- 摆四档色阶条：条宽 = 名字列宽（PD.LV_NAME_W），四段等分，段内写该档阈值。\r\n'
        '--   vals = { learn, yellow, green, grey }；tier = PD.LvTier(...)；dim = 已过段落灰显。\r\n'
        'function PD.PaintSkillBar(r, vals, tier, dim)\r\n',

        '-- 等级 → 条上横坐标比例（0 = 条左缘，1 = 条右缘）；算不出返回 nil。\r\n'
        '--   口径：四段等分，**阈值 T_k 画在段 k 的正中央**（=(k-0.5)/4），\r\n'
        '--   相邻两档之间按该档的数值跨度线性细分 —— 这样任何等级线都正好落在\r\n'
        '--   它自己那个数字底下（例：阈值 1/30/45/60 时，45 → 0.625 = 「45」的正中）。\r\n'
        'function PD.SBValPos(skill, learn, yellow, green, grey)\r\n'
        '    if not skill or type(learn) ~= "number" then return nil end\r\n'
        '    local t = PD.LvTier(skill, learn, yellow, green, grey)\r\n'
        '    if not t then return nil end\r\n'
        '    local tv = { learn, yellow, green, grey }\r\n'
        '    local lo, hi = tv[t], tv[t + 1]\r\n'
        '    if type(lo) ~= "number" then return nil end\r\n'
        '    -- 末档（灰）没有下一档，或用 (learn == yellow) 那种零跨度 ⇒ 走兜底跨度。\r\n'
        '    local span = (type(hi) == "number" and hi > lo) and (hi - lo) or PD.SB_VAL\r\n'
        '    local x = (t - 0.5) / 4 + (skill - lo) / span / 4\r\n'
        '    if x < 0 then x = 0 elseif x > 1 then x = 1 end\r\n'
        '    return x\r\n'
        'end\r\n'
        '\r\n'
        '-- 摆四档色阶条：条宽 = 名字列宽（PD.LV_NAME_W），四段等分，段内写该档阈值。\r\n'
        '--   vals = { learn, yellow, green, grey }；lvLo / lvHi = 本行技能区间两端；\r\n'
        '--   dim = 已过段落灰显。两根竖线分别落在 lvLo / lvHi（PD.SBValPos）。\r\n'
        'function PD.PaintSkillBar(r, vals, lvLo, lvHi, dim)\r\n')

# ── ④ PaintSkillBar 的竖线段：一根 tier → 两根等级线 ───────────────────────────
sub('PaintSkillBar-pin',
        '    if tier then\r\n'
        '        r.__sbPin:ClearAllPoints()\r\n'
        '        r.__sbPin:SetPoint("CENTER", r, "LEFT", PD.LV_NAME_X + (tier - 0.5) * seg, PD.SB_DY)\r\n'
        '        r.__sbPin:SetSize(2, PD.SB_H + 6)\r\n'
        '        r.__sbPin:SetAlpha(dim and 0.35 or 1)\r\n'
        '        r.__sbPin:Show()\r\n'
        '    else\r\n'
        '        r.__sbPin:Hide()\r\n'
        '    end\r\n',

        '    -- 两根竖线：本行技能区间的两端（左 = lvLo / 右 = lvHi），落位走 PD.SBValPos。\r\n'
        '    local lvs = { lvLo, lvHi }\r\n'
        '    for k = 1, 2 do\r\n'
        '        local p = r.__sbPin[k]\r\n'
        '        local x = PD.SBValPos(lvs[k], vals[1], vals[2], vals[3], vals[4])\r\n'
        '        if x then\r\n'
        '            p:ClearAllPoints()\r\n'
        '            p:SetPoint("CENTER", r, "LEFT", PD.LV_NAME_X + x * PD.LV_NAME_W, PD.SB_DY)\r\n'
        '            p:SetSize(2, PD.SB_H + 6)\r\n'
        '            p:SetAlpha(dim and 0.35 or 1)\r\n'
        '            p:Show()\r\n'
        '        else\r\n'
        '            p:Hide()\r\n'
        '        end\r\n'
        '    end\r\n')

# ── ⑤ HideSkillBar：收干净两根 ────────────────────────────────────────────────
sub('HideSkillBar',
        '    r.__sbPin:Hide()\r\n'
        'end\r\n',
        '    for k = 1, 2 do r.__sbPin[k]:Hide() end\r\n'
        'end\r\n')

# ── ⑥ BindRow 调用点 ─────────────────────────────────────────────────────────
sub('BindRow-call',
        '            PD.PaintSkillBar(r, spec.sbVals, spec.sbTier, spec.passed)\r\n',
        '            PD.PaintSkillBar(r, spec.sbVals, spec.sbLo, spec.sbHi, spec.passed)\r\n')

# ── ⑦ spec：本行技能区间两端（st[1] / st[2]）─────────────────────────────────
sub('segLo',
        '            local segHi = tonumber(st[2])\r\n',
        '            local segLo = tonumber(st[1])\r\n'
        '            local segHi = tonumber(st[2])\r\n')

sub('spec-sb-lo-hi',
        '                sbTier = rec and PD.LvTier(curLv, rec[7], rec[8], rec[9], rec[10]) or nil,\r\n',
        '                -- 2026-10-09 十一轮：两根竖线 = 本行技能区间两端（左侧「36 – 45」那两个数）。\r\n'
        '                sbLo = segLo, sbHi = segHi,\r\n')

assert T != text, '没有任何改动？'
out = T.encode('utf-8')
assert out.count(b'\r\n') == out.count(b'\n'), '写入后出现裸 LF'
open(P, 'wb').write(out)
print('OK 写入 %s：%d → %d 字节（%+d）' % (F, n0, len(out), len(out) - n0))

# ── 回读自检 ─────────────────────────────────────────────────────────────────
chk = open(P, 'rb').read().decode('utf-8')
need = [
    'function PD.SBValPos(skill, learn, yellow, green, grey)',
    'function PD.PaintSkillBar(r, vals, lvLo, lvHi, dim)',
    '    r.__sbPin = {}\r\n',
    'PD.SB_VAL = 11',
    '                sbLo = segLo, sbHi = segHi,\r\n',
    'PD.PaintSkillBar(r, spec.sbVals, spec.sbLo, spec.sbHi, spec.passed)',
]
bad = [n for n in need if n not in chk]
gone = ['r.__sbPin:SetPoint', 'r.__sbPin:Hide()', 'spec.sbTier, spec.passed', 'local segHi = tonumber(st[2])\r\n']
still = [g for g in gone if g in chk and g != 'local segHi = tonumber(st[2])\r\n']
print('回读：缺失 %s / 旧句残留 %s' % (bad or '无', still or '无'))
if bad or still:
    sys.exit(1)
print('耗时行数 %d / CRLF %d / 裸 LF %d'
      % (chk.count('\r\n'), chk.count('\r\n'), chk.count('\n') - chk.count('\r\n')))
