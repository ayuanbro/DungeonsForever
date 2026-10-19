# -*- coding: utf-8 -*-
"""把 harness 里以“注释文本”作切片锚的 9 处替换成等效的代码锚。

背景：注释精简后，`src.index('-------------------- 构建 --------------------')` 这类
锚点会直接 ValueError（注释已不存在）。锚点必须钉在**代码**上，注释不能当结构标记。
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

REPS = [
    (b"src.index('-------------------- \xe6\x9e\x84\xe5\xbb\xba --------------------')",
     b"src.index('U.dungeonDetailScroll:SetVerticalScroll(0)')",
     '\u6784\u5efa\u6a2a\u5e45 -> U.dungeonDetailScroll:SetVerticalScroll(0)'),
    (b"profui.index('-------------------- \xe5\xb7\xa6\xe5\xaf\xbc\xe8\x88\xaa / \xe5\xad\x90\xe9\xa1\xb5\xe7\xad\xbe')",
     b"profui.index('local NAV_SKILL_SLUG = {')",
     '\u5de6\u5bfc\u822a\u6a2a\u5e45 -> local NAV_SKILL_SLUG = {'),
    (b"profui.index('-------------------- \xe5\x85\xa8\xe9\x83\xa8\xe4\xb8\x93\xe4\xb8\x9a\xe6\x80\xbb\xe8\xa7\x88\xef\xbc\x9a\xe4\xb8\x89\xe5\x88\x97\xe5\xaf\xbc\xe8\x88\xaa\xe5\xae\xab\xe6\xa0\xbc')",
     b"profui.index('local function ixCardSub(slug, p)')",
     '\u5168\u4e13\u4e1a\u603b\u89c8\u6a2a\u5e45 -> local function ixCardSub(slug, p)'),
    (b"src.index('-- \xe5\x93\x81\xe8\xb4\xa8\xe5\x8f\x96\xe5\x80\xbc\xef\xbc\x9a')",
     b"src.index('function DG.QualOf(id)')",
     '\u54c1\u8d28\u53d6\u503c\u6ce8\u8bb0 -> function DG.QualOf(id)'),
    (b"src.index('-- \xe7\x89\xa9\xe5\x93\x81\xe5\x90\x8d\xef\xbc\x9a')",
     b"src.index('function DG.ItemName(id)')",
     '\u7269\u54c1\u540d\u6ce8\u8bb0 -> function DG.ItemName(id)'),
    (b"src.index('-------------------- \xe5\x89\xaf\xe6\x9c\xac\xe4\xbb\xbb\xe5\x8a\xa1\xef\xbc\x9a\xe5\xae\xa2\xe6\x88\xb7\xe7\xab\xaf\xe5\x8f\x96\xe6\x95\xb0\xe5\x8f\xa3 --------------------')",
     b"src.index('function DG.QLFn(name)')",
     '\u526f\u672c\u4efb\u52a1\u53d6\u6570\u53e3\u6a2a\u5e45 -> function DG.QLFn(name)'),
]

for fn in ['df_dungeon_check.py', 'mk_df_check.py']:
    p = os.path.join(HERE, fn)
    raw = open(p, 'rb').read()
    print('===== %s =====' % fn)
    for old, new, label in REPS:
        c = raw.count(old)
        if c:
            raw = raw.replace(old, new)
            print('  x%d  %s' % (c, label))
    open(p, 'wb').write(raw)

# 复核：还有没有残留的注释锚
print()
for fn in ['df_dungeon_check.py', 'mk_df_check.py']:
    p = os.path.join(HERE, fn)
    raw = open(p, 'rb').read()
    left = [l for l in raw.split(b'\n') if b".index('--" in l or b".index('----" in l]
    print('%s 残留注释锚：%d 处' % (fn, len(left)))
    for l in left:
        print('   ', l.decode('utf-8', 'replace'))
