# -*- coding: utf-8 -*-
"""补丁：变异库收尾（2026-10-09 第二轮）。

三件事：
  A. **重锚 MUT_SEARCH_FILTER_GONE**（原锚点 `    local list = PD.SearchFilter(PD.RecipeList())`
     在第二轮改写后只剩「附魔/制造品/声望」分支 —— 主路径已经不走它了，锚点 0 次，
     这条变异**静默失效**）。新锚点落在 PD.RecipeList 主路径的建表循环上：
     把 PD.RawHit 短路成 `if true then` ⇒ 列表退回「分类前 N 条」⇒ 内容级断言变红。
  B. **新增 4 条**：本轮 3 条新断言各自的反向变异 + 搜索改写的性能守护。
  C. **登记**：df_mut_check.py 的 MUTATIONS + df_check_new_muts.py 的 DEFAULT_WANT。

★ 注意：`mk_df_mut.py`（生成器）已经落后于产物（17 条产物独有的变异它不认识），
  重跑它会静默删掉它们 —— 已给它加了安全闸。本补丁直接改产物 `df_mut_check.py`。

用法：
    python _temp/patch_mut_perf2.py --check
    python _temp/patch_mut_perf2.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MUT = os.path.join(HERE, 'df_mut_check.py')
WANT = os.path.join(HERE, 'df_check_new_muts.py')

# ── A. 重锚 MUT_SEARCH_FILTER_GONE ─────────────────────────────────────
A_OLD = """MUT_SEARCH_FILTER_GONE = ('Core/ProfessionUI.lua', (
    b'    local list = PD.SearchFilter(PD.RecipeList())\\n',
    b'    local list = PD.RecipeList()\\n'))
"""
A_NEW = """# ★ 2026-10-09 第二轮重锚：主路径的搜索过滤已挪进 PD.RecipeList（PD.RawHit，建 spec
#   之前），旧的 `    local list = PD.SearchFilter(PD.RecipeList())` 现在只剩「附魔 /
#   制造品 / 声望」那三条小分支 —— 锚点 0 次，这条变异原本已经**静默没人守**了。
#   新锚点必须落在**主路径的建表循环**：把命中判定短路 ⇒ 列表退回「分类前 N 条」，
#   内容级断言（留下的每一行都真的命中）立刻变红。
#   刻意**只改 RecipeList 这一处** —— ScanRecipe 那处的 PD.RawHit 留着，这样红的是
#   「行内容不对」而不是「抬头条数不对」，指向性明确。
MUT_SEARCH_FILTER_GONE = ('Core/ProfessionUI.lua', (
    b'        if (not fk) or r[4] == fk then\\n'
    b'            if PD.RawHit(r, q) then\\n'
    b'                out[#out + 1] = PD.RecipeSpec(r)\\n',
    b'        if (not fk) or r[4] == fk then\\n'
    b'            if true then -- MUT: search filter gone\\n'
    b'                out[#out + 1] = PD.RecipeSpec(r)\\n'))
"""

# ── B. 新增 4 条变异（插在 ㉚ 分帧块之后） ─────────────────────────────
B_OLD = """MUT_SEARCH_NORENDER = ('Core/ProfessionUI.lua', (
    b'        PD.searchQ = t\\n        PD.Render()\\n',
    b'        PD.searchQ = t\\n'))
"""
B_NEW = """MUT_SEARCH_NORENDER = ('Core/ProfessionUI.lua', (
    b'        PD.searchQ = t\\n        PD.Render()\\n',
    b'        PD.searchQ = t\\n'))
# ★★ 2026-10-09 第二轮（用户：「加了进度条也没优化好，点配方那一瞬间有卡顿」）
#    这一轮的三条断言各配一条反向变异；另加一条守卫搜索改写的性能口径。
MUT_PROF_FULL_SPEC_BUILD = ('Core/ProfessionUI.lua', (
    b'        list = PD.RecipeList(math.min(realN, PD.ROW_CAP), PD.searchQ)\\n',
    b'        list = PD.RecipeList(#(d.rows or {}), PD.searchQ) -- MUT: spec for the full list\\n'))
MUT_PROF_SPEC_PREBUILD = ('Core/ProfessionUI.lua', (
    b'function PD.RecipeSpec(r)\\n'
    b'    local hasVendor = r[14] and r[14].vendors and #r[14].vendors > 0\\n',
    b'function PD.RecipeSpec(r)\\n'
    b'    local _m0 = PD.MatCol(r[12], PD.MAT_FS, PD.MAT_W) -- MUT: mats precomputed again\\n'
    b'    local hasVendor = r[14] and r[14].vendors and #r[14].vendors > 0\\n'))
MUT_PROF_NO_TW_MEMO = ('Core/ProfessionUI.lua', (
    b'    local w = m[text]\\n    if w ~= nil then return w end\\n',
    b'    local w = nil -- MUT: width memo gone\\n'))
MUT_PROF_NO_REQ_DEDUP = ('Core/ProfessionUI.lua', (
    b'        if not id or seen[id] then return end\\n',
    b'        if not id then return end -- MUT: request dedup gone\\n'))
"""

# ── B2. 登记（MUTATIONS 列表） ─────────────────────────────────────────
B2_OLD = """    ('专业页：间距行不入队（行池按索引取用留空洞）', MUT_PROFGATE_GAP_NOT_QUEUED),
"""
B2_NEW = """    ('专业页：间距行不入队（行池按索引取用留空洞）', MUT_PROFGATE_GAP_NOT_QUEUED),
    # ㉚b 配方页「点开那一瞬间」的同步重计算（2026-10-09 第二轮，用户报仍卡）
    ('专业页：首屏退回复建全量 spec（点开那一帧的卡顿回来了）', MUT_PROF_FULL_SPEC_BUILD),
    ('专业页：spec 又预算材料串与行文案（FitRecipeCols 随后重算一遍 = 纯白做）',
     MUT_PROF_SPEC_PREBUILD),
    ('专业页：量宽记忆化被摘（同一材料在几百条配方里反复逐字符量宽）', MUT_PROF_NO_TW_MEMO),
    ('专业页：物品请求不再按 id 去重（一页几百条重复请求同一批物品）', MUT_PROF_NO_REQ_DEDUP),
"""

# ── C. 登记（DEFAULT_WANT） ────────────────────────────────────────────
C_OLD = """    '专业页：间距行不入队（行池按索引取用留空洞）',
"""
C_NEW = """    '专业页：间距行不入队（行池按索引取用留空洞）',
    # ㉚b 配方页「点开那一瞬间」的同步重计算（2026-10-09 第二轮，用户报仍卡）
    '专业页：首屏退回复建全量 spec（点开那一帧的卡顿回来了）',
    '专业页：spec 又预算材料串与行文案（FitRecipeCols 随后重算一遍 = 纯白做）',
    '专业页：量宽记忆化被摘（同一材料在几百条配方里反复逐字符量宽）',
    '专业页：物品请求不再按 id 去重（一页几百条重复请求同一批物品）',
"""

JOBS = [
    # (文件, 名字, 锚点, 替换, 哨兵：出现即视为已应用；B/B2/C 是「在锚点后插入」，
    #  替换串里含锚点原文 ⇒ 必须给只在替换串里出现的哨兵)
    (MUT, 'A 重锚 MUT_SEARCH_FILTER_GONE', A_OLD, A_NEW, None),
    (MUT, 'B 新增 4 条变异定义', B_OLD, B_NEW,
     'MUT_PROF_FULL_SPEC_BUILD = ('),
    (MUT, 'B2 变异登记（MUTATIONS）', B2_OLD, B2_NEW,
     '㉚b 配方页「点开那一瞬间」的同步重计算'),
    (WANT, 'C 变异登记（DEFAULT_WANT）', C_OLD, C_NEW,
     '㉚b 配方页「点开那一瞬间」的同步重计算'),
]


def main():
    check = '--check' in sys.argv
    bad = 0
    plans = {}
    for path, name, old, new, marker in JOBS:
        raw = open(path, 'rb').read()
        src = raw.decode('utf-8')
        if path not in plans:
            plans[path] = [raw, src, []]
        cur = plans[path][1]
        if marker:
            if marker in cur:
                print('  [SKIP] %-28s 已应用' % name)
                continue
        elif cur.count(new) == 1 and cur.count(old) == 0:
            print('  [SKIP] %-28s 已应用' % name)
            continue
        if cur.count(old) != 1:
            print('  [BAD ] %-28s 锚点 %d 次' % (name, cur.count(old)))
            bad += 1
            continue
        if not marker and cur.count(new) >= 1:
            print('  [BAD ] %-28s 替换串已存在 %d 次' % (name, cur.count(new)))
            bad += 1
            continue
        plans[path][1] = cur.replace(old, new)
        print('  [OK  ] %-28s 锚点 1 次' % name)
    if bad:
        print('✗ %d 处有问题，未写盘' % bad)
        return 2
    if check:
        print('✓ 预检通过（--check，未写盘）')
        return 0
    for path, (raw, src, _) in plans.items():
        if src.encode('utf-8') == raw:
            print('✓ %s 无需改动' % os.path.basename(path))
            continue
        open(path, 'wb').write(src.encode('utf-8'))
        print('✓ 已写盘 %s：%d → %d 字节'
              % (os.path.basename(path), len(raw), len(src.encode('utf-8'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
