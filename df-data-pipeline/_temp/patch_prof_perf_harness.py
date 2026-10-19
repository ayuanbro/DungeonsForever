# -*- coding: utf-8 -*-
"""补丁：harness 断言跟上「配方页点开那一帧」的性能改造（2026-10-09 第二轮）。

三件事：
  1. 两条旧断言钉着「RecipeSpec 里预算材料串」的写法（`PD.MatCol(r[12], …)` /
     `mats = mcol`）—— 那正是本轮删掉的纯白做。改成断言**意图**并加负向条件，
     让「白做复辟」当场变红。
  2. `名称列按本页现算` 的第 3 条子句还写着 `s.mats = PD.MatCol(...)`，而代码已在
     并行的材料热区改造里变成多返回值赋值 ⇒ 改成语义等价的宽口径子句。
  3. 新增 3 条本轮的性能回归断言（只在**画得出来的行**上建 spec / 不预算材料串与
     tooltip 文案 / TextW 记忆化 + 请求去重）。

同时改 `df_dungeon_check.py` 与 `mk_df_check.py`（双份同步，项目规矩）。

用法：
    python _temp/patch_prof_perf_harness.py --check
    python _temp/patch_prof_perf_harness.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = [os.path.join(HERE, 'df_dungeon_check.py'),
         os.path.join(HERE, 'mk_df_check.py')]

# ── 1. `材料列文本按**分块宽度预算**生成` 的第 3 条子句 ────────────────
E1_OLD = """       and 'PD.MatCol(r[12], PD.MAT_FS, PD.MAT_W)' in profui)
"""
E1_NEW = """       and 'PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)' in profui)
"""

# ── 2. `配方行副行只剩部位等级` 的后两条子句 ───────────────────────────
E2_OLD = """       'sub = tostring(r[5] or "")' in profui and 'mats = mcol,\\n' in profui
       and 'local mcol, _, _, msegs = PD.MatCol(r[12], PD.MAT_FS, PD.MAT_W)' in profui)
"""
E2_NEW = """       'sub = tostring(r[5] or "")' in profui
       and 'PD.MatCol(r[12], PD.MAT_FS, PD.MAT_W)' not in profui
       and 'PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)' in profui)
"""

# ── 3. `名称列按本页现算` 的第 3 条子句 ───────────────────────────────
#   ⚠ 代码侧的真实 bug：PD.MatCol 返回 (col, w, n, segs)，segs 是**第 4 个**；
#     `s.mats, sg = PD.MatCol(...)` 会把第 2 个（数字 w）当成 matSegs 传给
#     PD.PaintMatSegs ⇒「attempt to get length of local 'segs' (a number value)」
#     配方页整页崩（2026-10-09 实测）。已修成 `s.mats, _, _, sg = ...`，
#     断言跟着把元数补齐。
E3_OLD = """       and 's.mats, sg = PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)' in profui
"""
E3_NEW = """       and 's.mats, _, _, sg = PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)' in profui
"""

# ── 4. 新增本轮性能回归断言（插在「配方页与升级页各自独立排版」之前） ──
E4_ANCHOR = """    ck('★★ 配方页与升级页各自独立排版（配方页单列居中列 / 升级页整页两栏）',
"""
E4_NEW = """    # ★★ 2026-10-09 第二轮（用户：「加了进度条也没优化好，点配方那一瞬间有卡顿」）：
    #   点开配方页那一帧**不许再对全量建 spec** —— 列表封顶只画 PD.ROW_CAP 条，
    #   「过滤后多少条 + 名称列最宽多少」交给 PD.ScanRecipe 的轻量扫描
    #   （不建 spec / 不拼文案 / 不量材料串）。实测（_temp/_prof_render_prof.py，
    #   leatherworking 511 条）：整帧 28.5ms → 4.7ms，RecipeSpec 511 → 300 次，
    #   TextW 7391 → 300 次（PD.TextW 记忆化），DG.RequestItem 1349 → 392 次（去重）。
    ck('★★ 配方页首屏只为画得出来的行建 spec（不许对全量建 —— 点开那一帧的卡顿就出在这）',
       'function PD.ScanRecipe' in profui
       and 'PD.RecipeList(math.min(realN, PD.ROW_CAP))' in profui
       and 'PD.FitRecipeCols(list, maxW)' in profui)
    ck('★★ spec 不再预算材料串与行 tooltip 文案（FitRecipeCols 会用定稿列宽重算一遍，那里是纯白做）',
       'PD.MatCol(r[12], PD.MAT_FS, PD.MAT_W)' not in profui
       and 'mkLines = function()' in profui
       and 'if self.__lines == nil and self.__mkLines then' in profui
       and 'r.__mkLines = spec.mkLines' in profui)
    ck('★ 量宽记忆化 + 物品请求按 id 去重（同一材料在几百条配方里重复量宽 / 重复请求）',
       'local _twMemo, _twN = {}, 0' in profui
       and 'if not id or seen[id] then return end' in profui)
    ck('★★ 配方页与升级页各自独立排版（配方页单列居中列 / 升级页整页两栏）',
"""

EDITS = [
    ('1 材料列预算生成断言', E1_OLD, E1_NEW),
    ('2 配方行副行断言', E2_OLD, E2_NEW),
    ('3 名称列现算断言', E3_OLD, E3_NEW),
    ('4 新增性能回归断言', E4_ANCHOR, E4_NEW),
]


def main():
    check = '--check' in sys.argv
    bad = 0
    plans = {}
    for path in FILES:
        raw = open(path, 'rb').read()
        src = raw.decode('utf-8')
        out = src
        print('== %s' % os.path.basename(path))
        for name, old, new in EDITS:
            c_old, c_new = out.count(old), out.count(new)
            if c_new == 1 and c_old == 0:
                print('  [SKIP] %-22s 已应用' % name)
                continue
            if c_old != 1:
                print('  [BAD ] %-22s 锚点 %d 次' % (name, c_old))
                bad += 1
                continue
            out = out.replace(old, new)
            print('  [OK  ] %-22s 锚点 1 次' % name)
        plans[path] = (raw, src, out)
    if bad:
        print('✗ %d 处有问题，未写盘' % bad)
        return 2
    if check:
        print('✓ 预检通过（--check，未写盘）')
        return 0
    for path, (raw, src, out) in plans.items():
        if out == src:
            print('  无需改动 %s' % os.path.basename(path))
            continue
        open(path, 'wb').write(out.encode('utf-8'))
        print('✓ 已写盘 %s（%d → %d 字节）' % (os.path.basename(path), len(raw), len(out.encode('utf-8'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
