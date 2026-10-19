# -*- coding: utf-8 -*-
"""只读：找 head += '--...' 这类 AugAssign / Add 拼接的注释模板。"""
import ast, os
exec(open('_temp/_tpl_dump.py',encoding='utf-8').read().split('seen=set()')[0])
def walk_all_strs(n):
    if isinstance(n,ast.Constant) and isinstance(n.value,str): yield n
    elif isinstance(n,ast.BinOp) and isinstance(n.op,ast.Add):
        for x in (n.left,n.right): yield from walk_all_strs(x)
    elif isinstance(n,ast.JoinedStr):
        yield n
seen=set()
for b in LIVE:
    p='_temp/'+b
    if not os.path.exists(p) or b in seen: continue
    seen.add(b)
    try: tree=ast.parse(open(p,encoding='utf-8',errors='replace').read())
    except SyntaxError: continue
    for node in ast.walk(tree):
        if isinstance(node,ast.AugAssign):
            tgt=node.target.id if isinstance(node.target,ast.Name) else '?'
            if tgt not in ('head','HEAD','head_cn','head_en') and not NAMES.match(tgt): continue
            for c in walk_all_strs(node.value):
                if isinstance(c,ast.Constant) and isinstance(c.value,str) and '--' in c.value:
                    lines=[l for l in c.value.split('\n') if l.strip()]
                    pure=bool(lines) and all(l.strip().startswith('--') for l in lines)
                    print(f"  {b:<22} 行{c.lineno:5d} {tgt} += 行数{len(lines)} 纯注释={pure}  {c.value.strip().splitlines()[0][:70]!r}")
