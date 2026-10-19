#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""patch_prof_perf9.py
  给第五刀补「记忆表」的守护：断言 + 变异 + 登记。

  ★ 为什么必须有这一条：`PD.ItemName` 的事务内记忆化只有「每次 Render 清空」才是对的。
    不清的后果是**静默的**：第一次打开配方页时物品名还没到货（显示占位），
    这份占位会被记忆表钉死一整局 —— 物品到货后的重扫（PD.SweepNames → PD.Render）
    也刷不回来，页面永远停在「暂时没有客户端数据」。所以钉住
    「Render 开头必须调 PD.ResetItemNameMemo()」，并给一条变异证明它非恒真。

  ★ 三处同步：df_dungeon_check.py（产物）+ mk_df_check.py（生成器）+ df_mut_check.py
    + df_check_new_muts.py（变异登记）。
  ★ 幂等：哨兵命中即整体 SKIP。--check 只预检不落盘。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

T_CHK = os.path.join(HERE, 'df_dungeon_check.py')
T_MK = os.path.join(HERE, 'mk_df_check.py')
T_MUT = os.path.join(HERE, 'df_mut_check.py')
T_WANT = os.path.join(HERE, 'df_check_new_muts.py')

SENTINEL = 'MUT_PROF_NO_NM_RESET'

# ── A 断言（两份 harness 同步）──────────────────────────────────────────────
A_OLD = """    ck('★ 量宽记忆化 + 物品请求按 id 去重（同一材料在几百条配方里重复量宽 / 重复请求）',
       'local _twMemo, _twN = {}, 0' in profui
       and 'if w ~= nil then return w end' in profui
       and 'if not id or seen[id] then return end' in profui)
"""

A_NEW = """    ck('★ 量宽记忆化 + 物品请求按 id 去重（同一材料在几百条配方里重复量宽 / 重复请求）',
       'local _twMemo, _twN = {}, 0' in profui
       and 'if w ~= nil then return w end' in profui
       and 'if not id or seen[id] then return end' in profui)
    # ★★ 2026-10-09 第五轮：实机 79.8ms 剩下的部分全在「引擎调用次数」上 ——
    #   DG.ItemName → GetItemInfo 是**零缓存**引擎调用，一页配方 2228 次里大半是
    #   同一种材料反复查 ⇒ 改成事务内记忆化（Render 开头清空）。
    #   ★ 守护点必须是「**每次渲染清空**」：不清就会把「名字还没到货」那一刻的
    #     占位钉死一整局，物品到货后的重扫也刷不回来（页面永远停在「暂时没有客户端数据」）。
    ck('★★ 物品名记忆表每次渲染清空（不清就会把「名字还没到货」的占位钉死一整局）',
       'local _nmMemo, _nmN = {}, 0' in profui
       and 'function PD.ResetItemNameMemo()' in profui
       and 'function PD.ItemName(id)' in profui
       and 'PD.ResetItemNameMemo()' in _prender)
"""

# ── B 变异定义 ─────────────────────────────────────────────────────────────
B_OLD = """MUT_PROF_NO_REQ_DEDUP = ('Core/ProfessionUI.lua', (
    b'        if not id or seen[id] then return end\\n',
    b'        if not id then return end -- MUT: request dedup gone\\n'))
"""

B_NEW = """MUT_PROF_NO_REQ_DEDUP = ('Core/ProfessionUI.lua', (
    b'        if not id or seen[id] then return end\\n',
    b'        if not id then return end -- MUT: request dedup gone\\n'))

# ★★ 物品名记忆表（2026-10-09 第五轮）：Render 开头不清 = 把「名字还没到货」那一刻的
#   占位钉死一整局（物品到货后的重扫也刷不回来）。静默失效，必须有人守。
MUT_PROF_NO_NM_RESET = ('Core/ProfessionUI.lua', (
    b'    PD.ResetItemNameMemo()\\n',
    b'    -- MUT: item-name memo never reset\\n'))
"""

# ── C 变异登记（MUTATIONS 表）───────────────────────────────────────────────
C_OLD = "    ('专业页：物品请求不再按 id 去重（一页几百条重复请求同一批物品）', MUT_PROF_NO_REQ_DEDUP),\n"
C_NEW = ("    ('专业页：物品请求不再按 id 去重（一页几百条重复请求同一批物品）', MUT_PROF_NO_REQ_DEDUP),\n"
         "    ('专业页：物品名记忆表不清（「名字未到货」的占位被钉死一整局）', MUT_PROF_NO_NM_RESET),\n")

# ── D DEFAULT_WANT 登记 ────────────────────────────────────────────────────
D_OLD = "    '专业页：物品请求不再按 id 去重（一页几百条重复请求同一批物品）',\n"
D_NEW = ("    '专业页：物品请求不再按 id 去重（一页几百条重复请求同一批物品）',\n"
         "    '专业页：物品名记忆表不清（「名字未到货」的占位被钉死一整局）',\n")

JOBS = [
    (T_CHK, 'A1 断言（产物 harness）', A_OLD, A_NEW),
    (T_MK, 'A2 断言（生成器同步）', A_OLD, A_NEW),
    (T_MUT, 'B  变异定义', B_OLD, B_NEW),
    (T_MUT, 'C  变异登记', C_OLD, C_NEW),
    (T_WANT, 'D  DEFAULT_WANT', D_OLD, D_NEW),
]


def to_file_style(text, raw):
    if b'\r\n' in raw:
        return text.replace('\r\n', '\n').replace('\n', '\r\n')
    return text


def main():
    check = '--check' in sys.argv
    bad = 0
    orig, work = {}, {}
    for path in {j[0] for j in JOBS}:
        raw = open(path, 'rb').read()
        orig[path] = raw
        work[path] = raw.decode('utf-8')
    for path, name, old, new in JOBS:
        base = orig[path].decode('utf-8')      # ★ 用**原始**文本判「已应用」，不让同文件
        cur = work[path]                       #   前一条插入污染后一条的判定
        o, n = to_file_style(old, orig[path]), to_file_style(new, orig[path])
        if o in base and n not in base:
            if cur.count(o) != 1:
                print('  [BAD ] %-24s 当前锚点 %d 次' % (name, cur.count(o)))
                bad += 1
                continue
            work[path] = cur.replace(o, n, 1)
            print('  [OK  ] %-24s 锚点 1 次' % name)
        else:
            print('  [SKIP] %-24s 已应用' % name)

    if bad:
        print('  ✗ 有 %d 处未通过，未落盘' % bad)
        return 1
    if check:
        print('  [OK  ] 预检通过（未落盘）')
        return 0
    for path, raw in orig.items():
        src = work[path]
        if src != raw.decode('utf-8'):
            with open(path, 'wb') as f:
                f.write(src.encode('utf-8'))
            print('  [OK  ] 已写入 %s' % os.path.basename(path))
    return 0


if __name__ == '__main__':
    sys.exit(main())
