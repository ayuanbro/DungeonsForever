# -*- coding: utf-8 -*-
"""只读：列出活跃生成器注释模板里含 % 格式化占位的点（清空会崩，需单独处理）。"""
import ast, os, re
exec(open('_temp/_tpl_dump.py',encoding='utf-8').read().split('seen=set()')[0])
PH=re.compile(r'%[-+ #0-9.]*[sdifgxXeE%]')
seen=set()
for b in LIVE:
    p='_temp/'+b
    if not os.path.exists(p) or b in seen: continue
    seen.add(b)
    try: tree=ast.parse(open(p,encoding='utf-8',errors='replace').read())
    except SyntaxError: continue
    for node in ast.walk(tree):
        if isinstance(node,ast.Assign):
            names=[t.id for t in node.targets if isinstance(t,ast.Name)]
            if not any(NAMES.match(n) for n in names): continue
            for c in walk_strs(node.value):
                if '--' not in c.value: continue
                ph=PH.findall(c.value)
                if ph: print(f"  {b:<26} 行{c.lineno:5d} {','.join(names):<12} 占位{len(ph)} {ph[:8]}")
        elif isinstance(node,ast.Expr) and isinstance(node.value,ast.Call):
            f=node.value.func
            fn=f.attr if isinstance(f,ast.Attribute) else (f.id if isinstance(f,ast.Name) else '')
            if fn not in APPEND_FUNCS: continue
            for a in node.value.args:
                if isinstance(a,ast.Constant) and isinstance(a.value,str) and a.value.strip().startswith('--'):
                    ph=PH.findall(a.value)
                    if ph: print(f"  {b:<26} 行{a.lineno:5d} {fn+'()':<12} 占位{len(ph)} {ph[:8]}")
print("=== 以上为含占位点；再看这些常量在文件里的实际使用形态（是否 % 应用）===")
