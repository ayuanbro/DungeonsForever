# -*- coding: utf-8 -*-
"""QA 独立：模糊搜所有可能的 Skyborne 旧写法/异体 + 天裔上下文。"""
import io, os, re, glob, json
DF = r'D:\workspace\DungeonsForever'
FILES = ([os.path.join(DF, 'Core', 'Data', 'Data_ClassGuide.lua'),
          os.path.join(DF, 'Core', 'Data', 'zhTW', 'Data_ClassGuide.lua')]
         + sorted(glob.glob(os.path.join(DF, '_temp', '_cg_trans', '*.json'))))
# 模糊：出现这些字根但不在规范名中的
ROOT = re.compile(r'[^\s"\\,{}\[\]]{0,3}(天空|空中|天翔|驭|翱|浮空|天裔)[^\s"\\,{}\[\]]{0,3}')
STD = ['高阶天裔', '掠风天裔', '联盟天裔', '天裔精灵', '天裔']
hit = {}
for f in FILES:
    t = io.open(f, encoding='utf-8', errors='replace').read()
    for m in ROOT.finditer(t):
        w = m.group(0)
        # 去掉纯规范名
        if any(w == s for s in STD):
            continue
        # 规范名内部的子串也跳过（如 "天裔精灵" 里的 "天裔"）
        hit.setdefault(w, set()).add(os.path.basename(f))
print('=== 模糊命中（字根 天空/空中/天翔/驭/翱/浮空/天裔 的邻接词，排除规范名）===')
for w in sorted(hit):
    print('   %-14s  in %s' % (w, sorted(hit[w])[:4]))

print()
print('=== 天裔 上下文（zh 产物，去重前 25 句）===')
t = io.open(os.path.join(DF, 'Core', 'Data', 'Data_ClassGuide.lua'), encoding='utf-8', errors='replace').read()
seen = set()
n = 0
for m in re.finditer(r'天裔', t):
    a = max(0, m.start() - 30); b = min(len(t), m.end() + 30)
    ctx = t[a:b].replace('\n', ' ')
    if ctx in seen: continue
    seen.add(ctx)
    print('   …%s…' % ctx)
    n += 1
    if n >= 25: break
