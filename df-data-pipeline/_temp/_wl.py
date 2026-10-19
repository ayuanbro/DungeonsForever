# -*- coding: utf-8 -*-
"""只读：统计活跃生成器的「lua 落盘出口」数量与形态。"""
import ast, os, re
exec(open('_temp/_tpl_dump.py',encoding='utf-8').read().split('seen=set()')[0])
seen=set()
for b in LIVE:
    p='_temp/'+b
    if not os.path.exists(p) or b in seen: continue
    seen.add(b)
    src=open(p,encoding='utf-8',errors='replace').read()
    try: tree=ast.parse(src)
    except SyntaxError as e:
        print(f"  {b:<24} !! 解析失败 {e}"); continue
    lines=src.split('\n')
    funcs=[]
    for n in ast.walk(tree):
        if isinstance(n,(ast.FunctionDef,)):
            body=ast.get_source_segment(src,n) or ''
            if re.search(r"open\([^)]*['\"](w|wb)['\"]",body) or '.write(' in body:
                funcs.append(n.name)
    hits=[(i+1,l.strip()[:100]) for i,l in enumerate(lines)
          if re.search(r"open\([^)]*['\"]w", l) or re.search(r"\.write\(", l)]
    # 排除写非 lua 的（json/txt）
    lua=[h for h in hits if '.json' not in h[1] and '_probe' not in h[1]]
    print(f"  {b:<24} 出口{len(lua):2d}  函数{sorted(set(funcs))[:6]}")
    for n,l in lua: print(f"       {n:5d}| {l}")
