# -*- coding: utf-8 -*-
"""变异锚点：新增「升级路线行第二根等级竖线丢失」（2026-10-09 十一轮）。

本轮产品侧把「一根当前档位竖线」换成「两根本行技能区间竖线」。原有的
MUT_PROF_LV_TBL_SRC_SAMEY（色阶条塌到名字行）仍然有效并能独立抓到回归，
但**「第二根线丢了」这件事本身**没有专属变异守 —— 补一条。

★ df_mut_check.py 是权威变异源（mk_df_mut.py 是被冻结的上游生成器，
  且 check_mut_anchors / df_check_new_muts / _skillbar_mut_verify 都 import 它）。
★ 锚点必须**纯 ASCII**（Python 3 的 b'...' 不许含非 ASCII 字面量）。
★ 幂等靠哨兵串判。

用法：python _temp/patch_mut_dual_pin.py [--check]
"""
import ast
import os
import sys

MUT = '_temp/df_mut_check.py'
PROF = r'D:\workspace\DungeonsForever\Core\ProfessionUI.lua'

SENTINEL = 'MUT_PROF_LV_PIN_DUAL_GONE'

DEF_OLD = (
    "MUT_PROF_LV_TBL_SRC_SAMEY = ('Core/ProfessionUI.lua', (\n"
)
DEF_NEW = (
    "# 十一轮（2026-10-09 用户：「这个竖线我希望显示两根」）：只画一根 / 第二根丢了。\n"
    "#   锚点取 PaintSkillBar 里两行闭包（注释 + lvs 表 + 循环头），全局唯一。\n"
    "#   期望：双 harness 的「两根竖线 = 本行技能区间两端」那条失败。\n"
    "MUT_PROF_LV_PIN_DUAL_GONE = ('Core/ProfessionUI.lua', (\n"
    "    b'    local lvs = { lvLo, lvHi }\\n',\n"
    "    b'    local lvs = { lvLo, nil } -- MUT: second level pin dropped\\n'))\n"
    "\n"
    "MUT_PROF_LV_TBL_SRC_SAMEY = ('Core/ProfessionUI.lua', (\n"
)

REG_OLD = "    ('专业页：色阶条塌到配方名那一行（两行叠一起）', MUT_PROF_LV_TBL_SRC_SAMEY),\n"
REG_NEW = ("    ('专业页：色阶条塌到配方名那一行（两行叠一起）', MUT_PROF_LV_TBL_SRC_SAMEY),\n"
           "    ('专业页：等级竖线只剩一根（第二根丢了）', MUT_PROF_LV_PIN_DUAL_GONE),\n")


def main():
    check = '--check' in sys.argv
    path = MUT
    raw = open(path, 'rb').read()
    src = raw.decode('utf-8')
    if SENTINEL in src:
        print('  [SKIP] %s：已应用' % path)
        return 0

    # 产品源码锚点必须恰好 1 次（否则变异注入会歧义）
    #   ⚠️ 产品文件是纯 CRLF，而变异定义里按惯例写裸 \n（_skillbar_mut_verify.py
    #      会做行尾自愈补成 \r\n）⇒ 前置校验两种换行都要认。
    prof = open(PROF, 'rb').read()
    c = prof.count(b'    local lvs = { lvLo, lvHi }\r\n') + prof.count(b'    local lvs = { lvLo, lvHi }\n')
    print('  [%s] 产品锚点命中 %d 次' % ('OK ' if c == 1 else 'BAD', c))
    if c != 1:
        return 1

    bad = []
    out = src
    for tag, old, new in (('定义', DEF_OLD, DEF_NEW), ('登记', REG_OLD, REG_NEW)):
        n = out.count(old)
        if n != 1:
            bad.append('%s 锚点 %d 次' % (tag, n))
            continue
        out = out.replace(old, new, 1)
    if bad:
        print('  [BAD ] %s' % ' / '.join(bad))
        return 1
    ast.parse(out)
    print('  [OK ] 定义 + 登记 各 1 次，Python 语法自检通过')
    if check:
        print('  [OK ] 预检通过（未落盘）')
        return 0
    open(path, 'wb').write(out.encode('utf-8'))
    assert open(path, 'rb').read() == out.encode('utf-8'), '回读不一致'
    print('  [OK ] 已写入 %s（%d → %d 字节）' % (path, len(raw), len(out.encode('utf-8'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
