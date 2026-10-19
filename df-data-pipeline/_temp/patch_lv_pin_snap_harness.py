# -*- coding: utf-8 -*-
"""双 harness：竖线口径由「段心插值」改成「吸附到色块左交界」（2026-10-09 十二轮）。

产品侧改动见 `patch_lv_pin_snap.py`：PD.SBValPos 由段内线性插值改成吸附
（第 t 档 ⇒ (t-1)/4），`PD.SB_VAL` 退役为 `PD.SB_EDGE`。

本补丁把两份 harness 里描述旧口径的断言同步过来。

用法：python _temp/patch_lv_pin_snap_harness.py [--check]
"""
import ast
import sys

DF = '_temp/df_dungeon_check.py'
MK = '_temp/mk_df_check.py'

# ── df：整块（注释 + ck）替换 ────────────────────────────────────────────────
DF_OLD = (
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
)

DF_NEW = (
    "    # ★★ 十一轮（2026-10-09）：两根竖线 = **本行技能区间两端**（左 = st[1] / 右 = st[2]）。\n"
    "    # ★★ 十二轮（2026-10-09 用户）：「如果是 36-45 那么第一根落在 2 号位，第二根落在\n"
    "    #   3 号位，这样能清楚的看到我这个配方处于哪个阶段 / 也就是说竖线落在交界处。」\n"
    "    #   → 落位口径 PD.SBValPos 由「段心 + 段内插值」改成**吸附到所在色块左交界**：\n"
    "    #     落在第 t 档 ⇒ x = (t-1)/4 ⇒ 只可能停在 0 / 0.25 / 0.50 / 0.75 四处。\n"
    "    #     例（阈值 1/30/45/60）：36 在第 2 档 ⇒ 0.25（2 号位）；45 在第 3 档 ⇒ 0.50（3 号位）。\n"
    "    #   连带退役：段内插值用的 PD.SB_VAL → 说明性常量 PD.SB_EDGE。\n"
    "    ck('★★ 色阶条四档等分 + 两根竖线吸附到所在色块左交界（36→2号位 / 45→3号位）',\n"
    "       'PD.SB_COL = {' in profui\n"
    "       and 'PD.SB_DY = -8' in profui\n"
    "       and 'PD.SB_EDGE = 4' in profui\n"
    "       and 'PD.SB_VAL' not in profui\n"
    "       and '    local seg = PD.LV_NAME_W / 4' in profui\n"
    "       and 'if grey and skill >= grey then return 4 end' in profui\n"
    "       and 'if yellow and skill >= yellow then return 2 end' in profui\n"
    "       and '    return (t - 1) / 4\\n' in profui\n"
    "       and 'local span = (type(hi)' not in profui\n"
    "       and '    local lvs = { lvLo, lvHi }' in profui\n"
    "       and 'p:SetPoint(\"CENTER\", r, \"LEFT\", PD.LV_NAME_X + x * PD.LV_NAME_W, PD.SB_DY)' in profui\n"
    "       and 'for k = 1, 2 do r.__sbPin[k]:Hide() end' in profui)\n"
)

# ── mk：两处小改 ─────────────────────────────────────────────────────────────
MK_REPS = [
    ("       and 'PD.SB_VAL = 11' in profui)\n",
     "       and 'PD.SB_EDGE = 4' in profui\n"
     "       and '    return (t - 1) / 4\\n' in profui\n"
     "       and 'PD.SB_VAL' not in profui)\n"),
    ("    # ★★ 十一轮：两根竖线 = 本行技能区间两端（左 = st[1] / 右 = st[2]）。\n",
     "    # ★★ 十一轮：两根竖线 = 本行技能区间两端（左 = st[1] / 右 = st[2]）。\n"
     "    # ★★ 十二轮（用户）：「竖线落在交界处」→ 吸附到所在色块左交界，\n"
     "    #   只停 0 / 0.25 / 0.50 / 0.75 四处（36 → 2 号位 = 0.25、45 → 3 号位 = 0.50）。\n"),
]


def main():
    check = '--check' in sys.argv
    plans = {}
    bad = 0

    # DF：整块替换
    raw = open(DF, 'rb').read()
    src = raw.decode('utf-8')
    if 'PD.SB_EDGE = 4' in src and 'PD.SB_VAL' not in src:
        print('  [SKIP] df_dungeon_check.py：已应用')
    else:
        c = src.count(DF_OLD)
        if c != 1:
            print('  [BAD ] df_dungeon_check.py：旧块锚点 %d 次' % c)
            bad += 1
        else:
            src = src.replace(DF_OLD, DF_NEW, 1)
            bad_df = 0
            for _ in ():  # 占位，保持结构清晰
                pass
            plans[DF] = (raw, src)

    # MK：两处替换
    raw = open(MK, 'rb').read()
    src = raw.decode('utf-8')
    if 'PD.SB_EDGE = 4' in src and 'PD.SB_VAL' not in src:
        print('  [SKIP] mk_df_check.py：已应用')
    else:
        ok = True
        for old, new in MK_REPS:
            c = src.count(old)
            if c != 1:
                print('  [BAD ] mk_df_check.py：锚点 %d 次 %r' % (c, old[:70]))
                ok = False
                bad += 1
                continue
            src = src.replace(old, new, 1)
        if ok:
            plans[MK] = (raw, src)

    for p in plans:
        ast.parse(plans[p][1])
    if bad:
        print('✗ %d 处未通过，未落盘' % bad)
        return 1
    if check:
        print('[OK ] 预检通过（未落盘）：%d 个文件待写' % len(plans))
        return 0
    for p, (raw, src) in plans.items():
        out = src.encode('utf-8')
        assert src.count('\r\n') == 0, '%s 应是纯 LF' % p
        open(p, 'wb').write(out)
        assert open(p, 'rb').read() == out, '回读不一致 %s' % p
        print('  [OK ] 已写入 %s（%d → %d 字节）' % (p, len(raw), len(out)))
    print('[OK ] 双 harness 语法自检通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
