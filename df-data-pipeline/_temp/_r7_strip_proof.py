# -*- coding: utf-8 -*-
"""第三生成器 strip 收口「外溢证明」（第七轮 ③）。

做法：从三个生成器源码里 AST 抽出真实 `_strip_comments_after_gen` 函数体，
在「strip_text 恒等（不落盘）」的干跑环境下执行，捕获它 **实际会 walk 的文件集**。
对每个生成器打印：
  - NEW（收口后）实际处理集（相对路径）
  - OLD（收口前）等价集 —— 三者旧代码都 `walk([DF/Core])`
  - 高危文件（并行手写件 / 跨生成器产物）成员关系：OLD=YES 且 NEW=NO 才算「已封闭外溢」

输出：_temp/_r7_strip_proof.txt
"""
import ast
import io
import os
import sys

DF = r'D:\workspace\DungeonsForever'
TEMP = os.path.join(DF, '_temp')
sys.path.insert(0, TEMP)
import strip_comments as S  # noqa: E402

REAL_WALK = S.walk


def rel(p):
    return os.path.relpath(p, DF).replace('\\', '/')


def load_strip_source(src_path):
    src = io.open(src_path, encoding='utf-8').read()
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == '_strip_comments_after_gen':
            return ast.get_source_segment(src, node)
    raise SystemExit('找不到 _strip_comments_after_gen：%s' % src_path)


def dry_run(label, src_path, extra_globals):
    """在恒等 strip_text 下执行真实函数体，返回它实际被喂入的文件集（相对路径）。"""
    fn_src = load_strip_source(src_path)
    seen = []

    def spy_walk(paths):
        resolved = list(REAL_WALK(paths))
        for f in resolved:
            seen.append(rel(f))
        for f in resolved:
            yield f

    saved_walk = S.walk
    saved_strip = S.strip_text
    S.walk = spy_walk
    S.strip_text = lambda t: (t, 0, 0)          # 恒等 → 绝不落盘
    try:
        ns = dict(extra_globals)
        ns['__name__'] = 'strip_proof'          # 阻断被测模块的 __main__ 分支
        ns['__file__'] = src_path               # 函数体用 __file__ 定位 _here
        exec(compile(fn_src, src_path, 'exec'), ns)
        ns['_strip_comments_after_gen']()
    finally:
        S.walk = saved_walk
        S.strip_text = saved_strip
    return sorted(set(seen))


def main():
    gen_fc = os.path.join(TEMP, 'fc_gen.py')
    gen_enus = os.path.join(TEMP, 'gen_enus_data.py')
    gen_loc = os.path.join(TEMP, 'gen_locales.py')

    # OLD 等价集：三者旧实现都 walk([DF/Core])
    old_core = sorted(rel(p) for p in REAL_WALK([os.path.join(DF, 'Core')]))

    cases = [
        ('fc_gen.py', gen_fc, {'OUT': os.path.join(DF, 'Core', 'Data')}),
        ('gen_enus_data.py', gen_enus, {'DST_DIR': os.path.join(DF, 'Core', 'Data', 'enUS')}),
        ('gen_locales.py', gen_loc, {'DST': os.path.join(DF, 'Locales', 'zhCN.lua')}),
    ]

    # 高危文件：并行手写件 + 跨生成器产物（不应被任何生成器 strip 扫到）
    risky = [
        'Core/LootFilterUI.lua', 'Core/MainFrame.lua', 'Core/Core.lua',
        'Core/LootFilter.lua', 'Core/TierUI.lua', 'Core/BisUI.lua',
        'Core/Bridge.lua', 'Core/DungeonUI.lua', 'Core/ExploreUI.lua',
        'Core/Hui.lua', 'Core/ProfessionUI.lua', 'Core/RaidUI.lua',
        'Core/Data/Data_LootFilter.lua', 'Core/Data/Data_ClassGuide.lua',
        'Core/Data/zhTW/Data_LootFilter.lua', 'Core/Data/zhTW/Data_ClassGuide.lua',
        'Core/Data/enUS/Data_ClassGuide.lua',
        'Locales/enUS.lua', 'Locales/zhTW.lua',
    ]

    lines = []
    w = lines.append
    w('=' * 78)
    w('第三生成器 strip 收口 · 外溢证明（第七轮 ③）')
    w('=' * 78)
    w('')
    w('★ 语义：从源码 AST 抽出真实 _strip_comments_after_gen 函数体，在 strip_text 恒等')
    w('  （绝不落盘）下执行，捕获它实际 walk 的文件集。')
    w('')
    w('OLD（收口前）等价集 = walk([Core])，共 %d 个 .lua：' % len(old_core))
    for f in old_core:
        w('    OLD  %s' % f)
    w('')

    results = {}
    for label, src, extra in cases:
        new = dry_run(label, src, extra)
        results[label] = new
        w('-' * 78)
        w('【%s】收口后实际处理 %d 个文件：' % (label, len(new)))
        for f in new:
            w('    NEW  %s' % f)
        w('')

    w('=' * 78)
    w('高危文件成员关系（OLD=收口前会被扫 → 外溢；NEW=收口后是否仍被扫）')
    w('=' * 78)
    header = '%-42s | %-3s | %s' % ('文件', 'OLD', 'NEW(各生成器)')
    w(header)
    w('-' * len(header))
    overflow_before = 0
    overflow_after = 0
    for rf in risky:
        in_old = rf in old_core
        news = [lbl.replace('.py', '') for lbl in results if rf in results[lbl]]
        if in_old:
            overflow_before += 1
        if news:
            overflow_after += 1
        w('%-42s | %-3s | %s' % (rf, 'YES' if in_old else ' - ',
                                 ('、'.join(news) if news else '（无）')))
    w('-' * len(header))
    w('')
    w('★ 高危文件：收口前会被 OLD 扫到 %d 个；收口后仍被任一生成器扫到 %d 个。'
      % (overflow_before, overflow_after))
    w('★ 判定：%s' % ('PASS（外溢已封闭）' if overflow_after == 0 else 'FAIL（仍有外溢）'))
    w('')
    w('★ 附：三个生成器收口后各自只碰自身产物 ——')
    w('  fc_gen.py         → %s' % ', '.join(results['fc_gen.py']))
    w('  gen_enus_data.py  → enUS 数据副本 %d 个（已排除 enUS/Data_ClassGuide.lua：%s）'
      % (len(results['gen_enus_data.py']),
         'PASS' if 'Core/Data/enUS/Data_ClassGuide.lua' not in results['gen_enus_data.py'] else 'FAIL'))
    w('  gen_locales.py    → %s' % ', '.join(results['gen_locales.py']))

    out = '\n'.join(lines) + '\n'
    io.open(os.path.join(TEMP, '_r7_strip_proof.txt'), 'w', encoding='utf-8', newline='\n').write(out)
    print(out)


if __name__ == '__main__':
    main()
