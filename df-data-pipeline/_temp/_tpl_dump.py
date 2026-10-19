# -*- coding: utf-8 -*-
"""只读：把「活跃生成器」的注释模板候选点整段打印出来（含过滤后剩什么）。"""
import ast, os, re, sys

LIVE = ["explore_gen.py","fc_bis.py","fc_gen.py","fc_guide.py","fc_pins.py","fc_tier.py",
        "gen_area_map.py","gen_boss_model.py","gen_boss_pos.py","gen_boss_skills.py",
        "gen_class_combat.py","gen_crates_data.py","gen_dungeon_entry.py","gen_enus.py",
        "gen_enus_data.py","gen_faction_qm.py","gen_factions_data.py","gen_gear_rare.py",
        "gen_gear_scrape.py","gen_gear_vendors.py","gen_locales.py","gen_plunder_data.py",
        "gen_prof_trainers.py","gen_pvp_data.py","gen_pvp_honor.py","gen_raidsets.py",
        "gen_zhtw.py","gen_zhtw_data.py","sync_data.py","port_dungeonsforever.py",
        "_build_pets_src.py","_build_pets_src.py","lf_gen_presets.py"]
NAMES = re.compile(r'^(HEAD|HEADER|HEAD_COMMON|HEAD_[A-Z_]+|HEADER_[A-Z_]+|GUARD|BANNER|TXT|txt|head|banner)$')
APPEND_FUNCS = ('append','A','Ap','add','write_line')

def filter_comments(s):
    out=[l for l in s.split('\n') if not l.strip().startswith('--')]
    res=[];pending=0
    for l in out:
        if l.strip()=='':
            pending+=1;continue
        if pending and res: res.append('')
        pending=0;res.append(l)
    return '\n'.join(res)

def walk_strs(node):
    if isinstance(node,ast.Constant) and isinstance(node.value,str): yield node
    elif isinstance(node,ast.List):
        for e in node.elts:
            if isinstance(e,ast.Constant) and isinstance(e.value,str): yield e
    elif isinstance(node,ast.Dict):
        for v in node.values:
            if isinstance(v,ast.Constant) and isinstance(v.value,str): yield v
            elif isinstance(v,ast.List):
                for e in v.elts:
                    if isinstance(e,ast.Constant) and isinstance(e.value,str): yield e

seen=set()
for b in LIVE:
    p='_temp/'+b
    if not os.path.exists(p) or b in seen: continue
    seen.add(b)
    try:
        tree=ast.parse(open(p,encoding='utf-8',errors='replace').read())
    except SyntaxError as e:
        print('!! 解析失败',b,e);continue
    hits=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Assign):
            names=[t.id for t in node.targets if isinstance(t,ast.Name)]
            if not any(NAMES.match(n) for n in names): continue
            for c in walk_strs(node.value):
                if '--' in c.value: hits.append((c.lineno,','.join(names),c.value))
        elif isinstance(node,ast.Expr) and isinstance(node.value,ast.Call):
            f=node.value.func
            fn=f.attr if isinstance(f,ast.Attribute) else (f.id if isinstance(f,ast.Name) else '')
            if fn not in APPEND_FUNCS: continue
            for a in node.value.args:
                if isinstance(a,ast.Constant) and isinstance(a.value,str) and a.value.strip().startswith('--'):
                    hits.append((a.lineno,fn+'()',a.value))
    if not hits: continue
    print('#'*90); print('##',b)
    for ln,nm,val in sorted(hits):
        lines=[l for l in val.split('\n') if l.strip()]
        pure=bool(lines) and all(l.strip().startswith('--') for l in lines)
        clean=filter_comments(val)
        codelines=[l for l in clean.split('\n') if l.strip()]
        has_long = '[[' in val or ']]' in val
        print(f'  -- 行{ln} {nm} 行数{len(lines)} 纯注释={pure} 过滤后剩{len(codelines)}行 含[[]]={has_long}')
        if not pure:
            print('     [过滤后剩余内容]')
            for l in codelines: print('       |',l[:110])
