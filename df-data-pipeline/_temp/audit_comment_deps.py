# -*- coding: utf-8 -*-
"""统计 harness 里有多少锚点/断言依赖“注释文本”。"""
import os, re, sys

HERE = r'D:\workspace\DungeonsForever\_temp'
FILES = ['df_dungeon_check.py', 'mk_df_check.py', 'df_mut_check.py', 'df_check_new_muts.py',
         'df_mut_probe.py']

def lines(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read().split('\n')

print('=' * 80)
print('① harness 里把“注释行”当代码切片锚的 index(...) 调用')
print('=' * 80)
total_anchor = 0
for fn in FILES:
    p = os.path.join(HERE, fn)
    if not os.path.exists(p):
        continue
    hits = []
    for i, ln in enumerate(lines(p), 1):
        # index('-------------------- xxx --------------------')  / index('-- ====')
        for m in re.finditer(r"\.index\(\s*['\"]([^'\"]*)['\"]", ln):
            arg = m.group(1)
            if arg.startswith('--') or arg.startswith('----'):
                hits.append((i, arg[:70]))
    if hits:
        print('\n### %s : %d 处' % (fn, len(hits)))
        for i, a in hits:
            print('   L%-6d %s' % (i, a))
        total_anchor += len(hits)
print('\n>>> 依赖注释切片锚合计：%d 处' % total_anchor)

print()
print('=' * 80)
print('② 断言字符串里含 “--” 的（可能是注释锚）')
print('=' * 80)
for fn in ['df_mut_check.py']:
    p = os.path.join(HERE, fn)
    src = open(p, encoding='utf-8', errors='replace').read()
    # MUTATIONS 里的 old 片段
    hits = re.findall(r"['\"]((?:[^'\"\\]|\\.)*--[^'\"\\]*)['\"]", src)
    cnt = 0
    for h in hits:
        if h.strip().startswith('#'):
            continue
        if '--' in h and not h.strip().startswith('"""'):
            cnt += 1
            if cnt <= 25:
                print('   %s' % h[:100])
    print('   ... 共 %d 条含 -- 的字符串' % cnt)
