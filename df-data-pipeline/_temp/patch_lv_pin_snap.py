# -*- coding: utf-8 -*-
"""升级路线行：竖线从「段内插值」改成「吸附到所在色块左交界」（2026-10-09 十二轮）。

用户口径：「如果是 36-45 那么第一根落在 2 号位，第二根落在 3 号位，这样能清楚的
        看到我这个配方处于哪个阶段。也就是说竖线落在交界处。」

改动（口径版）：
  · PD.SBValPos 由「阈值锚段心 + 段内线性插值」（36 → 0.475、45 → 0.625）
    改成 **吸附**：落在第 t 档 ⇒ x = (t - 1) / 4
       - 36 落在第 2 档（黄）⇒ 0.25 = **2 号位**（1 号位 = 0 = 1–30 块的左交界）
       - 45 落在第 3 档（绿）⇒ 0.50 = **3 号位**
    ⇒ 竖线只可能停在 0 / 0.25 / 0.5 / 0.75 四处，一眼看出「这个配方现在处于哪个阶段」。
  · 连带退役：段内插值用的 `PD.SB_VAL`（档内跨度兜底）整个删掉 —— 吸附不再需要。
    替换成一个说明性常量 `PD.SB_EDGE`（= 交界档位数 4，仅作文档用途，别处不再算术）。
  · `PD.PaintSkillBar` 的注释同步（签名与摆位逻辑**一字不动**）。

用法：python _temp/patch_lv_pin_snap.py [--check]
"""
import os
import sys

DEV = r'D:\workspace\DungeonsForever'
F = 'Core/ProfessionUI.lua'
P = os.path.join(DEV, *F.split('/'))

raw = open(P, 'rb').read()
# ★ 行尾自适应：ProfessionUI.lua 在 2026-10-09 被并行会话在 CRLF / LF 之间来回改过
#   （当前是纯 LF，与 AGENTS.md「只有 Hui/DungeonUI 是 CRLF」一致）。
#   本脚本按文件自身换行拼锚点，落盘后行尾与改前一致。
CRLF = raw.count(b'\r\n') == raw.count(b'\n') and raw.count(b'\r\n') > 0
EOL = '\r\n' if CRLF else '\n'
T = raw.decode('utf-8')
n0 = len(raw)


def _e(s):
    """把脚本里写死的 \\r\\n 锚点/fragment 归一到本文件当前换行。"""
    return s.replace('\r\n', EOL)

OLD_VAL = ('PD.SB_VAL = 11           -- 档内跨度兜底（该档到下一档没有数值跨度时用它，见 PD.SBValPos）\r\n')
NEW_VAL = ('PD.SB_EDGE = 4           -- 交界档位：四段等分 ⇒ 竖线只停在 0 / 1/4 / 1/2 / 3/4（见 PD.SBValPos）\r\n')

OLD_FN = (
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
)
NEW_FN = (
    '-- 等级 → 条上横坐标比例（0 = 条左缘，1 = 条右缘）；算不出返回 nil。\r\n'
    '--   口径：四段等分，竖线**吸附到所在色块的左交界** —— 落在第 t 档 ⇒ x = (t-1)/4。\r\n'
    '--   ⇒ 一眼看出「这个配方现在处于哪个阶段」（用户：36 落 2 号位、45 落 3 号位）。\r\n'
    '--   例（阈值 1/30/45/60）：36 在第 2 档（黄）⇒ x = 0.25；45 在第 3 档（绿）⇒ x = 0.50。\r\n'
    '--   ★ 只可能是 0 / 0.25 / 0.50 / 0.75 四选一（吸附，不做段内插值）。\r\n'
    'function PD.SBValPos(skill, learn, yellow, green, grey)\r\n'
    '    if not skill or type(learn) ~= "number" then return nil end\r\n'
    '    local t = PD.LvTier(skill, learn, yellow, green, grey)\r\n'
    '    if not t then return nil end\r\n'
    '    return (t - 1) / 4\r\n'
    'end\r\n'
)

OLD_CALL = ('--   dim = 已过段落灰显。两根竖线分别落在 lvLo / lvHi（PD.SBValPos）。\r\n')
NEW_CALL = ('--   dim = 已过段落灰显。两根竖线分别落在 lvLo / lvHi 所在的**色块左交界**\r\n'
            '--   （吸附，见 PD.SBValPos）—— 只停在 0 / 1/4 / 1/2 / 3/4 四处。\r\n')

for tag, old, new in (('常量', OLD_VAL, NEW_VAL), ('SBValPos 函数', OLD_FN, NEW_FN), ('PaintSkillBar 注释', OLD_CALL, NEW_CALL)):
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
open(P, 'wb').write(out)

chk = open(P, 'rb').read().decode('utf-8')
need = ['PD.SB_EDGE = 4', _e('    return (t - 1) / 4\r\n')]
gone = ['PD.SB_VAL', 'local span = (type(hi)', 'local tv = { learn, yellow, green, grey }']
bad = [x for x in need if x not in chk]
still = [x for x in gone if x in chk]
print('OK 写入 %s：%d → %d 字节（%+d）' % (F, n0, len(out), len(out) - n0))
print('回读：缺失 %s / 旧句残留 %s' % (bad or '无', still or '无'))
if bad or still:
    sys.exit(1)
print('CRLF %d / 裸 LF %d' % (chk.count('\r\n'), chk.count('\n') - chk.count('\r\n')))
