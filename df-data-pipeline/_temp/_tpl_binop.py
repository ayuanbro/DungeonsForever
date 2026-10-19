# -*- coding: utf-8 -*-
"""只读：找 append('-- ...' % x) 这类 BinOp 形态的注释模板，并判定「整行都是注释」还是「代码+尾注释」。"""
import ast, os, re
exec(open('_temp/_tpl_dump.py',encoding='utf-8').read().split('seen=set()')[0])
def lit_probe(n):
    """取表达式里的字面量文本（Constant / BinOp-Mod 左 / JoinedStr 常量段）。"""
    if isinstance(n,ast.Constant) and isinstance(n.value,str): return n.value,'Constant'
    if isinstance(n,ast.BinOp) and isinstance(n.op,ast.Mod) and isinstance(n.left,ast.Constant) \
       and isinstance(n.left.value,str): return n.left.value,'BinOpMod'
    if isinstance(n,ast.JoinedStr):
        s=''.join(v.value for v in n.values if isinstance(v,ast.Constant) and isinstance(v.value,str))
        return s,'JoinedStr'
    return None,type(n).__name__
seen=set()
for b in LIVE:
    p='_temp/'+b
    if not os.path.exists(p) or b in seen: continue
    seen.add(b)
    try: tree=ast.parse(open(p,encoding='utf-8',errors='replace').read())
    except SyntaxError: continue
    for node in ast.walk(tree):
        if not (isinstance(node,ast.Expr) and isinstance(node.value,ast.Call)): continue
        f=node.value.func
        fn=f.attr if isinstance(f,ast.Attribute) else (f.id if isinstance(f,ast.Name) else '')
        if fn not in APPEND_FUNCS: continue
        for a in node.value.args:
            probe,kind=lit_probe(a)
            if probe is None: continue
            if '--' not in probe: continue
            if isinstance(a,ast.Constant): continue     # Constant 已由主工具覆盖
            first=[l for l in probe.split('\n') if l.strip()]
            pure = bool(first) and all(l.strip().startswith('--') for l in first)
            print(f"  {b:<24} 行{a.lineno:5d} {kind:<10} 纯注释={pure}  {probe.strip()[:80]!r}")
