# -*- coding: utf-8 -*-
"""升级路线行：竖线落位改成「起点向下吸 / 终点向上吸」（2026-10-09 十三轮，用户改口）。

用户口径（贴 85–106 / 阈值 55·85·100·115 的截图）：
  「第一根竖线没有问题。
    第二根竖线因为 106 已经大于 100 了，那么第二根竖线就要放在 100 的右边。」
  （追问后定稿）「落在 100 和 115 的交界处，记住 a-b：
    a 如果小于 85 那么 a 在 55 左边；a 大于 85 且小于 100 则落在 55 和 85 交界处。」

⇒ 两根线**分别向两侧吸附到交界**：
  · a（起点 st[1]）**向下吸** —— 吸到**已经跨过**的那道交界（最大的 ≤a 的阈值）。
      36 → 0.25（跨过 30）、85 → 0.25（跨过 85）、<55 → 0.00
  · b（终点 st[2]）**向上吸** —— 吸到**将要到达**的那道交界（最小的 ≥b 的阈值）。
      45 → 0.50（正好压在 45）、106 → 0.75（>100 ⇒ 下一个交界 115）
  ⇒ 两图同时对上：旧图 36–45 ⇒ 0.25 / 0.50；新图 85–106 ⇒ 0.25 / 0.75。

改动（口径版，3 处）：
  ① `PD.SBValPos` 增可选参 `up`：true 走「向上吸」，否则维持原「向下吸」（LvTier）。
     ★ 向下吸那一支保持 `return (t - 1) / 4` 原句不变（旧断言锚点不破）。
  ② `PD.PaintSkillBar` 调用点：第二根（lvHi）传 `up = true`（`k == 2`）+ 注释同步。
  ③ 常量 `PD.SB_EDGE` 与 `PD.Row` 骨架注释的措辞同步（数值不动）。

用法：python _temp/patch_lv_pin_up.py [--check]
"""
import os
import sys

DEV = r'D:\workspace\DungeonsForever'
F = 'Core/ProfessionUI.lua'
P = os.path.join(DEV, *F.split('/'))

raw = open(P, 'rb').read()
# ★ 行尾自适应（本文件在 CRLF / LF 之间被并行会话反复整文件改写）
CRLF = raw.count(b'\r\n') == raw.count(b'\n') and raw.count(b'\r\n') > 0
EOL = '\r\n' if CRLF else '\n'
T = raw.decode('utf-8')
n0 = len(raw)


def _e(s):
    """把片段里的换行归一到本文件当前换行（先折成 \n 再统一）。"""
    return s.replace('\r\n', '\n').replace('\n', EOL)


OLD_CONST = 'PD.SB_EDGE = 4           -- 交界档位：四段等分 ⇒ 竖线只停在 0 / 1/4 / 1/2 / 3/4（见 PD.SBValPos）'
NEW_CONST = 'PD.SB_EDGE = 4           -- 交界点数：四段等分 ⇒ 竖线只停 0 / 1/4 / 1/2 / 3/4（见 PD.SBValPos）'

OLD_FN = (
    '-- 等级 → 条上横坐标比例（0 = 条左缘，1 = 条右缘）；算不出返回 nil。\n'
    '--   口径：四段等分，竖线**吸附到所在色块的左交界** —— 落在第 t 档 ⇒ x = (t-1)/4。\n'
    '--   ⇒ 一眼看出「这个配方现在处于哪个阶段」（用户：36 落 2 号位、45 落 3 号位）。\n'
    '--   例（阈值 1/30/45/60）：36 在第 2 档（黄）⇒ x = 0.25；45 在第 3 档（绿）⇒ x = 0.50。\n'
    '--   ★ 只可能是 0 / 0.25 / 0.50 / 0.75 四选一（吸附，不做段内插值）。\n'
    'function PD.SBValPos(skill, learn, yellow, green, grey)\n'
    '    if not skill or type(learn) ~= "number" then return nil end\n'
    '    local t = PD.LvTier(skill, learn, yellow, green, grey)\n'
    '    if not t then return nil end\n'
    '    return (t - 1) / 4\n'
    'end\n'
)
NEW_FN = (
    '-- 等级 → 条上横坐标比例（0 = 条左缘，1 = 条右缘）；算不出返回 nil。\n'
    '--   口径：四段等分，**阈值 thr[k] 画在第 k 段的左交界 (k-1)/4**（段内数字仍画正中）。\n'
    '--   本行技能区间 a–b 的两根竖线**分别向两侧吸附到交界**：\n'
    '--     · a（起点）**向下吸** —— 吸到**已经跨过**的那道交界（最大的 ≤a 的阈值）。\n'
    '--     · b（终点）**向上吸** —— 吸到**将要到达**的那道交界（最小的 ≥b 的阈值）。\n'
    '--   例①（阈值 1/30/45/60，区间 36–45）：a=36 ⇒ 0.25；b=45 ⇒ 0.50。\n'
    '--   例②（阈值 55/85/100/115，区间 85–106）：a=85 ⇒ 0.25；b=106 ⇒ 0.75（100–115 交界）。\n'
    '--   ★ 两根都只落在 0 / 0.25 / 0.50 / 0.75 四点上（吸附，不做段内插值）。\n'
    '--   up = true 走「向上吸」（终点 b）；否则「向下吸」（起点 a）。\n'
    'function PD.SBValPos(skill, learn, yellow, green, grey, up)\n'
    '    if not skill or type(learn) ~= "number" then return nil end\n'
    '    if up then\n'
    '        local thr = { learn, yellow, green, grey }\n'
    '        for k = 1, 4 do\n'
    '            if type(thr[k]) == "number" and skill <= thr[k] then return (k - 1) / 4 end\n'
    '        end\n'
    '        return 0.75\n'
    '    end\n'
    '    local t = PD.LvTier(skill, learn, yellow, green, grey)\n'
    '    if not t then return nil end\n'
    '    return (t - 1) / 4\n'
    'end\n'
)

OLD_CALL_DOC = (
    '--   dim = 已过段落灰显。两根竖线分别落在 lvLo / lvHi 所在的**色块左交界**\n'
    '--   （吸附，见 PD.SBValPos）—— 只停在 0 / 1/4 / 1/2 / 3/4 四处。\n'
)
NEW_CALL_DOC = (
    '--   dim = 已过段落灰显。两根竖线 = 本行技能区间两端 a–b（见 PD.SBValPos）：\n'
    '--   a 向下吸到已跨过的交界、b 向上吸到将要到达的交界 —— 只停 0 / 1/4 / 1/2 / 3/4。\n'
)

OLD_CALL = (
    '    -- 两根竖线：本行技能区间的两端（左 = lvLo / 右 = lvHi），落位走 PD.SBValPos。\n'
    '    local lvs = { lvLo, lvHi }\n'
    '    for k = 1, 2 do\n'
    '        local p = r.__sbPin[k]\n'
    '        local x = PD.SBValPos(lvs[k], vals[1], vals[2], vals[3], vals[4])\n'
)
NEW_CALL = (
    '    -- 两根竖线：起点 a = lvLo（向下吸）/ 终点 b = lvHi（向上吸），落位走 PD.SBValPos。\n'
    '    local lvs = { lvLo, lvHi }\n'
    '    for k = 1, 2 do\n'
    '        local p = r.__sbPin[k]\n'
    '        local x = PD.SBValPos(lvs[k], vals[1], vals[2], vals[3], vals[4], k == 2)\n'
)

OLD_ROW_NOTE = '    --   落位口径见 PD.SBValPos（吸附到所在色块的**左交界**，只停 0 / 1/4 / 1/2 / 3/4）。'
NEW_ROW_NOTE = '    --   落位口径见 PD.SBValPos（起点向下吸 / 终点向上吸，只停 0 / 1/4 / 1/2 / 3/4）。'

JOBS = [
    ('常量 SB_EDGE 注释', OLD_CONST, NEW_CONST),
    ('SBValPos 函数（加 up 支）', OLD_FN, NEW_FN),
    ('PaintSkillBar 注释', OLD_CALL_DOC, NEW_CALL_DOC),
    ('PaintSkillBar 调用点', OLD_CALL, NEW_CALL),
    ('Row 骨架注释', OLD_ROW_NOTE, NEW_ROW_NOTE),
]

for tag, old, new in JOBS:
    old, new = _e(old), _e(new)
    c = T.count(old)
    if c != 1:
        print('!! 锚点异常 [%s]：命中 %d 次（要求 1）' % (tag, c))
        sys.exit(1)
    T = T.replace(old, new, 1)

out = T.encode('utf-8')
if CRLF:
    assert out.count(b'\r\n') == out.count(b'\n'), '写入后出现裸 LF'
if '--check' in sys.argv:
    print('[OK ] 预检通过（未落盘）：%d → %d 字节（行尾 %s）' % (n0, len(out), 'CRLF' if CRLF else 'LF'))
    sys.exit(0)

# ★ 原子写：写完立刻回读自检
open(P, 'wb').write(out)
chk = open(P, 'rb').read().decode('utf-8')
need = ['PD.SB_EDGE = 4', _e('    return (t - 1) / 4\r\n'),
        'function PD.SBValPos(skill, learn, yellow, green, grey, up)',
        'if type(thr[k]) == "number" and skill <= thr[k] then return (k - 1) / 4 end',
        'PD.SBValPos(lvs[k], vals[1], vals[2], vals[3], vals[4], k == 2)']
gone = ['吸附到所在色块的**左交界**']
bad = [x for x in need if x not in chk]
still = [x for x in gone if x in chk]
print('OK 写入 %s：%d → %d 字节（%+d）' % (F, n0, len(out), len(out) - n0))
print('回读：缺失 %s / 旧句残留 %s' % (bad or '无', still or '无'))
if bad or still:
    sys.exit(1)
print('CRLF %d / 裸 LF %d' % (chk.count('\r\n'), chk.count('\n') - chk.count('\r\n')))
