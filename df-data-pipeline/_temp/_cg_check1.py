import json, io, os
SKIP = {'p','tb','ul','good','bad','races','h4','tick','star','horde','alliance','side_alliance','side_horde'}
def is_cn(s): return isinstance(s, str) and any(ord(c) > 127 for c in s)
import re
def real_en(v):  # 判断是否「真·未翻译」（排除类型标记/纯占位符/元数据）
    return isinstance(v, str) and v.strip() and not is_cn(v) and v not in SKIP and not re.fullmatch(r'(\|s\d+\|)+', v.strip())
for key in ['druid_feral','druid_restoration','hunter_beast-mastery','hunter_marksmanship','hunter_survival']:
    p = '_cg_trans/%s.json' % key
    if not os.path.exists(p): print(key, 'MISSING'); continue
    d = json.load(io.open(p, encoding='utf-8')); en = []
    def scan(v, path):
        if real_en(v): en.append((path, v))
        elif isinstance(v, list):
            for i, x in enumerate(v): scan(x, path)
        elif isinstance(v, dict):
            for k, x in v.items():
                if k in ('side','mark','t','key'): continue
                scan(x, path)
    for s in d['sections']:
        for f in s['flow']: scan(f, s['key']+':'+f['t'])
    print(key, '残留真英文段:', len(en))
    for pp, v in en[:5]: print('   ', pp, '|', repr(v[:60]))
