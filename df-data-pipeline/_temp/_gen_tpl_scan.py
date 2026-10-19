# -*- coding: utf-8 -*-
"""扫描生成器里「写进 lua 的注释模板」候选点（只读，不改）。

候选判定：
  · Assign 到白名单名字（HEAD / HEADER / head / HEAD_COMMON / GUARD / BANNER /
    HEAD_* / TXT 等）的字符串常量 —— 含隐式拼接（AST 里是单个 Constant）。
  · Expr 语句形如 X.append('...') / A('...')，字符串首行以 -- 开头。
  · HEAD = [...] 列表字面量里的字符串元素。
  · 字典字面量里的字符串值。
输出：逐点列 文件:行数 名字 过滤前后行数 样例。
"""
import ast
import glob
import os
import re
import sys

NAMES = re.compile(r'^(HEAD|HEADER|HEAD_COMMON|HEAD_[A-Z_]+|HEADER_[A-Z_]+|GUARD|BANNER|TXT|txt|head|banner)$')
APPEND_FUNCS = ('append', 'A', 'Ap', 'add', 'write_line')


def is_comment_block(s):
    lines = [l for l in s.split('\n') if l.strip()]
    return bool(lines) and all(l.strip().startswith('--') for l in lines)


def filter_comments(s):
    """逐行删掉以 -- 开头的行（保行尾风格近似）。"""
    out = []
    for l in s.split('\n'):
        if l.strip().startswith('--'):
            continue
        out.append(l)
    # 压掉因删除产生的连续空行，并去掉头部空行
    res, pending = [], 0
    for l in out:
        if l.strip() == '':
            pending += 1
            continue
        if pending and res:
            res.append('')
        pending = 0
        res.append(l)
    return '\n'.join(res)


def walk_strs(node):
    """产出 (name, 字符串节点, 值) —— 覆盖 Constant / List / Dict。"""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        yield node
    elif isinstance(node, ast.List):
        for e in node.elts:
            if isinstance(e, ast.Constant) and isinstance(e.value, str):
                yield e
    elif isinstance(node, ast.Dict):
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                yield v
            elif isinstance(v, ast.List):
                for e in v.elts:
                    if isinstance(e, ast.Constant) and isinstance(e.value, str):
                        yield e


def main():
    files = [p for p in sorted(glob.glob('_temp/*.py'))
             if not os.path.basename(p).startswith('_bak') and 'bak' not in os.path.basename(p)]
    only = sys.argv[1:] or None
    if only:
        files = [p for p in files if any(o in p for o in only)]
    grand = 0
    for p in files:
        try:
            src = open(p, encoding='utf-8', errors='replace').read()
            tree = ast.parse(src)
        except SyntaxError as e:
            print('  !! 解析失败', p, e)
            continue
        hits = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                names = [t.id for t in node.targets if isinstance(t, ast.Name)]
                if not any(NAMES.match(n) for n in names):
                    continue
                for c in walk_strs(node.value):
                    if '--' in c.value:
                        hits.append((c.lineno, ','.join(names), c.value))
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                f = node.value.func
                fn = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else '')
                if fn not in APPEND_FUNCS:
                    continue
                for a in node.value.args:
                    if isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value.strip().startswith('--'):
                        hits.append((a.lineno, fn + '()', a.value))
        if not hits:
            continue
        print('=' * 84)
        print(p)
        for ln, nm, val in sorted(hits):
            n0 = len([x for x in val.split('\n') if x.strip()])
            n1 = len([x for x in filter_comments(val).split('\n') if x.strip()])
            kind = '纯注释' if is_comment_block(val) else ('混合' if n1 else '空')
            print(f'   行{ln:5d}  {nm:<12} {n0:3d}→{n1:3d} 行  [{kind}]  {val.strip().splitlines()[0][:60] if val.strip() else ""}')
            grand += 1
    print('=' * 84)
    print('候选点合计', grand)


if __name__ == '__main__':
    main()
