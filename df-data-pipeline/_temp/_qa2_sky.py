# -*- coding: utf-8 -*-
"""QA(严过关) 独立扫描：Skyborne 统一正确性。不依赖工程师脚本。"""
import io, os, re, glob, sys, json

DF = r'D:\workspace\DungeonsForever'
BETA = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'

OLD = ['天空裔', '天裔族', '天空之民', '天空之城', '天空行者', '天翔族', '空中族',
       '空中精灵', '驭风者', '驭空', '天生族', '掠风天空裔', '尊主天空裔',
       '高空天行者', '天空之裔', '天空之灵']
STD = ['高阶天裔', '掠风天裔', '联盟天裔', '天裔精灵', '天裔']

def texts(path):
    if not os.path.exists(path):
        return None
    return io.open(path, encoding='utf-8', errors='replace').read()

def scan_set(files, label):
    print('=' * 78)
    print('[%s] 文件数=%d' % (label, len(files)))
    agg_old = {w: 0 for w in OLD}
    agg_std = {w: 0 for w in STD}
    per_file_old = {}
    for f in files:
        t = texts(f)
        if t is None:
            print('  MISSING', f); continue
        for w in OLD:
            c = t.count(w)
            if c:
                agg_old[w] += c
                per_file_old.setdefault(os.path.relpath(f, DF), {})[w] = c
        for w in STD:
            agg_std[w] += t.count(w)
    print('  -- 旧写法残留 --')
    for w in OLD:
        print('    %-12s = %d' % (w, agg_old[w]))
    tot = sum(agg_old.values())
    print('  >>> 旧写法合计 = %d' % tot)
    print('  -- 规范名分布 --')
    for w in STD:
        print('    %-12s = %d' % (w, agg_std[w]))
    print('  -- 命中文件明细 --')
    for k in sorted(per_file_old):
        print('    %s : %s' % (k, per_file_old[k]))
    return tot, agg_std

# 1) 译文源 JSON
js = sorted(glob.glob(os.path.join(DF, '_temp', '_cg_trans', '*.json')))
t1, s1 = scan_set(js, 'JSON 译文源 _cg_trans/*.json')

# 2) Lua 产物（源码侧）
lua = [os.path.join(DF, 'Core', 'Data', 'Data_ClassGuide.lua'),
       os.path.join(DF, 'Core', 'Data', 'zhTW', 'Data_ClassGuide.lua'),
       os.path.join(DF, 'Core', 'Data', 'enUS', 'Data_ClassGuide.lua')]
t2, s2 = scan_set(lua, 'Lua 产物 源码侧 ClassGuide 三件套')

# 3) Lua 产物（实机侧）
lua_b = [os.path.join(BETA, 'Core', 'Data', 'Data_ClassGuide.lua'),
         os.path.join(BETA, 'Core', 'Data', 'zhTW', 'Data_ClassGuide.lua'),
         os.path.join(BETA, 'Core', 'Data', 'enUS', 'Data_ClassGuide.lua')]
t3, s3 = scan_set(lua_b, 'Lua 产物 实机侧 ClassGuide 三件套')

# 4) 全库其它 Lua（Data_* 全部） — 看是否别处也有 Skyborne
alllua = []
for dp, _, fn in os.walk(os.path.join(DF, 'Core')):
    for f in fn:
        if f.endswith('.lua'):
            alllua.append(os.path.join(dp, f))
for dp, _, fn in os.walk(os.path.join(DF, 'Locales')):
    for f in fn:
        if f.endswith('.lua'):
            alllua.append(os.path.join(dp, f))
# 去掉 ClassGuide 三件套（已在上面）
cg = set(os.path.abspath(x) for x in lua)
alllua = [x for x in alllua if os.path.abspath(x) not in cg]
t4, s4 = scan_set(alllua, '全库其余 Lua')

# 5) 拉丁 Skyborne 在中文产物里
print('=' * 78)
print('[拉丁 Skyborne 残留] 中文产物中不应出现裸 Skyborne')
for f in [os.path.join(DF, 'Core', 'Data', 'Data_ClassGuide.lua'),
          os.path.join(DF, 'Core', 'Data', 'zhTW', 'Data_ClassGuide.lua')]:
    t = texts(f) or ''
    print('  %-50s bare Skyborne=%d' % (os.path.relpath(f, DF), len(re.findall(r'(?<![A-Za-z])Skyborne(?![A-Za-z])', t))))
