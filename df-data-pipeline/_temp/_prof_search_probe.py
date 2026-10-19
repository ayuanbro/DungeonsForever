# -*- coding: utf-8 -*-
"""非恒真证明（2026-10-09 第二轮）：配方页搜索 / 首屏性能 这一族的变异逐条隔离注入。

为什么不能直接用 `_mut_isolate.py`：
  它只看「harness 退出码非 0 + 有 FAIL 行」—— 而并行会话在团本页/任务页上有 22 条
  **在途红基线**，任何变异都会「看起来被抓住了」。这里用**基线差值法**：
  先把三个 runner 在干净副本树上的 FAIL 行收成基线集合，注入后只认**新增**的 FAIL 行，
  并且必须命中「指定断言名」。

三个 runner（互补，缺一不可）：
  · df_dungeon_check.py  —— 静态断言（首屏建 spec / 不预算 / 记忆化 / 过滤位置）
  · _prof_search_smoke.py —— 隔离冒烟（搜索框显隐、输入即滤、列宽现算、条数过滤）
  · _prof_search_audit.py —— **内容级**审计（留下的每一行是不是真的命中）
    ★ 只查条数的断言会放过「条数对、行是分类前 N 条」这种错 —— 本轮实锤过。

用法：python _temp/_prof_search_probe.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r'D:\workspace\DungeonsForever'
PY = sys.executable

RUNNERS = ['df_dungeon_check.py', '_prof_search_smoke.py', '_prof_search_audit.py']

# (标签, old, new, [必须新增变红的断言名子串…])
MUTS = [
    # ① 搜索过滤被绕过（本轮修回来的那条回归；同时也是新静态断言的守护）
    ('搜索：列表过滤被绕过（搜索框形同虚设）',
     '        if (not fk) or r[4] == fk then\n'
     '            if PD.RawHit(r, q) then\n'
     '                out[#out + 1] = PD.RecipeSpec(r)\n',
     '        if (not fk) or r[4] == fk then\n'
     '            if true then -- MUT: search filter gone\n'
     '                out[#out + 1] = PD.RecipeSpec(r)\n',
     ['搜索后列表里的每一条都真的命中', '搜索过滤在建 spec 之前']),
    # ② 名称列退回固定分割
    ('搜索：名称列退回固定分割（材料列变窄）',
     '    PD.MAT_X = nameW + PD.RECIPE_NAME_PAD\n',
     '    PD.MAT_X = math.floor(PD.MAT_ROW_W * 0.40)\n',
     ['现算的名称列比旧的固定分割窄']),
    # ③ 切离配方页搜索框不隐藏
    ('搜索：切离配方页搜索框不隐藏',
     '        if PD.tab == "recipe" and not PD.setOpen then\n'
     '            PD.searchBox:ClearAllPoints()',
     '        if false and PD.tab == "recipe" and not PD.setOpen then\n'
     '            PD.searchBox:ClearAllPoints()',
     ['搜索框只在配方页显示']),
    # ④ 输入后不重渲染
    ('搜索：输入后不重渲染（要按回车才滤）',
     '        PD.searchQ = t\n        PD.Render()\n',
     '        PD.searchQ = t\n',
     ['搜索框输入即滤']),
    # ⑤ 首屏退回复建全量 spec（本轮 3 条新断言之一）
    ('专业页：首屏退回复建全量 spec（点开那一帧的卡顿回来了）',
     '        list = PD.RecipeList(math.min(realN, PD.ROW_CAP), PD.searchQ)\n',
     '        list = PD.RecipeList(#(d.rows or {}), PD.searchQ) -- MUT: full list\n',
     ['配方页首屏只为画得出来的行建 spec']),
    # ⑥ spec 又预算材料串与行文案
    ('专业页：spec 又预算材料串与行文案（FitRecipeCols 随后重算一遍 = 纯白做）',
     'function PD.RecipeSpec(r)\n'
     '    local hasVendor = r[14] and r[14].vendors and #r[14].vendors > 0\n',
     'function PD.RecipeSpec(r)\n'
     '    local _m0 = PD.MatCol(r[12], PD.MAT_FS, PD.MAT_W) -- MUT: precomputed\n'
     '    local hasVendor = r[14] and r[14].vendors and #r[14].vendors > 0\n',
     ['spec 不再预算材料串与行 tooltip 文案']),
    # ⑦ 量宽记忆化被摘
    ('专业页：量宽记忆化被摘（同一材料在几百条配方里反复逐字符量宽）',
     '    local w = m[text]\n    if w ~= nil then return w end\n',
     '    local w = nil -- MUT: width memo gone\n',
     ['量宽记忆化 + 物品请求按 id 去重']),
    # ⑧ 物品请求不再按 id 去重
    ('专业页：物品请求不再按 id 去重（一页几百条重复请求同一批物品）',
     '        if not id or seen[id] then return end\n',
     '        if not id then return end -- MUT: request dedup gone\n',
     ['量宽记忆化 + 物品请求按 id 去重']),
]


def run_all(root):
    """返回 (按 runner 分组的输出文本)。"""
    env = dict(os.environ)
    env['DF_ADDON_ROOT'] = root
    out = {}
    for r in RUNNERS:
        p = subprocess.run([PY, os.path.join(HERE, r)], capture_output=True,
                           text=True, encoding='utf-8', errors='replace', env=env)
        out[r] = (p.stdout or '') + (p.stderr or '')
    return out


def fail_lines(outs):
    s = set()
    for txt in outs.values():
        for ln in txt.splitlines():
            if '[FAIL]' in ln:
                s.add(ln.strip())
    return s


def main():
    tmp = tempfile.mkdtemp(prefix='_prof_mut_')
    dst = os.path.join(tmp, 'DungeonsForever')
    print('拷贝隔离树 %s → %s' % (SRC, dst))
    shutil.copytree(SRC, dst, ignore=shutil.ignore_patterns(
        '.git', '.workbuddy', '__pycache__', '_temp', '_fc'))
    try:
        print('跑基线（3 个 runner）…')
        base = fail_lines(run_all(dst))
        print('基线 FAIL 行 %d 条' % len(base))

        p = os.path.join(dst, 'Core', 'ProfessionUI.lua')
        raw = open(p, 'rb').read()
        crlf = raw.count(b'\r\n') > 0
        orig = raw.decode('utf-8')
        if crlf:
            orig = orig.replace('\r\n', '\n')

        all_ok = True
        for label, old, new, want in MUTS:
            n = orig.count(old)
            if n != 1:
                print('✗ %-46s 锚点命中 %d 次' % (label, n))
                all_ok = False
                continue
            mut = orig.replace(old, new, 1)
            if crlf:
                mut = mut.replace('\n', '\r\n')
            open(p, 'wb').write(mut.encode('utf-8'))
            outs = run_all(dst)
            open(p, 'wb').write(raw)

            fresh = fail_lines(outs) - base
            hit = sorted({w for w in want
                          for ln in fresh if w in ln})
            if hit:
                print('✓ %-46s → 被「%s」抓住' % (label, hit[0]))
            else:
                print('✗ %-46s → 新增 FAIL 行 %d 条，但目标断言没红（白测！）'
                      % (label, len(fresh)))
                for ln in sorted(fresh)[:6]:
                    print('      ' + ln)
                all_ok = False
        print('=' * 66)
        print('非恒真证明：%s' % ('全部 %d 条变异都被目标断言抓住' % len(MUTS)
                                  if all_ok else '有漏网，必须修'))
        return 0 if all_ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
